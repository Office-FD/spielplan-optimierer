"""Post-processing: Spielreihenfolge innerhalb eines Turniertags bestimmen.

Prioritaet: min_gap (hart) → Ausrichterposition → max_gap (weich).

Fallback-Sequenz bei Unloesbarkeit:
  1. Ausrichterslots + max_gap
  2. Ausrichterslots + relaxierter max_gap
  3. Kein Ausrichter + max_gap
  4. Kein Ausrichter + relaxierter max_gap
  5. Best-Effort Greedy (min_gap-Verletzungen moeglich)
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional, Tuple

from .league_types import LeagueConfig, LeagueResult
from .ui import ok, warn


# ── Ausrichter-Verteilung ─────────────────────────────────────────────────────

def _balance_home_away(
        schedule: Dict[int, List[Tuple[str, str]]],
        host_per_day: Dict[int, str],
        cfg: LeagueConfig) -> None:
    """Gleicht Heim-/Auswärts-Zähler nach Ausrichter-Flip greedy aus.

    Flippt Nicht-Ausrichter-Spiele, bis kein Team mehr als 1 Heimspiel mehr
    hat als ein anderes. Ausrichter-Spiele werden nie verändert.
    Konvergenz garantiert: jeder Flip reduziert die Summe der quadratischen
    Abweichungen strikt (Bedingung home_diff >= 2 sichert das).
    """
    teams = cfg.teams
    n = len(teams)
    t_idx = {t: i for i, t in enumerate(teams)}

    home_count = [0] * n
    for games in schedule.values():
        for ht, at in games:
            hi = t_idx.get(ht, -1)
            if hi >= 0:
                home_count[hi] += 1

    improved = True
    while improved:
        improved = False
        for d in sorted(schedule.keys()):
            host = host_per_day.get(d)
            games = schedule[d]
            for i, (ht, at) in enumerate(games):
                if ht == host or at == host:
                    continue  # Ausrichter-Spiele nicht anruehren
                hi = t_idx.get(ht, -1)
                ai = t_idx.get(at, -1)
                if hi < 0 or ai < 0:
                    continue
                if home_count[hi] - home_count[ai] >= 2:
                    games[i] = (at, ht)
                    home_count[hi] -= 1
                    home_count[ai] += 1
                    improved = True


def _assign_hosts(days: List[int],
                  host_counts: Dict[str, int],
                  teams: List[str]) -> Dict[int, str]:
    """Verteilt Ausrichter auf Spieltage gemaess gewuenschter Anzahl pro Team."""
    pool: List[str] = []
    for team in teams:
        cnt = host_counts.get(team, 0)
        pool.extend([team] * cnt)

    rng = random.Random(42)
    rng.shuffle(pool)

    assignment: Dict[int, str] = {}
    for day, host in zip(sorted(days), pool):
        assignment[day] = host

    # Tage ohne Ausrichter: Round-Robin auffuellen
    unassigned = [d for d in sorted(days) if d not in assignment]
    if unassigned:
        cycle = teams[:]
        rng.shuffle(cycle)
        for i, day in enumerate(unassigned):
            assignment[day] = cycle[i % len(cycle)]

    return assignment


# ── Spielreihenfolge eines Turniertags ────────────────────────────────────────

def _order_day_games(games: List[Tuple[str, str]],
                     host_team: Optional[str],
                     host_slots_0: List[int],
                     min_gap: int,
                     max_gap: int) -> Tuple[List[Tuple[str, str]], bool, int]:
    """Ordnet Spiele eines Turniertags.

    host_slots_0: 0-indexierte Slot-Positionen fuer Ausrichterspiele.
                  Leer = keine Ausrichterpositions-Bedingung.
    Gibt (geordnete_Spiele, host_platziert, effektiver_max_gap) zurueck.
    Prioritaet: min_gap (hart) → Ausrichterposition → max_gap (weich).
    """
    N = len(games)
    if N <= 1:
        return games, bool(host_slots_0 and host_team), max_gap

    # ── Hilfsfunktionen ───────────────────────────────────────────────────────

    def _slot_valid(t: str, slot: int, placed: Dict, mg: int) -> bool:
        all_s = placed.get(t, [])
        prev = [s for s in all_s if s < slot]
        if prev:
            gap = slot - max(prev) - 1
            if gap < min_gap or gap > mg:
                return False
        nxt = [s for s in all_s if s > slot]
        if nxt:
            gap = min(nxt) - slot - 1
            if gap < min_gap or gap > mg:
                return False
        return True

    def _gap_violation(t: str, slot: int, placed: Dict) -> int:
        all_s = placed.get(t, [])
        v = 0
        prev = [s for s in all_s if s < slot]
        if prev:
            gap = slot - max(prev) - 1
            if gap < min_gap:
                v += (min_gap - gap) * 10
            elif gap > max_gap:
                v += gap - max_gap
        nxt = [s for s in all_s if s > slot]
        if nxt:
            gap = min(nxt) - slot - 1
            if gap < min_gap:
                v += (min_gap - gap) * 10
            elif gap > max_gap:
                v += gap - max_gap
        return v

    MAX_NODES = 50_000

    def _backtrack(unfixed: List[int], fi: int,
                   rem: List[Tuple[str, str]],
                   placed: Dict, mg: int,
                   nodes: List[int]) -> Optional[List[Tuple[int, Tuple[str, str]]]]:
        nodes[0] += 1
        if nodes[0] > MAX_NODES:
            return None
        if fi == len(unfixed):
            return [] if not rem else None
        slot = unfixed[fi]

        teams_rem = {t for g in rem for t in g}
        urgent = set()
        for t in teams_rem:
            prev_s = [s for s in placed.get(t, []) if s < slot]
            if prev_s and slot - max(prev_s) - 1 >= mg:
                urgent.add(t)

        candidates = [
            i for i, (ht, at) in enumerate(rem)
            if (not urgent or ht in urgent or at in urgent)
            and _slot_valid(ht, slot, placed, mg)
            and _slot_valid(at, slot, placed, mg)
        ]

        for i in candidates:
            ht, at = rem[i]
            new_rem = rem[:i] + rem[i + 1:]
            new_placed = {k: list(v) for k, v in placed.items()}
            new_placed.setdefault(ht, []).append(slot)
            new_placed.setdefault(at, []).append(slot)
            sub = _backtrack(unfixed, fi + 1, new_rem, new_placed, mg, nodes)
            if sub is not None:
                return [(slot, rem[i])] + sub

        return None

    def _try_solve(target_slots: List[int],
                   mg: int) -> Tuple[Optional[List[Tuple[str, str]]], bool]:
        """Versucht Loesung mit gegebenen Ausrichter-Slots und max_gap.
        Gibt (ordered, feasible) zurueck; (None, False) wenn Slots nicht belegbar.
        """
        # Doppelte Slots sofort ablehnen – wuerden Spiele lautlos ueberschreiben
        if len(set(target_slots)) < len(target_slots):
            return None, False

        slots: List[Optional[Tuple[str, str]]] = [None] * N
        pool = list(games)
        placed_init: Dict[str, List[int]] = {}

        for s in sorted(target_slots):
            if s >= N:
                return None, False
            host_idxs = [i for i, g in enumerate(pool)
                         if host_team and host_team in g]
            if not host_idxs:
                return None, False
            g = pool.pop(host_idxs[0])
            slots[s] = g
            for t in g:
                placed_init.setdefault(t, []).append(s)

        unfixed = [s for s in range(N) if slots[s] is None]
        nodes = [0]
        solution = _backtrack(unfixed, 0, pool, placed_init, mg, nodes)

        if solution is not None:
            for slot, game in solution:
                slots[slot] = game
            return [g for g in slots if g is not None], True

        return None, False

    # ── Fallback-Sequenz ──────────────────────────────────────────────────────

    valid_host_slots = [s for s in host_slots_0
                        if host_team and 0 <= s < N]

    if valid_host_slots:
        # Schritt 1: Ausrichter + max_gap
        ordered, ok_flag = _try_solve(valid_host_slots, max_gap)
        if ok_flag:
            return ordered, True, max_gap

        # Schritt 2: Ausrichter + relaxierter max_gap
        for mg in range(max_gap + 1, N + 1):
            ordered, ok_flag = _try_solve(valid_host_slots, mg)
            if ok_flag:
                return ordered, True, mg

    # Schritt 3: kein Ausrichter + max_gap
    ordered, ok_flag = _try_solve([], max_gap)
    if ok_flag:
        return ordered, False, max_gap

    # Schritt 4: kein Ausrichter + relaxierter max_gap
    for mg in range(max_gap + 1, N + 1):
        ordered, ok_flag = _try_solve([], mg)
        if ok_flag:
            return ordered, False, mg

    # Schritt 5: Best-Effort Greedy (kein Ausrichter, Verletzungen erlaubt)
    slots_be: List[Optional[Tuple[str, str]]] = [None] * N
    pool_be = list(games)
    placed_be: Dict[str, List[int]] = {}
    for slot in range(N):
        if not pool_be:
            break
        best_v, best_i = float('inf'), None
        for i, (ht, at) in enumerate(pool_be):
            v = _gap_violation(ht, slot, placed_be) + _gap_violation(at, slot, placed_be)
            if best_i is None or v < best_v:
                best_v, best_i = v, i
        game = pool_be.pop(best_i)
        slots_be[slot] = game
        for t in game:
            placed_be.setdefault(t, []).append(slot)

    return [g for g in slots_be if g is not None], False, max_gap


# ── Haupt-Funktion ────────────────────────────────────────────────────────────

def apply_tournament_ordering(result: LeagueResult,
                               cfg: LeagueConfig) -> LeagueResult:
    """Wendet Spielreihenfolge-Optimierung auf einen Turniertag-Spielplan an."""
    if cfg.games_per_team_per_day <= 1:
        return result

    tt = cfg.tt_settings
    if not tt:
        return result

    min_gap = int(tt.get('min_gap', 0))
    max_gap = int(tt.get('max_gap', 3))
    host_mode = tt.get('host_mode', 'per_team')

    # Host-Slots (1-indexiert → 0-indexiert)
    # N_eff = tatsaechliche Spielanzahl pro Tag (beruecksichtigt n_active_per_day)
    n_active = cfg.n_active_per_day if cfg.n_active_per_day > 0 else cfg.n_teams
    N_eff = n_active * cfg.games_per_team_per_day // 2
    raw_slots = tt.get('host_slots', None)
    if raw_slots is not None:
        host_slots_0 = [int(s) - 1 for s in raw_slots
                        if s and 1 <= int(s) <= N_eff]
    elif tt.get('host_position', False):
        # Rueckwaertskompatibilitaet: Slot 2 und N-1 (1-indexiert)
        host_slots_0 = [1, N_eff - 2] if N_eff >= 4 else []
    else:
        host_slots_0 = []

    days = sorted(result.schedule.keys())

    if host_mode == 'per_day':
        raw = tt.get('host_per_day', {})
        host_per_day = {int(k): v for k, v in raw.items()}
    else:
        host_counts = tt.get('host_counts', {})
        host_per_day = _assign_hosts(days, host_counts, cfg.teams) if host_counts else {}

    new_schedule: Dict = {}
    infeasible_relaxed: List[Tuple[int, int]] = []   # (day, eff_max_gap)
    infeasible_nohost:  List[int] = []               # Ausrichterpos. nicht einhaltbar

    for d in days:
        games = result.schedule.get(d, [])
        host = host_per_day.get(d)
        if host and not any(host in g for g in games):
            host = None

        # Ausrichter-Slots nur anwenden wenn Ausrichter vorhanden
        hs0 = host_slots_0 if (host and host_slots_0) else []

        ordered, host_placed, eff_max = _order_day_games(
            games, host, hs0, min_gap, max_gap
        )

        if hs0 and not host_placed:
            infeasible_nohost.append(d)
        if eff_max > max_gap:
            infeasible_relaxed.append((d, eff_max))

        # Ausrichter als Heimteam: alle Spiele mit Ausrichter als Gastteam umkehren
        if host:
            ordered = [(at, ht) if at == host else (ht, at) for ht, at in ordered]

        new_schedule[d] = ordered

    if infeasible_relaxed:
        by_mg: Dict[int, List[int]] = {}
        for d, mg in infeasible_relaxed:
            by_mg.setdefault(mg, []).append(d)
        for mg, dys in sorted(by_mg.items()):
            warn(f'{cfg.name}: max_gap={max_gap} an Spieltag(en) {dys} nicht '
                 f'einhaltbar – automatisch auf max_gap={mg} erhoeht '
                 f'(min_gap={min_gap} wird eingehalten).')

    if infeasible_nohost:
        warn(f'{cfg.name}: Ausrichterposition an Spieltag(en) {infeasible_nohost} '
             f'nicht einhaltbar (min_gap={min_gap} hat Vorrang) – ohne Ausrichterpos. geloest.')

    ok(f'{cfg.name}: Spielreihenfolge fuer {len(days)} Turniertage gesetzt '
       f'(min_gap={min_gap}, max_gap={max_gap}, '
       f'Ausrichterslots={[s+1 for s in host_slots_0] if host_slots_0 else "keine"})')

    # Heim/Auswärts nach Ausrichter-Flip ausgleichen (Nicht-Ausrichter-Spiele)
    if host_per_day:
        _balance_home_away(new_schedule, host_per_day, cfg)

    # Tatsaechlich verwendete Ausrichter pro Tag speichern
    used_hosts = {d: host_per_day[d] for d in days
                  if d in host_per_day
                  and any(host_per_day[d] in g for g in new_schedule.get(d, []))}

    # home_vals aus dem korrigierten Spielplan neu berechnen (Ausrichter-Flip einrechnen)
    t_idx_rev = {t: i for i, t in enumerate(cfg.teams)}
    new_home_vals = dict(result.home_vals)
    for d, games in new_schedule.items():
        home_count: Dict[int, int] = {}
        for ht, at in games:
            hi = t_idx_rev.get(ht)
            if hi is not None:
                home_count[hi] = home_count.get(hi, 0) + 1
        for ti in range(len(cfg.teams)):
            new_home_vals[(ti, d)] = home_count.get(ti, 0)

    return LeagueResult(
        league_id=result.league_id,
        status=result.status,
        objective=result.objective,
        schedule=new_schedule,
        sw_counts=result.sw_counts,
        sw_rates=result.sw_rates,
        travels=result.travels,
        mins=result.mins,
        secs=result.secs,
        home_vals=new_home_vals,
        h_vals=result.h_vals,
        x_vals=result.x_vals,
        cfg=result.cfg,
        groups=result.groups,
        hosts=used_hosts,
    )
