"""Phase-3-Nachbearbeitung per Simulated Annealing.

Optimiert Heimrecht-Zuweisungen ohne das Spielplangeruest zu aendern.
Jede Paarung (A, B) hat eine Hin- und eine Rueckbegegnung. SA tauscht
paarweise Heimrecht (Hin flippt → Rueck gespiegelt) und akzeptiert
Aenderungen per Metropolis-Kriterium.

Typische Verbesserung: 3-8% weniger Gesamtkilometer bei gleichwertigen
Wechselzahlverteilungen (gleiche Wandzeit wie Phase 1 pro Liga).
"""
from __future__ import annotations

import math
import random
import time
from typing import Dict, List, Tuple

import numpy as np

from .league_types import LeagueConfig, LeagueResult
from .ui import step, ok


# ── Kern-Hilfsfunktionen ─────────────────────────────────────────────────────

def _is_home(loc_val: int, ti: int) -> bool:
    return loc_val == ti


def _recompute_team(loc: List[List[int]], ti: int, N: int,
                    dist: np.ndarray) -> Tuple[int, int]:
    """Gibt (sw_count, travel_km) fuer ein einzelnes Team zurueck."""
    sw, km = 0, 0
    for d in range(1, N):
        sw += 1 if _is_home(loc[ti][d], ti) != _is_home(loc[ti][d + 1], ti) else 0
        km += int(dist[loc[ti][d], loc[ti][d + 1]])
    return sw, km


def _objective(sw_count: List[int], travel: List[int], w: dict,
               dst_eff_total: int = 0) -> float:
    """Gewichtete Zielfunktion (identisch mit CP-SAT-Formel, Skala 1000).

    `dst_eff_total` ist während eines SA-Laufs konstant (SA überspringt
    DST-Tage), wird aber für Wert-Konsistenz zum Phase-2-Objective addiert.
    """
    scale = 1000
    obj = (w['switch']    * scale * sum(sw_count)
            - w['sw_fair']   * scale * (max(sw_count) - min(sw_count))
            - w['travel']    * scale * sum(travel)
            - w['trav_fair'] * scale * (max(travel) - min(travel)))
    if w.get('dst_eff', 0) > 0 and dst_eff_total > 0:
        obj += w['dst_eff'] * scale * dst_eff_total
    return obj


def _compute_dst_eff_total(loc: List[List[int]], n: int,
                            dst_blocks: List[Tuple[int, int]],
                            days_set: set, dist: np.ndarray,
                            unreachable_km: int = 9999) -> int:
    """Summiert dst_eff über alle Teams + DST-Blöcke (Solver-Formel).

    gain(ti, i, j) = dist[ti,i] + dist[ti,j] - dist[i,j] für Team ti auf
    Auswärts-Venues i (d1) und j (d2). Bei Heim-Venue (i==ti oder j==ti) → 0.
    """
    total = 0
    for ti in range(n):
        for d1, d2 in dst_blocks:
            if d1 not in days_set or d2 not in days_set:
                continue
            i = loc[ti][d1]
            j = loc[ti][d2]
            if i == ti or j == ti or i == j:
                continue
            dti_i = int(dist[ti, i])
            dti_j = int(dist[ti, j])
            di_j  = int(dist[i, j])
            if (dti_i >= unreachable_km or dti_j >= unreachable_km
                    or di_j >= unreachable_km):
                continue
            gain = dti_i + dti_j - di_j
            if gain > 0:
                total += gain
    return total


# ── Haupt-Funktion ───────────────────────────────────────────────────────────

