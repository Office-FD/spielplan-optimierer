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
    n_active = kw.get('n_active_per_day', 0)
    # Allgemeine Formel (analog zu LeagueConfig.n_matchdays), unterstützt ungerades n
    games_per_day = (n_active if n_active > 0 else n) * gpd // 2
    if games_per_day > 0:
        n_md = nr * n * (n - 1) // 2 // games_per_day
    else:
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
        forced_home=kw.get('forced_home', {}),
        hier_weight=kw.get('hier_weight', 1.0),
        games_per_team_per_day=gpd,
        n_rounds=nr,
        n_teams_per_group=kw.get('n_teams_per_group', 0),
        n_active_per_day=n_active,
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

    def _make_tt_cfg(teams, days):
        raw = {k: 5.0 for k in WEIGHT_SCALES}
        n = len(teams)
        return LeagueConfig(
            league_id='BAL', name='BAL', teams=teams, locations=teams,
            dist=np.zeros((n, n)), dst_blocks=[],
            weekends=build_weekends(days, []),
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
        _balance_home_away(schedule, {}, _make_tt_cfg(teams4, [1, 2, 3]))
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
        _balance_home_away(schedule, {1: 'A', 2: 'B'}, _make_tt_cfg(teams3, [1, 2]))
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
        _balance_home_away(schedule, {}, _make_tt_cfg(teams4, [1, 2]))
        assert schedule == before, f'Balancierter Plan wurde veraendert: {schedule}'
        return 'Plan unveraendert (Differenz < 2)'
    check('_balance_home_away: bereits ausgeglichener Plan bleibt unveraendert', t9_balance_already_balanced)

    # =========================================================================
    # TEST 10 – Heimspiel-Pflichttage (forced_home, v1.2.x-Feature)
    # =========================================================================
    print('\n--- Test 10: Heimspiel-Pflichttage (forced_home) ---')

    def t10_forced_home_respektiert():
        forced = {'Hamburg': [1, 5], 'Frankfurt': [3, 8]}
        cfg_fh = make_cfg('FH', TEAMS6, dist=DIST6, forced_home=forced)
        r = solve(cfg_fh, tl=30)
        for team, fdays in forced.items():
            for d in fdays:
                if d > cfg_fh.n_matchdays:
                    continue
                has_home = any(ht == team for ht, _ in r.schedule.get(d, []))
                assert has_home, f'{team} hat KEIN Heimspiel am Pflichttag {d}'
        return f'Alle Pflichtheim-Tage eingehalten ({sum(len(v) for v in forced.values())} Tage)'
    check('Pflichtheim-Tage werden eingehalten', t10_forced_home_respektiert)

    def t10_forced_home_overrides_blocked():
        # Override-Verhalten: Sperrtag UND forced_home auf demselben Tag
        # → forced_home gewinnt (mit Warnung, siehe A-M2)
        forced  = {'Hamburg': [3]}
        blocked = {'Hamburg': [3, 4]}  # Tag 3 ist beides, Tag 4 nur blocked
        cfg_or = make_cfg('OR', TEAMS6, dist=DIST6, forced_home=forced, blocked=blocked)
        r = solve(cfg_or, tl=30)
        has_home_t3 = any(ht == 'Hamburg' for ht, _ in r.schedule.get(3, []))
        assert has_home_t3, 'Hamburg hat kein Heimspiel an Tag 3 (forced_home sollte blocked schlagen)'
        # Tag 4 ist nur blocked - kein Heimspiel
        has_home_t4 = any(ht == 'Hamburg' for ht, _ in r.schedule.get(4, []))
        assert not has_home_t4, 'Hamburg hat Heimspiel an reinem Sperrtag 4 (sollte verhindert sein)'
        return 'forced_home schlägt blocked an Tag 3, blocked greift an Tag 4'
    check('forced_home + blocked Override-Verhalten korrekt', t10_forced_home_overrides_blocked)

    def t10_forced_home_validator_konflikt():
        # Validator erkennt: gleicher Tag in blocked UND forced_home für SELBES Team
        # ohne forced_home-Vorrang würde es ja Sinn ergeben — validate_cfgs
        # gibt error wenn beides für denselben Tag gesetzt ist.
        # Aber: validate_cfgs erkennt die Override-Intent NICHT, sondern markiert es als Konflikt.
        from spielplan_multi.config_validator import validate_cfgs
        cfg_conf = make_cfg('CONF', TEAMS6, dist=DIST6,
                             forced_home={'Hamburg': [3]},
                             blocked={'Hamburg': [3]})
        issues = validate_cfgs({'CONF': cfg_conf})
        errors = [i for i in issues if i['level'] == 'error']
        assert any('Sperrtag' in i['msg'] and 'Pflichtheim' in i['msg'] for i in errors), \
            f'Validator erkennt blocked+forced_home-Konflikt nicht: {[i["msg"] for i in errors]}'
        return f'Validator markiert blocked+forced_home auf gleichem Tag als Fehler'
    check('Validator erkennt blocked+forced_home-Konflikt', t10_forced_home_validator_konflikt)

    # =========================================================================
    # TEST 11 – Spielfrei-Modus (ungerade Teamzahl, v1.2.2-Feature)
    # =========================================================================
    print('\n--- Test 11: Spielfrei-Modus (ungerade Teamzahl) ---')

    def t11_odd_teams_feasible():
        # 5 Teams, n_rounds=2 → 10 Spieltage (statt 8 bei gerader Zahl)
        TEAMS5 = ['T1', 'T2', 'T3', 'T4', 'T5']
        DIST5 = np.array([[0, 100, 200, 300, 400],
                          [100, 0, 150, 250, 350],
                          [200, 150, 0, 120, 220],
                          [300, 250, 120, 0, 100],
                          [400, 350, 220, 100, 0]], dtype=float)
        cfg5 = make_cfg('ODD', TEAMS5, dist=DIST5)
        # n_matchdays mit allgemeiner Formel: 2*5*4//2//(5*1//2) = 20//2 = 10
        assert cfg5.n_matchdays == 10, f'Erwartet 10 Spieltage, erhielt {cfg5.n_matchdays}'
        r = solve(cfg5, tl=45)
        # KEIN assert_schedule_complete: das pruefe `cnt == gpd` was im Spielfrei-Modus
        # nicht gilt (Bye-Tage haben `cnt == 0`).
        # Bei 5 Teams + gpd=1: pro Tag spielen 4 Teams (2 Spiele), 1 hat Spielfrei
        for d in cfg5.days:
            games = r.schedule.get(d, [])
            assert len(games) == 2, f'Tag {d}: {len(games)} Spiele, erwartet 2 (5 Teams, 1 Spielfrei)'
            teams_playing = {t for ht, at in games for t in (ht, at)}
            assert len(teams_playing) == 4, f'Tag {d}: {len(teams_playing)} Teams aktiv, erwartet 4'
        # Gesamtspielzahl: jede Paarung 2x = C(5,2)*2 = 20 Spiele
        total_games = sum(len(g) for g in r.schedule.values())
        assert total_games == 20, f'Total {total_games} Spiele, erwartet 20'
        return f'Ungerades n=5: {cfg5.n_matchdays} Spieltage, je 4 Teams aktiv + 1 Spielfrei, 20 Spiele total'
    check('Spielfrei-Modus: 5 Teams n_rounds=2 loest, jeder Tag 1 Bye', t11_odd_teams_feasible)

    def t11_odd_teams_fair_bye_distribution():
        TEAMS5 = ['T1', 'T2', 'T3', 'T4', 'T5']
        cfg5 = make_cfg('ODD2', TEAMS5)  # dist=0-Matrix, nur Heimrecht-Optimierung
        r = solve(cfg5, tl=45)
        # Jedes Team spielt: 4 Gegner × 2 Runden = 8 Spiele über 10 Tage → 2 Spielfrei pro Team
        bye_count: dict = {t: 0 for t in TEAMS5}
        for d in cfg5.days:
            teams_playing = {t for ht, at in r.schedule.get(d, []) for t in (ht, at)}
            for t in TEAMS5:
                if t not in teams_playing:
                    bye_count[t] += 1
        bye_vals = list(bye_count.values())
        assert all(v == 2 for v in bye_vals), \
            f'Bye-Verteilung unausgeglichen: {bye_count} (erwartet je 2)'
        return f'Bye-Verteilung fair: jedes Team genau 2 Spielfrei-Tage'
    check('Spielfrei-Modus: Bye fair verteilt (5 Teams × 2 Byes)', t11_odd_teams_fair_bye_distribution)

    # =========================================================================
    # TEST 12 – Schedule-Mutation-Funktionen (move/cancel/reschedule/recompute)
    # =========================================================================
    print('\n--- Test 12: Schedule-Mutation-Funktionen ---')

    from spielplan_multi.schedule_utils import (
        move_game, cancel_game, reschedule_game, recompute_result_stats,
    )

    def _solve_for_mutation():
        cfg_m = make_cfg('MUT', TEAMS6, dist=DIST6)
        r = solve(cfg_m, tl=30)
        return cfg_m, r

    def t12_recompute_stats_konsistenz():
        cfg_m, r = _solve_for_mutation()
        # Recompute aufrufen, Werte sollten denen vom Solver entsprechen
        travels, sw_counts, sw_rates = recompute_result_stats(r, cfg_m)
        # travels: Transitions-Modell, sollte mit Solver-Wert übereinstimmen (Solver minimiert dasselbe)
        # sw_rates: Denominator ist jetzt n_transitions (C-M2-Fix)
        n_tr = cfg_m.n_transitions
        for ti in range(cfg_m.n_teams):
            expected_rate = round(100.0 * sw_counts[ti] / n_tr, 1) if n_tr > 0 else 0.0
            assert abs(sw_rates[ti] - expected_rate) < 0.01, \
                f'sw_rates[{ti}]={sw_rates[ti]} != erwartet {expected_rate}'
        return f'recompute_stats konsistent (n_tr={n_tr}, max sw_rate={max(sw_rates):.1f}%)'
    check('recompute_result_stats: sw_rates-Denominator = n_transitions', t12_recompute_stats_konsistenz)

    def t12_move_game_konsistenz():
        cfg_m, r = _solve_for_mutation()
        # Suche einen Tag mit Spiel, das verschoben werden kann
        old_day = 1
        games_at_1 = list(r.schedule.get(old_day, []))
        if not games_at_1:
            return 'Übersprungen (kein Spiel an Tag 1)'
        ht, at = games_at_1[0]
        # Finde freien Tag für beide Teams (über schedule_utils.find_free_days)
        from spielplan_multi.schedule_utils import find_free_days
        free_days = find_free_days(r, cfg_m, ht, at)
        free_days = [d for d in free_days if d != old_day]
        if not free_days:
            return 'Übersprungen (kein freier Tag)'
        new_day = free_days[0]
        err_msg = move_game(r, cfg_m, old_day, 0, new_day)
        assert err_msg == '', f'move_game scheiterte: {err_msg}'
        # Verifikation: Spiel ist jetzt an new_day, nicht mehr an old_day
        assert (ht, at) in r.schedule.get(new_day, []), f'Spiel nicht an {new_day}'
        assert (ht, at) not in r.schedule.get(old_day, []), f'Spiel noch an {old_day}'
        # home_vals konsistent
        t_idx = {t: i for i, t in enumerate(cfg_m.teams)}
        assert r.home_vals.get((t_idx[ht], new_day)) == 1, 'home_vals[ht, new_day] != 1'
        assert r.home_vals.get((t_idx[at], new_day)) == 0, 'home_vals[at, new_day] != 0'
        return f'move {old_day}→{new_day} konsistent in schedule + home_vals'
    check('move_game: schedule und home_vals konsistent', t12_move_game_konsistenz)

    def t12_cancel_reschedule():
        cfg_m, r = _solve_for_mutation()
        # Spiel an Tag 1 absagen
        old_games = list(r.schedule.get(1, []))
        if not old_games:
            return 'Übersprungen (kein Spiel)'
        ht_c, at_c = cancel_game(r, cfg_m, 1, 0)
        assert ht_c is not None, 'cancel_game returned None'
        # Spiel ist weg
        remaining = list(r.schedule.get(1, []))
        assert (ht_c, at_c) not in remaining, 'Spiel nicht entfernt'
        # Reschedule auf freien Tag
        from spielplan_multi.schedule_utils import find_free_days
        free_days = find_free_days(r, cfg_m, ht_c, at_c)
        if not free_days:
            return 'Übersprungen (kein freier Tag für Reschedule)'
        err_msg = reschedule_game(r, cfg_m, free_days[0], ht_c, at_c)
        assert err_msg == '', f'reschedule_game scheiterte: {err_msg}'
        # Spiel ist eingetragen
        assert (ht_c, at_c) in r.schedule.get(free_days[0], []), 'Reschedule nicht im Schedule'
        return f'cancel + reschedule {ht_c} vs. {at_c} -> Tag {free_days[0]}'
    check('cancel_game + reschedule_game: Spielplan konsistent', t12_cancel_reschedule)

    def t12_mutation_turniertag_geguarded():
        # move_game, cancel_game, reschedule_game müssen bei gpd>1 ablehnen (C-M1/swap-Guard)
        # 9 Teams + K=3 + gpd=2 + n_rounds=1: valide Konfig (siehe Test 7).
        # cfg7 wurde in Test 7 schon erfolgreich geloest -> wiederverwenden statt neu solven.
        from spielplan_multi.solver import extract_groups
        r_tt = solve(cfg7, tl=30)
        r_tt.groups = extract_groups(r_tt.schedule, cfg7)
        r_tt.cfg = cfg7
        # move_game
        err_mv = move_game(r_tt, cfg7, 1, 0, 2)
        assert err_mv != '', 'move_game akzeptiert Turniertag (sollte abgelehnt werden)'
        assert 'Turniertag' in err_mv, f'move_game-Fehler erwaehnt Turniertag nicht: {err_mv}'
        # cancel_game
        ht_c, at_c = cancel_game(r_tt, cfg7, 1, 0)
        assert ht_c is None and at_c is None, 'cancel_game akzeptiert Turniertag'
        # reschedule_game
        err_re = reschedule_game(r_tt, cfg7, 1, cfg7.teams[0], cfg7.teams[1])
        assert err_re != '', 'reschedule_game akzeptiert Turniertag'
        assert 'Turniertag' in err_re, f'reschedule_game-Fehler erwaehnt Turniertag nicht: {err_re}'
        return 'move + cancel + reschedule bei Turniertag korrekt abgelehnt'
    check('Mutationen bei gpd>1 (Turniertag) abgelehnt', t12_mutation_turniertag_geguarded)

    # =========================================================================
    # TEST 13 – Heim-Balance pro Runde (round_balance, v1.5.0-Feature)
    # =========================================================================
    print('\n--- Test 13: Heim-Balance pro Runde (round_balance) ---')

    def t13_round_balance_wirkt():
        """Bei aktivem round_balance: Heim-Anzahl je Team und Runde maximal ±1 vom Mittel."""
        # 12 Teams, n_rounds=2 → 22 Spieltage → 11 pro Runde → Mittel 5.5 → 5 oder 6 Heim
        TEAMS12 = [f'Team{i:02d}' for i in range(1, 13)]
        n = len(TEAMS12)
        n_rounds = 2
        n_md = n_rounds * (n - 1)  # 22
        days = list(range(1, n_md + 1))
        raw = {k: 0.0 for k in WEIGHT_SCALES}
        raw['round_balance'] = 10.0  # stark aktiv
        cfg = LeagueConfig(
            league_id='RB', name='Round-Balance-Test',
            teams=TEAMS12, locations=TEAMS12,
            dist=np.zeros((n, n)), dst_blocks=[],
            weekends=build_weekends(days, []),
            apply_routing=False, f_num=125, f_den=100,
            w_scaled={k: v * WEIGHT_SCALES[k] for k, v in raw.items()},
            raw_weights=raw,
            pinned=[], blocked={},
            games_per_team_per_day=1, n_rounds=n_rounds, n_teams_per_group=0,
        )
        r = solve(cfg, tl=90)
        assert_schedule_complete(r, cfg)
        round_len = n_md // n_rounds
        deviations = []
        for ti, t in enumerate(TEAMS12):
            for r_idx in range(n_rounds):
                r_start = r_idx * round_len + 1
                r_end = (r_idx + 1) * round_len if r_idx < n_rounds - 1 else n_md
                home_count = sum(
                    1 for d in range(r_start, r_end + 1)
                    for ht, _ in r.schedule.get(d, [])
                    if ht == t
                )
                n_days_r = r_end - r_start + 1
                # Mittel = n_days_r / 2 (z.B. 5.5 bei 11 Tagen) -> optimal 5 oder 6
                ideal_lo = n_days_r // 2
                ideal_hi = (n_days_r + 1) // 2
                deviations.append(home_count - n_days_r / 2)
                assert ideal_lo <= home_count <= ideal_hi, (
                    f'{t} Runde {r_idx+1}: {home_count} Heim, erwartet '
                    f'{ideal_lo} oder {ideal_hi} (von {n_days_r} Spielen)'
                )
        max_abs_dev = max(abs(d) for d in deviations)
        return f'max |Abweichung vom Mittel| = {max_abs_dev:.1f} (erwartet 0.5)'
    check('Heim-Balance pro Runde: Heim-Anzahl ±1 vom Mittel (12 Teams)', t13_round_balance_wirkt)

    def t13_round_balance_aus_default():
        """Bei round_balance=0 (Default): keine zusätzlichen Constraints, alte Verteilung möglich."""
        # Lediglich: Modell baut sich und löst (keine Regression).
        TEAMS6 = ['Hamburg', 'Bremen', 'Hannover', 'Dortmund', 'Koeln', 'Frankfurt']
        raw = {k: 5.0 for k in WEIGHT_SCALES}
        raw['round_balance'] = 0.0  # explizit aus
        cfg = make_cfg('RB_OFF', TEAMS6, dist=DIST6)
        # Override raw_weights/w_scaled fuer diesen Test
        cfg.raw_weights['round_balance'] = 0.0
        cfg.w_scaled['round_balance']    = 0.0
        r = solve(cfg, tl=30)
        assert_schedule_complete(r, cfg)
        return 'round_balance=0 -> kein Constraint, Solver loest normal'
    check('Heim-Balance pro Runde: Default (=0) deaktiviert das Feature', t13_round_balance_aus_default)

    # =========================================================================
    print('\n--- Test 14: Constraint-Validator (validate_cfgs) ---')

    from spielplan_multi.config_validator import (
        validate as _validate_ui, validate_cfgs as _validate_cli
    )

    def _has_err(issues, fragment=None):
        for i in issues:
            if i['level'] == 'error' and (fragment is None or fragment in i['msg']):
                return True
        return False

    def _has_warn(issues, fragment=None):
        for i in issues:
            if i['level'] == 'warning' and (fragment is None or fragment in i['msg']):
                return True
        return False

    def t14_validator_dst_outside_range():
        """DST-Block ausserhalb gueltiger Spieltage -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, dst_blocks=[(999, 1000)])
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'DST-Block'), f'erwartet DST-Error, got {issues}'
        return 'DST-Block ST 999/1000 wird als Fehler gemeldet'
    check('Validator: DST-Block ausserhalb Spieltage -> error', t14_validator_dst_outside_range)

    def t14_validator_blocked_unknown_team():
        """Sperrtag fuer unbekanntes Team -> warning."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, blocked={'Phantom': [1, 2]})
        issues = _validate_cli({'VX': cfg})
        assert _has_warn(issues, 'Phantom'), f'erwartet Phantom-Warning, got {issues}'
        return 'Sperrtag fuer unbekanntes Team -> Warnung'
    check('Validator: Sperrtag-Team unbekannt -> warning', t14_validator_blocked_unknown_team)

    def t14_validator_blocked_outside_range():
        """Sperrtag-Spieltag ausserhalb Range -> warning."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, blocked={'Hamburg': [1, 99]})
        issues = _validate_cli({'VX': cfg})
        assert _has_warn(issues, 'liegen außerhalb'), f'erwartet outside-Warning, got {issues}'
        return 'Sperrtag-Spieltag 99 erkannt als ausserhalb'
    check('Validator: Sperrtag-Tag ausserhalb Range -> warning', t14_validator_blocked_outside_range)

    def t14_validator_blocked_all_days():
        """Alle Spieltage gesperrt fuer ein Team -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6,
                       blocked={'Hamburg': list(range(1, 11))})
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'Alle'), f'erwartet all-blocked-Error, got {issues}'
        return 'Alle 10 Spieltage gesperrt -> Fehler'
    check('Validator: alle Spieltage gesperrt -> error', t14_validator_blocked_all_days)

    def t14_validator_blocked_majority():
        """>50% Spieltage gesperrt -> warning."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6,
                       blocked={'Hamburg': [1, 2, 3, 4, 5, 6]})  # 6 von 10
        issues = _validate_cli({'VX': cfg})
        assert _has_warn(issues, 'Mehr als'), f'erwartet majority-Warning, got {issues}'
        return '6/10 Spieltage gesperrt -> Warnung'
    check('Validator: >50% gesperrt -> warning', t14_validator_blocked_majority)

    def t14_validator_pin_unknown_team():
        """Pflichtspiel mit unbekanntem Team -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6,
                       pinned=[{'teamA': 'Phantom', 'teamB': 'Hamburg', 'day': 1, 'home': 'Hamburg'}])
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'Phantom'), f'erwartet Phantom-Error, got {issues}'
        return 'Pflichtspiel mit unbekanntem teamA -> Fehler'
    check('Validator: Pin-Team unbekannt -> error', t14_validator_pin_unknown_team)

    def t14_validator_pin_self_play():
        """Pflichtspiel team_a == team_b -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6,
                       pinned=[{'teamA': 'Hamburg', 'teamB': 'Hamburg', 'day': 1, 'home': 'Hamburg'}])
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'sich selbst'), f'erwartet self-play-Error, got {issues}'
        return 'Hamburg gegen sich selbst -> Fehler'
    check('Validator: Pin Self-Play -> error', t14_validator_pin_self_play)

    def t14_validator_pin_invalid_day():
        """Pflichtspiel an Tag 99 (existiert nicht) -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6,
                       pinned=[{'teamA': 'Hamburg', 'teamB': 'Bremen',
                                'day': 99, 'home': 'Hamburg'}])
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'ST99'), f'erwartet day-Error, got {issues}'
        return 'Pin auf ST 99 -> Fehler'
    check('Validator: Pin ungueltiger Spieltag -> error', t14_validator_pin_invalid_day)

    def t14_validator_pin_invalid_day_type():
        """Pflichtspiel mit nicht-numerischem Tag -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6,
                       pinned=[{'teamA': 'Hamburg', 'teamB': 'Bremen',
                                'day': 'abc', 'home': 'Hamburg'}])
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'abc'), f'erwartet type-Error, got {issues}'
        return 'Pin day="abc" -> Fehler'
    check('Validator: Pin nicht-numerischer Tag -> error', t14_validator_pin_invalid_day_type)

    def t14_validator_round1_duplicate_pin():
        """n_rounds=1, gleiche Paarung 2x -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, n_rounds=1,
                       pinned=[
                           {'teamA': 'Hamburg', 'teamB': 'Bremen', 'day': 1, 'home': 'Hamburg'},
                           {'teamA': 'Hamburg', 'teamB': 'Bremen', 'day': 3, 'home': 'Bremen'},
                       ])
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'mehrfach'), f'erwartet duplicate-Error, got {issues}'
        return 'n_rounds=1 + doppelte Paarung -> Fehler'
    check('Validator: n_rounds=1 doppelter Pin -> error', t14_validator_round1_duplicate_pin)

    def t14_validator_round2_same_round_pin():
        """n_rounds=2, gleiche Paarung 2x in SELBER Runde -> error (B-M2)."""
        # n_md=10, round_len=5 -> ST1+ST3 sind beide in Runde 1.
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, n_rounds=2,
                       pinned=[
                           {'teamA': 'Hamburg', 'teamB': 'Bremen', 'day': 1, 'home': 'Hamburg'},
                           {'teamA': 'Hamburg', 'teamB': 'Bremen', 'day': 3, 'home': 'Bremen'},
                       ])
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'mehrfach'), f'erwartet same-round-Error, got {issues}'
        return 'n_rounds=2 + 2 Pins fuer Paarung in Runde 1 -> Fehler'
    check('Validator: n_rounds=2 Pin in derselben Runde -> error (B-M2)', t14_validator_round2_same_round_pin)

    def t14_validator_pin_too_many():
        """Mehr Pins als Spiele in der Saison -> error."""
        # 6 Teams, n_rounds=1 -> 15 Spiele. Wir machen 20 (fiktiv) Pins.
        many = [
            {'teamA': 'Hamburg', 'teamB': 'Bremen', 'day': (i % 5) + 1,
             'home': 'Hamburg'} for i in range(20)
        ]
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, n_rounds=1, pinned=many)
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, '20 Pflichtspiele'), f'erwartet pin-count-Error, got {issues}'
        return '20 Pins fuer 15 mögliche Spiele -> Fehler'
    check('Validator: zu viele Pins -> error', t14_validator_pin_too_many)

    def t14_validator_pin_too_many_warning():
        """>40% aller Spiele gepinnt -> warning."""
        # 6 Teams, n_rounds=2 -> 30 Spiele. 13 verschiedene Paarungen pinnen (>40%).
        pins = []
        cnt = 0
        for i, a in enumerate(TEAMS6):
            for j, b in enumerate(TEAMS6):
                if j <= i: continue
                pins.append({'teamA': a, 'teamB': b,
                             'day': (cnt % 9) + 1, 'home': a})
                cnt += 1
                if cnt >= 13: break
            if cnt >= 13: break
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, n_rounds=2, pinned=pins)
        issues = _validate_cli({'VX': cfg})
        assert _has_warn(issues, '> 40'), f'erwartet >40%-Warning, got {issues}'
        return '13/30 Pins (>40%) -> Warnung'
    check('Validator: >40% Pins -> warning', t14_validator_pin_too_many_warning)

    def t14_validator_forced_home_unknown_team():
        """Pflichtheim fuer unbekanntes Team -> warning."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, forced_home={'Phantom': [1, 2]})
        issues = _validate_cli({'VX': cfg})
        assert _has_warn(issues, 'Phantom'), f'erwartet Phantom-Warning, got {issues}'
        return 'Pflichtheim fuer unbekanntes Team -> Warnung'
    check('Validator: Pflichtheim Team unbekannt -> warning', t14_validator_forced_home_unknown_team)

    def t14_validator_forced_home_outside_range():
        """Pflichtheim Tag ausserhalb Range -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, forced_home={'Hamburg': [99]})
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'existieren nicht'), f'erwartet outside-Error, got {issues}'
        return 'Pflichtheim ST 99 -> Fehler'
    check('Validator: Pflichtheim ausserhalb Range -> error', t14_validator_forced_home_outside_range)

    def t14_validator_forced_home_dst_blocked():
        """DST + ein Tag forced_home + anderer Tag blocked -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6,
                       dst_blocks=[(3, 4)],
                       forced_home={'Hamburg': [3]},
                       blocked={'Hamburg': [4]})
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'DST-Block ST3/ST4'), f'erwartet dst+blocked+forced-Error, got {issues}'
        return 'DST 3/4 + Pflichtheim 3 + Sperrtag 4 -> Fehler'
    check('Validator: DST + forced_home + blocked -> error', t14_validator_forced_home_dst_blocked)

    def t14_validator_forced_home_pin_away():
        """Pflichtheim Tag X + Pin mit Team als Auswaerts -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6,
                       forced_home={'Hamburg': [1]},
                       pinned=[{'teamA': 'Hamburg', 'teamB': 'Bremen',
                                'day': 1, 'home': 'Bremen'}])
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'erzwingt Auswärtsspiel'), f'erwartet pin-away-Error, got {issues}'
        return 'Hamburg Pflichtheim ST1 + Pin Bremen home -> Fehler'
    check('Validator: forced_home + pin away -> error', t14_validator_forced_home_pin_away)

    def t14_validator_n_md_zero():
        """n_md=0 -> error (Pfad bei kaputter Format-Berechnung)."""
        # Wir basteln das direkt mit ctx, weil make_cfg n_md != 0 garantiert.
        from spielplan_multi.config_validator import _LeagueValCtx, _validate_league_common
        issues = []
        _err = lambda lid, msg: issues.append({'level': 'error', 'lid': lid, 'msg': msg})
        _warn = lambda lid, msg: issues.append({'level': 'warning', 'lid': lid, 'msg': msg})
        ctx = _LeagueValCtx(
            lid='X', name_md='X', teams=['A', 'B'], n_md=0, n_rounds=1, gpd=1,
            n_active=0, dst_blocks=[], blocked={}, forced_home={}, pinned=[], dist=None,
        )
        ok = _validate_league_common(ctx, _err, _warn)
        assert not ok, 'erwartet Skip-Return False'
        assert _has_err(issues, 'Spieltag-Berechnung'), f'erwartet n_md=0-Error, got {issues}'
        return 'n_md=0 -> Fehler + return False'
    check('Validator: n_md=0 -> error + skip', t14_validator_n_md_zero)

    def t14_validator_n_too_few():
        """n<2 -> error (Pfad bei einer-Team-Liga)."""
        from spielplan_multi.config_validator import _LeagueValCtx, _validate_league_common
        issues = []
        _err = lambda lid, msg: issues.append({'level': 'error', 'lid': lid, 'msg': msg})
        _warn = lambda lid, msg: issues.append({'level': 'warning', 'lid': lid, 'msg': msg})
        ctx = _LeagueValCtx(
            lid='X', name_md='X', teams=['Solo'], n_md=1, n_rounds=1, gpd=1,
            n_active=0, dst_blocks=[], blocked={}, forced_home={}, pinned=[], dist=None,
        )
        ok = _validate_league_common(ctx, _err, _warn)
        assert not ok, 'erwartet Skip-Return False'
        assert _has_err(issues, 'Mindestens 2'), f'erwartet n<2-Error, got {issues}'
        return 'n=1 -> Fehler + return False'
    check('Validator: n<2 -> error + skip', t14_validator_n_too_few)

    def t14_validator_dist_matrix_nan():
        """Distanzmatrix mit NaN -> warning."""
        dist_nan = np.array(DIST6)  # float
        dist_nan[0, 1] = np.nan
        cfg = make_cfg('VX', TEAMS6, dist=dist_nan)
        issues = _validate_cli({'VX': cfg})
        assert _has_warn(issues, 'Distanzmatrix'), f'erwartet NaN-Warning, got {issues}'
        return 'NaN in Distanzmatrix -> Warnung'
    check('Validator: Distanzmatrix NaN -> warning', t14_validator_dist_matrix_nan)

    def t14_validator_dist_matrix_empty():
        """Distanzmatrix mit Summe 0 -> warning."""
        cfg = make_cfg('VX', TEAMS6, dist=np.zeros((6, 6)))
        issues = _validate_cli({'VX': cfg})
        assert _has_warn(issues, 'Distanzmatrix'), f'erwartet empty-Warning, got {issues}'
        return 'Distanzmatrix Summe=0 -> Warnung'
    check('Validator: Distanzmatrix leer -> warning', t14_validator_dist_matrix_empty)

    def t14_validator_pin_conflicting_home():
        """Zwei Pins fuer dieselbe Paarung + Tag, aber unterschiedliches Heimrecht -> error."""
        cfg = make_cfg('VX', TEAMS6, dist=DIST6, n_rounds=2,
                       pinned=[
                           {'teamA': 'Hamburg', 'teamB': 'Bremen', 'day': 1, 'home': 'Hamburg'},
                           {'teamA': 'Hamburg', 'teamB': 'Bremen', 'day': 1, 'home': 'Bremen'},
                       ])
        issues = _validate_cli({'VX': cfg})
        assert _has_err(issues, 'widersprüchliches'), f'erwartet conflict-Error, got {issues}'
        return 'Zwei Pins gleicher Tag, anderes Heimrecht -> Fehler'
    check('Validator: Pin Heimrecht-Konflikt -> error', t14_validator_pin_conflicting_home)

    def t14_validator_ui_calendar_incomplete():
        """validate(): Kalender enthaelt weniger Spieltage als n_md -> warning."""
        leagues = {'VX': {'name': 'Test', 'teams': [('Hamburg', 'Hamburg'),
                                                    ('Bremen', 'Bremen'),
                                                    ('Hannover', 'Hannover'),
                                                    ('Dortmund', 'Dortmund')]}}
        kw_compat = {1: {'VX': [1, 2]}}  # nur 2 Spieltage aus 6 (n=4, n_rounds=2)
        issues = _validate_ui(
            ['VX'], leagues, {}, {}, {}, {'VX': DIST6[:4, :4]},
            kw_compat, {},
            calc_n_matchdays=lambda ld: 6,
            get_n_rounds_gpd=lambda ld: (2, 1),
        )
        assert _has_warn(issues, 'Kalender enthält'), f'erwartet cal-Warning, got {issues}'
        return 'Kalender 2/6 Tage -> Warnung'
    check('Validator (UI): Kalender unvollstaendig -> warning', t14_validator_ui_calendar_incomplete)

    def t14_validator_ui_cohome_no_calendar():
        """validate(): Co-Home-Verein, dessen Liga keinen Kalender hat -> warning."""
        leagues = {
            'A': {'name': 'Liga A', 'teams': [('Hamburg', 'Hamburg'),
                                              ('Bremen', 'Bremen'),
                                              ('Hannover', 'Hannover'),
                                              ('Dortmund', 'Dortmund')]},
            'B': {'name': 'Liga B', 'teams': [('Koeln', 'Koeln'),
                                              ('Frankfurt', 'Frankfurt'),
                                              ('Berlin', 'Berlin'),
                                              ('Muenchen', 'Muenchen')]},
        }
        kw_compat = {1: {'A': [1, 2, 3, 4, 5, 6]}}  # Liga B fehlt
        clubs = {'Verein-Multi': {'A': 'Hamburg', 'B': 'Koeln'}}
        issues = _validate_ui(
            ['A', 'B'], leagues, {}, {}, {}, {'A': DIST6[:4, :4], 'B': DIST6[:4, :4]},
            kw_compat, clubs,
            calc_n_matchdays=lambda ld: 6,
            get_n_rounds_gpd=lambda ld: (2, 1),
        )
        assert _has_warn(issues, 'Co-Home'), f'erwartet cohome-Warning, got {issues}'
        return 'Co-Home + Liga B ohne Kalender -> Warnung'
    check('Validator (UI): Co-Home Liga ohne Kalender -> warning', t14_validator_ui_cohome_no_calendar)

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
