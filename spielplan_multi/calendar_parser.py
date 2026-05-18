"""Rahmenterminplan-Excel parsen und Spieltag-Kalender je Liga erzeugen.

Das Spalten-Mapping (Liga-ID -> Spaltenindex) wird vom Aufrufer uebergeben.
Die KW-Spalte enthaelt entweder eine reine Zahl (z. B. 37) oder einen Text wie
"KW 37 07.09. - 13.09.2026" – beides wird unterstuetzt.

Zell-Logik:
  Einzelne Zahl "N"       -> Einzelspieltag N
  "N/M" oder "N & M"      -> Doppelspieltag-Paar (N, M)
  Alles andere            -> kein Spieltag (Pokal, NFC, etc.)
"""

from __future__ import annotations

import re
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .ui import ok, warn, err, step


def _parse_cell(val) -> List[int]:
    """Gibt Liste der Spieltag-Nummern zurueck oder [] wenn kein gueltiger Spieltag.

    Unterstuetzte Formate:
      "7"        -> Einzelspieltag
      "6/7"      -> Doppelspieltag (Slash-Schreibweise)
      "6 & 7"    -> Doppelspieltag (Ampersand-Schreibweise, z. B. Rahmenspielplan FLVD)
    """
    if val is None:
        return []
    if isinstance(val, float) and np.isnan(val):
        return []
    s = str(val).strip()
    # Einzelspieltag: reine Zahl
    if re.fullmatch(r'\d+', s):
        return [int(s)]
    # Doppelspieltag: Trennzeichen /, &, - jeweils mit optionalem Leerzeichen
    # Beispiele: "2/3"  "2 / 3"  "2&3"  "2 & 3"  "2-3"  "2 - 3"
    m = re.fullmatch(r'(\d+)\s*[-/&]\s*(\d+)', s)
    if m:
        d1, d2 = int(m.group(1)), int(m.group(2))
        return [min(d1, d2), max(d1, d2)]
    return []


def _to_date_str(cell) -> str:
    """Wandelt eine Zelle in einen Datumsstring um."""
    if cell is None:
        return ''
    if isinstance(cell, float) and np.isnan(cell):
        return ''
    if hasattr(cell, 'date'):
        return str(cell.date())
    return str(cell)


