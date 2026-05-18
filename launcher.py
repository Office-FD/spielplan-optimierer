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
import time
import urllib.error
import urllib.request
import webbrowser
import zipfile

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
    """Gibt ein Tupel aus ints zurück, z. B. '1.10.0' → (1, 10, 0)."""
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
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


def _apply_update(url: str, new_version: str) -> bool:
    # CR4-L2: NamedTemporaryFile statt mktemp (kein TOCTOU)
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".zip")
    os.close(tmp_fd)
    tmp_extract = tempfile.mkdtemp()
    try:
        urllib.request.urlretrieve(url, tmp_path)

        # CR4-L3: erst vollstaendig in temporaeres Verzeichnis entpacken
        with zipfile.ZipFile(tmp_path) as z:
            base_real = os.path.realpath(BASE_DIR)
            for member in z.namelist():
                if member.startswith("python/"):
                    continue
                # CR4-L4: Path-Traversal verhindern
                dest = os.path.realpath(os.path.join(BASE_DIR, member))
                if not dest.startswith(base_real + os.sep) and dest != base_real:
                    raise ValueError(f"ZIP-Eintrag außerhalb von BASE_DIR: {member}")
                z.extract(member, tmp_extract)

        # Alle extrahierten Dateien atomar nach BASE_DIR verschieben
        for root, dirs, files in os.walk(tmp_extract):
            rel_root = os.path.relpath(root, tmp_extract)
            dest_root = os.path.join(BASE_DIR, rel_root) if rel_root != "." else BASE_DIR
            os.makedirs(dest_root, exist_ok=True)
            for fname in files:
                src = os.path.join(root, fname)
                dst = os.path.join(dest_root, fname)
                shutil.move(src, dst)

        with open(VERSION_FILE, "w", encoding="utf-8") as f:
            f.write(new_version + "\n")
        return True
    except Exception as exc:
        _msgbox(
            "Spielplan-Optimierer – Update fehlgeschlagen",
            f"Das Update konnte nicht installiert werden:\n{exc}\n\n"
            "Das Programm startet trotzdem mit der aktuellen Version.",
            _MB_OK | _MB_ICONERROR,
        )
        return False
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        try:
            shutil.rmtree(tmp_extract, ignore_errors=True)
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


def main():
    updated = False

    # 1. Update pruefen (max. 5 Sekunden, Fehler werden ignoriert)
    new_version, dl_url = _check_update()
    if new_version:
        result = _msgbox(
            "Spielplan-Optimierer – Update verfuegbar",
            f"Version {new_version} ist auf GitHub verfuegbar.\n\n"
            "Jetzt aktualisieren? (Empfohlen)\n\n"
            "Das Programm startet danach automatisch.",
            _MB_YESNO | _MB_ICONINFO,
        )
        if result == _IDYES:
            updated = _apply_update(dl_url, new_version)

    # 2. Schon laufenden Server nutzen – aber NICHT nach einem Update (CR4-L5)
    if not updated and _server_ready():
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

    # 4. Streamlit-Server im Hintergrund starten (kein Fenster)
    CREATE_NO_WINDOW = 0x08000000
    subprocess.Popen(
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

    # 5. Warten bis Server bereit, dann Browser oeffnen
    if _wait_for_server(timeout=60):
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
