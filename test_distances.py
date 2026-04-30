#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests fuer die Distanzmatrix-Beschaffung (distances.py).

Testet:
  1. Validierung leerer Adressen
  2. Caching (Laden aus Cache, Speichern in Cache)
  3. Google Maps API - Erfolgsfall (gemockt)
  4. Google Maps API - Fehlerstatus (REQUEST_DENIED, etc.)
  5. Google Maps API - Element-Status nicht OK (keine Route)
  6. CSV laden - Matrix-Format
  7. CSV laden - Paarlisten-Format
  8. CSV laden - Unbekanntes Format (Fehler)
  9. Symmetrisierung der Matrix (maximum(dist, dist.T))
 10. Cache-Key-Stabilitaet (gleiche Adressen in verschiedener Schreibweise)
"""

from __future__ import annotations

import json
import sys
import tempfile
import traceback
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from spielplan_multi.distances import (
    _cache_key,
    _load_cache,
    _save_cache,
    calculate_distance_matrix,
    load_distances_from_file,
)

PASS = 'PASS'
FAIL = 'FAIL'
_results: list = []


def check(name: str, fn):
    try:
        detail = fn()
        print(f'  [{PASS}] {name}' + (f'  – {detail}' if detail else ''))
        _results.append((name, True, ''))
    except AssertionError as e:
        print(f'  [{FAIL}] {name}  – {e}')
        _results.append((name, False, str(e)))
    except Exception as e:
        tb = traceback.format_exc().strip().split('\n')[-1]
        print(f'  [{FAIL}] {name}  – EXCEPTION: {tb}')
        _results.append((name, False, f'Exception: {e}'))


# ── Hilfsfunktion: Fake-API-Response ─────────────────────────────────────────

def _make_element(km: int):
    return {'status': 'OK', 'distance': {'value': km * 1000}, 'duration': {'value': 3600}}


def _make_api_response(n: int, distances_row: list):
    """Erzeugt eine gueltige Distance-Matrix-API-Antwort fuer eine Zeile."""
    return {
        'status': 'OK',
        'rows': [{'elements': [_make_element(d) for d in distances_row]}],
    }


def _mock_session(n: int, dist_matrix: list):
    """Erstellt einen Mock-Session der pro get() die naechste Zeile liefert."""
    responses = []
    for i in range(n):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = _make_api_response(n, dist_matrix[i])
        responses.append(resp)
    session = MagicMock()
    session.get.side_effect = responses
    return session


# ── Tests ─────────────────────────────────────────────────────────────────────

def main():
    _results.clear()

    print('\n--- Test 1: Validierung leerer Adressen ---')

    def t1_empty_single():
        with tempfile.TemporaryDirectory() as td:
            mat = calculate_distance_matrix(
                ['Hamburg', '', 'Berlin'], 'KEY', Path(td) / 'c.json')
        assert mat is None, 'Leere Adresse sollte None zurueckgeben'
        return 'Leere Adresse korrekt abgefangen'
    check('Leere Adresse gibt None zurueck', t1_empty_single)

    def t1_whitespace_only():
        with tempfile.TemporaryDirectory() as td:
            mat = calculate_distance_matrix(
                ['Hamburg', '   ', 'Berlin'], 'KEY', Path(td) / 'c.json')
        assert mat is None
        return 'Nur-Whitespace-Adresse korrekt abgefangen'
    check('Nur-Whitespace-Adresse gibt None zurueck', t1_whitespace_only)

    def t1_all_empty():
        with tempfile.TemporaryDirectory() as td:
            mat = calculate_distance_matrix(
                ['', '', ''], 'KEY', Path(td) / 'c.json')
        assert mat is None
        return 'Alle leeren Adressen korrekt abgefangen'
    check('Alle leeren Adressen: None', t1_all_empty)

    print('\n--- Test 2: Cache ---')

    def t2_cache_speichern_laden():
        locs = ['Hamburg', 'Bremen', 'Berlin']
        n = len(locs)
        dist_mat = [[0, 120, 289], [120, 0, 390], [289, 390, 0]]
        k = _cache_key(locs)
        with tempfile.TemporaryDirectory() as td:
            cache_path = Path(td) / 'cache.json'
            _save_cache(cache_path, {k: dist_mat})
            mat = calculate_distance_matrix(locs, 'KEY', cache_path)
        assert mat is not None, 'Cache-Laden fehlgeschlagen'
        assert mat.shape == (n, n)
        assert mat[0, 1] == 120
        assert mat[1, 2] == 390
        assert np.all(np.diag(mat) == 0)
        return f'Cache {n}x{n} korrekt geladen'
    check('Distanzmatrix aus Cache laden', t2_cache_speichern_laden)

    def t2_cache_key_normalisierung():
        k1 = _cache_key(['Hamburg', 'Bremen', 'Berlin'])
        k2 = _cache_key(['  Hamburg  ', 'BREMEN', ' berlin '])
        assert k1 == k2, f'Cache-Keys ungleich: {k1} != {k2}'
        return 'Gleicher Key fuer verschiedene Schreibweisen'
    check('Cache-Key normalisiert Gross-/Kleinschreibung und Whitespace', t2_cache_key_normalisierung)

    def t2_leerer_cache():
        with tempfile.TemporaryDirectory() as td:
            cache = _load_cache(Path(td) / 'existiert_nicht.json')
        assert cache == {}
        return 'Leerer Cache korrekt'
    check('Nicht-vorhandener Cache gibt {} zurueck', t2_leerer_cache)

    print('\n--- Test 3: Google Maps API – Erfolgsfall ---')

    def t3_api_erfolg():
        locs = ['Hamburg', 'Bremen', 'Berlin']
        n = len(locs)
        dist_vals = [[0, 120, 289], [115, 0, 395], [292, 398, 0]]

        with tempfile.TemporaryDirectory() as td:
            cache_path = Path(td) / 'c.json'
            mock_sess = _mock_session(n, dist_vals)
            with patch('spielplan_multi.distances._build_session', return_value=mock_sess):
                mat = calculate_distance_matrix(locs, 'VALID_KEY', cache_path)

        assert mat is not None, 'API-Erfolg sollte Matrix liefern'
        assert mat.shape == (n, n)
        assert np.all(np.diag(mat) == 0), 'Diagonale sollte 0 sein'
        # Symmetrisierung: maximum(dist, dist.T)
        assert mat[0, 1] == mat[1, 0], 'Matrix sollte symmetrisch sein'
        assert mat[0, 1] == max(dist_vals[0][1], dist_vals[1][0])  # 120 vs 115 -> 120
        # Ergebnis im Cache gespeichert?
        with tempfile.TemporaryDirectory() as td2:
            cache_path2 = Path(td2) / 'c.json'
            _save_cache(cache_path2, {_cache_key(locs): mat.tolist()})
            mat2 = calculate_distance_matrix(locs, 'IGNORED', cache_path2)
        assert mat2 is not None
        assert np.array_equal(mat, mat2), 'Cache-Reload muss identisch sein'
        return f'{n}x{n}-Matrix, Sym={mat[0,1]}=max({dist_vals[0][1]},{dist_vals[1][0]})'
    check('API Erfolgsfall + Symmetrisierung + Cache-Schreiben', t3_api_erfolg)

    def t3_api_result_gecacht():
        locs = ['A', 'B', 'C']
        n = len(locs)
        dist_vals = [[0, 10, 20], [10, 0, 15], [20, 15, 0]]
        with tempfile.TemporaryDirectory() as td:
            cache_path = Path(td) / 'c.json'
            mock_sess = _mock_session(n, dist_vals)
            with patch('spielplan_multi.distances._build_session', return_value=mock_sess):
                mat1 = calculate_distance_matrix(locs, 'KEY', cache_path)
            # Zweiter Aufruf: kein API-Aufruf mehr (aus Cache)
            mock_sess2 = MagicMock()
            mock_sess2.get.side_effect = Exception('Sollte nicht aufgerufen werden')
            with patch('spielplan_multi.distances._build_session', return_value=mock_sess2):
                mat2 = calculate_distance_matrix(locs, 'KEY', cache_path)
        assert mat1 is not None and mat2 is not None
        assert np.array_equal(mat1, mat2)
        return 'Zweiter Aufruf nutzt Cache ohne API-Request'
    check('Zweiter Aufruf verwendet Cache (kein API-Request)', t3_api_result_gecacht)

    print('\n--- Test 4: Google Maps API – Fehlerfaelle ---')

    def t4_api_status_fehler():
        locs = ['Hamburg', 'Bremen']
        error_resp = MagicMock()
        error_resp.raise_for_status = MagicMock()
        error_resp.json.return_value = {
            'status': 'REQUEST_DENIED',
            'error_message': 'API key not valid.',
        }
        session = MagicMock()
        session.get.return_value = error_resp
        with tempfile.TemporaryDirectory() as td:
            with patch('spielplan_multi.distances._build_session', return_value=session):
                mat = calculate_distance_matrix(locs, 'WRONG_KEY', Path(td) / 'c.json')
        assert mat is None, 'Fehler-API-Status sollte None zurueckgeben'
        return 'REQUEST_DENIED korrekt als None zurueckgegeben'
    check('API REQUEST_DENIED -> None', t4_api_status_fehler)

    def t4_element_no_route():
        locs = ['Hamburg', 'Bremen', 'Insel_X']
        n = len(locs)
        # Insel_X ist nicht erreichbar -> ZERO_RESULTS fuer manche Routen
        dist_row0 = [{'status': 'OK', 'distance': {'value': 0}, 'duration': {}},
                     {'status': 'OK', 'distance': {'value': 120000}, 'duration': {}},
                     {'status': 'ZERO_RESULTS'}]
        dist_row1 = [{'status': 'OK', 'distance': {'value': 120000}, 'duration': {}},
                     {'status': 'OK', 'distance': {'value': 0}, 'duration': {}},
                     {'status': 'ZERO_RESULTS'}]
        dist_row2 = [{'status': 'ZERO_RESULTS'},
                     {'status': 'ZERO_RESULTS'},
                     {'status': 'OK', 'distance': {'value': 0}, 'duration': {}}]

        responses = []
        for row in [dist_row0, dist_row1, dist_row2]:
            resp = MagicMock()
            resp.raise_for_status = MagicMock()
            resp.json.return_value = {'status': 'OK', 'rows': [{'elements': row}]}
            responses.append(resp)
        session = MagicMock()
        session.get.side_effect = responses

        from spielplan_multi.config import UNREACHABLE_KM
        import sys as _sys
        with tempfile.TemporaryDirectory() as td:
            # stdin.isatty() auf False mocken -> kein interaktiver Prompt
            mock_stdin = MagicMock()
            mock_stdin.isatty.return_value = False
            with patch.object(_sys, 'stdin', mock_stdin), \
                 patch('spielplan_multi.distances._build_session', return_value=session):
                mat = calculate_distance_matrix(locs, 'KEY', Path(td) / 'c.json')
        assert mat is not None, 'Matrix mit ZERO_RESULTS sollte trotzdem zurueckkommen'
        assert mat[0, 2] == UNREACHABLE_KM
        assert mat[0, 1] == 120
        return f'ZERO_RESULTS -> UNREACHABLE_KM={UNREACHABLE_KM}, erreichbar=120km'
    check('Element ZERO_RESULTS -> UNREACHABLE_KM, Rest korrekt', t4_element_no_route)

    def t4_netzwerkfehler():
        locs = ['Hamburg', 'Bremen']
        session = MagicMock()
        session.get.side_effect = Exception('Connection error')
        with tempfile.TemporaryDirectory() as td:
            with patch('spielplan_multi.distances._build_session', return_value=session):
                mat = calculate_distance_matrix(locs, 'KEY', Path(td) / 'c.json')
        assert mat is None
        return 'Netzwerkfehler korrekt als None zurueckgegeben'
    check('Netzwerkfehler -> None', t4_netzwerkfehler)

    print('\n--- Test 5: CSV/Excel laden ---')

    def t5_matrix_format_csv():
        import csv, io as _io
        teams = ['Hamburg', 'Bremen', 'Berlin']
        dist_vals = [[0, 120, 289], [120, 0, 395], [289, 395, 0]]
        # CSV schreiben
        buf = _io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([''] + teams)
        for i, team in enumerate(teams):
            writer.writerow([team] + dist_vals[i])

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                          delete=False, encoding='utf-8') as f:
            f.write(buf.getvalue())
            tmp_path = f.name

        mat = load_distances_from_file(tmp_path, teams)
        Path(tmp_path).unlink(missing_ok=True)

        assert mat is not None, 'Matrix-CSV sollte geladen werden'
        assert mat.shape == (3, 3)
        assert mat[0, 1] == 120
        assert mat[1, 2] == 395
        assert np.all(np.diag(mat) == 0)
        return f'3x3-Matrix korrekt aus CSV geladen'
    check('CSV Matrix-Format laden', t5_matrix_format_csv)

    def t5_paarliste_format_csv():
        import csv, io as _io
        teams = ['Hamburg', 'Bremen', 'Berlin']
        pairs = [('Hamburg', 'Bremen', 120), ('Hamburg', 'Berlin', 289),
                 ('Bremen', 'Berlin', 395)]
        buf = _io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['von', 'nach', 'km'])
        for a, b, km in pairs:
            writer.writerow([a, b, km])

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                          delete=False, encoding='utf-8') as f:
            f.write(buf.getvalue())
            tmp_path = f.name

        mat = load_distances_from_file(tmp_path, teams)
        Path(tmp_path).unlink(missing_ok=True)

        assert mat is not None
        assert mat[0, 1] == mat[1, 0] == 120  # symmetrisch
        assert mat[0, 2] == mat[2, 0] == 289
        assert mat[1, 2] == mat[2, 1] == 395
        return '3 Paare symmetrisch geladen'
    check('CSV Paarlisten-Format (von/nach/km) laden', t5_paarliste_format_csv)

    def t5_paarliste_englisch():
        import csv, io as _io
        teams = ['TeamA', 'TeamB']
        buf = _io.StringIO()
        csv.writer(buf).writerows([['from', 'to', 'km'], ['TeamA', 'TeamB', 55]])
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                          delete=False, encoding='utf-8') as f:
            f.write(buf.getvalue())
            tmp_path = f.name
        mat = load_distances_from_file(tmp_path, ['TeamA', 'TeamB'])
        Path(tmp_path).unlink(missing_ok=True)
        assert mat is not None
        assert mat[0, 1] == mat[1, 0] == 55
        return 'Englische Spaltenbezeichner (from/to/km) erkannt'
    check('CSV Paarliste mit from/to/km-Spalten', t5_paarliste_englisch)

    def t5_unbekanntes_format():
        import csv, io as _io
        buf = _io.StringIO()
        csv.writer(buf).writerow(['Spalte1', 'Spalte2', 'Spalte3'])
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv',
                                          delete=False, encoding='utf-8') as f:
            f.write(buf.getvalue())
            tmp_path = f.name
        mat = load_distances_from_file(tmp_path, ['A', 'B'])
        Path(tmp_path).unlink(missing_ok=True)
        assert mat is None, 'Unbekanntes Format sollte None zurueckgeben'
        return 'Unbekanntes Format korrekt als None'
    check('CSV unbekanntes Format -> None', t5_unbekanntes_format)

    def t5_excel_matrix():
        import openpyxl
        teams = ['Koeln', 'Dortmund', 'Frankfurt']
        dist_vals = [[0, 90, 185], [90, 0, 220], [185, 220, 0]]
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append([''] + teams)
        for i, team in enumerate(teams):
            ws.append([team] + dist_vals[i])
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            tmp_path = f.name
        wb.save(tmp_path)
        mat = load_distances_from_file(tmp_path, teams)
        Path(tmp_path).unlink(missing_ok=True)
        assert mat is not None
        assert mat[0, 1] == 90
        assert mat[1, 2] == 220
        return '3x3 Excel-Matrix korrekt geladen'
    check('Excel Matrix-Format laden', t5_excel_matrix)

    print('\n--- Test 6: Symmetrisierung ---')

    def t6_symmetrisierung():
        locs = ['A', 'B', 'C']
        n = len(locs)
        # Asymmetrische Rohdaten (Einbahnstrassen o.ae.)
        dist_vals = [[0, 100, 200], [90, 0, 150], [210, 140, 0]]
        with tempfile.TemporaryDirectory() as td:
            mock_sess = _mock_session(n, dist_vals)
            with patch('spielplan_multi.distances._build_session', return_value=mock_sess):
                mat = calculate_distance_matrix(locs, 'K', Path(td) / 'c.json')
        assert mat is not None
        # Symmetrisierung: max(dist[i,j], dist[j,i])
        assert mat[0, 1] == mat[1, 0] == 100  # max(100, 90) = 100
        assert mat[0, 2] == mat[2, 0] == 210  # max(200, 210) = 210
        assert mat[1, 2] == mat[2, 1] == 150  # max(150, 140) = 150
        return 'Asymmetrische Matrix korrekt symmetrisiert (maximum)'
    check('Symmetrisierung via maximum(dist, dist.T)', t6_symmetrisierung)

    # =========================================================================
    # ZUSAMMENFASSUNG
    # =========================================================================
    print('\n' + '=' * 70)
    print('ZUSAMMENFASSUNG')
    print('=' * 70)
    passed = sum(1 for _, ok, _ in _results if ok)
    total  = len(_results)
    for name, ok, msg in _results:
        sym = '+' if ok else 'x'
        print(f'  {sym}  {name}' + (f'  -> {msg}' if msg else ''))
    print(f'\n  {passed}/{total} Tests bestanden\n')
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
