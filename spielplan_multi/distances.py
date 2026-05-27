"""Distanzmatrix-Beschaffung: Google Maps API, CSV/Excel-Datei oder manuelle Eingabe."""

import os
import re
import json
import time
import hashlib
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .ui import ok, warn, err, step, info, ask_yes_no
from .config import UNREACHABLE_KM


# ── Google Maps ───────────────────────────────────────────────────────────────

def get_api_key() -> Optional[str]:
    key = os.getenv('GOOGLE_MAPS_API_KEY', '').strip()
    if key:
        return key
    warn('GOOGLE_MAPS_API_KEY ist nicht gesetzt.')
    if sys.stdin.isatty():
        key = input('  Google Maps API Key eingeben (leer = Abbruch): ').strip()
        return key or None
    return None


def _cache_key(locations: List[str]) -> str:
    norm = [re.sub(r'\s+', ' ', loc.strip().lower()) for loc in locations]
    payload = json.dumps(norm, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def _load_cache(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _save_cache(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(path)


def _build_session():
    session = requests.Session()
    retry = Retry(
        total=5, connect=5, read=5,
        backoff_factor=0.6,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=['GET'],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://',  adapter)
    return session


def calculate_distance_matrix(locations: List[str],
                               api_key: str,
                               cache_path: Path) -> Optional[np.ndarray]:
    """Berechnet oder laedt eine Distanzmatrix per Google Maps API."""
    n = len(locations)

    # Validierung: leere oder nur-Whitespace-Adressen abfangen
    empty_idx = [i for i, loc in enumerate(locations) if not loc.strip()]
    if empty_idx:
        err(f'Leere Standort-Adressen an Position(en) {[i+1 for i in empty_idx]}. '
            f'Bitte alle Teamstandorte ausfuellen.')
        return None

    c = _load_cache(cache_path)
    k = _cache_key(locations)

    if k in c:
        try:
            arr = np.array(c[k], dtype=int)
            if arr.shape == (n, n) and np.all(np.diag(arr) == 0):
                ok('Distanzmatrix aus Cache geladen.')
                return arr
            warn('Cache invalide – berechne neu.')
        except Exception:
            warn('Cache nicht lesbar – berechne neu.')

    step('Berechne Distanzmatrix via Google Maps API ...')
    base    = 'https://maps.googleapis.com/maps/api/distancematrix/json'
    session = _build_session()
    dist    = np.zeros((n, n), dtype=int)

    for i in range(n):
        params = {
            'origins':      locations[i],
            'destinations': '|'.join(locations),
            'mode':         'driving',
            'units':        'metric',
            'key':          api_key,
        }
        try:
            r = session.get(base, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as exc:
            err(f'API-Fehler bei Origin {i+1}: {exc}')
            return None

        if data.get('status') != 'OK':
            err(f"API-Status: {data.get('error_message', data.get('status'))}")
            return None

        _rows = data.get('rows', [])
        elements = _rows[0].get('elements', []) if _rows else []
        if len(elements) != n:
            err('Antwortformat ungueltig.')
            return None

        for j, el in enumerate(elements):
            if el.get('status') == 'OK':
                try:
                    dist[i, j] = round(el['distance']['value'] / 1000)
                except (KeyError, TypeError):
                    warn(f'Unvollstaendige API-Antwort fuer {locations[i]} -> {locations[j]}, '
                         f'setze {UNREACHABLE_KM} km')
                    dist[i, j] = UNREACHABLE_KM
            else:
                warn(f'Keine Route {locations[i]} -> {locations[j]}, setze {UNREACHABLE_KM} km')
                dist[i, j] = UNREACHABLE_KM

        info(f'{i+1:2d}/{n} verarbeitet: {locations[i]}')
        time.sleep(0.15)

    # R8-C-L2: konservative Symmetrisierung — bei Einbahnstraßen oder
    # asymmetrischen Routen wird der längere Wert beider Richtungen genommen.
    # Das überschätzt km im Worst-Case leicht (~1 % bei FLVD-Routen), ist aber
    # für das Solver-Modell konsistent (eine Distanzangabe pro Paar).
    dist = np.maximum(dist, dist.T)

    unreachable = [(locations[i], locations[j])
                   for i in range(n) for j in range(n)
                   if i != j and dist[i, j] >= UNREACHABLE_KM]
    if unreachable:
        warn(f'{len(unreachable)} unerreichbare Routen erkannt.')
        for u in unreachable[:5]:
            warn(f'  -> {u[0]}  =>  {u[1]}')
        if sys.stdin.isatty() and not ask_yes_no('Trotzdem fortfahren?'):
            return None

    c[k] = dist.tolist()
    _save_cache(cache_path, c)
    ok('Distanzmatrix berechnet und gecacht.')
    return dist


# ── CSV / Excel-Datei ─────────────────────────────────────────────────────────

def load_distances_from_file(path: str, teams: List[str]) -> Optional[np.ndarray]:
    """Laedt eine Distanzmatrix aus einer CSV- oder Excel-Datei.

    Unterstuetzte Formate:
      1. Quadratische Matrix: erste Zeile = Header (Teamnamen),
         erste Spalte = Teamnamen, Rest = km-Werte.
      2. Paarliste: Spalten 'von', 'nach', 'km' (Reihenfolge egal).

    Gibt None bei Fehler zurueck.
    """
    import pandas as pd

    path = Path(path)
    step(f'Lade Distanzen aus {path.name} ...')

    try:
        if path.suffix.lower() in ('.xlsx', '.xls'):
            # ExcelFile als context manager → File-Handle wird sofort geschlossen.
            # Ohne `with` haelt pandas die Datei bis zur GC offen, was auf Windows
            # zu Datei-Lock-Problemen beim anschliessenden Loeschen fuehrt.
            with pd.ExcelFile(path) as xl:
                dist_sheet = next(
                    (s for s in xl.sheet_names if s.strip().lower() == 'distanzmatrix'),
                    None,
                )
                sheet = dist_sheet if dist_sheet else xl.sheet_names[0]
                df = xl.parse(sheet, header=0)
        else:
            df = pd.read_csv(path, sep=None, engine='python')
    except Exception as exc:
        err(f'Lesefehler: {exc}')
        return None

    n = len(teams)
    t_idx = {t.strip().lower(): i for i, t in enumerate(teams)}

    # Format 1: quadratische Matrix
    col_names = [str(c).strip().lower() for c in df.columns]
    col_map = {str(c).strip().lower(): str(c) for c in df.columns}
    _team_keys = [t.strip().lower() for t in teams]
    _matched = [t for t in _team_keys if t in col_names]
    _missing = [teams[i] for i, t in enumerate(_team_keys) if t not in col_names]
    # B-L8: 80%-Schwelle für "Format 1 erkannt, aber unvollstaendig"
    if _missing and len(_matched) >= max(1, int(0.8 * len(teams))):
        warn(f'Format 1 (Matrix) erkannt, aber Team(s) {_missing} nicht im Header gefunden – '
             f'pruefe Spaltenueberschriften.')
    if all(t.strip().lower() in col_names for t in teams):
        try:
            dist = np.full((n, n), UNREACHABLE_KM, dtype=int)
            np.fill_diagonal(dist, 0)
            for i, team_i in enumerate(teams):
                for j, team_j in enumerate(teams):
                    if i == j:
                        continue
                    col_key = col_map.get(team_j.strip().lower(), team_j.strip())
                    val = df.loc[df.iloc[:, 0].astype(str).str.strip().str.lower()
                                 == team_i.strip().lower(),
                                 col_key].values
                    if len(val) > 0:
                        _km = int(float(val[0]))
                        if _km < 0:
                            warn(f'Negative Distanz {_km} km für {team_i} → {team_j} – ignoriert.')
                        else:
                            dist[i, j] = _km
            dist = np.maximum(dist, dist.T)
            ok(f'Matrix-Format erkannt, {n}x{n} geladen.')
            return dist
        except Exception as exc:
            warn(f'Matrix-Format fehlgeschlagen ({exc}), versuche Paarliste ...')

    # Format 2: Paarliste mit Spalten von/nach/km (oder from/to/km)
    low_cols = {c.lower(): c for c in df.columns}
    from_col = low_cols.get('von') or low_cols.get('from')
    to_col   = low_cols.get('nach') or low_cols.get('to')
    km_col   = low_cols.get('km') or low_cols.get('distance') or low_cols.get('distanz')

    if from_col and to_col and km_col:
        dist = np.full((n, n), UNREACHABLE_KM, dtype=int)
        np.fill_diagonal(dist, 0)
        for _, row in df.iterrows():
            a = str(row[from_col]).strip().lower()
            b = str(row[to_col]).strip().lower()
            try:
                km = int(float(row[km_col]))
            except (ValueError, TypeError):
                continue
            if km < 0:
                warn(f'Negative Distanz {km} km für {row[from_col]} → {row[to_col]} – ignoriert.')
                continue
            ai = t_idx.get(a)
            bi = t_idx.get(b)
            if ai is not None and bi is not None:
                dist[ai, bi] = km
                dist[bi, ai] = km
        ok(f'Paarlisten-Format erkannt, {n}x{n} geladen.')
        return dist

    err('Dateiformat nicht erkannt. Benoetigt entweder quadratische Matrix oder '
        'Spalten "von"/"nach"/"km" (bzw. "from"/"to"/"km").')
    return None


# ── Manuelle Eingabe ──────────────────────────────────────────────────────────

def enter_distances_manually(teams: List[str]) -> np.ndarray:
    """Fragt den Benutzer nach allen paarweisen Distanzen."""
    n = len(teams)
    dist = np.zeros((n, n), dtype=int)

    info(f'Manuelle Eingabe fuer {n * (n - 1) // 2} Team-Paare.')
    info('Gib die Fahrtstrecke in km ein (ganze Zahlen).')

    for i in range(n):
        for j in range(i + 1, n):
            while True:
                raw = input(f'  {teams[i]}  <->  {teams[j]}  (km): ').strip()
                try:
                    km = int(raw)
                    if km < 0:
                        raise ValueError
                    dist[i, j] = dist[j, i] = km
                    break
                except ValueError:
                    err('Bitte eine positive ganze Zahl eingeben.')

    ok('Distanzmatrix manuell eingegeben.')
    return dist