def _extract_kw(raw) -> Optional[int]:
    """Extrahiert KW-Nummer aus reinem int, float oder Text wie 'KW 37 07.09. - ...'."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)):
        return None
    try:
        return int(raw)
    except (ValueError, TypeError):
        pass
    m = re.search(r'\bKW\s*(\d+)\b', str(raw), re.IGNORECASE)
    return int(m.group(1)) if m else None


def preview_columns(path: str | Path, n_rows: int = 5) -> Optional[pd.DataFrame]:
    """Gibt die ersten n_rows Zeilen der Excel-Datei zurueck (fuer Spalten-Auswahl)."""
    path = Path(path)
    tmp_path = None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        tmp.close()
        tmp_path = Path(tmp.name)
        shutil.copy2(path, tmp_path)
        df = pd.read_excel(tmp_path, sheet_name=0, header=None, nrows=n_rows + 5)
        return df
    except Exception as exc:
        err(f'Vorschau nicht moeglich: {exc}')
        return None
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def parse_rahmenterminplan(path: str | Path,
                            col_mapping: Dict[str, int],
                            kw_col: int = 16,
                            date_from_col: int = 17,
                            date_to_col: int = 18) -> Optional[dict]:
    """Liest den Rahmenspielplan und gibt ein Dict zurueck.

    Args:
        path:        Pfad zur Excel-Datei
        col_mapping: {liga_id: spaltenindex (0-basiert)}
        kw_col:      Spaltenindex der KW-Nummer
        date_from_col: Spaltenindex Wochen-Start
        date_to_col:   Spaltenindex Wochen-Ende

    Gibt zurueck:
    {
      'spieltage': { liga_id: {spieltag_nr: {'kw', 'week_start', 'week_end'}} },
      'dst_blocks': { liga_id: [(d1,d2), ...] },
      'kw_compat':  { kw: {liga_id: [st_nrs]} },
    }
    """
    path = Path(path)
    step(f'Lese Rahmenterminplan: {path.name}')

    tmp_path = None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False)
        tmp.close()
        tmp_path = Path(tmp.name)
        shutil.copy2(path, tmp_path)
        df = pd.read_excel(tmp_path, sheet_name=0, header=None)
    except PermissionError:
        err(f'Zugriff verweigert: {path}')
        return None
    except FileNotFoundError:
        err(f'Datei nicht gefunden: {path}')
        return None
    except Exception as exc:
        err(f'Lesefehler: {exc}')
        return None
    finally:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

    liga_ids = list(col_mapping.keys())
    spieltage:  Dict[str, Dict[int, dict]]       = {lid: {} for lid in liga_ids}
    dst_blocks: Dict[str, List[Tuple[int, int]]] = {lid: [] for lid in liga_ids}
    kw_compat:  Dict[int, Dict[str, List[int]]]  = {}

    for _, row in df.iterrows():
        kw_raw = row.iloc[kw_col] if kw_col < len(row) else None
        kw = _extract_kw(kw_raw)
        if kw is None:
            continue

        # Datum-Von / -Bis: aus separaten Spalten oder aus KW-Text extrahieren
        if date_from_col < len(row) and date_from_col != kw_col:
            week_start = _to_date_str(row.iloc[date_from_col])
        else:
            # Versuche aus KW-Text zu extrahieren: "KW 37 07.09. - 13.09.2026"
            dm = re.search(r'(\d{2}\.\d{2}\.)\s*-\s*(\d{2}\.\d{2}\.\d{4})', str(kw_raw))
            if dm:
                end_year  = int(dm.group(2)[-4:])
                start_mon = int(dm.group(1).split('.')[1])
                end_mon   = int(dm.group(2).split('.')[1])
                start_year = end_year - 1 if start_mon > end_mon else end_year
                week_start = dm.group(1) + str(start_year)
            else:
                week_start = ''

        if date_to_col < len(row) and date_to_col != kw_col:
            week_end = _to_date_str(row.iloc[date_to_col])
        else:
            dm = re.search(r'(\d{2}\.\d{2}\.)\s*-\s*(\d{2}\.\d{2}\.\d{4})', str(kw_raw))
            week_end = dm.group(2) if dm else ''

        kw_entry: Dict[str, List[int]] = {}

        for lid, col in col_mapping.items():
            if col >= len(row):
                continue
            sts = _parse_cell(row.iloc[col])
            if not sts:
                continue

            for st in sts:
                spieltage[lid][st] = {
                    'kw':         kw,
                    'week_start': week_start,
                    'week_end':   week_end,
                }

            if len(sts) == 2:
                blk = (sts[0], sts[1])
                if blk not in dst_blocks[lid]:
                    dst_blocks[lid].append(blk)

            kw_entry[lid] = sts

        if kw_entry:
            if kw not in kw_compat:
                kw_compat[kw] = {}
            for lid, sts in kw_entry.items():
                kw_compat[kw].setdefault(lid, [])
                for st in sts:
                    if st not in kw_compat[kw][lid]:
                        kw_compat[kw][lid].append(st)

    for lid in liga_ids:
        n = len(spieltage[lid])
        if n == 0:
            warn(f'Keine Spieltage fuer {lid} gefunden – Spalte/Format pruefen.')
        else:
            ok(f'{lid}: {n} Spieltage erkannt, {len(dst_blocks[lid])} DST-Blocks')

    return {
        'spieltage':  spieltage,
        'dst_blocks': dst_blocks,
        'kw_compat':  kw_compat,
    }


def build_weekends(days: List[int], dst_blocks: List[Tuple[int, int]]) -> List[List[int]]:
    """Gruppiert Spieltage in Wochenend-Bloecke (DST = [d1,d2], sonst [d]).

    DST-Blöcke werden nur übernommen wenn BEIDE Spieltage in `days` enthalten sind.
    Blöcke mit Spieltagen außerhalb der gültigen Range (z. B. vom Rahmenplan einer
    größeren Liga) werden ignoriert – ohne diesen Filter entsteht ein KeyError im
    CP-SAT-Worker wenn homeW[ti, d] auf einen nicht existierenden Tag zugreift.
    """
    days_set = set(days)
    used = set()
    weekends = []
    for d1, d2 in dst_blocks:
        if d1 in days_set and d2 in days_set:
            weekends.append([d1, d2])
            used.update((d1, d2))
    for d in days:
        if d not in used:
            weekends.append([d])
    return sorted(weekends, key=lambda w: w[0])
