"""Regression: per-Team DST-Balance (Reise-Entlastung Randlagen-Teams).

Markierte Teams (`cfg.dst_relief = {team: max_home_dst}`) duerfen weniger Heim-DST
und buendeln dafuer mehr Auswaerts-Doppelspieltage. Diese Tests pruefen:
  1. Mit Relief bleibt das Modell FEASIBLE (auch im Extremfall cap=0).
  2. Der Saison-Cap wird eingehalten (Heim-DST des Teams <= cap).
  3. Das Entlastungs-Team buendelt MEHR Auswaerts-DST als ohne Relief.
  4. Ohne Relief (leeres Dict) ist das Verhalten unveraendert (Standard-Balance).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from spielplan_multi.league_types import LeagueConfig
from spielplan_multi.config import WEIGHT_SCALES
from spielplan_multi.calendar_parser import build_weekends
from spielplan_multi.multi_solver import solve_league_phase1

_PASS = 0


def _check(cond, msg):
    global _PASS
    assert cond, f'FAIL: {msg}'
    print(f'  [PASS] {msg}')
    _PASS += 1


def _make_cfg(relief=None):
    n = 10
    teams = [f'T{i}' for i in range(n)]
    # T0 ist Randlage: weit weg von allen anderen (hohe Distanz), Rest eng beieinander.
    coords = np.array([[0.0, 0.0]] + [[100.0 + i, 5.0 * i] for i in range(1, n)])
    dist = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dist[i, j] = float(np.hypot(*(coords[i] - coords[j])))
    N = 2 * (n - 1)  # 18 Spieltage, round_len=9
    days = list(range(1, N + 1))
    # 2 DST-Bloecke je Runde, mit Abstand (vermeidet Nachbarschafts-Konflikte). 4*2=8 < n=10.
    dst_blocks = [(2, 3), (6, 7), (11, 12), (15, 16)]
    raw = {k: 5.0 for k in WEIGHT_SCALES}
    raw['dst_eff'] = 10.0
    scaled = {k: v * WEIGHT_SCALES[k] for k, v in raw.items()}
    return LeagueConfig(
        league_id='REL', name='Relief-Test', teams=teams, locations=teams,
        dist=dist, dst_blocks=dst_blocks, weekends=build_weekends(days, dst_blocks),
        apply_routing=False, f_num=3, f_den=2, w_scaled=scaled, raw_weights=raw,
        pinned=[], blocked={}, calendar={}, hier_weight=1.0,
        dst_relief=(relief or {}),
    )


def _home_dst_and_aa(result, cfg, team):
    """(#Heim-DST, #Auswaerts-Auswaerts-DST) fuer ein Team aus dem Schedule."""
    idx = {t: i for i, t in enumerate(cfg.teams)}
    sched = result.schedule

    def state(day):
        st = {}
        for ht, at in sched.get(day, []):
            if ht in idx:
                st[ht] = 'H'
            if at in idx:
                st[at] = 'A'
        return st

    home_dst = aa = 0
    for d1, d2 in cfg.dst_blocks:
        s1, s2 = state(d1), state(d2)
        if team in s1 and team in s2:
            if s1[team] == 'H':
                home_dst += 1
            elif s1[team] == 'A' and s2[team] == 'A':
                aa += 1
    return home_dst, aa


def main():
    base = _make_cfg(relief={})
    r_base = solve_league_phase1(base, time_limit=60, seed=42, num_workers=4)
    _check(r_base is not None and r_base.schedule, 'Baseline (kein Relief) ist FEASIBLE')
    base_home, base_aa = _home_dst_and_aa(r_base, base, 'T0')
    _check(base_home == 2, f'Baseline: T0 hat Standard-Balance 2 Heim-DST (ist {base_home})')

    # Relief cap=0 → T0 darf KEIN Heim-DST, alle 4 DST auswaerts.
    rel = _make_cfg(relief={'T0': 0})
    r_rel = solve_league_phase1(rel, time_limit=60, seed=42, num_workers=4)
    _check(r_rel is not None and r_rel.schedule, 'Relief cap=0 bleibt FEASIBLE (kein INFEASIBLE)')
    rel_home, rel_aa = _home_dst_and_aa(r_rel, rel, 'T0')
    _check(rel_home == 0, f'Saison-Cap eingehalten: T0 hat 0 Heim-DST (ist {rel_home})')
    _check(rel_aa > base_aa, f'T0 buendelt mehr Auswaerts-DST mit Relief ({rel_aa}) als ohne ({base_aa})')

    # Relief cap=1 → hoechstens 1 Heim-DST.
    rel1 = _make_cfg(relief={'T0': 1})
    r_rel1 = solve_league_phase1(rel1, time_limit=60, seed=42, num_workers=4)
    _check(r_rel1 is not None and r_rel1.schedule, 'Relief cap=1 bleibt FEASIBLE')
    h1, _ = _home_dst_and_aa(r_rel1, rel1, 'T0')
    _check(h1 <= 1, f'Saison-Cap=1 eingehalten: T0 hat <=1 Heim-DST (ist {h1})')

    print(f'\n  {_PASS}/7 Tests bestanden')
    return 0


if __name__ == '__main__':
    sys.exit(main())
