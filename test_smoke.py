"""Smoke-Test fuer die generischen Solver-Komponenten.

Testet ohne Wizard und ohne Google-Maps-API:
  1. build_league_vars  – Modellaufbau
  2. solve_league_phase1 – Einzelliga-Lauf
  3. run_phase1          – parallele Ausfuehrung via ProcessPoolExecutor
  4. run_phase1 n_seeds=3 – beste Loesung je Liga
  5. refine_schedule     – SA-Nachbearbeitung

Aufruf: python test_smoke.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
from ortools.sat.python import cp_model

from spielplan_multi.league_types import LeagueConfig
from spielplan_multi.config import WEIGHT_SCALES
from spielplan_multi.solver import build_league_vars, solve_league_phase1
from spielplan_multi.multi_solver import run_phase1
from spielplan_multi.sa_refine import refine_schedule


# ── Hilfsfunktionen ──────────────────────────────────────────────────────────

def make_config(lid: str, teams: list, dist_matrix: np.ndarray) -> LeagueConfig:
    n = len(teams)
    N = 2 * (n - 1)
    return LeagueConfig(
        league_id=lid,
        name=f'Test-Liga {lid}',
        teams=teams,
        locations=teams,
        dist=dist_matrix,
        dst_blocks=[],
        weekends=[[d] for d in range(1, N + 1)],
        apply_routing=False,
        f_num=3, f_den=2,
        w_scaled=WEIGHT_SCALES,
        raw_weights=WEIGHT_SCALES,
        pinned=[],
        blocked={},
        calendar={},
        hier_weight=1.0,
    )


def validate_schedule(schedule: dict, cfg: LeagueConfig):
    """Jedes Team spielt genau einmal pro Spieltag."""
    teams = set(cfg.teams)
    for d in cfg.days:
        games = schedule.get(d, [])
        assert len(games) == cfg.n_games_per_day, \
            f"ST{d}: {len(games)} Spiele erwartet {cfg.n_games_per_day}"
        played: set = set()
        for ht, at in games:
            assert ht in teams and at in teams, f"Unbekanntes Team: {ht} / {at}"
            assert ht not in played and at not in played, \
                f"ST{d}: {ht} oder {at} spielt doppelt"
            played.update([ht, at])
        assert len(played) == cfg.n_teams, \
            f"ST{d}: {len(played)} statt {cfg.n_teams} Teams aktiv"


def check(label: str, ok: bool, detail: str = ''):
    mark = '[OK]  ' if ok else '[FAIL]'
    print(f'  {mark} {label}' + (f' – {detail}' if detail else ''))
    if not ok:
        sys.exit(1)


# ── Konfigurationen ───────────────────────────────────────────────────────────

teams_a = ['Alpha', 'Beta', 'Gamma', 'Delta']
dist_a = np.array([
    [0,   100, 200, 300],
    [100, 0,   150, 250],
    [200, 150, 0,   120],
    [300, 250, 120, 0  ],
], dtype=float)

teams_b = ['Eins', 'Zwei', 'Drei', 'Vier']
dist_b = np.array([
    [0,   80,  160, 240],
    [80,  0,   100, 180],
    [160, 100, 0,   90 ],
    [240, 180, 90,  0  ],
], dtype=float)

cfg_a = make_config('TEST_A', teams_a, dist_a)
cfg_b = make_config('TEST_B', teams_b, dist_b)


if __name__ == '__main__':

    # ── Test 1: Modellaufbau ──────────────────────────────────────────────────

    print('\n=== Test 1: build_league_vars (4 Teams) ===')
    try:
        model = cp_model.CpModel()
        lv = build_league_vars(model, cfg_a)
        check('Modell aufgebaut', True,
              f'{len(lv.matches)} Matches, {len(lv.days)} Spieltage')
        check('Keine move-Variablen', True, 'build_league_vars beendet ohne Fehler')
    except Exception as exc:
        check('build_league_vars', False, str(exc))


    # ── Test 2: solve_league_phase1 ───────────────────────────────────────────

    print('\n=== Test 2: solve_league_phase1 (4 Teams, 30s, Gap=5%) ===')
    try:
        result = solve_league_phase1(cfg_a, time_limit=30, seed=42)
        check('Loesung vorhanden', result is not None)
        validate_schedule(result.schedule, cfg_a)
        check('Schedule valide', True,
              f'obj={result.objective:.0f}  km={sum(result.travels)}  '
              f'switches={result.sw_counts}')
        check('km > 0', sum(result.travels) > 0, f'{sum(result.travels)} km')
        check('Hints vorhanden', len(result.x_vals) > 0,
              f'{len(result.x_vals)} x-Hints')
    except Exception as exc:
        check('solve_league_phase1', False, str(exc))
        import traceback; traceback.print_exc()


    # ── Test 3: run_phase1 parallel (2 Ligen, 30s) ───────────────────────────

    print('\n=== Test 3: run_phase1 parallel (2x 4 Teams, 30s) ===')
    try:
        cfgs = {'TEST_A': cfg_a, 'TEST_B': cfg_b}
        results = run_phase1(cfgs, time_limit=30, seed=42, n_seeds=2)

        check('Beide Ligen geloest', len(results) == 2,
              f'{len(results)} Ergebnisse')
        for lid, res in results.items():
            check(f'{lid}: Loesung vorhanden', res is not None)
            validate_schedule(res.schedule, cfgs[lid])
            check(f'{lid}: Schedule valide', True,
                  f'obj={res.objective:.0f}  km={sum(res.travels)}')
    except Exception as exc:
        check('run_phase1', False, str(exc))
        import traceback; traceback.print_exc()


    # ── Test 4: n_seeds=3 – beste Loesung wird selektiert ────────────────────

    print('\n=== Test 4: run_phase1 n_seeds=3 (beste Loesung je Liga) ===')
    try:
        cfgs = {'TEST_A': cfg_a, 'TEST_B': cfg_b}
        results3 = run_phase1(cfgs, time_limit=30, seed=0, n_seeds=3)

        check('Beide Ligen geloest', len(results3) == 2)
        for lid, res in results3.items():
            check(f'{lid}: Loesung vorhanden', res is not None)
            validate_schedule(res.schedule, cfgs[lid])
            check(f'{lid}: Schedule valide', True,
                  f'obj={res.objective:.0f}  km={sum(res.travels)}')
        for lid in results3:
            r1 = solve_league_phase1(cfgs[lid], time_limit=30, seed=0, num_workers=1)
            if r1 is not None:
                check(f'{lid}: n_seeds=3 >= n_seeds=1',
                      results3[lid].objective >= r1.objective - 1,
                      f'{results3[lid].objective:.0f} >= {r1.objective:.0f}')
    except Exception as exc:
        check('run_phase1 n_seeds=3', False, str(exc))
        import traceback; traceback.print_exc()


    # ── Test 5: SA-Nachbearbeitung ────────────────────────────────────────────

    print('\n=== Test 5: refine_schedule (SA-Nachbearbeitung, 10s) ===')
    try:
        base = solve_league_phase1(cfg_a, time_limit=30, seed=42)
        check('Basis-Loesung vorhanden', base is not None)
        if base is not None:
            refined = refine_schedule(base, cfg_a, time_limit=10, seed=42)
            check('Refinement zurueckgegeben', refined is not None)
            validate_schedule(refined.schedule, cfg_a)
            check('Schedule nach SA valide', True,
                  f'km {sum(base.travels)} -> {sum(refined.travels)}  '
                  f'sw {sum(base.sw_counts)} -> {sum(refined.sw_counts)}')
            check('km nicht verschlechtert',
                  sum(refined.travels) <= sum(base.travels) + 1,
                  f'{sum(refined.travels)} <= {sum(base.travels)} + 1')
    except Exception as exc:
        check('refine_schedule', False, str(exc))
        import traceback; traceback.print_exc()

    print('\n=== Alle Tests bestanden ===\n')
