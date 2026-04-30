@echo off
cd /d "%~dp0"
title Spielplan-Optimierer

echo.
echo  Spielplan-Optimierer wird gestartet...
echo  Der Browser oeffnet sich automatisch.
echo  Dieses Fenster bitte offen lassen.
echo.

if not exist ".venv\Scripts\streamlit.exe" (
    echo  [HINWEIS] Virtuelle Umgebung nicht gefunden.
    echo  Bitte zuerst install.bat ausfuehren.
    echo.
    pause
    exit /b 1
)

.venv\Scripts\streamlit run app.py ^
    --server.headless false ^
    --server.port 8501 ^
    --browser.gatherUsageStats false
pause
