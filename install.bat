@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Spielplan-Optimierer – Erstinstallation

echo.
echo  ============================================================
echo   Spielplan-Optimierer – Erstinstallation
echo   FLOORBALL VERBAND DEUTSCHLAND (FD)
echo  ============================================================
echo.

:: ── Python ermitteln (python oder py-Launcher) ───────────────────────────────
set PYTHON=
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON=python
) else (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON=py
    )
)

if "%PYTHON%"=="" (
    echo  Python wurde nicht gefunden.
    echo.
    echo  Versuche automatische Installation via winget...
    echo  (Internetverbindung erforderlich)
    echo.
    winget install --id Python.Python.3.13 --source winget ^
        --accept-package-agreements --accept-source-agreements
    if !errorlevel! neq 0 (
        echo.
        echo  [FEHLER] Automatische Installation fehlgeschlagen.
        echo.
        echo  Bitte Python 3.11 oder neuer manuell installieren:
        echo  https://www.python.org/downloads/
        echo.
        echo  Wichtig: Haken bei "Add Python to PATH" setzen!
        echo  Danach install.bat erneut ausfuehren.
        echo.
        pause
        exit /b 1
    )
    echo.
    echo  Python wurde installiert.
    echo  Bitte dieses Fenster schliessen, eine NEUE Eingabeaufforderung
    echo  oeffnen und install.bat erneut starten.
    echo.
    pause
    exit /b 0
)

:: ── Python-Version anzeigen ──────────────────────────────────────────────────
for /f "tokens=2 delims= " %%v in ('%PYTHON% --version 2^>^&1') do set PYVER=%%v
echo  Python %PYVER% gefunden (via %PYTHON%).
echo.

:: ── Virtuelle Umgebung erstellen ─────────────────────────────────────────────
if not exist ".venv\Scripts\activate.bat" (
    echo  Erstelle virtuelle Umgebung (.venv)...
    %PYTHON% -m venv .venv
    if !errorlevel! neq 0 (
        echo.
        echo  [FEHLER] Virtuelle Umgebung konnte nicht erstellt werden.
        pause
        exit /b 1
    )
    echo  Virtuelle Umgebung erstellt.
    echo.
) else (
    echo  Virtuelle Umgebung bereits vorhanden.
    echo.
)

:: ── Pakete installieren ──────────────────────────────────────────────────────
echo  Installiere Abhaengigkeiten (kann einige Minuten dauern)...
echo  Bitte warten...
echo.
.venv\Scripts\python -m pip install --upgrade pip --quiet
.venv\Scripts\pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo  [FEHLER] Installation der Pakete fehlgeschlagen.
    echo  Bitte Internetverbindung pruefen und install.bat erneut starten.
    echo.
    pause
    exit /b 1
)

:: ── Ausgabe-Ordner anlegen ───────────────────────────────────────────────────
if not exist "Spielplaene" mkdir Spielplaene

echo.
echo  ============================================================
echo   Installation abgeschlossen!
echo.
echo   Den Optimierer starten: start.bat doppelklicken
echo  ============================================================
echo.
pause
