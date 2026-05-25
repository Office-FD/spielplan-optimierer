"""Pytest-Wrapper für die existierenden CLI-Test-Scripts.

Die Test-Scripts test_smoke.py, test_features.py, test_distances.py und
test_all.py nutzen ein eigenes check()-Framework und enden mit sys.exit(0/1).
Statt sie einzeln zu pytest-fähigen Tests umzubauen, ruft dieser Wrapper
jedes Script als Subprocess auf und prüft den Exit-Code.

Verwendung in CI:
    pytest test_pytest_runner.py -v

Vorteile:
  - Existierende Scripts bleiben CLI-kompatibel (Exit-Code, formatierte Ausgabe)
  - Pytest sieht 4 separate Tests, fängt deren Output ab
  - Bei Failure zeigt pytest das vollständige stdout/stderr des Sub-Scripts

Hinweis: Die Sub-Scripts laden CP-SAT-Modelle und können je 1-3 Minuten dauern.
GitHub Actions sollte mit ausreichendem Timeout konfiguriert werden.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent

# Default-Timeout pro Sub-Script in Sekunden. Sehr großzügig für CI-Umgebung.
_DEFAULT_TIMEOUT = 600


def _run_script(name: str, timeout: int = _DEFAULT_TIMEOUT) -> None:
    """Führt ein CLI-Test-Script aus und failt mit dessen stdout/stderr bei Fehler."""
    script = _HERE / name
    if not script.exists():
        pytest.skip(f'{name} nicht gefunden')

    # PYTHONIOENCODING erzwingen — verhindert UnicodeEncodeError auf Windows-CI
    env = os.environ.copy()
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'

    try:
        result = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=timeout,
            cwd=str(_HERE),
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        pytest.fail(f'{name} hat Timeout ({timeout}s) überschritten.\n'
                    f'Partial stdout:\n{exc.stdout}\nPartial stderr:\n{exc.stderr}')

    if result.returncode != 0:
        pytest.fail(
            f'{name} exit={result.returncode}\n'
            f'--- stdout ---\n{result.stdout}\n'
            f'--- stderr ---\n{result.stderr}'
        )


def test_smoke_script() -> None:
    """Smoke-Tests: Modell-Aufbau, Phase-1-Lauf, parallele Seeds, SA-Refine."""
    _run_script('test_smoke.py', timeout=300)


def test_features_script() -> None:
    """Feature-Tests: Excel-Sheets, iCal, swap_home_away, assign_game_times, ..."""
    _run_script('test_features.py', timeout=300)


def test_distances_script() -> None:
    """Distance-Tests: Cache, Google-Maps-Mock, CSV/Excel-Loader, Symmetrisierung."""
    _run_script('test_distances.py', timeout=120)


def test_all_script() -> None:
    """Comprehensive: alle Solver-Features inkl. forced_home, Spielfrei, Mutationen."""
    _run_script('test_all.py', timeout=1200)