def refine_schedule(result: LeagueResult,
                    cfg: LeagueConfig,
                    time_limit: int = 120,
                    seed: int = 42) -> LeagueResult:
    """SA-Nachbearbeitung: optimiert Heimrecht ohne Terminverschiebung.

    Invarianten:
      - Jedes Team spielt genau einmal pro Spieltag (unveraendert)
      - Jede Paarung hat genau 1 Hin- und 1 Rueckbegegnung (unveraendert)
      - Gepinnte Spiele und DST-Bloecke werden nicht angetastet
      - Sperrtage werden respektiert

    Hinweis zur Reproduzierbarkeit: Die Hauptschleife ist zeitgesteuert
    (`while time.time() - t0 < time_limit`), nicht iterationsgesteuert.
    Bei gleichem `seed` liefert sie auf einer Maschine reproduzierbare
    Ergebnisse, kann aber auf unterschiedlich schnellen Maschinen
    unterschiedlich viele Iterationen durchlaufen und damit andere
    Loesungen finden. Fuer strikt reproduzierbare Ergebnisse muesste
    auf iterationsbasiertes Abbruchkriterium umgestellt werden.
    """
    if time_limit <= 0 or not result.schedule:
        return result
    if cfg.games_per_team_per_day > 1 or cfg.n_teams_per_group > 0:
        return result  # Turniertag: keine SA-Optimierung (travel=0, switches=0)
    if cfg.n_rounds not in (1, 2):
        from .ui import info as _info
        _info(f'SA-Refine: n_rounds={cfg.n_rounds} – uebersprungen (nur Einfach-/Hin-Rueckrunde).')
        return result

    n             = cfg.n_teams
    N             = cfg.n_matchdays
    dist          = cfg.dist
    hinrunde_end  = cfg.hinrunde_end
    t_idx         = {t: i for i, t in enumerate(cfg.teams)}

    # ── Zustand aufbauen: loc[team][day] = venue_index ───────────────────────
    # venue_index = Index des Heimteams, an dessen Halle gespielt wird
    loc: List[List[int]] = [[ti] * (N + 2) for ti in range(n)]
    for d, games in result.schedule.items():
        for ht, at in games:
            hi   = t_idx.get(ht, -1)
            ai_t = t_idx.get(at, -1)
            if hi < 0 or ai_t < 0:
                continue
            loc[hi][d]   = hi   # Heimteam an eigenem Standort
            loc[ai_t][d] = hi   # Gastteam am Standort des Heimteams

    # ── Paarungsdaten ─────────────────────────────────────────────────────────
    # pair_info[pid] = (low_idx, high_idx, hin_day, rueck_day)
    # a_home_hin[pid]: True ↔ low_idx hat in der Hinrunde Heimrecht
    pair_info: List[Tuple[int, int, int, int]] = []
    a_home_hin: List[bool]                      = []
    key_to_pid: Dict[Tuple[int, int], int]      = {}

    for d in range(1, N + 1):
        for ht, at in result.schedule.get(d, []):
            hi, ai_t = t_idx.get(ht, -1), t_idx.get(at, -1)
            if hi < 0 or ai_t < 0:
                continue
            low, high = min(hi, ai_t), max(hi, ai_t)
            phase = 'hin' if d <= hinrunde_end else 'rueck'
            if (low, high) not in key_to_pid:
                pid = len(pair_info)
                key_to_pid[(low, high)] = pid
                pair_info.append((low, high, 0, 0))
                a_home_hin.append(False)
            pid = key_to_pid[(low, high)]
            li, hi_p, h_d, r_d = pair_info[pid]
            if phase == 'hin':
                pair_info[pid] = (li, hi_p, d, r_d)
                a_home_hin[pid] = (hi == li)
            else:
                pair_info[pid] = (li, hi_p, h_d, d)

    n_pairs = len(pair_info)

    if n_pairs == 0:
        return result

    # ── Verbotene Swaps ───────────────────────────────────────────────────────
    dst_days = cfg.dst_days

    blocked_by: Dict[int, set] = {
        t_idx[t]: set(days)
        for t, days in cfg.blocked.items() if t in t_idx
    }

    forced_by: Dict[int, set] = {
        t_idx[t]: set(fdays)
        for t, fdays in cfg.forced_home.items() if t in t_idx
    }

    pinned_set: set = set()
    for pm in cfg.pinned:
        a_name, b_name = pm.get('teamA', ''), pm.get('teamB', '')
        if a_name in t_idx and b_name in t_idx:
            low  = min(t_idx[a_name], t_idx[b_name])
            high = max(t_idx[a_name], t_idx[b_name])
            if (low, high) in key_to_pid:
                pinned_set.add(key_to_pid[(low, high)])

    # ── Initiale Statistiken ──────────────────────────────────────────────────
    sw_count = [0] * n
    travel   = [0] * n
    for ti in range(n):
        sw_count[ti], travel[ti] = _recompute_team(loc, ti, N, dist)

    # dst_eff_total: konstant während SA (SA überspringt DST-Tage), einmal
    # vorausberechnen für Objective-Konsistenz mit Phase 2.
    _days_set = set(cfg.days)
    dst_eff_total = _compute_dst_eff_total(loc, n, cfg.dst_blocks, _days_set, dist)

    current_obj = _objective(sw_count, travel, cfg.w_scaled, dst_eff_total)
    best_obj    = current_obj
    best_loc    = [row[:] for row in loc]
    best_sw     = sw_count[:]
    best_km     = travel[:]

    step(f'SA-Refine – {cfg.name}: '
         f'obj={best_obj:.0f}  km={sum(travel)}  sw={sum(sw_count)}')

    # ── Temperatur-Sampling ───────────────────────────────────────────────────
    rng     = random.Random(seed)
    samples: List[float] = []

    for _ in range(min(400, n_pairs * 6)):
        pid = rng.randrange(n_pairs)
        if pid in pinned_set:
            continue
        ai, bi, hd, rd = pair_info[pid]
        if hd in dst_days or rd in dst_days:
            continue
        new_hv = bi if a_home_hin[pid] else ai
        new_rv = ai if a_home_hin[pid] else bi
        old_hv = ai if a_home_hin[pid] else bi
        old_rv = bi if a_home_hin[pid] else ai
        if hd in blocked_by.get(new_hv, set()) or rd in blocked_by.get(new_rv, set()):
            continue
        if hd in forced_by.get(old_hv, set()) or rd in forced_by.get(old_rv, set()):
            continue
        # Probe-Swap
        # R8-B-L3: rd==0 ist Sentinel für "kein Rückspiel" (Einfachrunde) —
        # _recompute_team ignoriert Position 0 ohnehin, aber wir schreiben dort
        # nichts hin, um nicht zu suggerieren, dass dort eine Venue stuende.
        loc[ai][hd] = loc[bi][hd] = new_hv
        if rd > 0:
            loc[ai][rd] = loc[bi][rd] = new_rv
        ns_ai, nk_ai = _recompute_team(loc, ai, N, dist)
        ns_bi, nk_bi = _recompute_team(loc, bi, N, dist)
        ns = sw_count[:]; ns[ai] = ns_ai; ns[bi] = ns_bi
        nk = travel[:];   nk[ai] = nk_ai; nk[bi] = nk_bi
        samples.append(abs(_objective(ns, nk, cfg.w_scaled, dst_eff_total) - current_obj))
        # Revert
        loc[ai][hd] = loc[bi][hd] = old_hv
        if rd > 0:
            loc[ai][rd] = loc[bi][rd] = old_rv

    mean_d = sum(samples) / len(samples) if samples else 1000.0
    T      = max(mean_d * 2.0, 1.0)
    T_end  = T * 0.001

    # ── SA-Hauptschleife ──────────────────────────────────────────────────────
    t0         = time.time()
    iterations = 0
    accepted   = 0

    while time.time() - t0 < time_limit:
        iterations += 1
        pid = rng.randrange(n_pairs)

        if pid in pinned_set:
            continue
        ai, bi, hd, rd = pair_info[pid]
        if hd in dst_days or rd in dst_days:
            continue

        # Sperrtag-Check fuer neues Heimrecht
        new_hin_h  = bi if a_home_hin[pid] else ai
        new_ruec_h = ai if a_home_hin[pid] else bi
        if hd in blocked_by.get(new_hin_h,  set()):
            continue
        if rd in blocked_by.get(new_ruec_h, set()):
            continue

        # Pflichttag-Check: aktuelles Heimteam darf nicht auf Pflichttag zu Auswärts werden
        old_hin_h  = ai if a_home_hin[pid] else bi
        old_ruec_h = bi if a_home_hin[pid] else ai
        if hd in forced_by.get(old_hin_h,  set()):
            continue
        if rd in forced_by.get(old_ruec_h, set()):
            continue

        new_hv = bi if a_home_hin[pid] else ai
        new_rv = ai if a_home_hin[pid] else bi
        old_hv = ai if a_home_hin[pid] else bi
        old_rv = bi if a_home_hin[pid] else ai

        # Swap anwenden (temporaer)
        # R8-B-L3: rd==0 = Sentinel (Einfachrunde, kein Rueckspiel) ueberspringen
        loc[ai][hd] = loc[bi][hd] = new_hv
        if rd > 0:
            loc[ai][rd] = loc[bi][rd] = new_rv

        ns_ai, nk_ai = _recompute_team(loc, ai, N, dist)
        ns_bi, nk_bi = _recompute_team(loc, bi, N, dist)
        ns = sw_count[:]; ns[ai] = ns_ai; ns[bi] = ns_bi
        nk = travel[:];   nk[ai] = nk_ai; nk[bi] = nk_bi

        new_obj = _objective(ns, nk, cfg.w_scaled, dst_eff_total)
        delta   = new_obj - current_obj

        # Geometrische Abkuehlung
        progress = (time.time() - t0) / time_limit
        T_curr   = T * math.exp(math.log(T_end / T) * progress)

        if delta >= 0 or rng.random() < math.exp(delta / T_curr):
            a_home_hin[pid] = not a_home_hin[pid]
            sw_count        = ns
            travel          = nk
            current_obj     = new_obj
            accepted       += 1
            if current_obj > best_obj:
                best_obj = current_obj
                best_loc = [row[:] for row in loc]
                best_sw  = sw_count[:]
                best_km  = travel[:]
        else:
            loc[ai][hd] = loc[bi][hd] = old_hv
            if rd > 0:
                loc[ai][rd] = loc[bi][rd] = old_rv

    # ── Schedule aus bestem Zustand rekonstruieren ────────────────────────────
    schedule: Dict[int, List[Tuple[str, str]]] = {d: [] for d in range(1, N + 1)}
    for ai, bi, hd, rd in pair_info:
        for d, venue in ((hd, best_loc[ai][hd]), (rd, best_loc[ai][rd])):
            if d == 0:   # Einfachrunde: kein Rueckspiel (rd=0 als Sentinel)
                continue
            if venue == ai:
                schedule[d].append((cfg.teams[ai], cfg.teams[bi]))
            else:
                schedule[d].append((cfg.teams[bi], cfg.teams[ai]))

    # home_vals aus dem neuen schedule rekonstruieren (gleicher Pattern wie
    # _session_from_json in app.py): SA tauscht Heimrecht von Paaren, also
    # ist result.home_vals nach SA stale. Heatmap, Excel-Heatmap und
    # recompute_result_stats lesen home_vals → falsche Anzeige ohne diesen Fix.
    new_home_vals: Dict = {}
    for d, games in schedule.items():
        for ht, at in games:
            hi = t_idx.get(ht, -1)
            ai_t = t_idx.get(at, -1)
            if hi >= 0:
                new_home_vals[(hi, d)] = 1
            if ai_t >= 0:
                new_home_vals[(ai_t, d)] = 0

    km_delta = sum(best_km) - sum(result.travels)
    accept_rate = accepted / iterations if iterations > 0 else 0.0
    ok(f'  {cfg.league_id}: km {sum(result.travels)} -> {sum(best_km)} '
       f'({km_delta:+d})  sw {sum(result.sw_counts)} -> {sum(best_sw)}  '
       f'iter={iterations:,}  akzept={accept_rate:.1%}')

    return LeagueResult(
        league_id=result.league_id,
        status=result.status,
        objective=best_obj,
        schedule=schedule,
        sw_counts=best_sw,
        sw_rates=[sc / cfg.n_transitions * 100 if cfg.n_transitions > 0 else 0.0
                  for sc in best_sw],
        travels=best_km,
        mins=result.mins,
        secs=result.secs,
        home_vals=new_home_vals,
        h_vals=result.h_vals,
        x_vals=result.x_vals,
        cfg=result.cfg,
        groups=result.groups,
        hosts=result.hosts,
        game_times=result.game_times,
        # B1/Bonus-4 Hotfix (v1.12.1): Telemetrie-Felder aus Phase 1/2 durchreichen,
        # damit sie nach SA-Refine nicht auf Defaults zurueckspringen.
        gap_history=list(result.gap_history or []),
        best_bound=result.best_bound,
        final_gap=result.final_gap,
        phase2_objective=result.phase2_objective,  # A7-M3: Pre-SA-objective fuer Gap
    )
