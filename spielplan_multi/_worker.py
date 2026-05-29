"""Solver-Worker-Prozess: läuft in eigenem Prozess, daher via terminate() killbar."""
import os
import sys
import logging
import warnings

# Streamlit-Warnungen im Subprocess unterdrücken (fehlender ScriptRunContext ist erwartet).
# logging-Filter für alle streamlit.*-Logger (z. B. streamlit.runtime.*).
logging.getLogger('streamlit').setLevel(logging.ERROR)
# warnings.warn()-basierte ScriptRunContext-Warnung: Streamlit nutzt warnings.warn(), nicht logging.
warnings.filterwarnings('ignore', message='.*ScriptRunContext.*')


def run_solver(cfgs, clubs, kw_compat, w_cohome, solver_cfg, log_q, base_dir: str = '.'):
    """Solver-Hauptfunktion für den separaten Worker-Prozess.

    base_dir muss das Projektverzeichnis sein, damit spielplan_multi importierbar ist.
    Ergebnisse werden über log_q als ('__RESULTS__', results)-Tuple gesendet,
    gefolgt von '__DONE__'.

    Parallel werden alle Log-Zeilen in .cache/opt_log.txt geschrieben und die PID
    in .cache/opt_pid.txt — damit eine neue Streamlit-Session nach WebSocket-Abbruch
    in den laufenden Prozess einsteigen kann (Session-Rejoin).
    """
    from pathlib import Path
    _base = Path(base_dir)
    if str(_base) not in sys.path:
        sys.path.insert(0, str(_base))

    from spielplan_multi.multi_solver import solve_all
    import pickle as _pickle

    # ── PID-Datei schreiben (für Session-Rejoin-Erkennung) ───────────────────
    _pid_file = _base / '.cache' / 'opt_pid.txt'
    _log_file_path = _base / '.cache' / 'opt_log.txt'
    try:
        _pid_file.parent.mkdir(parents=True, exist_ok=True)
        _pid_file.write_text(str(os.getpid()))
    except Exception:
        _pid_file = None

    # Log-Datei öffnen (truncate: neuer Lauf überschreibt alten)
    _log_fh = None
    try:
        _log_fh = open(_log_file_path, 'w', encoding='utf-8')
    except Exception:
        pass

    class _Writer:
        def __init__(self, q, log_fh):
            self._q = q
            self._log = log_fh
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
                    if self._log is not None:
                        try:
                            self._log.write(line + '\n')
                            self._log.flush()
                        except Exception:
                            pass

        def flush(self):
            pass

    sys.stdout = _Writer(log_q, _log_fh)
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
        if _log_fh is not None:
            try:
                _log_fh.close()
            except Exception:
                pass
        # PID-Datei löschen → signalisiert der neuen Session dass Lauf beendet ist
        if _pid_file is not None:
            try:
                _pid_file.unlink(missing_ok=True)
            except Exception:
                pass
