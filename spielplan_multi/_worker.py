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
    from spielplan_multi.runtime_paths import run_cache_dir
    import pickle as _pickle

    # Laufdateien in lokalen, OneDrive-freien Cache (gleiche Funktion wie in app.py).
    _cache = run_cache_dir(_base)

    # ── PID-Datei schreiben (für Session-Rejoin-Erkennung) ───────────────────
    _pid_file = _cache / 'opt_pid.txt'
    _log_file_path = _cache / 'opt_log.txt'
    _meta_file = _cache / 'opt_meta.json'
    try:
        _pid_file.write_text(str(os.getpid()))
    except Exception:
        _pid_file = None

    # Meta (Startzeit + geschätzte Gesamtlaufzeit) – damit die Rejoin-Ansicht
    # nach Browser-Abbruch Laufzeit + Fortschritt anzeigen kann (fremde Session
    # hat kein opt_start_time/Solver-Config).
    try:
        import time as _time_meta
        import json as _json_meta
        _total_est = (int(solver_cfg.get('seeds', 1)) * int(solver_cfg.get('p1', 0))
                      + int(solver_cfg.get('p2', 0))
                      + int(solver_cfg.get('sa', 0)) * max(1, len(cfgs)))
        _meta_file.write_text(_json_meta.dumps(
            {'start': _time_meta.time(), 'total': _total_est}))
    except Exception:
        _meta_file = None

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
        # Ergebnis auf Platte schreiben – das ist jetzt der EINZIGE Übergabeweg
        # an die UI. Fehler NICHT mehr verschlucken: ohne diese Datei kann die
        # UI nach __DONE__ kein Ergebnis laden.
        _pkl = _cache / 'last_result.pkl'
        try:
            _pkl.write_bytes(_pickle.dumps({
                'results':   results,
                'clubs':     clubs,
                'kw_compat': kw_compat,
            }))
        except Exception as _pkl_exc:
            import traceback as _tb_pkl
            log_q.put(f'[FEHLER] Ergebnis konnte nicht gespeichert werden: {_pkl_exc}')
            log_q.put(_tb_pkl.format_exc())
        # WICHTIG: `results` NICHT über die Queue senden. Ein so großes Objekt
        # füllt den ~64 KB-Pipe-Puffer der multiprocessing.Queue; der
        # QueueFeederThread blockiert dann in _send_bytes und der Worker hängt
        # beim Prozess-Ende ewig in _finalize_join (join auf den Feeder).
        # Die UI lädt das Ergebnis aus last_result.pkl, sobald __DONE__ ankommt.
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
        if _meta_file is not None:
            try:
                _meta_file.unlink(missing_ok=True)
            except Exception:
                pass
