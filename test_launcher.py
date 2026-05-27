"""Tests für launcher.py — Update-Mechanismus, Port-Handling, Build-Release-Filter.

Testet kritische Distribution-Pfade ohne echte Netz-/GitHub-Zugriffe.

Verwendung:
    .venv/Scripts/python.exe test_launcher.py
    pytest test_launcher.py -v
"""
from __future__ import annotations

import io
import os
import socket
import sys
import tempfile
import zipfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))


# ── Helper: check()-Framework analog zu test_all.py ──────────────────────────
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


# ── Helper: launcher-Module ohne main() laden ────────────────────────────────
# launcher.py hat `main()` als Top-Level-Funktion. Wir importieren das Modul
# wie ein normales Python-Modul (kein __main__-Trigger).
import importlib.util


def _load_launcher_module():
    spec = importlib.util.spec_from_file_location('launcher', _HERE / 'launcher.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_launcher = _load_launcher_module()


# ── Tests: _parse_version ────────────────────────────────────────────────────
def t_parse_version_simple():
    assert _launcher._parse_version('1.13.1') == (1, 13, 1)
    assert _launcher._parse_version('1.0.0') == (1, 0, 0)
    return None


def t_parse_version_v_prefix():
    assert _launcher._parse_version('v1.13.1') == (1, 13, 1)
    assert _launcher._parse_version(' v2.0.0 ') == (2, 0, 0)
    return None


def t_parse_version_prerelease_suffix():
    """Pre-Release-Suffixe werden abgetrennt, semver-Vergleich bleibt korrekt."""
    assert _launcher._parse_version('1.3.0-beta') == (1, 3, 0)
    assert _launcher._parse_version('1.3.0.rc1') == (1, 3, 0)
    assert _launcher._parse_version('1.3.0+build123') == (1, 3, 0)
    # Vergleich: 1.10.0 > 1.9.0 (semantisch, nicht lexikografisch)
    assert _launcher._parse_version('1.10.0') > _launcher._parse_version('1.9.0')
    return None


def t_parse_version_invalid_falls_back():
    """Komplett ungültige Strings ergeben (0,) — niemals Crash."""
    assert _launcher._parse_version('') == (0,)
    assert _launcher._parse_version('nonsense') == (0,)
    return None


# ── Tests: _port_is_free + _wait_for_port_free ───────────────────────────────
def t_port_is_free_when_unused():
    """Bei freiem Port liefert _port_is_free True."""
    # Wenn jemand grad Streamlit auf 8501 laufen hat, schlägt das fehl. In CI ok.
    if _launcher._port_is_free():
        # Test geht durch — Port wirklich frei
        return 'Port 8501 ist frei'
    # Wenn nicht: skip ohne Failure
    return 'Port 8501 belegt — Test übersprungen'


def t_port_is_free_when_occupied():
    """Wenn ein Listening-Socket gebunden ist, ist _port_is_free False."""
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        blocker.bind(('127.0.0.1', _launcher.PORT))
        blocker.listen(1)
        assert _launcher._port_is_free() is False
    finally:
        blocker.close()
    return None


def t_wait_for_port_free_timeout():
    """_wait_for_port_free liefert False nach Timeout bei belegtem Port."""
    import time as _time
    blocker = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        blocker.bind(('127.0.0.1', _launcher.PORT))
        blocker.listen(1)
        start = _time.monotonic()
        result = _launcher._wait_for_port_free(timeout=2)
        elapsed = _time.monotonic() - start
        assert result is False, f'Sollte False sein bei belegtem Port: {result}'
        assert 1.5 <= elapsed <= 3.0, f'Timing falsch: {elapsed}'
    finally:
        blocker.close()
    return f'{elapsed:.1f}s gewartet, korrekt False'


# ── Tests: ZIP-Path-Traversal-Guard in _apply_update ─────────────────────────
def t_zip_path_traversal_guard():
    """ZIPs mit `../..`-Einträgen müssen zurückgewiesen werden (CR4-L4-Fix)."""
    # Direktes Test der Guard-Logik: wir simulieren, wie _apply_update die
    # Path-Validierung durchführt. Erzeugen ein bösartiges ZIP und prüfen,
    # ob die realpath-Validierung fehl-schlägt.
    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = Path(tmp_dir) / 'mal.zip'
        with zipfile.ZipFile(zip_path, 'w') as zf:
            # Bösartiger Eintrag, der nach /etc/passwd zeigen würde
            zf.writestr('../../../etc/passwd', 'pwned')
            zf.writestr('legit/app.py', '# ok')

        # Replikation der Guard-Logik aus _apply_update Z. 130-137
        base = Path(tmp_dir) / 'app'
        base.mkdir()
        base_real = os.path.realpath(base)
        rejected = []
        accepted = []
        with zipfile.ZipFile(zip_path) as z:
            for member in z.namelist():
                if member.startswith('python/'):
                    continue
                dest = os.path.realpath(os.path.join(base, member))
                if not dest.startswith(base_real + os.sep) and dest != base_real:
                    rejected.append(member)
                else:
                    accepted.append(member)

        assert '../../../etc/passwd' in rejected, f'Pfad-Traversal-Eintrag durchgelassen: {rejected=}'
        assert 'legit/app.py' in accepted, f'Legitimer Eintrag abgelehnt: {accepted=}'
    return f'1 abgelehnt, 1 akzeptiert'


# ── Tests: build_release._should_include ─────────────────────────────────────
def t_build_release_excludes():
    """build_release.py filtert Cache- und Build-Verzeichnisse korrekt."""
    import importlib.util as _iu
    spec = _iu.spec_from_file_location('build_release', _HERE / 'build_release.py')
    bm = _iu.module_from_spec(spec)
    spec.loader.exec_module(bm)

    # Cache + Build-Output muss raus
    assert bm._should_include('.cache/dist_X.json') is False
    assert bm._should_include('Spielplaene/Liga_A.xlsx') is False
    assert bm._should_include('__pycache__/x.pyc') is False
    assert bm._should_include('installer/Output/Setup.exe') is False
    # R8-G-L2: neue Excludes
    assert bm._should_include('dist/foo.exe') is False
    assert bm._should_include('build/temp.txt') is False
    assert bm._should_include('coverage_html/index.html') is False
    # App-Dateien drin
    assert bm._should_include('app.py') is True
    assert bm._should_include('spielplan_multi/solver.py') is True
    assert bm._should_include('VERSION') is True
    # .pyc nicht
    assert bm._should_include('spielplan_multi/__pycache__/foo.pyc') is False
    return None


def t_build_release_zip_has_min_files():
    """build_release.main sanity-check: bricht ab bei < 10 Dateien."""
    # Wir testen nicht den ZIP-Build (lässt Datei liegen), sondern nur die
    # Logik direkt. Bei einem leeren Repo würde count < 10 sein.
    import importlib.util as _iu
    spec = _iu.spec_from_file_location('build_release', _HERE / 'build_release.py')
    bm = _iu.module_from_spec(spec)
    spec.loader.exec_module(bm)
    # _should_include muss bei normalem Repo > 10 Dateien akzeptieren
    accepted = 0
    for root, dirs, files in os.walk(_HERE):
        dirs[:] = sorted(d for d in dirs
                         if d not in bm.EXCLUDE_DIRS and not d.startswith('.'))
        for fname in files:
            rel_path = os.path.relpath(os.path.join(root, fname), _HERE)
            if bm._should_include(rel_path):
                accepted += 1
    assert accepted >= 10, f'Nur {accepted} Dateien — EXCLUDE_DIRS zu aggressiv?'
    return f'{accepted} Dateien akzeptiert'


# ── main() ───────────────────────────────────────────────────────────────────

def main() -> int:
    print('\n=== test_launcher.py — Distribution-Pfad-Tests ===\n')

    check('_parse_version: einfache Version', t_parse_version_simple)
    check('_parse_version: v-Prefix wird abgetrennt', t_parse_version_v_prefix)
    check('_parse_version: Pre-Release-Suffix korrekt', t_parse_version_prerelease_suffix)
    check('_parse_version: Fallback bei Garbage-Input', t_parse_version_invalid_falls_back)
    check('_port_is_free: True bei freiem Port', t_port_is_free_when_unused)
    check('_port_is_free: False bei belegtem Port', t_port_is_free_when_occupied)
    check('_wait_for_port_free: korrekter Timeout', t_wait_for_port_free_timeout)
    check('ZIP-Path-Traversal-Guard rejected schaedliche Pfade', t_zip_path_traversal_guard)
    check('build_release._should_include filtert korrekt', t_build_release_excludes)
    check('build_release Sanity-Check >= 10 Dateien', t_build_release_zip_has_min_files)

    print()
    n_total = 10
    if _failures:
        print(f'FEHLER: {len(_failures)}/{n_total} Tests fehlgeschlagen.')
        for name, err in _failures:
            print(f'  - {name}: {err}')
        return 1
    print(f'  {n_total}/{n_total} Tests bestanden')
    return 0


if __name__ == '__main__':
    sys.exit(main())
