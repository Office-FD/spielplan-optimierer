"""Einstiegspunkt: spielplan_multi

Aufruf:
  python -m spielplan_multi          (aus dem Claude-Ordner)
  python main.py                     (direkt, falls CWD = spielplan_multi)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Sicherstellen, dass das Elternverzeichnis im Suchpfad ist
_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from spielplan_multi.ui import banner, section, ok, info, warn, err
from spielplan_multi.wizard import run_wizard
from spielplan_multi.multi_solver import solve_all
from spielplan_multi.excel_output import (
    build_league_excel, save_league_excel,
    build_cohome_summary, save_cohome_summary,
    build_hall_schedule, save_hall_schedule,
)


def main():
    banner('SPIELPLAN-OPTIMIERER | Multi-Liga-Scheduler')
    info('Optimierung beliebig vieler Ligen mit Co-Home-Koordination')

    # Ausgabeverzeichnis = gleicher Ordner wie main.py
    output_dir = _HERE.parent / 'Spielplaene'
    cache_dir  = _HERE.parent / '.cache'
    output_dir.mkdir(exist_ok=True)
    cache_dir.mkdir(exist_ok=True)

    # ── Wizard ───────────────────────────────────────────────────────────────
    config = run_wizard(cache_dir=cache_dir)
    if config is None:
        err('Wizard abgebrochen. Kein Spielplan erstellt.')
        return

    cfgs        = config['cfgs']
    clubs       = config['clubs']
    kw_compat   = config['kw_compat']
    w_cohome    = config['w_cohome']
    phase1_time = config['phase1_time']
    phase2_time = config['phase2_time']
    night_mode  = config['night_mode']
    n_seeds     = config.get('n_seeds', 2)
    sa_time     = config.get('sa_time', 120)

    # ── Optimierung ──────────────────────────────────────────────────────────
    results = solve_all(
        cfgs=cfgs,
        clubs=clubs,
        kw_compat=kw_compat,
        w_cohome=w_cohome,
        phase1_time=phase1_time,
        phase2_time=phase2_time,
        night_mode=night_mode,
        n_seeds=n_seeds,
        sa_time=sa_time,
    )

    # ── Ergebnis ausgeben ────────────────────────────────────────────────────
    banner('SPIELPLAENE WERDEN ERSTELLT')
    saved_files = []

    for lid, result in results.items():
        if result is None:
            warn(f'{lid}: Kein Ergebnis – wird uebersprungen.')
            continue

        # Konsolen-Ausgabe
        section(f'SPIELPLAN: {result.cfg.name}')
        dst_days    = result.cfg.dst_days
        n_rounds    = result.cfg.n_rounds
        n_per_round = max(1, result.cfg.n_matchdays // n_rounds)
        _phase_lbl  = {1: 'Hin', 2: 'Rue'} if n_rounds == 2 else {}
        for d in result.cfg.days:
            typ      = 'DST' if d in dst_days else 'EST'
            rnd      = min(n_rounds, (d - 1) // n_per_round + 1)
            phase    = _phase_lbl.get(rnd, f'R{rnd}')
            print(f'\n  Spieltag {d:2d} ({phase}/{typ}):')
            for i, (ht, at) in enumerate(result.schedule.get(d, []), 1):
                print(f'    {i}. {ht:22s} vs. {at}')

        import numpy as np
        _tr = result.travels or [0]
        _sw = result.sw_counts or [0]
        print(f'\n  Reise: min={min(_tr)} max={max(_tr)} '
              f'O={np.mean(_tr):.0f} km')
        print(f'  Switches: min={min(_sw)} max={max(_sw)}')

        # Excel speichern
        wb       = build_league_excel(result)
        filename = save_league_excel(wb, result, output_dir)
        saved_files.append(filename)
        ok(f'Excel gespeichert: {filename}')

    # Co-Home-Zusammenfassung
    if clubs:
        wb_ch    = build_cohome_summary(results, clubs, kw_compat)
        fn_ch    = save_cohome_summary(wb_ch, output_dir)
        saved_files.append(fn_ch)
        ok(f'Co-Home-Zusammenfassung: {fn_ch}')

    # Hallenbelegungsplan
    if results:
        wb_hall = build_hall_schedule(results)
        fn_hall = save_hall_schedule(wb_hall, output_dir)
        saved_files.append(fn_hall)
        ok(f'Hallenbelegungsplan: {fn_hall}')

    # ── Abschluss ─────────────────────────────────────────────────────────────
    banner('FERTIG')
    print(f'\n  Ausgabe-Verzeichnis: {output_dir}')
    print(f'\n  Erstellte Dateien ({len(saved_files)}):')
    for f in saved_files:
        print(f'    {f}')


if __name__ == '__main__':
    try:
        main()
        banner('PROGRAMM ERFOLGREICH ABGESCHLOSSEN')
    except KeyboardInterrupt:
        print('\n\n  Abbruch durch Benutzer.')
        sys.exit(0)
    except Exception:
        banner('FEHLER AUFGETRETEN')
        import traceback
        traceback.print_exc()
    finally:
        if sys.stdin.isatty():
            print()
            try:
                input('  Druecke Enter zum Beenden ...')
            except EOFError:
                pass
