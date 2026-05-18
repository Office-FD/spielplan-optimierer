"""Zweiphasen-Orchestrierung fuer beliebig viele Ligen.

Phase 1: Jede Liga unabhaengig loesen (parallel, mehrere Seeds).
Phase 2: Gemeinsames Modell mit Co-Home-Bonus und Warm-Start aus Phase 1.
Phase 3: SA-Nachbearbeitung pro Liga.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from ortools.sat.python import cp_model

from .ui import banner, step, ok, warn, err, info
from .league_types import LeagueConfig, LeagueVars, LeagueResult
from .solver import (build_league_vars, add_league_objective,
                     solve_league_phase1, set_hints,
                     extract_schedule, extract_statistics, extract_hints,
                     extract_groups)
from .sa_refine import refine_schedule
from .tt_scheduler import apply_tournament_ordering


# ── Phase-1-Worker fuer parallele Ausfuehrung ────────────────────────────────

def _phase1_worker(args):
    """Loest eine einzelne Liga in einem separaten Thread."""
    import traceback as _tb
    lid, cfg, time_limit, seed, num_workers = args
    try:
        result = solve_league_phase1(cfg, time_limit=time_limit, seed=seed,
                                     num_workers=num_workers)
        if result is not None:
            status_name = 'OK'
        else:
            status_name = 'NO_SOL'
    except Exception as exc:
        result = None
        status_name = f'EXC:{_tb.format_exc()}'
    return lid, result, status_name


# ── Phase 1: unabhaengige Ligen ──────────────────────────────────────────────

def run_phase1(cfgs: Dict[str, LeagueConfig],
               time_limit: int = 900,
               seed: int = 42,
               n_seeds: int = 2) -> Dict[str, Optional[LeagueResult]]:
    """Loest alle Ligen parallel mit mehreren Seeds; gibt die beste Loesung je Liga zurueck."""
    active = list(cfgs.keys())
    if not active:
        warn('Keine Ligen konfiguriert.')
        return {}

    n_jobs = len(active) * n_seeds
    cpu = os.cpu_count() or 4
    workers_per = max(1, cpu // n_jobs)

    banner('PHASE 1 - UNABHAENGIGE LIGA-OPTIMIERUNG (PARALLEL)')
    info(f'Zeitlimit: {time_limit}s | {len(active)} Ligen x {n_seeds} Seeds '
         f'= {n_jobs} Jobs | je {workers_per} CPU-Worker')

    seed_list = [seed + i * 100 for i in range(n_seeds)]
    tasks = [
        (lid, cfgs[lid], time_limit, s, workers_per)
        for lid in active
        for s in seed_list
    ]

    raw: Dict[str, list] = {lid: [] for lid in active}
    with ThreadPoolExecutor(max_workers=n_jobs) as pool:
        futures = {pool.submit(_phase1_worker, task): task[0] for task in tasks}
        for f in as_completed(futures):
            try:
                lid, result, status_name = f.result()
                if result is not None:
                    raw[lid].append(result)
                elif status_name != 'OK':
                    warn(f'[{lid}] Phase-1-Seed fehlgeschlagen: {status_name}')
            except Exception as worker_exc:
                err(f'Phase-1-Worker-Fehler (Prozess-Absturz): {worker_exc}')
                import traceback as _tb
                warn(_tb.format_exc())

    results: Dict[str, Optional[LeagueResult]] = {}
    for lid in active:
        candidates = raw[lid]
        if not candidates:
            results[lid] = None
            warn(f'{lid}: Keine Loesung in Phase 1.')
        else:
            best = max(candidates, key=lambda r: r.objective)
            results[lid] = best
            ok(f'  {lid}: beste obj={best.objective:.0f} '
               f'({len(candidates)}/{n_seeds} Seeds erfolgreich)')

    ok('Phase 1 abgeschlossen.')
    return results


# ── Co-Home-Constraints ──────────────────────────────────────────────────────

def _add_cohome_constraints(model: cp_model.CpModel,
                             all_lv: Dict[str, LeagueVars],
                             cfgs: Dict[str, LeagueConfig],
                             clubs: Dict[str, Dict[str, str]],
                             kw_compat: Dict[int, Dict[str, List[int]]],
                             w_cohome: int) -> list:
    """Fuegt weiche Co-Home-Bonus-Constraints hinzu.

    Fuer jeden Mehrsparten-Verein und jede Kalenderwoche, in der alle seine
    Ligen einen Spieltag haben, wird eine BoolVar co_home erzeugt.
    co_home = 1 gdw. alle betroffenen Teams in dieser KW Heimrecht haben.
    Der Bonus w_cohome * sum(co_home) geht in die Zielfunktion ein.
    """
    cohome_terms = []

    for club_name, liga_team_map in clubs.items():
        active = {lid: tname for lid, tname in liga_team_map.items()
                  if lid in all_lv and tname in all_lv[lid].team_idx}
        if len(active) < 2:
            continue

        for kw, kw_data in kw_compat.items():
            entries = []
            for lid, tname in active.items():
                if lid not in kw_data:
                    continue
                sts = kw_data[lid]
                if not sts:
                    continue
                # Turniertag: home ist IntVar, kein BoolVar → Co-Home nicht anwendbar
                if cfgs[lid].games_per_team_per_day > 1 or cfgs[lid].n_teams_per_group > 0:
                    continue
                ti = all_lv[lid].team_idx[tname]
                # Ersten gültigen Spieltag dieser Liga in der KW verwenden
                st = next((s for s in sts if s in all_lv[lid].days), None)
                if st is not None:
                    entries.append((lid, ti, st))

            if len(entries) < 2:
                continue

            home_vars = [all_lv[lid].home[ti, st] for lid, ti, st in entries]

            co_var = model.NewBoolVar(
                f'cohome_{"_".join(club_name.split())}_{kw}'
            )
            model.AddBoolAnd(home_vars).OnlyEnforceIf(co_var)
            model.AddBoolOr([v.Not() for v in home_vars]).OnlyEnforceIf(co_var.Not())
            cohome_terms.append(w_cohome * co_var)

    n_terms = len(cohome_terms)
    n_clubs = len([c for c in clubs
                   if len({l: t for l, t in clubs[c].items() if l in all_lv}) >= 2])
    ok(f'Co-Home-Bonus: {n_terms} Variablen erzeugt ({n_clubs} Vereine).')
    return cohome_terms


# ── Phase 2: kombiniertes Modell ─────────────────────────────────────────────

def run_phase2(cfgs: Dict[str, LeagueConfig],
               clubs: Dict[str, Dict[str, str]],
               kw_compat: Dict[int, Dict[str, List[int]]],
               phase1_results: Dict[str, Optional[LeagueResult]],
               w_cohome: float = 5.0,
               time_limit: int = 5400,
               seed: int = 42,
               rel_gap: float = 0.02) -> Dict[str, Optional[LeagueResult]]:
    """Phase 2: Ein gemeinsames CP-SAT-Modell fuer alle Ligen."""
    if not cfgs:
        warn('run_phase2: keine Ligen übergeben – übersprungen.')
        return {}
    banner('PHASE 2 - KOMBINIERTES MULTI-LIGA-MODELL')
    info(f'Zeitlimit: {time_limit}s | Gap-Limit: {rel_gap*100:.1f}% | Co-Home-Gewicht: {w_cohome}')

    model   = cp_model.CpModel()
    all_lv: Dict[str, LeagueVars] = {}
    obj_terms = []

    for lid, cfg in cfgs.items():
        hw = cfg.hier_weight
        step(f'Baue Modell fuer {cfg.name} (Hierarchiegewicht {hw}) ...')
        lv    = build_league_vars(model, cfg, prefix=lid + '_')
        terms = add_league_objective(model, lv, cfg, hier_weight=hw)
        all_lv[lid] = lv
        obj_terms.extend(terms)
        ok(f'  {lid}: {len(lv.matches)} Matches, {len(lv.days)} Spieltage')

    # Co-Home-Bonus (nur wenn mehrere Ligen und kw_compat vorhanden)
    if len(cfgs) >= 2 and clubs and kw_compat:
        w_cohome_int = int(round(w_cohome * 1000))
        cohome_terms = _add_cohome_constraints(
            model, all_lv, cfgs, clubs, kw_compat, w_cohome_int
        )
        obj_terms.extend(cohome_terms)

    model.Maximize(sum(obj_terms))

    # Warm-Start-Hints aus Phase 1
    hints_set = 0
    for lid, result in phase1_results.items():
        if result is not None and lid in all_lv:
            set_hints(model, all_lv[lid], result)
            hints_set += 1
    ok(f'Warm-Start-Hints aus {hints_set}/{len(cfgs)} Liga(en) gesetzt.')

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds  = time_limit
    solver.parameters.num_search_workers   = min(8, os.cpu_count() or 1)
    solver.parameters.log_search_progress  = True
    solver.parameters.random_seed          = seed
    solver.parameters.symmetry_level       = 1
    solver.parameters.max_memory_in_mb     = 4096
    if rel_gap > 0:
        solver.parameters.relative_gap_limit = rel_gap

    from .solver import _ProgressCallback
    banner('SOLVER GESTARTET (PHASE 2)')
    t0     = time.time()
    _p2_cb = _ProgressCallback('P2', 'Phase-2-Gesamt', t0)
    status = solver.Solve(model, _p2_cb)
    elapsed = time.time() - t0
    mins_total, secs_total = int(elapsed // 60), int(elapsed % 60)

    banner('SOLVER ERGEBNIS (PHASE 2)')
    print(f'  Status:    {solver.StatusName(status)}')
    try:
        print(f'  Objective: {solver.ObjectiveValue():.2f}')
    except Exception:
        print('  Objective: n/a')
    print(f'  Laufzeit:  {mins_total:02d}:{secs_total:02d} (mm:ss)')

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        err('Keine gueltige Loesung in Phase 2 gefunden.')
        warn('Verwende Phase-1-Ergebnisse als Fallback.')
        return phase1_results

    results: Dict[str, Optional[LeagueResult]] = {}
    for lid, lv in all_lv.items():
        cfg = cfgs[lid]
        schedule              = extract_schedule(solver, lv)
        sw_counts, sw_rates, travels = extract_statistics(solver, lv, cfg)
        home_vals, h_vals, x_vals   = extract_hints(solver, lv)
        groups                = extract_groups(schedule, cfg)

        _p1 = phase1_results.get(lid)
        results[lid] = LeagueResult(
            league_id=lid,
            status=status,
            objective=solver.ObjectiveValue(),
            schedule=schedule,
            sw_counts=sw_counts,
            sw_rates=sw_rates,
            travels=travels,
            mins=mins_total,
            secs=secs_total,
            home_vals=home_vals,
            h_vals=h_vals,
            x_vals=x_vals,
            cfg=cfg,
            groups=groups,
            hosts=_p1.hosts if _p1 else {},
            game_times=_p1.game_times if _p1 else {},
        )
        _sw = sw_counts or [0]
        ok(f'  {lid}: {sum(travels)} km gesamt, '
           f'Switches {min(_sw)}-{max(_sw)}')

    return results


# ── Phase 3: SA-Nachbearbeitung ──────────────────────────────────────────────

def run_phase3(results: Dict[str, Optional[LeagueResult]],
               cfgs: Dict[str, LeagueConfig],
               sa_time: int = 120,
               seed: int = 42) -> Dict[str, Optional[LeagueResult]]:
    """Phase 3: SA-Nachbearbeitung – Heimrecht-Optimierung je Liga."""
    banner('PHASE 3 - SA-NACHBEARBEITUNG')
    info(f'SA-Zeit pro Liga: {sa_time}s | Ligen: {len(cfgs)}')

    refined = {}
    for lid, result in results.items():
        if result is None or lid not in cfgs:
            refined[lid] = result
            continue
        refined[lid] = refine_schedule(result, cfgs[lid],
                                       time_limit=sa_time, seed=seed)
    return refined


# ── Gesamt-Orchestrierung ─────────────────────────────────────────────────────

def solve_all(cfgs: Dict[str, LeagueConfig],
              clubs: Dict[str, Dict[str, str]],
              kw_compat: Dict[int, Dict[str, List[int]]],
              w_cohome: float = 5.0,
              phase1_time: int = 900,
              phase2_time: int = 5400,
              night_mode: bool = False,
              seed: int = 42,
              rel_gap: float = 0.02,
              n_seeds: int = 2,
              sa_time: int = 120) -> Dict[str, Optional[LeagueResult]]:
    """Fuehrt Phase 1 + 2 + 3 durch und gibt die finalen Ergebnisse zurueck."""
    if night_mode:
        phase2_time = 28800  # 8 Stunden
        rel_gap     = 0.005  # 0,5% Gap – Abbruch bei nahezu-optimalem Ergebnis
        info('Nachtlauf-Modus: Phase-2-Zeitlimit = 8h, Gap-Limit = 0,5%.')

    phase1 = run_phase1(cfgs, time_limit=phase1_time, seed=seed, n_seeds=n_seeds)

    phase2 = run_phase2(
        cfgs=cfgs,
        clubs=clubs,
        kw_compat=kw_compat,
        phase1_results=phase1,
        w_cohome=w_cohome,
        time_limit=phase2_time,
        seed=seed,
        rel_gap=rel_gap,
    )

    phase3 = run_phase3(phase2, cfgs, sa_time=sa_time, seed=seed) if sa_time > 0 else dict(phase2)

    # Turniertag-Spielreihenfolge anwenden (Weg X)
    for lid, result in list(phase3.items()):
        if result is not None and cfgs.get(lid) and cfgs[lid].games_per_team_per_day > 1:
            if cfgs[lid].tt_settings:
                phase3[lid] = apply_tournament_ordering(result, cfgs[lid])

    return phase3
