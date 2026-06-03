"""Regression: Worker-Prozess-Übergabe (Queue + Ergebnis-Pickle).

Hintergrund (Mai 2026): Der Worker schickte das komplette `results`-Objekt über
eine `multiprocessing.Queue`. Bei großen Spielplänen füllt das den ~64 KB-Pipe-
Puffer; der QueueFeederThread blockiert in `_send_bytes` und der Worker hängt
beim Prozess-Ende ewig in `_finalize_join` (join auf den Feeder). Folge: `__DONE__`
erreicht die UI nie, die Optimierung „bleibt in Phase 2 hängen", obwohl längst
fertig gerechnet.

Fix: `results` läuft NUR noch über `last_result.pkl` auf Platte (lokaler,
OneDrive-freier Cache). Über die Queue laufen nur kurze Log-Zeilen + `__DONE__`.

Diese Tests prüfen die Invarianten:
  1. Der Worker beendet sich sauber (kein Hänger beim Exit).
  2. `__DONE__` kommt über die Queue an.
  3. KEIN großes `('__RESULTS__', ...)`-Objekt wandert durch die Queue.
  4. Das Ergebnis liegt als ladbares `last_result.pkl` vor.
"""
import os
import sys
import queue as _queue
import tempfile
import multiprocessing
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from spielplan_multi.league_types import LeagueConfig
from spielplan_multi.config import WEIGHT_SCALES
from spielplan_multi.runtime_paths import run_cache_dir


def _make_config(lid, teams, dist):
    n = len(teams)
    N = 2 * (n - 1)
    raw = {k: 5.0 for k in WEIGHT_SCALES}
    scaled = {k: v * WEIGHT_SCALES[k] for k, v in raw.items()}
    return LeagueConfig(
        league_id=lid, name=f'Test-Liga {lid}', teams=teams, locations=teams,
        dist=dist, dst_blocks=[], weekends=[[d] for d in range(1, N + 1)],
        apply_routing=False, f_num=3, f_den=2, w_scaled=scaled, raw_weights=raw,
        pinned=[], blocked={}, calendar={}, hier_weight=1.0,
    )


def _drain(log_q, proc, timeout_s=90):
    """Liest die Queue leer bis `__DONE__` oder Prozess-Ende; gibt alle Items zurück."""
    import time
    items, done, t0 = [], False, time.time()
    while time.time() - t0 < timeout_s:
        try:
            it = log_q.get(timeout=1.0)
        except _queue.Empty:
            if not proc.is_alive():
                break
            continue
        items.append(it)
        if it == '__DONE__':
            done = True
            break
    return items, done


def main():
    n = 4
    teams = [f'T{i}' for i in range(n)]
    rng = np.arange(n)
    dist = (np.abs(rng[:, None] - rng[None, :]) * 50.0).astype(float)

    cfgs = {'TEST_A': _make_config('TEST_A', teams, dist)}
    solver_cfg = {'p1': 5, 'p2': 5, 'nm': False, 'seeds': 1, 'sa': 0}

    # Cache in ein isoliertes Temp-Verzeichnis umlenken (LOCALAPPDATA wird vom
    # Kindprozess geerbt) – berührt nie den echten Cache des Nutzers.
    tmp = tempfile.mkdtemp(prefix='spielplan_test_')
    os.environ['LOCALAPPDATA'] = tmp
    cache = run_cache_dir(tmp)

    from spielplan_multi._worker import run_solver
    log_q = multiprocessing.Queue()
    proc = multiprocessing.Process(
        target=run_solver,
        args=(cfgs, {}, {}, 5.0, solver_cfg, log_q, str(Path(__file__).resolve().parent)),
        daemon=True,
    )
    proc.start()
    items, done = _drain(log_q, proc)
    proc.join(timeout=30)

    passed = 0

    # 1. Prozess sauber beendet (kein Exit-Hänger)
    assert not proc.is_alive(), 'FAIL: Worker-Prozess hängt nach __DONE__ (Exit-Deadlock!)'
    print('  [PASS] Worker-Prozess beendet sich sauber (kein Exit-Hänger)')
    passed += 1

    # 2. __DONE__ angekommen
    assert done, 'FAIL: __DONE__ kam nicht über die Queue an'
    print('  [PASS] __DONE__ über die Queue empfangen')
    passed += 1

    # 3. Kein großes __RESULTS__-Objekt durch die Queue
    res_msgs = [it for it in items
                if isinstance(it, tuple) and it and it[0] == '__RESULTS__']
    assert not res_msgs, f'FAIL: {len(res_msgs)} __RESULTS__-Objekt(e) in der Queue – Deadlock-Risiko!'
    assert all(isinstance(it, str) for it in items), 'FAIL: Nicht-String in Queue (nur Log-Zeilen erlaubt)'
    print(f'  [PASS] Queue trägt nur kurze Log-Zeilen ({len(items)} Stück), kein __RESULTS__')
    passed += 1

    # 4. Ergebnis als ladbares Pickle vorhanden
    import pickle
    pkl = cache / 'last_result.pkl'
    assert pkl.exists(), f'FAIL: last_result.pkl nicht geschrieben ({pkl})'
    data = pickle.loads(pkl.read_bytes())
    assert 'results' in data and 'TEST_A' in data['results'], 'FAIL: results/TEST_A fehlt im Pickle'
    assert data['results']['TEST_A'] is not None, 'FAIL: TEST_A-Ergebnis ist None'
    print('  [PASS] last_result.pkl geschrieben und ladbar (TEST_A enthalten)')
    passed += 1

    # 5. PID-Datei nach Lauf wieder entfernt (finally-Block lief durch)
    assert not (cache / 'opt_pid.txt').exists(), 'FAIL: opt_pid.txt nicht aufgeräumt'
    print('  [PASS] opt_pid.txt nach Lauf entfernt (finally lief durch)')
    passed += 1

    # Aufräumen
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)

    print(f'\n  {passed}/5 Tests bestanden')
    return 0


if __name__ == '__main__':
    sys.exit(main())
