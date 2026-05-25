"""CP-SAT-Modellbauer fuer Spielplan-Optimierung.

Unterstuetzt alle Formate:
  - Standard (gpd=1): Hin/Rueck/Dreifachrunde, DST, Routing, Blocked, Pinned
  - Turniertag Stufe 1 (gpd>1, K=0): alle Teams an einem Ort
  - Turniertag Stufe 2 (gpd>1, K>0): automatische Gruppenbildung

Bedingungen fuer Stufe 2:
  - K muss n teilen (K | n), nur dann entstehen gleich grosse Gruppen
  - (n-1) % gpd == 0, damit die Spieltage ganzzahlig aufgehen
  - K*gpd gerade (ganzzahlige Spiele pro Gruppe), gpd <= K-1

Oeffentliche API:
  build_league_vars(model, cfg, prefix)  -> LeagueVars
  add_league_objective(model, lv, cfg, hier_weight, coef_scale) -> List[IntExpr]
  solve_league_phase1(cfg, time_limit, seed, rel_gap) -> LeagueResult | None
  extract_schedule(solver, lv)   -> Dict[int, List[Tuple[str,str]]]
  extract_groups(schedule, cfg)  -> Dict[int, List[List[str]]]  (nur Stufe 2)
  extract_statistics(solver, lv, cfg) -> (sw_counts, sw_rates, travels)
  extract_hints(solver, lv)      -> (home_vals, h_vals, x_vals)
"""

from __future__ import annotations

import math
import os
import sys
import time
from collections import Counter
from typing import Dict, List, Optional, Tuple

import numpy as np
from ortools.sat.python import cp_model

from .ui import step, ok, warn, err, banner
from .league_types import LeagueConfig, LeagueVars, LeagueResult
from .config import UNREACHABLE_KM


# ── Hilfsfunktion: Match-Liste aufbauen ─────────────────────────────────────

_PHASE_NAMES = ['hin', 'rueck', 'dritt']


def _build_matches(teams: List[str], n_rounds: int = 2):
    pairs, matches = [], []
    pair_round_to_match = {}
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            a, b = teams[i], teams[j]
            pairs.append((a, b))
            for r in range(n_rounds):
                m = len(matches)
                phase = _PHASE_NAMES[r] if r < len(_PHASE_NAMES) else f'r{r + 1}'
                matches.append({'A': a, 'B': b, 'phase': phase, 'round': r + 1})
                pair_round_to_match[(a, b, r + 1)] = m
    return pairs, matches, pair_round_to_match


# ── Kern: Liga-Variablen und Constraints in ein Model einfuegen ──────────────

