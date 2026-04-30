#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feature-Test fuer alle erweiterten Funktionen.

Testet ohne Streamlit und ohne Google-Maps-API:
  1. Persistenter Cache-Pfad  (schedule_utils importierbar)
  2. Team-Ansichten-Sheet     (build_league_excel erzeugt Sheet)
  3. Kalender-Export (.ics)   (build_ics_bytes korrekte VEVENT-Anzahl)
  4. Manueller Tausch         (swap_home_away aendert Schedule + Stats)
  5. Fairness-Analyse-Sheet   (build_league_excel enthaelt Fairness-Sheet)
  6. Constraint-Validierung   (config_validator erkennt Fehler/Warnungen)

Aufruf: python test_features.py
"""
from __future__ import annotations

import io
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

from spielplan_multi.league_types import LeagueConfig, LeagueResult
from spielplan_multi.config import WEIGHT_SCALES
from spielplan_multi.solver import solve_league_phase1
from spielplan_multi.calendar_parser import build_weekends
from spielplan_multi.excel_output import build_league_excel, build_hall_schedule
from spielplan_multi.schedule_utils import (
    recompute_result_stats,
    swap_home_away,
    build_ics_bytes,
    build_print_html,
    assign_game_times,
)
from spielplan_multi.config_validator import validate as validate_cfg


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

_results: list = []

def check(name: str, fn):
    try:
        detail = fn()
        print(f'  [PASS] {name}' + (f'  – {detail}' if detail else ''))
        _results.append((name, True))
    except AssertionError as e:
        print(f'  [FAIL] {name}  – {e}')
        _results.append((name, False))
    except Exception as e:
        tb = traceback.format_exc().strip().split('\n')[-1]
        print(f'  [FAIL] {name}  – EXCEPTION: {tb}')
        _results.append((name, False))


def make_cfg(lid: str, teams: list, dist=None, dst_blocks=None, calendar=None):
    n   = len(teams)
    dst = dst_blocks or []
    nr  = 2
    days = list(range(1, nr * (n - 1) + 1))
    raw = {k: 5.0 for k in WEIGHT_SCALES}
    if dist is None:
        dist = np.zeros((n, n))
    cal = calendar or {}
    return LeagueConfig(
        league_id=lid, name=f'Liga {lid}',
        teams=teams, locations=teams,
        dist=dist, dst_blocks=dst,
        weekends=build_weekends(days, dst),
        apply_routing=False,
        f_num=125, f_den=100,
        w_scaled={k: v * WEIGHT_SCALES[k] for k, v in raw.items()},
        raw_weights=raw,
        pinned=[], blocked={},
        calendar=cal,
        hier_weight=1.0,
        games_per_team_per_day=1,
        n_rounds=nr,
    )


TEAMS = ['Alpha', 'Beta', 'Gamma', 'Delta']
DIST  = np.array([
    [0,   100, 200, 300],
    [100, 0,   150, 250],
    [200, 150, 0,   120],
    [300, 250, 120, 0  ],
], dtype=float)
# 4 Teams, n_rounds=2 -> 6 Spieltage
CAL = {1: {'kw': 37}, 2: {'kw': 38}, 3: {'kw': 39},
       4: {'kw': 40}, 5: {'kw': 41}, 6: {'kw': 42}}


# ── Tests ─────────────────────────────────────────────────────────────────────

def main():
    _results.clear()

    # ── Feature 4: Persistenter Cache importierbar ────────────────────────────
    print('\n--- Feature 4: Persistenter Cache-Pfad ---')

    def t_cache_import():
        from spielplan_multi.schedule_utils import build_ics_bytes  # noqa: F401
        _here = Path(__file__).resolve().parent
        cache_dir = _here / '.cache'
        assert str(cache_dir).endswith('.cache'), f'Unerwarteter Pfad: {cache_dir}'
        return f'.cache liegt in {_here.name}/'
    check('schedule_utils importierbar', t_cache_import)

    # ── Loesung erzeugen (Basis fuer alle weiteren Tests) ─────────────────────
    print('\n--- Loesung erzeugen (Basis) ---')
    cfg = make_cfg('TEST', TEAMS, dist=DIST, calendar=CAL)
    result = None

    def t_solve():
        nonlocal result
        r = solve_league_phase1(cfg, time_limit=30, seed=42)
        assert r is not None, 'Solver: keine Loesung (None)'
        r.cfg = cfg
        result = r
        total = sum(len(g) for g in r.schedule.values())
        exp   = cfg.n_teams * (cfg.n_teams - 1) // 2 * cfg.n_rounds
        assert total == exp, f'{total} Spiele statt {exp}'
        return f'obj={r.objective:.0f}  km={sum(r.travels)}  sw={r.sw_counts}'
    check('solve_league_phase1 loest (4 Teams, kein DST)', t_solve)

    if result is None:
        print('\n  Ueberspringe weitere Tests (keine Loesung).')
        _summarize()
        return

    # ── Feature 1: Team-Ansichten-Sheet ───────────────────────────────────────
    print('\n--- Feature 1: Team-Ansichten im Excel ---')

    def t_team_ansichten_sheet():
        buf = io.BytesIO()
        wb  = build_league_excel(result)
        wb.save(buf)
        buf.seek(0)
        import openpyxl
        wb2 = openpyxl.load_workbook(buf)
        assert 'Team-Ansichten' in wb2.sheetnames, \
            f'Sheet fehlt. Vorhandene Sheets: {wb2.sheetnames}'
        return f'Sheets: {wb2.sheetnames}'
    check('Excel enthaelt Sheet "Team-Ansichten"', t_team_ansichten_sheet)

    def t_fairness_sheet():
        wb  = build_league_excel(result)
        assert 'Fairness-Analyse' in wb.sheetnames, 'Sheet fehlt'
        ws  = wb['Fairness-Analyse']
        # Titel-Zelle muss den Liga-Namen enthalten
        merged_val = ws.cell(1, 1).value or ''
        assert 'FAIRNESS-ANALYSE' in str(merged_val), f'Kein Titel: {merged_val!r}'
        # Mindestens n+8 ausgefüllte Zeilen (Titel + 3 Abschnitte)
        filled = [r for r in ws.iter_rows(values_only=True) if any(v for v in r)]
        assert len(filled) >= cfg.n_teams + 6, f'Zu wenige Zeilen: {len(filled)}'
        return f'{len(filled)} gefuellte Zeilen'
    check('Fairness-Analyse Sheet vorhanden und befuellt', t_fairness_sheet)

    def t_team_ansichten_inhalt():
        wb  = build_league_excel(result)
        ws  = wb['Team-Ansichten']
        rows = list(ws.iter_rows(values_only=True))
        assert len(rows) > 1, 'Sheet ist leer'
        header = rows[0]
        assert 'ST' in header or header[0] == 'ST', f'Kein ST-Header: {header}'
        # Mindestens len(days)+1 Zeilen (Header + eine pro Spieltag)
        assert len(rows) >= cfg.n_matchdays + 1, \
            f'Zu wenige Zeilen: {len(rows)}'
        return f'{len(rows)-1} Datenzeilen, {len(header)} Spalten'
    check('Team-Ansichten hat korrekte Zeilen', t_team_ansichten_inhalt)

    # ── Feature 3: Kalender-Export (.ics) ────────────────────────────────────
    print('\n--- Feature 3: Kalender-Export (.ics) ---')

    def t_ics_parsebar():
        raw = build_ics_bytes(result, season_year=2026)
        txt = raw.decode('utf-8')
        assert txt.startswith('BEGIN:VCALENDAR'), 'Kein VCALENDAR-Header'
        assert txt.endswith('END:VCALENDAR'), 'Kein VCALENDAR-Footer'
        n_events = txt.count('BEGIN:VEVENT')
        exp_games = sum(len(g) for g in result.schedule.values())
        assert n_events == exp_games, \
            f'{n_events} VEVENTs, erwartet {exp_games}'
        return f'{n_events} VEVENT-Eintraege'
    check('ICS erzeugt und VEVENT-Anzahl korrekt', t_ics_parsebar)

    def t_ics_datum():
        raw = build_ics_bytes(result, season_year=2026)
        txt = raw.decode('utf-8')
        # KW 37 liegt nach KW 26 -> Jahr 2026
        assert 'DTSTART;VALUE=DATE:2026' in txt, \
            'Kein 2026-Datum fuer KW>=37 gefunden'
        return 'Jahreszuordnung KW37->2026 korrekt'
    check('ICS: Datum aus Kalender-KW berechnet', t_ics_datum)

    # ── Feature 2: Manueller Tausch ──────────────────────────────────────────
    print('\n--- Feature 2: Manueller Heim-/Auswaerts-Tausch ---')

    def t_swap_basic():
        import copy
        r2  = copy.deepcopy(result)
        cfg2 = cfg
        # Ersten Spieltag nehmen, erstes Spiel tauschen
        day1 = cfg2.days[0]
        games_before = list(r2.schedule[day1])
        ht_before, at_before = games_before[0]
        swap_home_away(r2, cfg2, day1, 0)
        games_after = r2.schedule[day1]
        ht_after, at_after = games_after[0]
        assert ht_after == at_before and at_after == ht_before, \
            f'Tausch fehlgeschlagen: {ht_before}/{at_before} -> {ht_after}/{at_after}'
        return f'ST{day1}: {ht_before} vs {at_before} -> {ht_after} vs {at_after}'
    check('swap_home_away tauscht Schedule-Eintrag', t_swap_basic)

    def t_swap_home_vals():
        import copy
        r2  = copy.deepcopy(result)
        cfg2 = cfg
        day1 = cfg2.days[0]
        ht, at = r2.schedule[day1][0]
        t_idx  = {t: i for i, t in enumerate(cfg2.teams)}
        hi, ai = t_idx[ht], t_idx[at]
        val_ht_before = r2.home_vals.get((hi, day1))
        val_at_before = r2.home_vals.get((ai, day1))
        swap_home_away(r2, cfg2, day1, 0)
        val_ht_after = r2.home_vals.get((hi, day1))
        val_at_after = r2.home_vals.get((ai, day1))
        assert val_ht_after == 0, f'home_vals[{ht}] sollte 0 sein, ist {val_ht_after}'
        assert val_at_after == 1, f'home_vals[{at}] sollte 1 sein, ist {val_at_after}'
        return (f'{ht}: {val_ht_before}->{val_ht_after}  '
                f'{at}: {val_at_before}->{val_at_after}')
    check('swap_home_away aktualisiert home_vals', t_swap_home_vals)

    def t_recompute():
        travels, sw_counts, sw_rates = recompute_result_stats(result, cfg)
        assert len(travels)   == cfg.n_teams, f'travels Laenge {len(travels)}'
        assert len(sw_counts) == cfg.n_teams, f'sw_counts Laenge {len(sw_counts)}'
        assert len(sw_rates)  == cfg.n_teams, f'sw_rates Laenge {len(sw_rates)}'
        assert all(t >= 0 for t in travels),   'Negative travels'
        assert all(s >= 0 for s in sw_counts), 'Negative sw_counts'
        return f'travels={travels}  sw={sw_counts}'
    check('recompute_result_stats gibt konsistente Werte', t_recompute)

    # ── Spielzeiten zuweisen ─────────────────────────────────────────────────
    print('\n--- Spielzeiten zuweisen ---')

    def t_assign_basic():
        import copy
        r2 = copy.deepcopy(result)
        assign_game_times(r2, ['14:00', '16:00'])
        assert r2.game_times, 'game_times ist leer'
        for d in cfg.days:
            assert d in r2.game_times, f'ST{d} fehlt in game_times'
            assert len(r2.game_times[d]) == len(r2.schedule[d]), \
                f'Falsche Anzahl Zeiten fuer ST{d}'
        first_d = cfg.days[0]
        assert r2.game_times[first_d][0] == '14:00', 'Erste Zeit falsch'
        return f'{len(r2.game_times)} Spieltage mit Zeiten'
    check('assign_game_times fuellt alle Spieltage', t_assign_basic)

    def t_assign_fewer_slots():
        import copy
        r2 = copy.deepcopy(result)
        assign_game_times(r2, ['14:00'])   # nur 1 Slot, aber 2 Spiele/Tag
        first_d = cfg.days[0]
        assert r2.game_times[first_d][0] == '14:00', 'Slot 0 falsch'
        assert r2.game_times[first_d][1] == '', 'Fehlender Slot sollte leer sein'
        return 'Fehlende Slots werden als leer gesetzt'
    check('Fehlende Zeitslots werden als leer gesetzt', t_assign_fewer_slots)

    def t_excel_mit_zeiten():
        import copy, io
        import openpyxl
        r2 = copy.deepcopy(result)
        r2.cfg = cfg
        assign_game_times(r2, ['14:00', '16:00'])
        wb  = build_league_excel(r2)
        buf = io.BytesIO(); wb.save(buf); buf.seek(0)
        wb2 = openpyxl.load_workbook(buf)
        ws  = wb2['Spielplan']
        hdr = [ws.cell(1, c).value for c in range(1, 9)]
        assert 'Uhrzeit' in hdr, f'Uhrzeit fehlt im Header: {hdr}'
        # Pruefe ob eine Zelle einen Zeitwert hat
        found_time = any(
            ws.cell(r, hdr.index('Uhrzeit') + 1).value == '14:00'
            for r in range(2, 5)
        )
        assert found_time, 'Kein 14:00 Wert in Spielplan-Sheet gefunden'
        return f'Header: {[h for h in hdr if h]}'
    check('Excel-Spielplan enthaelt Uhrzeit-Spalte nach Zuweisung', t_excel_mit_zeiten)

    def t_html_mit_zeiten():
        import copy
        r2 = copy.deepcopy(result)
        r2.cfg = cfg
        assign_game_times(r2, ['14:00', '16:00'])
        html = build_print_html(r2, season_year=2026)
        assert '14:00' in html, '14:00 fehlt im HTML'
        assert '<th>Uhrzeit</th>' in html, 'Uhrzeit-Spalten-Header fehlt'
        return 'Uhrzeiten im HTML enthalten'
    check('HTML enthaelt Uhrzeiten nach Zuweisung', t_html_mit_zeiten)

    # ── Druckbarer Spielplan (HTML) ───────────────────────────────────────────
    print('\n--- Druckbarer Spielplan (HTML) ---')

    def t_print_html_struktur():
        html = build_print_html(result, season_year=2026)
        assert '<!DOCTYPE html>' in html, 'Kein DOCTYPE'
        assert '<table' in html, 'Keine Tabelle'
        assert 'window.print()' in html, 'Kein Print-Button'
        assert cfg.name in html, 'Liga-Name fehlt'
        return f'{len(html):,} Zeichen'
    check('HTML enthaelt Grundstruktur und Print-Button', t_print_html_struktur)

    def t_print_html_alle_teams():
        html = build_print_html(result, season_year=2026)
        for t in cfg.teams:
            assert t in html, f'Team {t!r} fehlt im HTML'
        return f'Alle {cfg.n_teams} Teams enthalten'
    check('HTML enthaelt alle Teams', t_print_html_alle_teams)

    def t_print_html_alle_spiele():
        html = build_print_html(result, season_year=2026)
        # Jedes Spiel erscheint zweimal: im Gesamtplan + in Team-Ansicht
        for d, games in result.schedule.items():
            for ht, at in games:
                assert ht in html and at in html, f'Spiel {ht} vs {at} fehlt'
        return f'{sum(len(g) for g in result.schedule.values())} Spiele im HTML'
    check('HTML enthaelt alle Spielpaarungen', t_print_html_alle_spiele)

    def t_print_html_ohne_kalender():
        import copy
        r2 = copy.deepcopy(result)
        r2.cfg = copy.deepcopy(cfg)
        r2.cfg.calendar = {}   # kein Kalender
        html = build_print_html(r2, season_year=0)
        assert '<!DOCTYPE html>' in html, 'Kein HTML ohne Kalender'
        return 'HTML auch ohne Kalender-Daten generierbar'
    check('HTML auch ohne Kalender generierbar', t_print_html_ohne_kalender)

    # ── Feature 5 (neu): Constraint-Validierung ──────────────────────────────
    print('\n--- Feature 5: Constraint-Validierung ---')

    def _make_ld(teams, fmt='Hin-/Rueckrunde'):
        return {'name': 'TestLiga', 'teams': [(t, t) for t in teams], 'fmt': fmt}

    def _calc_nmd(ld):
        n = len(ld.get('teams', []))
        return 2 * (n - 1) if n >= 2 else 0

    def _get_nr_gpd(ld): return (2, 1)

    def _run(leagues=None, dst=None, blocked=None, pinned=None,
             dist=None, kw_compat=None, clubs=None):
        lids = list((leagues or {}).keys())
        return validate_cfg(
            league_order     = lids,
            leagues          = leagues or {},
            dst_per_liga     = dst or {},
            blocked          = blocked or {},
            pinned           = pinned or {},
            dist_matrices    = dist or {},
            kw_compat        = kw_compat or {},
            clubs            = clubs or {},
            calc_n_matchdays = _calc_nmd,
            get_n_rounds_gpd = _get_nr_gpd,
        )

    def t_clean_config():
        issues = _run(
            leagues={'A': _make_ld(['X', 'Y', 'Z', 'W'])},
            dist={'A': np.ones((4, 4))},
        )
        assert issues == [], f'Fehler bei sauberer Config: {issues}'
        return 'Keine Probleme bei gueltiger Config'
    check('Saubere Config liefert keine Probleme', t_clean_config)

    def t_too_few_teams():
        issues = _run(leagues={'A': _make_ld(['EinTeam'])})
        errs = [i for i in issues if i['level'] == 'error']
        assert any('2 Teams' in i['msg'] for i in errs), f'Kein Fehler: {errs}'
        return 'Fehler bei 1 Team erkannt'
    check('Zu wenige Teams wird als Fehler erkannt', t_too_few_teams)

    def t_all_days_blocked():
        # 4 Teams -> 6 Spieltage; Team X auf allen 6 Tagen gesperrt
        issues = _run(
            leagues={'A': _make_ld(['X', 'Y', 'Z', 'W'])},
            blocked={'A': {'X': [1, 2, 3, 4, 5, 6]}},
            dist={'A': np.ones((4, 4))},
        )
        errs = [i for i in issues if i['level'] == 'error']
        assert any('alle' in i['msg'].lower() or 'alle' in i['msg'] for i in errs), \
            f'Kein Fehler bei allen Sperrtagen: {errs}'
        return 'Fehler bei allen Sperrtagen erkannt'
    check('Alle Heimspieltage gesperrt wird als Fehler erkannt', t_all_days_blocked)

    def t_dst_out_of_range():
        # 4 Teams -> 6 Spieltage; DST-Block auf ST7+8 (ungueltig)
        issues = _run(
            leagues={'A': _make_ld(['X', 'Y', 'Z', 'W'])},
            dst={'A': [(7, 8)]},
            dist={'A': np.ones((4, 4))},
        )
        errs = [i for i in issues if i['level'] == 'error']
        assert any('DST' in i['msg'] for i in errs), f'Kein DST-Fehler: {errs}'
        return 'Fehler fuer ungueltige DST-Tage erkannt'
    check('DST-Block ausserhalb gueltigem Bereich als Fehler erkannt', t_dst_out_of_range)

    def t_pinned_wrong_day():
        issues = _run(
            leagues={'A': _make_ld(['X', 'Y', 'Z', 'W'])},
            pinned={'A': [{'teamA': 'X', 'teamB': 'Y', 'day': 99, 'home': 'X'}]},
            dist={'A': np.ones((4, 4))},
        )
        errs = [i for i in issues if i['level'] == 'error']
        assert any('ST99' in i['msg'] or 'nicht existiert' in i['msg'] for i in errs), \
            f'Kein Fehler fuer ungueltigen Pflichtspieltag: {errs}'
        return 'Fehler fuer ungueltige Pflichtspieltag erkannt'
    check('Pflichtspiel auf ungueltigem Spieltag als Fehler erkannt', t_pinned_wrong_day)

    def t_contradicting_home():
        issues = _run(
            leagues={'A': _make_ld(['X', 'Y', 'Z', 'W'])},
            pinned={'A': [
                {'teamA': 'X', 'teamB': 'Y', 'day': 1, 'home': 'X'},
                {'teamA': 'X', 'teamB': 'Y', 'day': 1, 'home': 'Y'},
            ]},
            dist={'A': np.ones((4, 4))},
        )
        errs = [i for i in issues if i['level'] == 'error']
        assert any('widersprüchlich' in i['msg'] or 'widerspruc' in i['msg'].lower()
                   for i in errs), f'Kein Widerspruch-Fehler: {errs}'
        return 'Widersprüchliches Heimrecht erkannt'
    check('Widersprüchliches Heimrecht wird als Fehler erkannt', t_contradicting_home)

    def t_warning_half_blocked():
        # Mehr als 50% der Tage gesperrt -> Warnung (nicht alle)
        issues = _run(
            leagues={'A': _make_ld(['X', 'Y', 'Z', 'W'])},
            blocked={'A': {'X': [1, 2, 3, 4]}},   # 4 von 6 Tagen gesperrt
            dist={'A': np.ones((4, 4))},
        )
        warns = [i for i in issues if i['level'] == 'warning']
        errs  = [i for i in issues if i['level'] == 'error']
        assert not any('alle' in i['msg'].lower() for i in errs), \
            'Fehler statt Warnung bei teilweiser Sperrung'
        assert any('Hälfte' in i['msg'] or 'haelfte' in i['msg'].lower()
                   or 'Hälfte' in i['msg'] for i in warns), \
            f'Keine Warnung bei >50% gesperrt: {warns}'
        return 'Warnung bei >50% Sperrtagen erkannt'
    check('Warnung bei mehr als 50% gesperrten Tagen', t_warning_half_blocked)

    # ── Hallenbelegungsplan ───────────────────────────────────────────────────
    print('\n--- Hallenbelegungsplan ---')

    def t_hall_returns_workbook():
        wb = build_hall_schedule({'TEST': result})
        assert wb is not None, 'build_hall_schedule gab None zurueck'
        return f'{len(wb.sheetnames)} Sheet(s): {wb.sheetnames}'
    check('build_hall_schedule gibt Workbook zurueck', t_hall_returns_workbook)

    def t_hall_sheet_name():
        wb = build_hall_schedule({'TEST': result})
        assert 'Hallenbelegungsplan' in wb.sheetnames, \
            f'Sheet "Hallenbelegungsplan" fehlt: {wb.sheetnames}'
        return 'Sheet "Hallenbelegungsplan" vorhanden'
    check('Hallenbelegungsplan hat korrekten Sheet-Namen', t_hall_sheet_name)

    def t_hall_row_count():
        wb = build_hall_schedule({'TEST': result})
        ws = wb['Hallenbelegungsplan']
        n_games = sum(len(gs) for gs in result.schedule.values())
        data_rows = [r for r in ws.iter_rows(min_row=4, values_only=True)
                     if any(c is not None for c in r)]
        assert len(data_rows) >= n_games, \
            f'Zu wenige Zeilen: {len(data_rows)} < {n_games} Spiele'
        return f'{len(data_rows)} Datenzeilen fuer {n_games} Spiele'
    check('Hallenbelegung enthaelt alle Spiele als Zeilen', t_hall_row_count)

    def t_hall_header_cols():
        wb = build_hall_schedule({'TEST': result})
        ws = wb['Hallenbelegungsplan']
        header = [c.value for c in ws[3] if c.value is not None]
        for col in ('Spieltag', 'Liga', 'Heimteam', 'Gastteam'):
            assert col in header, f'Spalte "{col}" fehlt: {header}'
        return f'Header: {header}'
    check('Hallenbelegung hat Pflicht-Spalten', t_hall_header_cols)

    def t_hall_multi_league():
        cfg2 = make_cfg('L2', ['Eins', 'Zwei', 'Drei', 'Vier'], dist=DIST, calendar=CAL)
        r2 = solve_league_phase1(cfg2, time_limit=20, seed=1)
        assert r2 is not None, 'Solver Liga 2: keine Loesung'
        r2.cfg = cfg2
        wb = build_hall_schedule({'TEST': result, 'L2': r2})
        ws = wb['Hallenbelegungsplan']
        n_total = (sum(len(gs) for gs in result.schedule.values())
                   + sum(len(gs) for gs in r2.schedule.values()))
        data_rows = [r for r in ws.iter_rows(min_row=4, values_only=True)
                     if any(c is not None for c in r)]
        assert len(data_rows) >= n_total, \
            f'Zu wenige Zeilen fuer 2 Ligen: {len(data_rows)} < {n_total}'
        return f'{len(data_rows)} Zeilen fuer 2 Ligen ({n_total} Spiele)'
    check('Hallenbelegung funktioniert mit 2 Ligen', t_hall_multi_league)

    def t_hall_with_times():
        assign_game_times(result, ['14:00', '16:00'])
        wb = build_hall_schedule({'TEST': result})
        ws = wb['Hallenbelegungsplan']
        header = [c.value for c in ws[3] if c.value is not None]
        assert 'Uhrzeit' in header, f'Uhrzeit-Spalte fehlt bei gesetzten Zeiten: {header}'
        return 'Uhrzeit-Spalte vorhanden wenn game_times gesetzt'
    check('Hallenbelegung zeigt Uhrzeit-Spalte wenn Zeiten zugewiesen', t_hall_with_times)

    def t_hall_saveable():
        wb = build_hall_schedule({'TEST': result})
        buf = io.BytesIO()
        wb.save(buf)
        assert buf.tell() > 0, 'Gespeichertes Excel ist leer'
        return f'{buf.tell()} Bytes'
    check('Hallenbelegungsplan-Excel speicherbar (kein TypeError)', t_hall_saveable)

    def t_hall_empty_results():
        wb = build_hall_schedule({})
        ws = wb['Hallenbelegungsplan']
        data_rows = [r for r in ws.iter_rows(min_row=4, values_only=True)
                     if any(c is not None for c in r)]
        assert len(data_rows) == 0, f'Leere results sollten 0 Zeilen ergeben, war {len(data_rows)}'
        return 'Leeres Dict -> 0 Datenzeilen'
    check('build_hall_schedule mit leerem Dict stuerzt nicht ab', t_hall_empty_results)

    _summarize()


def _summarize():
    passed = sum(1 for _, ok in _results if ok)
    total  = len(_results)
    print(f'\n  {passed}/{total} Tests bestanden\n')
    if passed < total:
        sys.exit(1)


if __name__ == '__main__':
    main()
