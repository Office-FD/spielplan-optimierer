"""Laufzeit-Cache-Pfad für Optimierungs-Artefakte (Ergebnis-Pickle, Log, PID).

Bevorzugt einen lokalen, NICHT von OneDrive synchronisierten Ordner. Hintergrund:
Liegt der Cache im OneDrive-Verzeichnis, kann der Sync-Client Schreibzugriffe
sperren oder verzögern. In der Praxis (Mai 2026) führte das dazu, dass
`last_result.pkl` am Ende eines 11-Stunden-Laufs nicht geschrieben werden konnte
und der Lauf verloren ging. Worker und UI müssen denselben Pfad verwenden – daher
diese gemeinsame Hilfsfunktion, die von app.py UND _worker.py importiert wird.
"""
import os
from pathlib import Path


def run_cache_dir(base_dir=None) -> Path:
    """Verzeichnis für Optimierungs-Laufdateien (last_result.pkl / opt_log.txt / opt_pid.txt).

    Reihenfolge:
      1. %LOCALAPPDATA%\\Spielplan-Optimierer\\cache  (Windows, OneDrive-frei)
      2. <base_dir>/.cache  als Fallback
      3. ./  als letzter Ausweg
    Das zurückgegebene Verzeichnis existiert (wird bei Bedarf angelegt).
    """
    candidates = []
    local = os.environ.get('LOCALAPPDATA')
    if local:
        candidates.append(Path(local) / 'Spielplan-Optimierer' / 'cache')
    candidates.append(Path(base_dir or '.') / '.cache')
    for d in candidates:
        try:
            d.mkdir(parents=True, exist_ok=True)
            return d
        except Exception:
            continue
    return Path('.')
