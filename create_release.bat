@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"
title Release-Paket erstellen

:: ── Version festlegen ────────────────────────────────────────────────────────
:: Anpassen vor jedem Release
set VERSION=1.0.0-beta1
set ZIPNAME=Spielplan-Optimierer-v%VERSION%.zip

echo.
echo  ============================================================
echo   Release-Paket erstellen: %ZIPNAME%
echo  ============================================================
echo.

:: Alte Datei entfernen
if exist "%ZIPNAME%" (
    del "%ZIPNAME%"
    echo  Alte Version geloescht.
)

:: ── ZIP mit PowerShell erstellen ─────────────────────────────────────────────
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$src = Get-Location; $zip = Join-Path $src '%ZIPNAME%'; " ^
  "$exclude = @('.venv','.cache','Spielplaene','__pycache__','.git','memory'); " ^
  "$files = Get-ChildItem -Path $src -Recurse -File | Where-Object { " ^
  "  $rel = $_.FullName.Substring($src.Path.Length + 1); " ^
  "  $parts = $rel -split '[\\/]'; " ^
  "  $skip = $false; " ^
  "  foreach ($p in $parts) { if ($exclude -contains $p) { $skip = $true; break } }; " ^
  "  -not $skip -and " ^
  "  $_.Extension -notin @('.pyc','.pyo') -and " ^
  "  $_.Name -ne '%ZIPNAME%' " ^
  "}; " ^
  "$tmp = Join-Path $env:TEMP 'release_staging'; " ^
  "if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }; " ^
  "foreach ($f in $files) { " ^
  "  $rel = $f.FullName.Substring($src.Path.Length + 1); " ^
  "  $dst = Join-Path $tmp $rel; " ^
  "  $dir = Split-Path $dst; " ^
  "  if (-not (Test-Path $dir)) { New-Item $dir -ItemType Directory | Out-Null }; " ^
  "  Copy-Item $f.FullName $dst " ^
  "}; " ^
  "Compress-Archive -Path (Join-Path $tmp '*') -DestinationPath $zip -Force; " ^
  "Remove-Item $tmp -Recurse -Force; " ^
  "Write-Host ('  Fertig: ' + (Get-Item $zip).Length / 1MB + ' MB')"

if %errorlevel% neq 0 (
    echo.
    echo  [FEHLER] ZIP konnte nicht erstellt werden.
    pause
    exit /b 1
)

echo.
echo  ============================================================
echo   %ZIPNAME% ist bereit fuer den Upload.
echo  ============================================================
echo.
pause