def build_league_vars(model: cp_model.CpModel,
                      cfg: LeagueConfig,
                      prefix: str = '') -> LeagueVars:
    """Fuegt alle Variablen und Hard-Constraints einer Liga in `model` ein.

    Durch `prefix` koennen mehrere Ligen im selben Model koexistieren.
    Gibt LeagueVars zurueck (kein Solver-Lauf, nur Modellaufbau).
    """
    n = cfg.n_teams
    if n < 2:
        raise ValueError(f'Liga {cfg.name!r}: mindestens 2 Teams erforderlich (hat {n}).')
    days = cfg.days
    dist_int = cfg.dist.astype(int)  # einmal konvertieren, spart int() in inner loops
    N = cfg.n_matchdays
    n_transitions = cfg.n_transitions
    n_gpd = cfg.n_games_per_day
    gpd   = cfg.games_per_team_per_day
    K     = cfg.n_teams_per_group   # 0 = Stufe 1, >0 = Stufe 2
    G     = cfg.n_groups_per_day
    t_idx = {t: i for i, t in enumerate(cfg.teams)}
    dist = cfg.dist

    n_rounds = cfg.n_rounds
    pairs, matches, pair_round_to_match = _build_matches(cfg.teams, n_rounds)
    num_pairs   = len(pairs)
    num_matches = len(matches)

    team_in_match = [[False] * num_matches for _ in range(n)]
    team_matches  = {ti: [] for ti in range(n)}
    for m, info in enumerate(matches):
        ai, bi = t_idx[info['A']], t_idx[info['B']]
        team_in_match[ai][m] = True
        team_in_match[bi][m] = True
        team_matches[ai].append((m, True,  ai, bi))
        team_matches[bi].append((m, False, ai, bi))

    reachable = {ti: list(range(n)) for ti in range(n)}
    is_turniertag = (gpd > 1 or K > 0)  # kein loc/travel bei Turniertag

    # ── Variablen ───────────────────────────────────────────────────────────
    p = prefix  # Kurzform

    x = {(m, d): model.NewBoolVar(f'{p}x_{m}_{d}')
         for m in range(num_matches) for d in days}

    h = {m: model.NewBoolVar(f'{p}h_{m}') for m in range(num_matches)}

    yA, yB = {}, {}
    for m in range(num_matches):
        for d in days:
            yA[m, d] = model.NewBoolVar(f'{p}yA_{m}_{d}')
            yB[m, d] = model.NewBoolVar(f'{p}yB_{m}_{d}')
            model.Add(yA[m, d] + yB[m, d] == x[m, d])
            model.Add(yA[m, d] <= 1 - h[m])
            model.Add(yA[m, d] >= x[m, d] - h[m])
            model.Add(yB[m, d] <= h[m])
            model.Add(yB[m, d] >= x[m, d] + h[m] - 1)

    if gpd == 1:
        home = {(ti, d): model.NewBoolVar(f'{p}home_{ti}_{d}')
                for ti in range(n) for d in days}
    else:
        home = {(ti, d): model.NewIntVar(0, gpd, f'{p}home_{ti}_{d}')
                for ti in range(n) for d in days}

    switch = {(ti, d): model.NewBoolVar(f'{p}sw_{ti}_{d}')
              for ti in range(n) for d in range(1, N)}

    sw_count = {ti: model.NewIntVar(0, n_transitions, f'{p}swc_{ti}') for ti in range(n)}
    max_sw   = model.NewIntVar(0, n_transitions, f'{p}max_sw')
    min_sw   = model.NewIntVar(0, n_transitions, f'{p}min_sw')

    # loc-Variablen nur im Standard-Format (gpd=1, kein Gruppenmodell)
    if not is_turniertag:
        loc = {}
        for ti in range(n):
            for d in days:
                for i in reachable[ti]:
                    loc[ti, d, i] = model.NewBoolVar(f'{p}loc_{ti}_{d}_{i}')
    else:
        loc = {}

    flat = sorted(int(v) for v in dist.flatten() if 0 < v < UNREACHABLE_KM)
    travel_ub = sum(flat[-n_transitions:]) if len(flat) >= n_transitions else (sum(flat) if flat else 1)
    travel_ub = max(travel_ub, 1)

    travel     = {ti: model.NewIntVar(0, travel_ub, f'{p}trv_{ti}') for ti in range(n)}
    max_travel = model.NewIntVar(0, travel_ub, f'{p}max_trv')
    min_travel = model.NewIntVar(0, travel_ub, f'{p}min_trv')

    num_weekends = len(cfg.weekends)
    if gpd == 1:
        homeW = {(ti, w): model.NewBoolVar(f'{p}homeW_{ti}_{w}')
                 for ti in range(n) for w in range(num_weekends)}
    else:
        homeW = {}

    # ── Constraints ─────────────────────────────────────────────────────────

    # Jedes Match genau einmal; Phasen-Trennung (jede Runde auf eigene Spieltage)
    round_len = N // max(1, n_rounds)
    for m, info in enumerate(matches):
        model.Add(sum(x[m, d] for d in days) == 1)
        r       = info['round']
        r_start = (r - 1) * round_len + 1
        r_end   = r * round_len if r < n_rounds else N
        for d in days:
            if not (r_start <= d <= r_end):
                model.Add(x[m, d] == 0)

    if K == 0:
        # Stufe 1: feste Anzahl Spiele pro Tag
        for d in days:
            model.Add(sum(x[m, d] for m in range(num_matches)) == n_gpd)
        # Gerade Teamzahl → jedes Team spielt exakt gpd Spiele pro Tag.
        # Ungerade Teamzahl → ein Team hat je Spieltag spielfrei (≤ gpd).
        needs_bye = (n * gpd) % 2 == 1
        for ti in range(n):
            for d in days:
                cstr = sum(x[m, d] for m in range(num_matches) if team_in_match[ti][m])
                if needs_bye:
                    model.Add(cstr <= gpd)
                else:
                    model.Add(cstr == gpd)
    # Stufe 2: Spiele-Constraints werden nach Gruppenbildung gesetzt (siehe unten)

    # home-Variable konsistent mit yA/yB
    for ti in range(n):
        tpd = {d: [] for d in days}
        for m, is_A, _, _ in team_matches[ti]:
            for d in days:
                tpd[d].append(yA[m, d] if is_A else yB[m, d])
        for d in days:
            model.Add(home[ti, d] == sum(tpd[d]))

    # Heimrecht-Balance pro Paarung: jede Runde bringt n_rounds Matches je Paar.
    # Fuer n_rounds=1: keine Einschraenkung noetig (Solver waehllt frei).
    # Fuer n_rounds=2: genau 1 Heimspiel je Team pro Paarung (sum == 1).
    # Fuer n_rounds=3: 1 oder 2 Heimspiele (floor <= sum <= ceil).
    h_lo = math.floor(n_rounds / 2)
    h_hi = math.ceil(n_rounds / 2)
    if n_rounds >= 2:
        for pid in range(num_pairs):
            pair_h = sum(h[n_rounds * pid + r] for r in range(n_rounds))
            if h_lo == h_hi:
                model.Add(pair_h == h_lo)
            else:
                model.Add(pair_h >= h_lo)
                model.Add(pair_h <= h_hi)

    # DST: gleiches Heimrecht in beiden Tagen des Blocks
    days_set_early = set(days)
    for ti in range(n):
        for d1, d2 in cfg.dst_blocks:
            if d1 in days_set_early and d2 in days_set_early:
                model.Add(home[ti, d1] == home[ti, d2])
            else:
                warn(f'[{cfg.league_id}] DST-Block ({d1},{d2}) ausserhalb Spieltage – ignoriert.')

    # Vorberechnung: gesperrte Tage und Wochenenden je Team (fuer Konsekutiv-Constraint)
    days_set = set(days)
    blocked_per_team: dict = {ti: set() for ti in range(n)}
    for _team, _bdays in cfg.blocked.items():
        _ti = t_idx.get(_team)
        if _ti is not None:
            blocked_per_team[_ti].update(d for d in _bdays if d in days_set)

    blocked_weekends_per_team: dict = {ti: set() for ti in range(n)}
    for _ti in range(n):
        for _w, _wdays in enumerate(cfg.weekends):
            if any(d in blocked_per_team[_ti] for d in _wdays):
                blocked_weekends_per_team[_ti].add(_w)

    dst_weekends: set = {
        _w for _w, _wdays in enumerate(cfg.weekends)
        if any(d in cfg.dst_days for d in _wdays)
    }

    # Sliding-Window + Switch: nur fuer Standard-Format (gpd=1)
    # needs_bye: bei ungerader Teamzahl hat je Spieltag ein Team spielfrei (home=0 am Bye-Tag).
    # Die >=1-Schranken muessen dann konditionalisiert werden: nur erzwingen wenn alle
    # Tage im Fenster tatsaechlich gespielt werden (sonst zaehlt der Bye-Tag als "away").

    if gpd == 1:
        for ti in range(n):
            for w, wdays in enumerate(cfg.weekends):
                model.Add(homeW[ti, w] == home[ti, wdays[0]])
        if num_weekends >= 4:
            for ti in range(n):
                for w in range(num_weekends - 3):
                    seg = [homeW[ti, w + k] for k in range(4)]
                    model.Add(sum(seg) <= 3)
                    if (not any((w + k) in blocked_weekends_per_team[ti] for k in range(4))
                            and not any((w + k) in dst_weekends for k in range(4))):
                        if needs_bye:
                            # Erzwinge >= 1 nur wenn alle 4 Spieltage der Wochen tatsaechlich gespielt
                            _plays = sum(
                                sum(x[m, d] for m in range(num_matches) if team_in_match[ti][m])
                                for k in range(4) for d in cfg.weekends[w + k]
                            )
                            model.Add(sum(seg) >= _plays - 3)
                        else:
                            model.Add(sum(seg) >= 1)

        # 3-Wochenend-Fenster: max 2 von 3 aufeinanderfolgenden Wochenenden gleich.
        # Ohne diesen Check entsteht ein 5-in-Folge-Muster: DST-Block + Einzeltag + DST-Block
        # (alle mit gleichem Heimrecht) – weil alle Einzelspieltag-Fenster DST-Tage enthalten
        # und dadurch übersprungen werden.
        if num_weekends >= 3:
            for ti in range(n):
                for w in range(num_weekends - 2):
                    seg = [homeW[ti, w + k] for k in range(3)]
                    model.Add(sum(seg) <= 2)
                    if not any((w + k) in blocked_weekends_per_team[ti] for k in range(3)):
                        if needs_bye:
                            _plays = sum(
                                sum(x[m, d] for m in range(num_matches) if team_in_match[ti][m])
                                for k in range(3) for d in cfg.weekends[w + k]
                            )
                            model.Add(sum(seg) >= _plays - 2)
                        else:
                            model.Add(sum(seg) >= 1)

        for ti in range(n):
            for d in range(1, N):
                model.Add(switch[ti, d] >= home[ti, d]     - home[ti, d + 1])
                model.Add(switch[ti, d] >= home[ti, d + 1] - home[ti, d])
                model.Add(switch[ti, d] <= home[ti, d]     + home[ti, d + 1])
                model.Add(switch[ti, d] <= 2 - home[ti, d] - home[ti, d + 1])
            model.Add(sw_count[ti] == sum(switch[ti, d] for d in range(1, N)))
    else:
        # Turniertag: Switch nicht relevant, sw_count auf 0 fixieren
        for ti in range(n):
            for d in range(1, N):
                model.Add(switch[ti, d] == 0)
            model.Add(sw_count[ti] == 0)

    model.AddMaxEquality(max_sw, [sw_count[ti] for ti in range(n)])
    model.AddMinEquality(min_sw, [sw_count[ti] for ti in range(n)])

    # Konsekutiv-Constraint: max 2 gleiche Heim/Auswaerts hintereinander (nur gpd=1)
    dst_day_set = cfg.dst_days
    if gpd == 1:
        # Standard: Pruefe auf Spieltag-Ebene, DST-Ausnahme erlaubt Fenster-3
        for ti in range(n):
            for ki in range(N - 2):
                d0, d1, d2 = days[ki], days[ki + 1], days[ki + 2]
                if not (d0 in dst_day_set or d1 in dst_day_set or d2 in dst_day_set):
                    seg = [home[ti, d0], home[ti, d1], home[ti, d2]]
                    model.Add(sum(seg) <= 2)   # nicht 3x Heim
                    # "nicht 3x Auswaerts" nur wenn kein Tag durch Sperre erzwungen away
                    if not any(d in blocked_per_team[ti] for d in (d0, d1, d2)):
                        if needs_bye:
                            # Spielfrei-Tag zaehlt als home=0; nur erzwingen wenn alle 3 Tage gespielt
                            _plays = sum(
                                sum(x[m, d] for m in range(num_matches) if team_in_match[ti][m])
                                for d in (d0, d1, d2)
                            )
                            model.Add(sum(seg) >= _plays - 2)
                        else:
                            model.Add(sum(seg) >= 1)
            for ki in range(N - 3):
                d0, d1, d2, d3 = days[ki], days[ki + 1], days[ki + 2], days[ki + 3]
                if d0 in dst_day_set or d1 in dst_day_set or d2 in dst_day_set or d3 in dst_day_set:
                    continue  # DST-Tage überspringen: back-to-back-DST-Blöcke (z.B. (1,2)(3,4))
                              # würden sonst die Heimteam-Sets beider Blöcke zur Disjunktheit zwingen
                              # → mathematisch unlösbar (Hinrunde braucht 12 Slots, nur 9 verfügbar)
                seg = [home[ti, d0], home[ti, d1], home[ti, d2], home[ti, d3]]
                model.Add(sum(seg) <= 3)   # nicht 4x Heim
                if not any(d in blocked_per_team[ti] for d in (d0, d1, d2, d3)):
                    if needs_bye:
                        _plays = sum(
                            sum(x[m, d] for m in range(num_matches) if team_in_match[ti][m])
                            for d in (d0, d1, d2, d3)
                        )
                        model.Add(sum(seg) >= _plays - 3)
                    else:
                        model.Add(sum(seg) >= 1)   # nicht 4x Auswaerts
        # DST-Nachbarschaft: max 3 in Folge rund um DST-Blöcke (Constraints A/B/C)
        # Verhindert: pre2+pre1+DST(2), DST(2)+post1+post2, pre1+DST(2)+post1 = je 4 in Folge
        # needs_bye: bei ungerader Teamzahl ist home[ti, d] = 0 erzwungen an Bye-Tagen.
        # Wenn DST + pre1 + post1 (oder analog) alle Bye-Tage sind, wäre 0+0 >= 1 INFEASIBLE.
        # Fix: bei needs_bye die >=1-Schranke konditionalisieren auf tatsächlich gespielte Tage.
        def _plays_expr(ti_, d_):
            """Sum(x[m,d_]) über alle Matches von ti_ — 0 falls ti_ Bye, 1 sonst (gpd==1)."""
            return sum(x[m, d_] for m in range(num_matches) if team_in_match[ti_][m])

        if cfg.dst_blocks:
            _non_dst = [d for d in days if d not in dst_day_set]
            for ti in range(n):
                for _d1, _d2 in cfg.dst_blocks:
                    if _d1 not in days_set or _d2 not in days_set:
                        continue
                    h_dst = home[ti, _d1]
                    _pres  = [d for d in _non_dst if d < _d1]
                    _posts = [d for d in _non_dst if d > _d2]
                    pre1  = _pres[-1] if len(_pres) >= 1 else None
                    pre2  = _pres[-2] if len(_pres) >= 2 else None
                    post1 = _posts[0] if len(_posts) >= 1 else None
                    post2 = _posts[1] if len(_posts) >= 2 else None
                    # A: pre1 und post1 nicht beide gleich DST
                    if pre1 is not None and post1 is not None:
                        model.Add(home[ti, pre1] + home[ti, post1] <= 1).OnlyEnforceIf(h_dst)
                        if not any(d in blocked_per_team[ti] for d in (pre1, post1)):
                            if needs_bye:
                                _p = _plays_expr(ti, pre1) + _plays_expr(ti, post1)
                                model.Add(home[ti, pre1] + home[ti, post1] >= _p - 1).OnlyEnforceIf(h_dst.Not())
                            else:
                                model.Add(home[ti, pre1] + home[ti, post1] >= 1).OnlyEnforceIf(h_dst.Not())
                    # B: post1 und post2 nicht beide gleich DST
                    if post1 is not None and post2 is not None:
                        model.Add(home[ti, post1] + home[ti, post2] <= 1).OnlyEnforceIf(h_dst)
                        if not any(d in blocked_per_team[ti] for d in (post1, post2)):
                            if needs_bye:
                                _p = _plays_expr(ti, post1) + _plays_expr(ti, post2)
                                model.Add(home[ti, post1] + home[ti, post2] >= _p - 1).OnlyEnforceIf(h_dst.Not())
                            else:
                                model.Add(home[ti, post1] + home[ti, post2] >= 1).OnlyEnforceIf(h_dst.Not())
                    # C: pre2 und pre1 nicht beide gleich DST
                    if pre2 is not None and pre1 is not None:
                        model.Add(home[ti, pre2] + home[ti, pre1] <= 1).OnlyEnforceIf(h_dst)
                        if not any(d in blocked_per_team[ti] for d in (pre2, pre1)):
                            if needs_bye:
                                _p = _plays_expr(ti, pre2) + _plays_expr(ti, pre1)
                                model.Add(home[ti, pre2] + home[ti, pre1] >= _p - 1).OnlyEnforceIf(h_dst.Not())
                            else:
                                model.Add(home[ti, pre2] + home[ti, pre1] >= 1).OnlyEnforceIf(h_dst.Not())
    # Turniertag (gpd>1): kein Konsekutiv-Constraint noetig

    if not is_turniertag:
        # Standort-Constraints (nur Standard-Format, gpd=1)
        # <=1 statt ==1: bei Spielfrei-Tagen (ungerade Teams) sind alle loc=0 – das ist korrekt.
        for ti in range(n):
            for d in days:
                model.Add(sum(loc[ti, d, i] for i in range(n)) <= 1)
                by_loc = {i: [] for i in range(n)}
                for m, is_A, ai, bi in team_matches[ti]:
                    if is_A:
                        by_loc[ai].append(yA[m, d])
                        by_loc[bi].append(yB[m, d])
                    else:
                        by_loc[bi].append(yB[m, d])
                        by_loc[ai].append(yA[m, d])
                for i, terms in by_loc.items():
                    model.Add(loc[ti, d, i] == (sum(terms) if terms else 0))

        # Reise-Constraints
        for ti in range(n):
            parts = []
            for d in range(1, N):
                for i in range(n):
                    dist_terms = [dist_int[i, j] * loc[ti, d + 1, j]
                                  for j in range(n) if dist_int[i, j] > 0]
                    if not dist_terms:
                        continue
                    contrib = model.NewIntVar(0, travel_ub, f'{p}c_{ti}_{d}_{i}')
                    model.Add(contrib == sum(dist_terms)).OnlyEnforceIf(loc[ti, d, i])
                    model.Add(contrib == 0).OnlyEnforceIf(loc[ti, d, i].Not())
                    parts.append(contrib)
            model.Add(travel[ti] == (sum(parts) if parts else 0))

        # DST-Routing
        if cfg.apply_routing and cfg.dst_blocks:
            for ti in range(n):
                for d1, d2 in cfg.dst_blocks:
                    for i in range(n):
                        if dist_int[ti, i] == 0:
                            continue
                        for j in range(n):
                            lhs = (dist_int[i, j] + dist_int[j, ti]) * cfg.f_den
                            rhs = cfg.f_num * dist_int[ti, i]
                            if lhs > rhs:
                                model.Add(loc[ti, d2, j] == 0).OnlyEnforceIf(
                                    [loc[ti, d1, i], home[ti, d1].Not()])

        # DST-Reiseeffizienz: reward pairing long-distance away trips in the same DST block
        # gain(ti, i, j) = dist(home_ti, i) + dist(home_ti, j) - dist(i, j)
        # positive when i and j are close to each other but far from ti's home
        dst_eff_total = None
        if cfg.dst_blocks and cfg.w_scaled.get('dst_eff', 0.0) > 0:
            dst_eff_terms = []
            for ti in range(n):
                for d1, d2 in cfg.dst_blocks:
                    if d1 not in days_set or d2 not in days_set:
                        continue
                    for i in range(n):
                        if i == ti:
                            continue
                        dti_i = int(dist_int[ti, i])
                        if dti_i >= UNREACHABLE_KM:
                            continue
                        for j in range(n):
                            if j == ti or j == i:
                                continue
                            dti_j = int(dist_int[ti, j])
                            di_j  = int(dist_int[i, j])
                            if dti_j >= UNREACHABLE_KM or di_j >= UNREACHABLE_KM:
                                continue
                            gain = dti_i + dti_j - di_j
                            if gain <= 0:
                                continue
                            z = model.NewBoolVar(f'{p}ze_{ti}_{d1}_{d2}_{i}_{j}')
                            model.Add(z <= loc[ti, d1, i])
                            model.Add(z <= loc[ti, d2, j])
                            model.Add(z >= loc[ti, d1, i] + loc[ti, d2, j] - 1)
                            dst_eff_terms.append(gain * z)
            if dst_eff_terms:
                finite = dist_int[dist_int < UNREACHABLE_KM]
                max_d  = int(finite.max()) if len(finite) > 0 else 1000
                ub_eff = max(1, n * len(cfg.dst_blocks) * 2 * max_d)
                dst_eff_total = model.NewIntVar(0, ub_eff, f'{p}dst_eff_tot')
                model.Add(dst_eff_total == sum(dst_eff_terms))
    else:
        # Turniertag: kein Standort-Modell, Reise auf 0 setzen
        for ti in range(n):
            model.Add(travel[ti] == 0)
        dst_eff_total = None

    model.AddMaxEquality(max_travel, [travel[ti] for ti in range(n)])
    model.AddMinEquality(min_travel, [travel[ti] for ti in range(n)])

    # ── Stufe 2: Gruppenformation ────────────────────────────────────────────
    if K > 0:
        in_g = {(ti, d, g): model.NewBoolVar(f'{p}ing_{ti}_{d}_{g}')
                for ti in range(n) for d in days for g in range(G)}
        play_in_g = {(m, d, g): model.NewBoolVar(f'{p}pig_{m}_{d}_{g}')
                     for m in range(num_matches) for d in days for g in range(G)}

        # Jedes Team in max. 1 Gruppe pro Tag
        for ti in range(n):
            for d in days:
                model.Add(sum(in_g[ti, d, g] for g in range(G)) <= 1)

        # Genau K Teams pro Gruppe pro Tag
        for d in days:
            for g in range(G):
                model.Add(sum(in_g[ti, d, g] for ti in range(n)) == K)

        # Co-location: x[m,d] = sum(play_in_g[m,d,g])
        # play_in_g[m,d,g]=1 erfordert beide Teams in Gruppe g am Tag d
        for m, info in enumerate(matches):
            ai, bi = t_idx[info['A']], t_idx[info['B']]
            for d in days:
                model.Add(x[m, d] == sum(play_in_g[m, d, g] for g in range(G)))
                for g in range(G):
                    model.Add(in_g[ai, d, g] >= play_in_g[m, d, g])
                    model.Add(in_g[bi, d, g] >= play_in_g[m, d, g])

        # Spiele pro Team: genau gpd wenn anwesend, sonst 0
        for ti in range(n):
            for d in days:
                pld = model.NewBoolVar(f'{p}pld_{ti}_{d}')
                model.Add(sum(in_g[ti, d, g] for g in range(G)) == pld)
                tm_games = [x[m, d] for m in range(num_matches) if team_in_match[ti][m]]
                model.Add(sum(tm_games) == gpd).OnlyEnforceIf(pld)
                model.Add(sum(tm_games) == 0).OnlyEnforceIf(pld.Not())

        # Obere Schranke fuer Gesamtspiele pro Tag
        for d in days:
            model.Add(sum(x[m, d] for m in range(num_matches)) <= G * K * gpd // 2)

        # Spielfrei-Fairness: wenn n_active < n, sollen alle Teams gleich viele Spielfrei-Tage haben
        n_active = cfg.n_active_per_day if cfg.n_active_per_day > 0 else n
        if n_active < n:
            participate_lo = N * n_active // n
            participate_hi = math.ceil(N * n_active / n)
            for ti in range(n):
                total_part = sum(in_g[ti, d, g] for d in days for g in range(G))
                model.Add(total_part >= participate_lo)
                model.Add(total_part <= participate_hi)

    # Pflichtspiele
    days_set_pin = set(days)
    for pm in cfg.pinned:
        a, b, day = pm['teamA'], pm['teamB'], pm['day']
        home_team = pm.get('home')
        if day not in days_set_pin:
            warn(f'[{prefix}] Pflichtspiel {a} vs. {b}: ST{day} nicht in Spieltagen – ignoriert.')
            continue
        ia, ib    = t_idx.get(a), t_idx.get(b)
        if ia is None or ib is None:
            warn(f'[{prefix}] Pflichtspiel: Team {a!r} oder {b!r} nicht in Liga – ignoriert.')
            continue
        can_a, can_b = (a, b) if ia <= ib else (b, a)
        round_num = min(n_rounds, (day - 1) // max(1, round_len) + 1)
        m = pair_round_to_match.get((can_a, can_b, round_num))
        if m is None:
            warn(f'[{prefix}] Pflichtspiel nicht zuordenbar: {a} vs. {b} ST{day}')
            continue
        model.Add(x[m, day] == 1)
        if home_team:
            if home_team not in (can_a, can_b):
                warn(f'[{prefix}] Pflichtspiel {a} vs. {b}: Heimrecht "{home_team}" unbekannt – ignoriert.')
            else:
                model.Add(h[m] == (0 if home_team == can_a else 1))

    # Heimspiel-Sperrtage (überspringt Tage, die auch Pflichtheim-Tage sind)
    for team, block_days in cfg.blocked.items():
        ti = t_idx.get(team)
        if ti is None:
            continue
        forced_set = set(cfg.forced_home.get(team, []))
        _overridden = [d for d in block_days if d in days and d in forced_set]
        if _overridden:
            warn(f'[{cfg.league_id}] Team {team!r}: Sperrtag(e) {sorted(_overridden)} '
                 f'werden durch Pflichtheim überschrieben (Heimspiel erzwungen).')
        for d in block_days:
            if d in days and d not in forced_set:
                model.Add(home[ti, d] == 0)

    # Heimspiel-Pflichttage
    for team, force_days in cfg.forced_home.items():
        ti = t_idx.get(team)
        if ti is None:
            continue
        for d in force_days:
            if d in days:
                model.Add(home[ti, d] == 1)

    return LeagueVars(
        x=x, h=h, home=home, switch=switch,
        sw_count=sw_count, travel=travel,
        max_sw=max_sw, min_sw=min_sw,
        max_travel=max_travel, min_travel=min_travel,
        team_idx=t_idx, matches=matches, days=days,
        dst_eff_total=dst_eff_total,
    )


# ── Zielfunktion ─────────────────────────────────────────────────────────────

def add_league_objective(model, lv: LeagueVars, cfg: LeagueConfig,
                          hier_weight: float = 1.0,
                          coef_scale: int = 1000) -> list:
    """Gibt eine Liste von Zielfunktionstermen zurueck (noch nicht addiert).

    Der Aufrufer summiert alle Terme aus allen Ligen und ruft model.Maximize().
    """
    n = cfg.n_teams
    days = lv.days
    N = cfg.n_matchdays

    W = {k: int(round(v * coef_scale * hier_weight)) for k, v in cfg.w_scaled.items()}

    is_tt = cfg.games_per_team_per_day > 1 or cfg.n_teams_per_group > 0
    if is_tt:
        total_switch  = 0
        switch_spread = 0
    else:
        total_switch  = sum(lv.switch[ti, d] for ti in range(n) for d in range(1, N))
        switch_spread = lv.max_sw - lv.min_sw
    total_travel  = sum(lv.travel[ti]    for ti in range(n))
    travel_spread = lv.max_travel - lv.min_travel

    terms = [
         W['switch']    * total_switch,
        -W['sw_fair']   * switch_spread,
        -W['travel']    * total_travel,
        -W['trav_fair'] * travel_spread,
    ]
    if lv.dst_eff_total is not None and W.get('dst_eff', 0) > 0:
        terms.append(W['dst_eff'] * lv.dst_eff_total)
    return terms


# ── Ergebnis-Extraktion ──────────────────────────────────────────────────────

def extract_schedule(solver: cp_model.CpSolver,
                     lv: LeagueVars) -> Dict[int, List[Tuple[str, str]]]:
    schedule = {d: [] for d in lv.days}
    for m, info in enumerate(lv.matches):
        a, b = info['A'], info['B']
        for d in lv.days:
            if solver.BooleanValue(lv.x[m, d]):
                ht, at = (a, b) if not solver.BooleanValue(lv.h[m]) else (b, a)
                schedule[d].append((ht, at))
                break
    return schedule


def extract_groups(schedule: Dict[int, List[Tuple[str, str]]],
                   cfg: LeagueConfig) -> Dict[int, List[List[str]]]:
    """Rekonstruiert Gruppen-Zuweisung aus Schedule (nur fuer Stufe 2: K>0).

    Nutzt zusammenhaengende Komponenten des Spielgraphen pro Tag.
    """
    if cfg.n_teams_per_group <= 0:
        return {}
    groups: Dict[int, List[List[str]]] = {}
    for day, matches in schedule.items():
        adj: Dict[str, set] = {t: set() for t in cfg.teams}
        for ht, at in matches:
            adj[ht].add(at)
            adj[at].add(ht)
        visited: set = set()
        day_groups: List[List[str]] = []
        for team in cfg.teams:
            if team in visited or not adj[team]:
                continue
            component: List[str] = []
            stack = [team]
            while stack:
                t = stack.pop()
                if t in visited:
                    continue
                visited.add(t)
                component.append(t)
                stack.extend(adj[t] - visited)
            day_groups.append(sorted(component))
        day_groups.sort(key=lambda g: g[0])
        groups[day] = day_groups
    return groups


def extract_statistics(solver: cp_model.CpSolver,
                       lv: LeagueVars,
                       cfg: LeagueConfig):
    sw_counts, sw_rates, travels = [], [], []
    for ti in range(cfg.n_teams):
        sc = solver.Value(lv.sw_count[ti])
        tr = solver.Value(lv.travel[ti])
        sw_counts.append(sc)
        sw_rates.append(sc / cfg.n_transitions * 100 if cfg.n_transitions > 0 else 0.0)
        travels.append(tr)
    return sw_counts, sw_rates, travels


def extract_hints(solver: cp_model.CpSolver,
                  lv: LeagueVars) -> Tuple[dict, dict, dict]:
    """Extrahiert alle BoolVar-Werte fuer Phase-2-Warm-Start."""
    home_vals = {k: solver.Value(v) for k, v in lv.home.items()}
    h_vals    = {m: solver.Value(v) for m, v in lv.h.items()}
    x_vals    = {k: solver.Value(v) for k, v in lv.x.items()}
    return home_vals, h_vals, x_vals


def set_hints(model: cp_model.CpModel,
              lv: LeagueVars,
              result: 'LeagueResult') -> None:
    """Setzt Phase-1-Loesungswerte als Hints in Phase-2-Modell."""
    for k, val in result.home_vals.items():
        if k in lv.home:
            model.AddHint(lv.home[k], val)
    for m, val in result.h_vals.items():
        if m in lv.h:
            model.AddHint(lv.h[m], val)
    for k, val in result.x_vals.items():
        if k in lv.x:
            model.AddHint(lv.x[k], val)


# ── Fortschritts-Callback ────────────────────────────────────────────────────

class _ProgressCallback(cp_model.CpSolverSolutionCallback):
    """Gibt bei jeder neuen Bestlösung eine [BEST]-Zeile auf stdout aus.

    Da stdout im Worker-Thread auf _QueueWriter umgeleitet wird, landen
    diese Zeilen automatisch im Streamlit-Log und können dort geparst werden.
    """

    def __init__(self, lid: str, name: str, t0: float):
        super().__init__()
        self._lid   = lid
        self._name  = name
        self._t0    = t0
        self._best  = None
        self._count = 0

    def on_solution_callback(self):
        self._count += 1
        obj     = self.ObjectiveValue()
        elapsed = time.time() - self._t0
        mins, secs = int(elapsed // 60), int(elapsed % 60)
        delta = ''
        if self._best is not None and abs(self._best) > 0:
            delta = f'  d{(obj - self._best) / abs(self._best) * 100:+.1f}%'
        self._best = obj
        sys.stdout.write(
            f'[BEST] {self._lid}  obj={obj:.0f}  t={mins:02d}:{secs:02d}{delta}'
            f'  (#{self._count})\n'
        )
        sys.stdout.flush()


# ── Phase-1: Einzelliga-Lauf ─────────────────────────────────────────────────

def solve_league_phase1(cfg: LeagueConfig,
                        time_limit: int = 900,
                        seed: int = 42,
                        rel_gap: float = 0.05,
                        num_workers: int = 0) -> Optional[LeagueResult]:
    """Loest eine einzelne Liga unabhaengig (Phase 1)."""
    step(f'Phase 1 – {cfg.name} ({cfg.n_teams} Teams, {cfg.n_matchdays} Spieltage) ...')

    model = cp_model.CpModel()
    lv    = build_league_vars(model, cfg, prefix='')
    obj   = add_league_objective(model, lv, cfg, hier_weight=1.0)
    model.Maximize(sum(obj))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds  = time_limit
    solver.parameters.num_search_workers   = num_workers if num_workers > 0 else min(8, os.cpu_count() or 1)
    solver.parameters.log_search_progress  = False
    solver.parameters.random_seed          = seed
    solver.parameters.symmetry_level       = 1
    solver.parameters.max_memory_in_mb     = 4096
    if rel_gap > 0:
        solver.parameters.relative_gap_limit = rel_gap

    t0       = time.time()
    callback = _ProgressCallback(cfg.league_id, cfg.name, t0)
    status   = solver.Solve(model, callback)
    elapsed = time.time() - t0
    mins, secs = int(elapsed // 60), int(elapsed % 60)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        warn(f'Keine Loesung fuer {cfg.league_id} in Phase 1 '
             f'({solver.StatusName(status)}).')
        return None

    ok(f'  {cfg.league_id}: {solver.StatusName(status)}  '
       f'obj={solver.ObjectiveValue():.0f}  t={mins:02d}:{secs:02d}')

    schedule            = extract_schedule(solver, lv)
    sw_counts, sw_rates, travels = extract_statistics(solver, lv, cfg)
    home_vals, h_vals, x_vals   = extract_hints(solver, lv)
    groups              = extract_groups(schedule, cfg)

    return LeagueResult(
        league_id=cfg.league_id,
        status=status,
        objective=solver.ObjectiveValue(),
        schedule=schedule,
        sw_counts=sw_counts,
        sw_rates=sw_rates,
        travels=travels,
        mins=mins, secs=secs,
        home_vals=home_vals,
        h_vals=h_vals,
        x_vals=x_vals,
        cfg=cfg,
        groups=groups,
    )
