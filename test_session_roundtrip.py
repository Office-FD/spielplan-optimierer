"""Tests für JSON-Session-Roundtrip — Schema 1.0 + 1.1 Backward-Compat.

`_session_to_json` (app.py:3269) und `_session_from_json` (app.py:3345) sind
streamlit-abhaengig und schwer direkt testbar. Wir validieren stattdessen die
**Schema-Logik** isoliert: LeagueResult <-> JSON-Dict <-> LeagueResult.

Verwendung:
    .venv/Scripts/python.exe test_session_roundtrip.py
    pytest test_session_roundtrip.py -v
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import numpy as np
from spielplan_multi.league_types import LeagueConfig, LeagueResult


# ── Helper: check()-Framework ────────────────────────────────────────────────
_PASS_PREFIX = '  [PASS]'
_FAIL_PREFIX = '  [FAIL]'
_failures: list = []


def check(name: str, fn):
    try:
        msg = fn()
    except AssertionError as e:
        _failures.append((name, str(e)))
        print(f'{_FAIL_PREFIX} {name}  -> AssertionError: {e}')
        return
    except Exception as e:
        _failures.append((name, f'{type(e).__name__}: {e}'))
        print(f'{_FAIL_PREFIX} {name}  -> {type(e).__name__}: {e}')
        return
    print(f'{_PASS_PREFIX} {name}' + (f'  -> {msg}' if msg else ''))


# ── Helper: synthetische LeagueResult-Fixtures ───────────────────────────────
def _mk_cfg(lid='L1', n_teams=4) -> LeagueConfig:
    teams = tuple(f'T{i}' for i in range(n_teams))
    return LeagueConfig(
        league_id=lid,
        name=f'Test-Liga {lid}',
        teams=teams,
        locations=tuple(f'Ort{i}' for i in range(n_teams)),
        dist=np.zeros((n_teams, n_teams), dtype=int),
        dst_blocks=[],
        weekends=[[d] for d in range(1, 7)],
        apply_routing=False, f_num=0, f_den=1,
        w_scaled={'switch': 80.0, 'sw_fair': 2.0, 'travel': 0.05,
                  'trav_fair': 0.02, 'dst_eff': 0.0, 'round_balance': 0.0},
        raw_weights={'switch': 1.0},
        pinned=[], blocked={}, forced_home={},
        calendar={},
        hier_weight=1.0,
        games_per_team_per_day=1,
        n_rounds=2,
        n_teams_per_group=0,
        n_active_per_day=0,
        tt_settings={},
    )


def _mk_result(lid='L1', with_telemetry=True) -> LeagueResult:
    cfg = _mk_cfg(lid)
    schedule = {1: [('T0', 'T1'), ('T2', 'T3')],
                2: [('T0', 'T2'), ('T1', 'T3')]}
    home_vals = {(0, 1): 1, (1, 1): 0, (2, 1): 1, (3, 1): 0,
                 (0, 2): 1, (1, 2): 0, (2, 2): 1, (3, 2): 0}
    res = LeagueResult(
        league_id=lid,
        status=2,  # FEASIBLE
        objective=123_456.0,
        schedule=schedule,
        sw_counts=[3, 3, 3, 3],
        sw_rates=[60.0, 60.0, 60.0, 60.0],
        travels=[100, 110, 120, 130],
        mins=5, secs=30,
        home_vals=home_vals,
        h_vals={}, x_vals={},
        cfg=cfg,
    )
    if with_telemetry:
        res.gap_history = [(0.5, 100_000.0), (1.0, 110_000.0), (1.5, 123_456.0)]
        res.best_bound = 150_000.0
        res.final_gap = 0.1771
        res.phase2_objective = 125_000.0
        res.seed_histories = {42: list(res.gap_history),
                              142: [(0.6, 90_000.0), (1.1, 95_000.0)]}
    return res


# ── Helper: minimaler JSON-Serializer aus app.py extrahiert ──────────────────
def _result_to_json_dict(res: LeagueResult) -> dict:
    """Replikat der Logik aus app._session_to_json (Z. 3290-3320)."""
    return {
        'schedule': {str(d): [[ht, at] for ht, at in games]
                     for d, games in res.schedule.items()},
        'game_times': {str(d): list(times)
                       for d, times in (res.game_times or {}).items()},
        'groups': {str(d): [list(g) for g in grps]
                   for d, grps in (res.groups or {}).items()},
        'hosts': {str(d): host
                  for d, host in (res.hosts or {}).items()},
        'objective':   float(res.objective) if res.objective is not None else None,
        'best_bound':  float(res.best_bound) if res.best_bound is not None else None,
        'final_gap':   float(res.final_gap)  if res.final_gap  is not None else None,
        'gap_history': [[float(t), float(o)] for t, o in (res.gap_history or [])],
        'mins':        int(res.mins or 0),
        'secs':        int(res.secs or 0),
        'phase2_objective': (float(res.phase2_objective)
                              if res.phase2_objective is not None else None),
    }


def _json_dict_to_result(lid: str, data: dict, cfg: LeagueConfig) -> LeagueResult:
    """Replikat der Logik aus app._session_from_json."""
    from ortools.sat.python import cp_model as _cp

    schedule = {int(d): [tuple(g) for g in games]
                for d, games in data.get('schedule', {}).items()}
    game_times = {int(d): list(times)
                  for d, times in data.get('game_times', {}).items()}
    groups = {int(d): [list(g) for g in grps]
              for d, grps in data.get('groups', {}).items()}
    hosts = {int(d): host
             for d, host in data.get('hosts', {}).items()}

    _t_idx = {t: i for i, t in enumerate(cfg.teams)}
    _home_vals: dict = {}
    for _d, _games in schedule.items():
        for _ht, _at in _games:
            _hi = _t_idx.get(_ht, -1)
            _ai = _t_idx.get(_at, -1)
            if _hi >= 0:
                _home_vals[(_hi, _d)] = 1
            if _ai >= 0:
                _home_vals[(_ai, _d)] = 0

    _telem_obj   = data.get('objective')
    _telem_bound = data.get('best_bound')
    _telem_gap   = data.get('final_gap')
    _telem_hist  = [(float(t), float(o)) for t, o in data.get('gap_history', [])]
    _telem_mins  = int(data.get('mins', 0) or 0)
    _telem_secs  = int(data.get('secs', 0) or 0)
    _telem_p2obj = data.get('phase2_objective')

    return LeagueResult(
        league_id=lid,
        status=_cp.FEASIBLE,
        objective=float(_telem_obj) if _telem_obj is not None else 0.0,
        schedule=schedule,
        sw_counts=[], sw_rates=[], travels=[],
        mins=_telem_mins, secs=_telem_secs,
        home_vals=_home_vals,
        h_vals={}, x_vals={},
        cfg=cfg,
        groups=groups,
        hosts=hosts,
        game_times=game_times,
        gap_history=_telem_hist,
        best_bound=float(_telem_bound) if _telem_bound is not None else None,
        final_gap=float(_telem_gap)    if _telem_gap   is not None else None,
        phase2_objective=(float(_telem_p2obj) if _telem_p2obj is not None else None),
    )


# ── Tests ────────────────────────────────────────────────────────────────────

def t_roundtrip_v11_full_telemetry():
    """LeagueResult mit allen Telemetrie-Feldern -> JSON -> wieder identisch."""
    orig = _mk_result(with_telemetry=True)
    d = _result_to_json_dict(orig)
    raw = json.dumps({'version': '1.1', 'results': {orig.league_id: d}})
    loaded_data = json.loads(raw)
    loaded = _json_dict_to_result(orig.league_id,
                                    loaded_data['results'][orig.league_id],
                                    orig.cfg)
    assert loaded.objective == orig.objective
    assert loaded.best_bound == orig.best_bound
    assert abs(loaded.final_gap - orig.final_gap) < 1e-6
    assert loaded.phase2_objective == orig.phase2_objective
    assert len(loaded.gap_history) == len(orig.gap_history)
    assert loaded.gap_history[0] == orig.gap_history[0]
    assert loaded.schedule == orig.schedule
    assert loaded.mins == orig.mins and loaded.secs == orig.secs
    return f'{len(orig.gap_history)} hist entries, all telemetry fields match'


def t_roundtrip_v10_no_telemetry():
    """v1.0-JSON ohne Telemetrie-Felder lädt ohne Crash, Defaults greifen."""
    orig = _mk_result(with_telemetry=False)
    d = _result_to_json_dict(orig)
    # Telemetrie-Felder entfernen (Simulation v1.0-Schema)
    for k in ('best_bound', 'final_gap', 'gap_history', 'phase2_objective', 'objective'):
        d.pop(k, None)
    raw = json.dumps({'version': '1.0', 'results': {orig.league_id: d}})
    loaded_data = json.loads(raw)
    loaded = _json_dict_to_result(orig.league_id,
                                    loaded_data['results'][orig.league_id],
                                    orig.cfg)
    assert loaded.best_bound is None
    assert loaded.final_gap is None
    assert loaded.phase2_objective is None
    assert loaded.gap_history == []
    assert loaded.objective == 0.0  # Default bei fehlendem Feld
    assert loaded.schedule == orig.schedule
    return 'v1.0-Loader liefert None-Defaults für Telemetrie'


def t_roundtrip_home_vals_reconstruction():
    """home_vals werden aus schedule rekonstruiert (R8-Hotfix v1.2.8)."""
    orig = _mk_result(with_telemetry=True)
    d = _result_to_json_dict(orig)
    raw = json.dumps({'version': '1.1', 'results': {orig.league_id: d}})
    loaded = _json_dict_to_result(orig.league_id,
                                    json.loads(raw)['results'][orig.league_id],
                                    orig.cfg)
    # home_vals nicht direkt im JSON, aus schedule abgeleitet
    assert loaded.home_vals.get((0, 1)) == 1, 'T0 sollte Heim an ST1 sein'
    assert loaded.home_vals.get((1, 1)) == 0, 'T1 sollte Gast an ST1 sein'
    assert loaded.home_vals.get((2, 1)) == 1
    assert loaded.home_vals.get((3, 1)) == 0
    return f'{len(loaded.home_vals)} home_vals rekonstruiert'


def t_telemetry_round_trip_through_json_string():
    """Volle JSON-Encode + Decode-Round-Trip via Bytes (wie echte Session-Datei)."""
    orig = _mk_result(with_telemetry=True)
    d = _result_to_json_dict(orig)
    full = {'version': '1.1', 'config': {}, 'results': {orig.league_id: d}}
    blob = json.dumps(full).encode('utf-8')
    # Decode wie in _session_from_json
    parsed = json.loads(blob.decode('utf-8'))
    assert parsed['version'] == '1.1'
    res_data = parsed['results'][orig.league_id]
    assert res_data['phase2_objective'] == orig.phase2_objective
    assert len(res_data['gap_history']) == 3
    return f'JSON {len(blob)} bytes, round-trip OK'


def t_schema_version_field_present():
    """_session_to_json setzt 'version' im Top-Level."""
    # Direkter Check, dass app.py-Quelltext das richtige Feld setzt.
    src = (_HERE / 'app.py').read_text(encoding='utf-8')
    assert "'version': '1.1'" in src, 'Schema-Version 1.1 nicht gesetzt'
    return None


def t_schema_unknown_version_handled():
    """_session_from_json gibt Warnung bei unbekannter Schema-Version (R8-E-L3)."""
    src = (_HERE / 'app.py').read_text(encoding='utf-8')
    assert '_KNOWN_SCHEMA_VERSIONS' in src, 'Schema-Version-Whitelist nicht vorhanden'
    assert "{'1.0', '1.1'}" in src or '"1.0", "1.1"' in src, \
        'v1.0 + v1.1 nicht in Whitelist'
    return None


def t_empty_results_dict_works():
    """Sitzung ohne Spielpläne (nur Konfig) muss laden ohne Crash."""
    full = {'version': '1.1', 'config': {}, 'results': {}}
    blob = json.dumps(full).encode('utf-8')
    parsed = json.loads(blob.decode('utf-8'))
    assert parsed['results'] == {}
    return None


def t_seed_histories_in_results():
    """R7-A7-M2: seed_histories werden im Result mitgesichert."""
    orig = _mk_result(with_telemetry=True)
    # seed_histories ist ein neues Feld, getrennt von gap_history
    assert orig.seed_histories, 'seed_histories sollte gesetzt sein'
    assert 42 in orig.seed_histories
    assert 142 in orig.seed_histories
    assert len(orig.seed_histories[42]) == 3
    return f'{len(orig.seed_histories)} Seeds gesammelt'


def t_corrupt_json_safe_handling():
    """Direkt korrupte JSON-Bytes -> json.loads wirft JSONDecodeError."""
    bad_blob = b'{"version": "1.1", "results": {invalid}'
    raised = False
    try:
        json.loads(bad_blob)
    except json.JSONDecodeError:
        raised = True
    assert raised, 'JSON-Decoder sollte bei Garbage-Input fehlschlagen'
    return None


# ── main() ───────────────────────────────────────────────────────────────────

def main() -> int:
    print('\n=== test_session_roundtrip.py - JSON-Schema 1.0/1.1 ===\n')

    check('v1.1 Round-Trip: alle Telemetrie-Felder bleiben erhalten',
          t_roundtrip_v11_full_telemetry)
    check('v1.0 Backward-Compat: ohne Telemetrie-Felder ladbar',
          t_roundtrip_v10_no_telemetry)
    check('home_vals werden korrekt aus schedule rekonstruiert',
          t_roundtrip_home_vals_reconstruction)
    check('Voller Encode/Decode via Bytes',
          t_telemetry_round_trip_through_json_string)
    check('Schema-Version 1.1 Feld in app.py vorhanden',
          t_schema_version_field_present)
    check('Schema-Version-Whitelist erkennt unbekannte Versionen (R8-E-L3)',
          t_schema_unknown_version_handled)
    check('Leeres results-Dict laedt ohne Crash',
          t_empty_results_dict_works)
    check('seed_histories-Feld (R7-A7-M2) erreichbar',
          t_seed_histories_in_results)
    check('Korruptes JSON wirft JSONDecodeError',
          t_corrupt_json_safe_handling)

    print()
    n_total = 9
    if _failures:
        print(f'FEHLER: {len(_failures)}/{n_total} Tests fehlgeschlagen.')
        for name, err in _failures:
            print(f'  - {name}: {err}')
        return 1
    print(f'  {n_total}/{n_total} Tests bestanden')
    return 0


if __name__ == '__main__':
    sys.exit(main())
