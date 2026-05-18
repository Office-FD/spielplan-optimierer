"""Solver-Worker-Prozess: läuft in eigenem Prozess, daher via terminate() killbar."""
import sys
import logging

# Streamlit-Warnungen im Subprocess unterdrücken (fehlender ScriptRunContext ist erwartet).
# Kind-Logger ohne eigenen Level erben diesen Wert → alle streamlit.* WARNING-Meldungen werden gefiltert.
logging.getLogger('streamlit').setLevel(logging.ERROR)


def run_solver(cfgs, clubs, kw_compat, w_cohome, solver_cfg, log_q, base_dir: str = '.'):
    """Solver-Hauptfunktion für den separaten Worker-Prozess.

    base_dir muss das Projektverzeichnis sein, damit spielplan_multi importierbar ist.
    Ergebnisse werden über log_q als ('__RESULTS__', results)-Tuple gesendet,
    gefolgt von '__DONE__'.
    """
    from pathlib import Path
    _base = Path(base_dir)
    if str(_base) not in sys.path:
        sys.path.insert(0, str(_base))

    from spielplan_multi.multi_solver import solve_all
    import pickle as _pickle

    class _Writer:
        def __init__(self, q):
            self._q = q
            self._buf = ''

        def write(self, text: str):
            self._buf += text
            while '\n' in self._buf:
                line, self._buf = self._buf.split('\n', 1)
                if line.strip():
                    try:
                        self._q.put(line)
                    except Exception:
                        pass

        def flush(self):
            pass

    sys.stdout = _Writer(log_q)
    try:
        results = solve_all(
            cfgs=cfgs,
            clubs=clubs,
            kw_compat=kw_compat,
            w_cohome=w_cohome,
            phase1_time=solver_cfg['p1'],
            phase2_time=solver_cfg['p2'],
            night_mode=solver_cfg['nm'],
            n_seeds=solver_cfg['seeds'],
            sa_time=solver_cfg['sa'],
        )
        _pkl = _base / '.cache' / 'last_result.pkl'
        try:
            _pkl.parent.mkdir(parents=True, exist_ok=True)
            _pkl.write_bytes(_pickle.dumps({
                'results':   results,
                'clubs':     clubs,
                'kw_compat': kw_compat,
            }))
        except Exception:
            pass
        log_q.put(('__RESULTS__', results))
    except Exception as exc:
        import traceback
        log_q.put(f'[FEHLER] {exc}')
        log_q.put(traceback.format_exc())
    finally:
        log_q.put('__DONE__')
