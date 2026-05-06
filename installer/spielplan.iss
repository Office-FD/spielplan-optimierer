; Inno Setup Script – Spielplan-Optimierer Bootstrap-Installer
; Wird mit build_bootstrap.bat erstellt.
; Erfordert Inno Setup 6.1+ (https://jrsoftware.org/isinfo.php)

#ifndef MyAppVersion
  #define MyAppVersion "1.1.0"
#endif

#define MyAppName "Spielplan-Optimierer"
#define MyAppPublisher "FLOORBALL VERBAND DEUTSCHLAND e.V."
#define MyAppURL "https://github.com/Office-FD/spielplan-optimierer"
#define MyAppExeName "Spielplan-Optimierer.exe"

[Setup]
AppId={{B3F2A1C4-7E8D-4F5A-9B2C-1D6E3F8A7B4C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
; Per-User-Install in LocalAppData – kein Admin-Recht noetig (auch fuer Auto-Updates)
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=Spielplan-Optimierer-Setup-v{#MyAppVersion}
SetupIconFile=build\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
; Mindestanforderung Windows 10
MinVersion=10.0

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verkn&uepfung erstellen"; GroupDescription: "Weitere Optionen:"

[Files]
; Embedded Python mit allen installierten Paketen
Source: "build\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".agents,__pycache__,*.pyc,tests,test_*"
; Kompilierter Launcher (erstellt durch build_bootstrap.bat)
Source: "build\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent

[Code]
var
  DownloadPage: TDownloadWizardPage;

procedure InitializeWizard;
begin
  DownloadPage := CreateDownloadPage(
    'App-Dateien werden geladen',
    'Die aktuellste Programmversion wird von GitHub heruntergeladen...',
    nil
  );
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  if CurPageID = wpReady then
  begin
    DownloadPage.Clear;
    DownloadPage.Add(
      'https://github.com/Office-FD/spielplan-optimierer/releases/latest/download/app-files.zip',
      'app-files.zip',
      ''
    );
    DownloadPage.Show;
    try
      try
        DownloadPage.Download;
        Result := True;
      except
        if DownloadPage.AbortedByUser then
          Log('Download vom Benutzer abgebrochen.')
        else
          MsgBox(
            'Fehler beim Herunterladen der App-Dateien:' + #13#10 +
            GetExceptionMessage + #13#10 + #13#10 +
            'Bitte Internetverbindung pruefen und erneut versuchen.',
            mbError, MB_OK
          );
        Result := False;
      end;
    finally
      DownloadPage.Hide;
    end;
  end else
    Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  ZipPath, AppDir, ScriptPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    ZipPath := ExpandConstant('{tmp}\app-files.zip');
    AppDir  := ExpandConstant('{app}');
    ScriptPath := ExpandConstant('{tmp}\extract.ps1');

    if not FileExists(ZipPath) then
    begin
      MsgBox('app-files.zip wurde nicht gefunden. App-Dateien konnten nicht installiert werden.', mbError, MB_OK);
      Exit;
    end;

    // PowerShell-Skript schreiben (vermeidet Quoting-Probleme mit Leerzeichen in Pfaden)
    SaveStringToFile(
      ScriptPath,
      'Expand-Archive -LiteralPath "' + ZipPath + '" -DestinationPath "' + AppDir + '" -Force',
      False
    );

    Exec(
      'powershell.exe',
      '-NoProfile -ExecutionPolicy Bypass -File "' + ScriptPath + '"',
      AppDir,
      SW_HIDE,
      ewWaitUntilTerminated,
      ResultCode
    );

    if ResultCode <> 0 then
      MsgBox(
        'Fehler beim Entpacken der App-Dateien (Code: ' + IntToStr(ResultCode) + ').' + #13#10 +
        'Bitte das Setup erneut ausfuehren.',
        mbError, MB_OK
      );
  end;
end;
