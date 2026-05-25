@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Spielplan-Optimierer - Bootstrap-Installer erstellen

echo ============================================================
echo  Spielplan-Optimierer - Bootstrap-Installer Build
echo ============================================================
echo.

:: --- Pfade ---
set "ROOT=%~dp0.."
set "BUILD=%~dp0build"
set "PYEMBED=%BUILD%\python"
set "PYVER=3.13.3"
set "PYZIP=python-%PYVER%-embed-amd64.zip"
set "PYURL=https://www.python.org/ftp/python/%PYVER%/%PYZIP%"

:: --- Voraussetzungen pruefen ---
echo [1/6] Voraussetzungen pruefen...

where python >nul 2>&1
if errorlevel 1 (
    echo FEHLER: Python nicht gefunden. Bitte Python 3.13 installieren.
    pause & exit /b 1
)

where pyinstaller >nul 2>&1
if errorlevel 1 (
    echo  PyInstaller nicht gefunden. Wird installiert...
    python -m pip install pyinstaller --quiet
    if errorlevel 1 ( echo FEHLER: PyInstaller-Installation fehlgeschlagen. & pause & exit /b 1 )
)

:: Inno Setup suchen: erst im PATH, dann an Standardpfaden
set "ISCC="
set "PF86=%ProgramFiles(x86)%"
where iscc >nul 2>&1
if not errorlevel 1 set "ISCC=iscc"
if not defined ISCC if exist "%PF86%\Inno Setup 6\iscc.exe" set "ISCC=%PF86%\Inno Setup 6\iscc.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\iscc.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\iscc.exe"
if not defined ISCC (
    echo FEHLER: Inno Setup nicht gefunden.
    echo Bitte von https://jrsoftware.org/isinfo.php installieren.
    pause & exit /b 1
)
echo  Inno Setup gefunden: %ISCC%

if not exist "%BUILD%" mkdir "%BUILD%"

:: --- Embedded Python herunterladen ---
echo [2/6] Python %PYVER% Embedded Package...

if exist "%PYEMBED%\python.exe" (
    echo  Bereits vorhanden, wird uebersprungen.
    echo  (Loeschen Sie %PYEMBED% um neu zu erstellen.)
) else (
    if not exist "%BUILD%\%PYZIP%" (
        echo  Herunterladen von python.org...
        powershell -NoProfile -Command "Invoke-WebRequest -Uri '%PYURL%' -OutFile '%BUILD%\%PYZIP%'"
        if errorlevel 1 ( echo FEHLER: Download fehlgeschlagen. & pause & exit /b 1 )

        :: F-L6: SHA256-Verifikation gegen den von python.org publizierten Hash.
        :: Hash von https://www.python.org/downloads/release/python-3133/
        :: → "Windows embeddable package (64-bit)" SHA256.
        :: ACHTUNG: Bei PYVER-Update muss dieser Hash mit aktualisiert werden.
        set "PY_SHA256=ba88e0d7370f198cd00f44dc31e3f8c3267dd2c413e57ec8538b243cefc7e8fb"
        echo  Pruefe SHA256...
        powershell -NoProfile -Command ^
            "$h = (Get-FileHash -Algorithm SHA256 -LiteralPath '%BUILD%\%PYZIP%').Hash.ToLower(); if ($h -ne '%PY_SHA256%') { Write-Host 'SHA256 mismatch: erwartet %PY_SHA256%, erhalten ' $h; exit 1 }"
        if errorlevel 1 (
            echo FEHLER: SHA256-Verifikation fehlgeschlagen - Datei moeglicherweise korrupt oder kompromittiert.
            del "%BUILD%\%PYZIP%" 2>nul
            pause & exit /b 1
        )
        echo  SHA256 OK.
    )
    echo  Entpacken...
    powershell -NoProfile -Command "Expand-Archive -Path '%BUILD%\%PYZIP%' -DestinationPath '%PYEMBED%' -Force"

    :: site-packages aktivieren (pth-Datei anpassen)
    powershell -NoProfile -Command "Get-ChildItem '%PYEMBED%\*._pth' | ForEach-Object { (Get-Content $_) -replace '#import site','import site' | Set-Content $_ }"

    :: pip installieren
    echo  pip einrichten...
    powershell -NoProfile -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%BUILD%\get-pip.py'"
    "%PYEMBED%\python.exe" "%BUILD%\get-pip.py" --no-warn-script-location --quiet
    if errorlevel 1 ( echo FEHLER: pip-Installation fehlgeschlagen. & pause & exit /b 1 )

    :: Abhaengigkeiten installieren
    echo  Pakete installieren (das dauert einige Minuten)...
    "%PYEMBED%\python.exe" -m pip install --no-warn-script-location --quiet -r "%ROOT%\requirements.txt"
    if errorlevel 1 ( echo FEHLER: Paket-Installation fehlgeschlagen. & pause & exit /b 1 )
    echo  Python-Umgebung fertig.
)

:: --- Icon erstellen ---
echo [3/6] Icon erstellen...
set "ICON_SRC=%ROOT%\assets\floorball_icon.png"
set "ICON_ICO=%BUILD%\icon.ico"

if exist "%ICON_ICO%" (
    echo  Bereits vorhanden.
) else if exist "%ICON_SRC%" (
    python -m pip install pillow --quiet 2>nul
    python -c "from PIL import Image; img=Image.open(r'%ICON_SRC%').convert('RGBA'); img.save(r'%ICON_ICO%')" 2>nul
    if exist "%ICON_ICO%" (
        echo  icon.ico erstellt.
    ) else (
        echo  Konnte Icon nicht erstellen, Standard-Icon wird verwendet.
        set "ICON_ICO="
    )
) else (
    echo  Kein Icon-Bild gefunden, Standard-Icon wird verwendet.
    set "ICON_ICO="
)

:: --- Launcher kompilieren ---
echo [4/6] Launcher kompilieren (PyInstaller)...

cd /d "%ROOT%"
if defined ICON_ICO (
    pyinstaller --onefile --noconsole --name "Spielplan-Optimierer" --icon "%ICON_ICO%" --distpath "%BUILD%" --workpath "%BUILD%\pyi_work" --specpath "%BUILD%" launcher.py
) else (
    pyinstaller --onefile --noconsole --name "Spielplan-Optimierer" --distpath "%BUILD%" --workpath "%BUILD%\pyi_work" --specpath "%BUILD%" launcher.py
)
if errorlevel 1 ( echo FEHLER: PyInstaller fehlgeschlagen. & pause & exit /b 1 )
echo  Spielplan-Optimierer.exe erstellt.

:: --- Version auslesen ---
set /p VERSION=<"%ROOT%\VERSION"
set "VERSION=%VERSION: =%"
echo  Version: %VERSION%

:: --- Inno Setup ausfuehren ---
echo [5/6] Installer erstellen (Inno Setup)...
cd /d "%~dp0"
"%ISCC%" spielplan.iss /DMyAppVersion="%VERSION%"
if errorlevel 1 ( echo FEHLER: Inno Setup fehlgeschlagen. & pause & exit /b 1 )

:: --- Ergebnis ---
echo.
echo [6/6] Fertig!
echo.
echo  Installer: installer\Output\Spielplan-Optimierer-Setup-v%VERSION%.exe
echo.
echo  Naechste Schritte:
echo  1. VERSION-Datei erhoehen (z.B. 1.2.0)
echo  2. python build_release.py  (erstellt app-files.zip)
echo  3. git tag v%VERSION% ^& git push --tags
echo     (GitHub Actions erstellt den Release automatisch)
echo.
pause
