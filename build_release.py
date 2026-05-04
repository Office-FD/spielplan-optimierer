"""
Erstellt app-files.zip fuer GitHub Releases.
Enthaelt alle App-Dateien ohne Python-Umgebung, Cache oder Build-Artefakte.

Verwendung: python build_release.py
Ausgabe:    app-files.zip im Projektverzeichnis
"""
import os
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "app-files.zip")

EXCLUDE_DIRS = {
    ".venv", ".cache", "Spielplaene", "__pycache__",
    ".git", "installer", "memory", ".pytest_cache",
}
EXCLUDE_FILES = {
    "build_release.py",
    "create_release.bat",
    "create_overview_doc.py",
    "app-files.zip",
    "launcher.py",        # wird vom Bootstrap-Installer mitgeliefert
}
EXCLUDE_EXTS = {".pyc", ".pyo"}


def _should_include(rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    if parts[0] in EXCLUDE_DIRS or parts[0].startswith("."):
        return False
    if len(parts) > 1 and parts[1] in ("__pycache__",):
        return False
    if os.path.basename(rel_path) in EXCLUDE_FILES:
        return False
    if os.path.splitext(rel_path)[1].lower() in EXCLUDE_EXTS:
        return False
    return True


def main():
    version = "unbekannt"
    try:
        with open(os.path.join(HERE, "VERSION"), encoding="utf-8") as f:
            version = f.read().strip()
    except OSError:
        pass

    count = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, dirs, files in os.walk(HERE):
            dirs[:] = sorted(
                d for d in dirs
                if d not in EXCLUDE_DIRS and not d.startswith(".")
            )
            for fname in files:
                abs_path = os.path.join(root, fname)
                rel_path = os.path.relpath(abs_path, HERE)
                if _should_include(rel_path):
                    z.write(abs_path, rel_path)
                    count += 1

    size_mb = os.path.getsize(OUT) / 1024 / 1024
    print(f"app-files.zip erstellt: {count} Dateien, {size_mb:.1f} MB")
    print(f"Version: {version}")
    print(f"Pfad: {OUT}")


if __name__ == "__main__":
    main()
