"""Coverage-Lauf fuer alle Test-Skripte.

Faehrt nacheinander die 4 Test-Skripte unter `coverage run --parallel-mode`,
kombiniert die Resultate und gibt Report + HTML aus.

Nutzung:
    python run_coverage.py           # Voller Lauf + Report
    python run_coverage.py --html    # Zusaetzlich HTML in coverage_html/

Laufzeit: ~14 Min (entspricht test_pytest_runner-Laufzeit).
"""
from __future__ import annotations
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent

TEST_SCRIPTS = [
    ("test_smoke.py",     300),  # ~30s typisch
    ("test_features.py",  300),  # ~30s typisch
    ("test_distances.py", 120),  # ~10s typisch
    ("test_all.py",      1200),  # ~13 min typisch (Solver)
]


def run(cmd: list[str], timeout: int | None = None) -> int:
    """Run a command, stream output, return exit code."""
    print(f'\n>>> {" ".join(cmd)}')
    t0 = time.time()
    try:
        result = subprocess.run(cmd, cwd=HERE, timeout=timeout)
        dt = time.time() - t0
        print(f'    exit={result.returncode}  dauer={dt:.1f}s')
        return result.returncode
    except subprocess.TimeoutExpired:
        print(f'    TIMEOUT nach {timeout}s')
        return 124


def main() -> int:
    py = sys.executable
    want_html = '--html' in sys.argv

    # 1) Alte Coverage-Files löschen
    run([py, '-m', 'coverage', 'erase'])

    # 2) Tests einzeln mit coverage run --parallel-mode
    failed = []
    for script, timeout in TEST_SCRIPTS:
        rc = run([py, '-m', 'coverage', 'run', '--parallel-mode',
                  script], timeout=timeout)
        if rc != 0:
            failed.append(script)

    # 3) Kombinieren
    print('\n>>> Coverage kombinieren ...')
    run([py, '-m', 'coverage', 'combine'])

    # 4) Report
    print('\n=== Coverage-Report ===')
    run([py, '-m', 'coverage', 'report'])

    # 5) HTML (optional)
    if want_html:
        print('\n>>> HTML-Report generieren ...')
        run([py, '-m', 'coverage', 'html'])
        print('\nReport: coverage_html/index.html')

    if failed:
        print(f'\nWARNUNG: {len(failed)} Test-Skripte hatten Fehler: {failed}')
        return 1
    print('\nAlle Tests bestanden.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
