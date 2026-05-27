"""
Spielplan-Optimierer Launcher.
- Prueft GitHub auf Updates, installiert bei Bestaetigung
- Startet Streamlit-Server ohne sichtbares Fenster
- Oeffnet Browser sobald Server bereit ist
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import zipfile
from typing import Optional

GITHUB_REPO = "Office-FD/spielplan-optimierer"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
APP_ZIP_NAME = "app-files.zip"
PORT = 8501

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PYTHON_EXE = os.path.join(BASE_DIR, "python", "python.exe")
APP_PY = os.path.join(BASE_DIR, "app.py")
VERSION_FILE = os.path.join(BASE_DIR, "VERSION")

_MB_OK = 0x00
_MB_YESNO = 0x04
_MB_ICONINFO = 0x40
_MB_ICONERROR = 0x10
_IDYES = 6


def _msgbox(title: str, msg: str, flags: int = _MB_OK | _MB_ICONINFO) -> int:
    return ctypes.windll.user32.MessageBoxW(0, msg, title, flags)


def _parse_version(v: str) -> tuple:
    """Gibt ein Tupel aus ints zurueck, z.B. '1.10.0' -> (1, 10, 0).

    Pre-Release-Suffixe wie '-beta', '.rc1' werden abgetrennt:
    '1.3.0-beta' -> (1, 3, 0). Damit funktionieren Pre-Releases als
    "kleiner als" das nicht-pre-Release-Aequivalent.
    """
    try:
        core = v.strip().lstrip("v").split("-")[0].split("+")[0]
        parts = []
        for x in core.split("."):
            # Nur reine Integer-Teile akzeptieren; Suffix-Tags wie 'rc1' stoppen
            if x.isdigit():
                parts.append(int(x))
            else:
                break
        return tuple(parts) if parts else (0,)
    except Exception:
        return (0,)


def _get_local_version() -> str:
    try:
        with open(VERSION_FILE, encoding="utf-8") as f:
            return f.read().strip().lstrip("v")
    except OSError:
        return "0.0.0"


def _check_update():
    """Gibt (neue_version, download_url) oder (None, None) zurueck."""
    try:
        req = urllib.request.Request(
            GITHUB_API, headers={"User-Agent": "spielplan-launcher/1.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        latest = data.get("tag_name", "").lstrip("v")
        local = _get_local_version()
        if not latest:
            return None, None
        # CR4-L1: semantischer Versionsvergleich statt lexikografisch
        if _parse_version(latest) <= _parse_version(local):
            return None, None
        for asset in data.get("assets", []):
            if asset["name"] == APP_ZIP_NAME:
                return latest, asset["browser_download_url"]
        return None, None
    except Exception:
        return None, None


# Verzeichnisse die NICHT vom Update beruehrt werden:
# - python/        : embedded Python-Umgebung (im Installer fixed, nicht im app-files.zip)
# - Spielplaene/   : Nutzer-Daten
# - .cache/        : Distanz-Cache, last_result.pkl
_UPDATE_PROTECTED = {"python", "Spielplaene", ".cache"}


def _apply_update(url: str, new_version: str) -> bool:
    """Update atomar mit Backup/Rollback (F-M1).

    Ablauf:
      1. ZIP downloaden
      2. ZIP in tmp_extract entpacken (mit Path-Traversal-Guard)
      3. Aktuelle App-Dateien (ausser _UPDATE_PROTECTED) nach backup_dir bewegen
      4. Neue Dateien aus tmp_extract nach BASE_DIR bewegen
      5. VERSION-Datei schreiben
      6. Erfolg: backup_dir loeschen
      7. Failure (in Schritt 4-5): Rollback aus backup_dir
    """
    # CR4-L2: mkstemp statt mktemp (kein TOCTOU)
    tmp_fd, tmp_zip = tempfile.mkstemp(suffix=".zip")
    os.close(tmp_fd)
    tmp_extract = tempfile.mkdtemp(prefix="spielplan_extract_")
    backup_dir  = tempfile.mkdtemp(prefix="spielplan_backup_")
    backed_up   = []   # Liste der Items die ins Backup verschoben wurden

    try:
        urllib.request.urlretrieve(url, tmp_zip)

        # CR4-L3: erst vollstaendig in temporaeres Verzeichnis entpacken
        with zipfile.ZipFile(tmp_zip) as z:
            base_real = os.path.realpath(BASE_DIR)
            for member in z.namelist():
                if member.startswith("python/"):
                    continue
                # CR4-L4: Path-Traversal verhindern
                dest = os.path.realpath(os.path.join(BASE_DIR, member))
                if not dest.startswith(base_real + os.sep) and dest != base_real:
                    raise ValueError(f"ZIP-Eintrag außerhalb von BASE_DIR: {member}")
                z.extract(member, tmp_extract)

        # F-M1: Backup aller bestehenden App-Items (ausser PROTECTED) ins backup_dir.
        # Damit ist BASE_DIR jetzt sauber, der nachfolgende Move kann nicht durch
        # File-Locks scheitern.
        for item in os.listdir(BASE_DIR):
            if item in _UPDATE_PROTECTED or item == "VERSION":
                continue
            src = os.path.join(BASE_DIR, item)
            dst = os.path.join(backup_dir, item)
            shutil.move(src, dst)
            backed_up.append(item)

        # Neue Dateien aus tmp_extract nach BASE_DIR
        try:
            for root, _dirs, files in os.walk(tmp_extract):
                rel_root = os.path.relpath(root, tmp_extract)
                dest_root = (os.path.join(BASE_DIR, rel_root)
                             if rel_root != "." else BASE_DIR)
                os.makedirs(dest_root, exist_ok=True)
                for fname in files:
                    shutil.move(os.path.join(root, fname),
                                os.path.join(dest_root, fname))

            # VERSION-Datei erst NACH erfolgreichem Move schreiben
            with open(VERSION_FILE, "w", encoding="utf-8") as f:
                f.write(new_version + "\n")

            # Erfolg: Backup loeschen
            shutil.rmtree(backup_dir, ignore_errors=True)
            return True

        except Exception:
            # ROLLBACK: aktuelle (teilweise neue) Dateien entfernen, Backup zurueck
            for item in backed_up:
                target = os.path.join(BASE_DIR, item)
                if os.path.exists(target):
                    if os.path.isdir(target):
                        shutil.rmtree(target, ignore_errors=True)
                    else:
                        try:
                            os.unlink(target)
                        except OSError:
                            pass
                try:
                    shutil.move(os.path.join(backup_dir, item), target)
                except OSError:
                    pass  # Best-effort: bei kaputtem Backup, weiter
            raise

    except Exception as exc:
        _msgbox(
            "Spielplan-Optimierer – Update fehlgeschlagen",
            f"Das Update konnte nicht installiert werden:\n{exc}\n\n"
            "Das Programm startet mit der bisherigen Version.",
            _MB_OK | _MB_ICONERROR,
        )
        return False

    finally:
        try:
            os.unlink(tmp_zip)
        except OSError:
            pass
        try:
            shutil.rmtree(tmp_extract, ignore_errors=True)
        except OSError:
            pass
        try:
            shutil.rmtree(backup_dir, ignore_errors=True)
        except OSError:
            pass


def _server_ready() -> bool:
    try:
        urllib.request.urlopen(f"http://localhost:{PORT}", timeout=1)
        return True
    except Exception:
        return False


def _wait_for_server(timeout: int = 45) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _server_ready():
            return True
        time.sleep(0.5)
    return False


def _port_is_free() -> bool:
    """Prueft, ob Port PORT auf 127.0.0.1 bindbar ist.

    R8-G-M1: Auf Windows kann ein gerade beendeter Server-Socket noch 30-60 s
    im TIME_WAIT-State sein. Bind-Versuch ist verlaesslicher als _server_ready().
    """
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        # Ohne SO_REUSEADDR — Streamlit setzt das auch nicht.
        sock.bind(("127.0.0.1", PORT))
        return True
    except OSError:
        return False
    finally:
        try:
            sock.close()
        except OSError:
            pass


def _wait_for_port_free(timeout: int = 30) -> bool:
    """Wartet bis Port frei ist (TIME_WAIT abgeklungen). True wenn frei,
    False bei Timeout.

    R8-G-M1: Ersatz fuer ein blindes time.sleep(1) nach Server-terminate vor
    Neustart. Polling alle 0.5 s.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_is_free():
            return True
        time.sleep(0.5)
    return False


