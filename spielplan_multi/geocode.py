"""Adress-Geocoding via OpenStreetMap Nominatim mit lokalem Cache.

Nominatim ist gratis aber rate-limited (1 Request/Sekunde).
Cache liegt in .cache/geocodes.json — Adresse -> (lat, lon).

Verwendung:
    from spielplan_multi.geocode import geocode_addresses
    coords = geocode_addresses(['Musterstr. 1, 12345 Berlin', ...])
    # coords[addr] = (lat, lon) oder None bei Fehler
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests


_CACHE_DIR = Path(__file__).resolve().parent.parent / '.cache'
_CACHE_FILE = _CACHE_DIR / 'geocodes.json'

# Nominatim verlangt einen UA-Header mit Kontakt-Info
_USER_AGENT = 'spielplan-optimierer/1.9 (it@floorball.de)'
_NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
_RATE_LIMIT_SEC = 1.1  # leicht über 1.0 um sicher zu sein


def _load_cache() -> Dict[str, Optional[Tuple[float, float]]]:
    if not _CACHE_FILE.exists():
        return {}
    try:
        with open(_CACHE_FILE, encoding='utf-8') as f:
            raw = json.load(f)
        # Konvertiere [lat, lon]-Listen zurück zu Tuples (oder None)
        return {k: (tuple(v) if isinstance(v, list) else None) for k, v in raw.items()}
    except (OSError, ValueError):
        return {}


def _save_cache(cache: Dict[str, Optional[Tuple[float, float]]]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Tuples → Listen für JSON-Serialisierung
    serializable = {k: (list(v) if v else None) for k, v in cache.items()}
    try:
        with open(_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def _normalize(addr: str) -> str:
    return ' '.join(addr.strip().split()).lower()


def _query_nominatim(addr: str) -> Optional[Tuple[float, float]]:
    """Einzelner Nominatim-Lookup. Gibt None zurueck bei Fehler oder kein Treffer."""
    try:
        r = requests.get(
            _NOMINATIM_URL,
            params={'q': addr, 'format': 'json', 'limit': 1,
                    'addressdetails': 0, 'countrycodes': 'de,at,ch,nl,be,fr,lu,dk'},
            headers={'User-Agent': _USER_AGENT},
            timeout=10,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if not data:
            return None
        return float(data[0]['lat']), float(data[0]['lon'])
    except (requests.RequestException, ValueError, KeyError):
        return None


def geocode_addresses(addresses: List[str],
                      progress_callback=None
                      ) -> Dict[str, Optional[Tuple[float, float]]]:
    """Geocode eine Liste von Adressen mit Cache.

    Args:
        addresses: Adressen-Strings (Duplikate sind ok, werden dedupliziert).
        progress_callback: Optional `f(i, n, addr)` — wird vor jedem
            Nominatim-Request aufgerufen (nicht fuer Cache-Treffer).

    Returns:
        Dict {addr: (lat, lon) | None} — None heisst nicht gefunden.
        Identitaets-Map: jede Eingabe-Adresse ist im Result-Dict.
    """
    cache = _load_cache()
    result: Dict[str, Optional[Tuple[float, float]]] = {}

    # Deduplizieren — gleiche normalisierte Adresse nur einmal nachschlagen
    unique_addrs: Dict[str, str] = {}  # normalized -> original (erste Vorkommnis)
    for addr in addresses:
        if not addr:
            continue
        key = _normalize(addr)
        if key not in unique_addrs:
            unique_addrs[key] = addr

    # Cache-Treffer + neue Lookups einsammeln
    todo = []
    for norm_key, orig_addr in unique_addrs.items():
        if norm_key in cache:
            result[orig_addr] = cache[norm_key]
        else:
            todo.append((norm_key, orig_addr))

    # Rate-limited Nominatim-Lookups
    for i, (norm_key, orig_addr) in enumerate(todo):
        if progress_callback:
            try:
                progress_callback(i + 1, len(todo), orig_addr)
            except Exception:
                pass
        coord = _query_nominatim(orig_addr)
        cache[norm_key] = coord
        result[orig_addr] = coord
        # Cache nach jedem Request speichern — übersteht Crashes
        _save_cache(cache)
        # Rate-Limit nur zwischen Requests (nicht nach letztem)
        if i < len(todo) - 1:
            time.sleep(_RATE_LIMIT_SEC)

    # Identitaets-Map: alle Original-Adressen abdecken
    for addr in addresses:
        if not addr:
            continue
        if addr not in result:
            result[addr] = cache.get(_normalize(addr))

    return result


def clear_cache() -> None:
    """Loescht den Geocoding-Cache (testing/debugging)."""
    if _CACHE_FILE.exists():
        try:
            _CACHE_FILE.unlink()
        except OSError:
            pass
