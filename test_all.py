#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Umfassender Funktionstest des Spielplan-Optimierers.

Testet alle Features:
  1. Standard-Liga (Hin/Rueckrunde, 6 Teams)
  2. DST-Optimierung (Doppelspieltage)
  3. Gesamt-km Minimierung + Routinggewicht
  3b. DST-Routing-Constraint (apply_routing=True)
  4. Heimrechtwechsel und -fairness
  5. Gesperrte Heimspieltage (Blocked Days)
  6. Vorgegebene Partien (Pflichtspiele / Pinned)
  7. Turniertag Stufe 2 (9 Teams, K=3, gpd=2) + Gruppeninfo in Excel
  8. Multi-Liga: Co-Optimierung, Co-Home-Bonus, SA-Nachbearbeitung

Aufruf: python test_all.py
"""
from __future__ import annotations

import io
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from ortools.sat.python import cp_model

from spielplan_multi.league_types import LeagueConfig, LeagueResult
from spielplan_multi.config import WEIGHT_SCALES
from spielplan_multi.solver import solve_league_phase1, extract_groups
from spielplan_multi.multi_solver import solve_all
from spielplan_multi.excel_output import build_league_excel
from spielplan_multi.calendar_parser import build_weekends


# -- Hilfsfunktionen ----------------------------------------------------------

PASS = 'PASS'
FAIL = 'FAIL'

_results: list = []

def check(name: str, fn):
    """Fuehrt einen Test aus, gibt PASS/FAIL aus."""
    try:
        detail = fn()
        print(f'  [{PASS}] {name}' + (f'  – {detail}' if detail else ''))
        _results.append((name, True, ''))
    except AssertionError as e:
        msg = str(e)
        print(f'  [{FAIL}] {name}  – {msg}')
        _results.append((name, False, msg))
    except Exception as e:
        tb = traceback.format_exc().strip().split('\n')[-1]
        print(f'  [{FAIL}] {name}  – EXCEPTION: {tb}')
        _results.append((name, False, f'Exception: {e}'))


def make_cfg(lid, teams, dist=None, **kw):
    n = len(teams)
    raw = {k: 5.0 for k in WEIGHT_SCALES}
    if dist is None:
        dist = np.zeros((n, n))
    nr = kw.get('n_rounds', 2)
    gpd = kw.get('games_per_team_per_day', 1)
    n_md = nr * (n - 1) // max(1, gpd)
    days = list(range(1, n_md + 1))
    dst = kw.get('dst_blocks', [])
    return LeagueConfig(
        league_id=lid, name=lid,
        teams=teams, locations=teams,
        dist=dist, dst_blocks=dst,
        weekends=build_weekends(days, dst),
        apply_routing=kw.get('apply_routing', False),
        f_num=kw.get('f_num', 125), f_den=100,
        w_scaled={k: v * WEIGHT_SCALES[k] for k, v in raw.items()},
        raw_weights=raw,
        pinned=kw.get('pinned', []),
        blocked=kw.get('blocked', {}),
        hier_weight=kw.get('hier_weight', 1.0),
        games_per_team_per_day=gpd,
        n_rounds=nr,
        n_teams_per_group=kw.get('n_teams_per_group', 0),
    )


def solve(cfg, tl=25):
    r = solve_league_phase1(cfg, time_limit=tl, seed=42)
    assert r is not None, 'Solver gab None (INFEASIBLE)'
    assert r.status in (cp_model.OPTIMAL, cp_model.FEASIBLE), \
        f'Status {r.status}'
    return r


def assert_schedule_complete(r: LeagueResult, cfg: LeagueConfig):
    """Alle Matches genau einmal, richtige Spiele/Tag/Team."""
    gpd = cfg.games_per_team_per_day
    for d in cfg.days:
        games = r.schedule.get(d, [])
        assert len(games) == cfg.n_games_per_day, \
            f'Tag {d}: {len(games)} Spiele, erwartet {cfg.n_games_per_day}'
        cnt = {}
        for ht, at in games:
            cnt[ht] = cnt.get(ht, 0) + 1
            cnt[at] = cnt.get(at, 0) + 1
        for t in cfg.teams:
            assert cnt.get(t, 0) == gpd, \
                f'Tag {d}: {t} spielt {cnt.get(t,0)}x statt {gpd}x'
    total = sum(len(g) for g in r.schedule.values())
    exp = cfg.n_teams * (cfg.n_teams - 1) // 2 * cfg.n_rounds
    assert total == exp, f'{total} Spiele gesamt, erwartet {exp}'


def assert_home_balance(r: LeagueResult, cfg: LeagueConfig):
    """Jede Paarung hat pro Runde genau 1 Heimrecht je Team (n_rounds>=2)."""
    if cfg.n_rounds < 2:
        return
    hinend = cfg.hinrunde_end
    rnd_len = cfg.n_matchdays // cfg.n_rounds
    for d, games in r.schedule.items():
        rnd = min(cfg.n_rounds, (d - 1) // rnd_len + 1)
        for ht, at in games:
            pass  # round is tracked below
    pair_home: dict = {}
    for d, games in r.schedule.items():
        rnd = min(cfg.n_rounds, (d - 1) // rnd_len + 1)
        for ht, at in games:
            key = tuple(sorted([ht, at]) + [rnd])
            assert key not in pair_home, \
                f'Doppelspiel in Runde {rnd}: {ht} vs {at}'
            pair_home[key] = ht
    # Pruefe: fuer jedes (a,b) haben Runde1 und Runde2 unterschiedliches Heimteam
    if cfg.n_rounds == 2:
        pairs: dict = {}
        for (a, b, rnd), h in pair_home.items():
            pairs.setdefault((a, b), {})[rnd] = h
        for (a, b), rounds in pairs.items():
            if len(rounds) == 2:
                assert rounds[1] != rounds[2], \
                    f'Paarung {a}/{b}: gleiches Heimrecht beide Runden'


# -- Distanzmatrix für 6 Teams -------------------------------------------------

TEAMS6 = ['Hamburg', 'Bremen', 'Hannover', 'Dortmund', 'Koeln', 'Frankfurt']
DIST6 = np.array([
    [  0, 120, 150, 230, 360, 400],
    [120,   0,  90, 210, 330, 370],
    [150,  90,   0, 200, 280, 320],
    [230, 210, 200,   0, 100, 200],
    [360, 330, 280, 100,   0, 190],
    [400, 370, 320, 200, 190,   0],
], dtype=float)


def main():
    _results.clear()

    # =========================================================================
    # TEST 1 – Standard-Liga: Grundfunktion, Hin/Rueckrunde
    # =========================================================================
    print('\n--- Test 1: Standard-Liga (Hin/Rueckrunde, 6 Teams) ---')

    cfg1 = make_cfg('STD', TEAMS6, dist=DIST6)

    def t1_loest():
        r = solve(cfg1)
        assert_schedule_complete(r, cfg1)
        assert_home_balance(r, cfg1)
        return f'obj={r.objective:.0f}  km={sum(r.travels)}'
    check('Standard-Liga loest und Schedule vollstaendig', t1_loest)

    def t1_km_positiv():
        r = solve(cfg1)
        assert sum(r.travels) > 0, 'Gesamt-km=0 obwohl echte Distanzen'
        return f'{sum(r.travels)} km gesamt'
    check('Reisedistanzen > 0 (echte Distanzmatrix)', t1_km_positiv)

    def t1_switches():
        r = solve(cfg1)
        assert len(r.sw_counts) == len(TEAMS6)
        assert all(s >= 0 for s in r.sw_counts)
        return f'sw min={min(r.sw_counts)} max={max(r.sw_counts)}'
    check('Heimrechtwechsel-Statistik vorhanden', t1_switches)

    # =========================================================================
    # TEST 2 – DST-Optimierung (Doppelspieltage)
    # =========================================================================
    print('\n--- Test 2: DST-Optimierung ---')

    cfg2 = make_cfg('DST', TEAMS6, dist=DIST6, dst_blocks=[(1, 2), (7, 8)])

    def t2_dst_heimrecht():
        r = solve(cfg2)
        for d1, d2 in cfg2.dst_blocks:
            home_d1 = {t: 0 for t in cfg2.teams}
            home_d2 = {t: 0 for t in cfg2.teams}
            for ht, at in r.schedule.get(d1, []):
                home_d1[ht] += 1
            for ht, at in r.schedule.get(d2, []):
                home_d2[ht] += 1
            for t in cfg2.teams:
                assert home_d1[t] == home_d2[t], \
                    f'DST ({d1},{d2}): {t} hat {home_d1[t]} vs {home_d2[t]} Heimspiele'
        return f'2 DST-Bloecke korrekt ({cfg2.dst_blocks})'
    check('Heimrecht konsistent in DST-Bloecken', t2_dst_heimrecht)

    def t2_schedule_ok():
        r = solve(cfg2)
        assert_schedule_complete(r, cfg2)
        return f'{cfg2.n_matchdays} Spieltage'
    check('DST-Schedule vollstaendig', t2_schedule_ok)

    # =========================================================================
    # TEST 3 – Gesamt-km Minimierung
    # =========================================================================
    print('\n--- Test 3: Gesamt-km Minimierung ---')

    raw_km = {k: 0.0 for k in WEIGHT_SCALES}
    raw_km['travel'] = 10.0
    raw_km['trav_fair'] = 10.0

    def make_km_cfg():
        n = len(TEAMS6)
        nr, gpd = 2, 1
        n_md = nr * (n - 1)
        days = list(range(1, n_md + 1))
        return LeagueConfig(
            league_id='KM', name='KM',
            teams=TEAMS6, locations=TEAMS6,
            dist=DIST6, dst_blocks=[],
            weekends=build_weekends(days, []),
            apply_routing=False, f_num=125, f_den=100,
            w_scaled={k: v * WEIGHT_SCALES[k] for k, v in raw_km.items()},
            raw_weights=raw_km,
            pinned=[], blocked={},
            games_per_team_per_day=1, n_rounds=2, n_teams_per_group=0,
        )

    def t3_km_optimiert():
        cfg_km = make_km_cfg()
        r = solve(cfg_km, tl=30)
        km_km = sum(r.travels)
        cfg_no = make_cfg('NO', TEAMS6, dist=DIST6)
        r_no = solve(cfg_no, tl=30)
        km_no = sum(r_no.travels)
        assert km_km <= km_no * 1.05, \
            f'KM-opt ({km_km}) schlechter als neutral ({km_no})'
        return f'km-opt={km_km}  neutral={km_no}'
    check('Km-Optimierung verbessert Reisedistanz', t3_km_optimiert)

    # =========================================================================
    # TEST 3b – DST-Routing-Constraint
    # =========================================================================
    print('\n--- Test 3b: DST-Routing-Constraint ---')

    # Routing-Konfiguration: 6 Teams, 1 DST-Block in der Mitte, f=200% (machbar)
    # f_num=125 + 2 DST-Bloecke ist mit DIST6 INFEASIBLE (zu wenig Spielraum).
    # f_num=200 + 1 DST-Block ist FEASIBLE und testet den Constraint sinnvoll.
    def make_routing_cfg(apply: bool, f_num: int = 200):
        n = len(TEAMS6)
        nr, gpd = 2, 1
        n_md = nr * (n - 1)
        days = list(range(1, n_md + 1))
        dst = [(5, 6)]   # 1 DST-Block in Mitte der Rückrunde
        raw = {k: 5.0 for k in WEIGHT_SCALES}
        return LeagueConfig(
            league_id='RT', name='Routing-Test',
            teams=TEAMS6, locations=TEAMS6,
            dist=DIST6, dst_blocks=dst,
            weekends=build_weekends(days, dst),
            apply_routing=apply, f_num=f_num, f_den=100,
            w_scaled={k: v * WEIGHT_SCALES[k] for k, v in raw.items()},
            raw_weights=raw,
            pinned=[], blocked={},
            games_per_team_per_day=1, n_rounds=2, n_teams_per_group=0,
        )

    def t3b_routing_lösbar():
        cfg_rt = make_routing_cfg(apply=True)
        r = solve(cfg_rt, tl=45)
        assert_schedule_complete(r, cfg_rt)
        return f'FEASIBLE mit apply_routing=True (f=200), km={sum(r.travels)}'
    check('Solver ist mit apply_routing=True loesbar (1 DST, f=200)', t3b_routing_lösbar)

    def t3b_routing_dst_heimrecht_konsistent():
        cfg_rt = make_routing_cfg(apply=True)
        r = solve(cfg_rt, tl=45)
        for d1, d2 in cfg_rt.dst_blocks:
            home_d1 = {ht: True for ht, _ in r.schedule.get(d1, [])}
            home_d1.update({at: False for _, at in r.schedule.get(d1, [])})
            home_d2 = {ht: True for ht, _ in r.schedule.get(d2, [])}
            home_d2.update({at: False for _, at in r.schedule.get(d2, [])})
            for t in cfg_rt.teams:
                assert home_d1.get(t) == home_d2.get(t), \
                    f'DST ({d1},{d2}): {t} hat unterschiedliches Heimrecht'
        return 'DST-Heimrecht mit Routing konsistent'
    check('DST-Heimrecht bleibt konsistent bei apply_routing=True', t3b_routing_dst_heimrecht_konsistent)

    def t3b_routing_begrenzung():
        """Mit Routing darf Umweg max. f_num/f_den des direkten Wegs betragen."""
        cfg_rt = make_routing_cfg(apply=True, f_num=200)
        r = solve(cfg_rt, tl=45)
        f = cfg_rt.f_num / cfg_rt.f_den   # 2.0
        t_idx = {t: i for i, t in enumerate(cfg_rt.teams)}

        violations = 0
        for d1, d2 in cfg_rt.dst_blocks:
            games_d1 = r.schedule.get(d1, [])
            games_d2 = r.schedule.get(d2, [])
            for ht1, at1 in games_d1:
                # at1 ist Auswärtsteam an d1, spielt an Spielort von ht1
                i        = t_idx[ht1]    # Spielort d1
                ti       = t_idx[at1]    # Heimatort des Auswärtsteams
                direct   = DIST6[ti, i]
                if direct == 0:
                    continue
                # Spiel von at1 an d2 finden
                d2_game  = next(((ht, at) for ht, at in games_d2
                                 if ht == at1 or at == at1), None)
                if d2_game is None:
                    continue
                j        = t_idx[d2_game[0]]   # Spielort d2
                via      = DIST6[i, j] + DIST6[j, ti]
                if via > f * direct + 0.5:      # +0.5 als Rundungs-Puffer
                    violations += 1

        assert violations == 0, \
            f'{violations} Routing-Verstoss(e): Umweg > f={f:.1f}x direkter Weg'
        return f'Routing-Constraint eingehalten (f={f:.1f}, DST {cfg_rt.dst_blocks})'
    check('Routing-Constraint begrenzt Umweg auf f_num/f_den', t3b_routing_begrenzung)

    # =========================================================================
    # TEST 4 – Heimrechtfairness
    # =========================================================================
    print('\n--- Test 4: Heimrechtfairness ---')

    def t4_fairness():
        r = solve(cfg1)
        sw = r.sw_counts
        spread = max(sw) - min(sw)
        assert spread <= cfg1.n_transitions, \
            f'Spread {spread} > n_transitions {cfg1.n_transitions}'
        assert len(r.sw_rates) == len(TEAMS6)
        assert all(0 <= v <= 100 for v in r.sw_rates)
        return f'Spread={spread}  rates={[round(v,1) for v in r.sw_rates]}'
    check('Wechsel-Spread und -Raten plausibel', t4_fairness)

    def t4_rates_vollstaendig():
        r = solve(cfg1)
        assert len(r.sw_rates) == cfg1.n_teams
        assert all(isinstance(v, float) for v in r.sw_rates)
        return f'{cfg1.n_teams} Raten vorhanden'
    check('Wechselquoten fuer alle Teams berechnet', t4_rates_vollstaendig)

    # =========================================================================
    # TEST 5 – Gesperrte Heimspieltage (Blocked Days)
    # =========================================================================
    print('\n--- Test 5: Gesperrte Heimspieltage ---')

    blocked5 = {'Hamburg': [1, 2, 3], 'Koeln': [8, 9, 10]}
    cfg5 = make_cfg('BLK', TEAMS6, dist=DIST6, blocked=blocked5)

    def t5_blocked_respektiert():
        r = solve(cfg5)
        for team, bdays in blocked5.items():
            for d in bdays:
                if d > cfg5.n_matchdays:
                    continue
                for ht, at in r.schedule.get(d, []):
                    assert ht != team, \
                        f'{team} spielt Heimspiel an gesperrtem Tag {d}'
        return f'Sperrtage {blocked5} eingehalten'
    check('Alle Sperrtage fuer Heimspiele eingehalten', t5_blocked_respektiert)

    # =========================================================================
    # TEST 6 – Vorgegebene Partien (Pflichtspiele / Pinned)
    # =========================================================================
    print('\n--- Test 6: Pflichtspiele ---')

    pinned6 = [
        {'teamA': 'Hamburg',  'teamB': 'Bremen',    'day': 1, 'home': 'Hamburg'},
        {'teamA': 'Hannover', 'teamB': 'Dortmund',  'day': 4, 'home': 'Dortmund'},
    ]
    cfg6 = make_cfg('PIN', TEAMS6, dist=DIST6, pinned=pinned6)

    def t6_pinned_tag_und_heim():
        r = solve(cfg6)
        for pm in pinned6:
            a, b, d, h = pm['teamA'], pm['teamB'], pm['day'], pm.get('home')
            found = False
            for ht, at in r.schedule.get(d, []):
                if set([ht, at]) == {a, b}:
                    found = True
                    if h:
                        assert ht == h, \
                            f'Pflichtspiel {a} vs {b} Tag {d}: Heimteam ist {ht}, erwartet {h}'
            assert found, f'Pflichtspiel {a} vs {b} nicht an Tag {d} gefunden'
        return f'{len(pinned6)} Pflichtspiele korrekt platziert'
    check('Pflichtspiele am richtigen Tag mit richtigem Heimrecht', t6_pinned_tag_und_heim)

    # =========================================================================
    # TEST 7 – Turniertag Stufe 2 (9 Teams, K=3, gpd=2)
    # =========================================================================
    print('\n--- Test 7: Turniertag Stufe 2 ---')

    TEAMS9 = [f'T{i}' for i in range(1, 10)]
    cfg7 = make_cfg('TT2', TEAMS9, n_teams_per_group=3, games_per_team_per_day=2, n_rounds=1)

    def t7_loest():
        r = solve(cfg7, tl=30)
        assert_schedule_complete(r, cfg7)
        return f'{cfg7.n_matchdays} Spieltage, {sum(len(g) for g in r.schedule.values())} Spiele'
    check('Stufe-2-Liga loest (9 Teams, K=3, gpd=2)', t7_loest)

    def t7_gruppen_extrahiert():
        r = solve(cfg7, tl=30)
        grps = extract_groups(r.schedule, cfg7)
        assert len(grps) == cfg7.n_matchdays, \
            f'{len(grps)} Tage mit Gruppen, erwartet {cfg7.n_matchdays}'
        G = cfg7.n_groups_per_day
        K = cfg7.n_teams_per_group
        for d, gs in grps.items():
            assert len(gs) == G, f'Tag {d}: {len(gs)} Gruppen, erwartet {G}'
            all_teams = [t for g in gs for t in g]
            assert len(all_teams) == len(TEAMS9), \
                f'Tag {d}: {len(all_teams)} Teams in Gruppen, erwartet {len(TEAMS9)}'
            assert len(set(all_teams)) == len(TEAMS9), \
                f'Tag {d}: doppelte Teams in Gruppen'
            for g in gs:
                assert len(g) == K, f'Tag {d}: Gruppe hat {len(g)} Teams, erwartet {K}'
        return f'{G} Gruppen/Tag, alle {len(TEAMS9)} Teams pro Tag abgedeckt'
    check('Gruppen korrekt extrahiert (G=3, K=3)', t7_gruppen_extrahiert)

    def t7_excel_gruppen_sheet():
        r = solve(cfg7, tl=30)
        r.groups = extract_groups(r.schedule, cfg7)
        r.cfg = cfg7
        wb = build_league_excel(r)
        assert 'Gruppen-Uebersicht' in wb.sheetnames, \
            f'Kein Gruppen-Uebersicht-Sheet. Sheets: {wb.sheetnames}'
        ws = wb['Gruppen-Uebersicht']
        G = cfg7.n_groups_per_day
        header_vals = [ws.cell(1, c).value for c in range(1, G + 3)]
        assert header_vals[0] == 'Spieltag', f'Erste Spalte: {header_vals[0]}'
        assert all(f'Gruppe {i}' in str(v) for i, v in enumerate(header_vals[1:G+1], 1)), \
            f'Gruppen-Header: {header_vals[1:G+1]}'
        ws_sp = wb['Spielplan']
        hdr_row = [ws_sp.cell(1, c).value for c in range(1, 8)]
        assert 'Gruppe' in hdr_row, f'Spielplan-Header: {hdr_row}'
        buf = io.BytesIO(); wb.save(buf)
        return f'{len(buf.getvalue())} Bytes, Sheets: {wb.sheetnames}'
    check('Excel hat Gruppen-Uebersicht-Sheet und Gruppe-Spalte', t7_excel_gruppen_sheet)

    def t7_travels_null():
        r = solve(cfg7, tl=30)
        assert all(v == 0 for v in r.travels), \
            f'Reisedistanzen bei Turniertag nicht 0: {r.travels}'
        assert all(v == 0 for v in r.sw_counts), \
            f'Switches bei Turniertag nicht 0: {r.sw_counts}'
        return 'travel=0, sw=0 (korrekt fuer Turniertag)'
    check('Turniertag: travel=0, switches=0', t7_travels_null)

    # =========================================================================
    # TEST 8 – Multi-Liga: Co-Optimierung + Co-Home + SA
    # =========================================================================
    print('\n--- Test 8: Multi-Liga (Co-Opt + Co-Home + SA) ---')

    TEAMS_A = ['HH-A', 'HH-B', 'HH-C', 'HH-D', 'HH-E', 'HH-F']
    TEAMS_B = ['HB-A', 'HB-B', 'HB-C', 'HB-D', 'HB-E', 'HB-F']
    cfg8a = make_cfg('L_A', TEAMS_A, dist=DIST6)
    cfg8b = make_cfg('L_B', TEAMS_B, dist=DIST6)
    clubs8 = {'Mehrspartenverein': {'L_A': 'HH-A', 'L_B': 'HB-A'}}
    kw_compat8 = {1: {'L_A': [1], 'L_B': [1]}}

    def t8_beide_loesen():
        results = solve_all(
            {'L_A': cfg8a, 'L_B': cfg8b},
            clubs={}, kw_compat={},
            w_cohome=5, phase1_time=20, phase2_time=20, sa_time=5, n_seeds=1,
        )
        assert len(results) == 2, f'Nur {len(results)}/2 Ligen'
        for lid, r in results.items():
            assert r is not None, f'{lid}: None'
            assert r.status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
            cfg = {'L_A': cfg8a, 'L_B': cfg8b}[lid]
            assert_schedule_complete(r, cfg)
        return f'L_A obj={results["L_A"].objective:.0f}  L_B obj={results["L_B"].objective:.0f}'
    check('Beide Ligen loesen in Phase 1+2+3', t8_beide_loesen)

    def t8_excel_beide():
        results = solve_all(
            {'L_A': cfg8a, 'L_B': cfg8b},
            clubs={}, kw_compat={},
            w_cohome=5, phase1_time=20, phase2_time=20, sa_time=0, n_seeds=1,
        )
        for lid, r in results.items():
            cfg = {'L_A': cfg8a, 'L_B': cfg8b}[lid]
            r.cfg = cfg
            wb = build_league_excel(r)
            buf = io.BytesIO(); wb.save(buf)
            assert len(buf.getvalue()) > 5000, f'{lid}: Excel zu klein'
            assert 'Spielplan' in wb.sheetnames
        return 'Excel fuer beide Ligen generiert'
    check('Excel-Export fuer beide Ligen fehlerfrei', t8_excel_beide)

    def t8_cohome_constraint():
        results = solve_all(
            {'L_A': cfg8a, 'L_B': cfg8b},
            clubs=clubs8, kw_compat=kw_compat8,
            w_cohome=50, phase1_time=20, phase2_time=20, sa_time=0, n_seeds=1,
        )
        for lid, r in results.items():
            assert r is not None, f'{lid}: None'
        return 'Co-Home-Modell lief durch ohne Absturz'
    check('Co-Home-Constraint (Mehrspartenverein) kein Absturz', t8_cohome_constraint)

    def t8_gemischt_std_tt2():
        cfgs = {'STD': cfg8a, 'TT2': cfg7}
        results = solve_all(
            cfgs, clubs={}, kw_compat={},
            w_cohome=5, phase1_time=20, phase2_time=20, sa_time=5, n_seeds=1,
        )
        assert results['STD'] is not None
        assert results['TT2'] is not None
        assert results['STD'].status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        assert results['TT2'].status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        return f'STD+TT2 in einem Lauf, TT2-groups={len(results["TT2"].groups)} Tage'
    check('Gemischter Lauf: Standard-Liga + Stufe-2-Turniertag', t8_gemischt_std_tt2)

    # =========================================================================
    # TEST 9 – Turniertag-Spielreihenfolge (tt_scheduler)
    # =========================================================================
    print('\n--- Test 9: Turniertag-Spielreihenfolge (tt_scheduler) ---')

    from spielplan_multi.tt_scheduler import _order_day_games

    def _check_gaps(ordered, min_gap, label):
        from collections import defaultdict
        pos = defaultdict(list)
        for i, (ht, at) in enumerate(ordered):
            pos[ht].append(i); pos[at].append(i)
        for t, ps in pos.items():
            ps.sort()
            for k in range(len(ps) - 1):
                g = ps[k + 1] - ps[k] - 1
                assert g >= min_gap, \
                    f'{label}: {t} gap={g} < min_gap={min_gap} (Positionen {ps})'

    def t9_min_gap_eingehalten():
        games = [('A','B'),('A','C'),('B','C'),('D','E'),('D','F'),('E','F')]
        for min_gap in (0, 1):
            for host_slots in ([], [1], [1, 4]):
                ordered, _, _ = _order_day_games(
                    games, 'A', host_slots, min_gap=min_gap, max_gap=3)
                _check_gaps(ordered, min_gap,
                             f'min_gap={min_gap} host_slots={host_slots}')
        return 'min_gap in allen Konstellationen eingehalten'
    check('min_gap immer eingehalten (6 Spiele, verschiedene Slots)', t9_min_gap_eingehalten)

    def t9_host_ist_heimteam():
        games = [('A','B'),('A','C'),('B','C'),('D','E'),('D','F'),('E','F')]
        from spielplan_multi.tt_scheduler import apply_tournament_ordering
        from spielplan_multi.league_types import LeagueConfig, LeagueResult
        from spielplan_multi.config import WEIGHT_SCALES
        from spielplan_multi.calendar_parser import build_weekends
        raw = {k: 5.0 for k in WEIGHT_SCALES}
        teams6 = ['A','B','C','D','E','F']
        cfg_tt = LeagueConfig(
            league_id='TT', name='TT', teams=teams6, locations=teams6,
            dist=np.zeros((6,6)), dst_blocks=[],
            weekends=build_weekends([1,2], []),
            apply_routing=False, f_num=125, f_den=100,
            w_scaled={k: v * WEIGHT_SCALES[k] for k, v in raw.items()},
            raw_weights=raw, pinned=[], blocked={},
            games_per_team_per_day=2, n_rounds=1, n_teams_per_group=0,
            tt_settings={'min_gap': 0, 'max_gap': 3, 'host_slots': [],
                         'host_mode': 'per_day', 'host_per_day': {1: 'A', 2: 'B'}},
        )
        dummy_result = LeagueResult(
            league_id='TT', status=4, objective=0,
            schedule={1: list(games), 2: list(games)},
            sw_counts=[0]*6, sw_rates=[0.0]*6, travels=[0]*6,
            mins=0, secs=0,
            home_vals={}, h_vals={}, x_vals={},
            cfg=cfg_tt, groups={}, hosts={},
        )
        result = apply_tournament_ordering(dummy_result, cfg_tt)
        for d, host in [(1, 'A'), (2, 'B')]:
            for ht, at in result.schedule[d]:
                if at == host:
                    assert False, f'Tag {d}: {host} als Gastteam in ({ht},{at})'
        return 'Ausrichter immer Heimteam nach apply_tournament_ordering'
    check('Ausrichter erscheint als Heimteam in allen Spielen', t9_host_ist_heimteam)

    def t9_keine_duplikate_in_host_slots():
        games = [('A','B'),('A','C'),('B','C'),('D','E'),('D','F'),('E','F')]
        ordered, hp, _ = _order_day_games(games, 'A', [2, 2], min_gap=0, max_gap=3)
        assert len(ordered) == len(games), \
            f'Spielanzahl nach Duplikat-Slots: {len(ordered)} != {len(games)}'
        return 'Duplikat-Slots werden sicher behandelt'
    check('Duplikat-Slots in host_slots kein Datenverlust', t9_keine_duplikate_in_host_slots)

    print('\n--- _balance_home_away (Turniertag Heim-Balance) ---')

    def _make_tt_cfg(teams):
        raw = {k: 5.0 for k in WEIGHT_SCALES}
        n = len(teams)
        return LeagueConfig(
            league_id='BAL', name='BAL', teams=teams, locations=teams,
            dist=np.zeros((n, n)), dst_blocks=[],
            weekends=build_weekends(list(range(1, n)), []),
            apply_routing=False, f_num=125, f_den=100,
            w_scaled={k: v * WEIGHT_SCALES[k] for k, v in raw.items()},
            raw_weights=raw, pinned=[], blocked={},
            games_per_team_per_day=2, n_rounds=1, n_teams_per_group=0,
            tt_settings={},
        )

    def t9_balance_basic():
        from spielplan_multi.tt_scheduler import _balance_home_away
        teams4 = ['A', 'B', 'C', 'D']
        # Absichtlich unausgewogen: A=3 Heim, B=2, C=1, D=0
        schedule = {
            1: [('A', 'B'), ('A', 'C')],
            2: [('A', 'D'), ('B', 'C')],
            3: [('B', 'D'), ('C', 'D')],
        }
        _balance_home_away(schedule, {}, _make_tt_cfg(teams4))
        t_idx = {t: i for i, t in enumerate(teams4)}
        home_count = [0] * 4
        for games in schedule.values():
            for ht, at in games:
                home_count[t_idx[ht]] += 1
        diff = max(home_count) - min(home_count)
        assert diff <= 1, f'Unbalanciert: home_count={home_count} max-min={diff}'
        return f'home_count={home_count} max-min={diff}'
    check('_balance_home_away: unausgewogener Plan wird ausgeglichen', t9_balance_basic)

    def t9_balance_host_protected():
        from spielplan_multi.tt_scheduler import _balance_home_away
        teams3 = ['A', 'B', 'C']
        # A Ausrichter Tag 1, B Ausrichter Tag 2 -> ihre Spiele duerfen nicht geflippt werden
        schedule = {
            1: [('A', 'B'), ('A', 'C'), ('B', 'C')],
            2: [('B', 'A'), ('B', 'C'), ('A', 'C')],
        }
        _balance_home_away(schedule, {1: 'A', 2: 'B'}, _make_tt_cfg(teams3))
        for ht, at in schedule[1]:
            if 'A' in (ht, at):
                assert ht == 'A', f'Tag 1: A ist Gastteam in ({ht},{at})'
        for ht, at in schedule[2]:
            if 'B' in (ht, at):
                assert ht == 'B', f'Tag 2: B ist Gastteam in ({ht},{at})'
        return 'Ausrichter-Spiele unberuehrt'
    check('_balance_home_away: Ausrichter-Spiele werden nicht veraendert', t9_balance_host_protected)

    def t9_balance_already_balanced():
        from spielplan_multi.tt_scheduler import _balance_home_away
        import copy
        teams4 = ['A', 'B', 'C', 'D']
        # Perfekt balanciert: jeder genau 1 Heimspiel -> kein Flip noetig
        schedule = {
            1: [('A', 'B'), ('C', 'D')],
            2: [('B', 'A'), ('D', 'C')],
        }
        before = copy.deepcopy(schedule)
        _balance_home_away(schedule, {}, _make_tt_cfg(teams4))
        assert schedule == before, f'Balancierter Plan wurde veraendert: {schedule}'
        return 'Plan unveraendert (Differenz < 2)'
    check('_balance_home_away: bereits ausgeglichener Plan bleibt unveraendert', t9_balance_already_balanced)

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