def _start_streamlit_server() -> Optional[subprocess.Popen]:
    """Startet den Streamlit-Subprocess; gibt das Process-Objekt zurueck."""
    CREATE_NO_WINDOW = 0x08000000
    return subprocess.Popen(
        [
            PYTHON_EXE,
            "-m", "streamlit", "run", APP_PY,
            "--server.headless=true",
            "--browser.gatherUsageStats=false",
            f"--server.port={PORT}",
        ],
        creationflags=CREATE_NO_WINDOW,
        cwd=BASE_DIR,
    )


def main():
    """Launcher-Hauptfunktion mit Background-Update-Check (F-L2).

    Reihenfolge:
      1. Update-Check in Background-Thread starten (blockiert NICHT den App-Start)
      2. Bestehender Server vorhanden? Wenn ja: Browser oeffnen und fertig
         (Update-Check laeuft fuer den naechsten Start)
      3. Sonst: Server starten, Update-Check parallel
      4. Server-Ready abwarten
      5. Wenn waehrend Server-Start ein Update gefunden wurde: Dialog,
         ggf. Server stoppen + Update + neu starten
      6. Browser oeffnen
    """
    update_result: dict = {}
    update_done = threading.Event()

    def _bg_check():
        try:
            ver, url = _check_update()
            if ver:
                update_result['version'] = ver
                update_result['url'] = url
        finally:
            update_done.set()

    # 1. Update-Check im Background (max. 5s timeout im _check_update)
    threading.Thread(target=_bg_check, daemon=True).start()

    # 2. Wenn Server schon laeuft: einfach Browser oeffnen.
    # Update wird beim naechsten Neustart angeboten (Update-Check laeuft trotzdem
    # weiter im Background, aber wir warten nicht darauf).
    if _server_ready():
        webbrowser.open(f"http://localhost:{PORT}")
        return

    # 3. Python-Installation pruefen
    if not os.path.isfile(PYTHON_EXE):
        _msgbox(
            "Spielplan-Optimierer – Fehler",
            f"Python-Installation nicht gefunden:\n{PYTHON_EXE}\n\n"
            "Bitte das Programm neu installieren.",
            _MB_OK | _MB_ICONERROR,
        )
        return

    # 4. Streamlit-Server SOFORT starten - parallel zum Update-Check
    server_proc = _start_streamlit_server()

    # 5. Auf Update-Check warten (max 5s — _check_update hat eigenes Timeout).
    # Falls Update gefunden → vor Server-Bereit-Wait fragen, damit der Nutzer
    # keinen unnoetigen Browser-Tab oeffnet.
    update_done.wait(timeout=5)

    if update_result.get('version'):
        new_version = update_result['version']
        dl_url      = update_result['url']
        result = _msgbox(
            "Spielplan-Optimierer – Update verfuegbar",
            f"Version {new_version} ist auf GitHub verfuegbar.\n\n"
            "Jetzt aktualisieren? (Empfohlen)\n\n"
            "Das Programm wird kurz beendet und neu gestartet.",
            _MB_YESNO | _MB_ICONINFO,
        )
        if result == _IDYES:
            # Server beenden, Update anwenden, neu starten
            try:
                server_proc.terminate()
                try:
                    server_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    server_proc.kill()
                    try:
                        server_proc.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
            except Exception:
                pass
            # R8-G-M1: Aktiv warten bis Port wieder bindbar ist (Windows-TIME_WAIT
            # kann 30-60 s dauern). Ersetzt blindes time.sleep(1).
            if not _wait_for_port_free(timeout=30):
                _msgbox(
                    "Spielplan-Optimierer – Update",
                    f"Der Port {PORT} ist nach 30 Sekunden noch belegt.\n\n"
                    "Update wird nicht installiert; bitte das Programm beenden\n"
                    "und in 1–2 Minuten erneut starten.",
                    _MB_OK | _MB_ICONERROR,
                )
                # Fallback: alten Server moeglichst weiter nutzen — versuche Restart.
                server_proc = _start_streamlit_server()
            else:
                if _apply_update(dl_url, new_version):
                    server_proc = _start_streamlit_server()
                # Bei Update-Fail laeuft die App mit der alten Version weiter
                # → neuen Server starten
                else:
                    server_proc = _start_streamlit_server()

    # 6. Warten bis Server bereit, dann Browser oeffnen
    # R8-G-L3: 120s statt 60s — auf aelteren Notebooks mit Antivirus oder
    # waehrend Windows-Updates kann ein Streamlit-Cold-Start 90+ s dauern.
    if _wait_for_server(timeout=120):
        webbrowser.open(f"http://localhost:{PORT}")
    else:
        _msgbox(
            "Spielplan-Optimierer – Fehler",
            "Der Server konnte nicht gestartet werden.\n\n"
            "Moegliche Ursachen:\n"
            "- Port 8501 ist blockiert\n"
            "- Fehlende App-Dateien (Neuinstallation empfohlen)\n\n"
            "Bei weiteren Problemen wenden Sie sich an den Administrator.",
            _MB_OK | _MB_ICONERROR,
        )


if __name__ == "__main__":
    main()
