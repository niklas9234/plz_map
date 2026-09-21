#define MyAppName "PLZ-Karte"
#ifndef MyAppVersion
  #error MyAppVersion must be supplied by build.ps1 from the release tag
#endif
#define MyAppExeName "PLZ-Karte.exe"

[Setup]
AppId={{702FD881-85A7-4DB8-A28F-A8070BCF77B9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\PLZ-Karte
DefaultGroupName=PLZ-Karte
; Keep this machine-wide: Intune runs the installer as SYSTEM and {autopf}
; therefore resolves to the native Program Files directory.
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist-installer
OutputBaseFilename=PLZ-Karte-{#MyAppVersion}-Setup
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\..\PLZ-Karte.ico

[Files]
Source: "..\..\dist\PLZ-Karte\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "C:\Logs\PLZ-Karte"; Permissions: users-modify

[Icons]
; SYSTEM has no interactive user's profile. Put Start menu entries in the
; shared Programs folder so that every intended user can see them.
Name: "{commonprograms}\PLZ-Karte\PLZ-Karte starten"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{commonprograms}\PLZ-Karte\PLZ-Karte beenden"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--shutdown"; WorkingDir: "{app}"
Name: "{autodesktop}\PLZ-Karte"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "PLZ-Karte jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; An Intune uninstall runs as SYSTEM and therefore cannot read the interactive
; user's %LOCALAPPDATA% control file. Try the graceful, same-user path first,
; then make sure no remaining server process keeps files in {app} locked.
Filename: "{app}\{#MyAppExeName}"; Parameters: "--shutdown"; Flags: runhidden waituntilterminated skipifdoesntexist
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM ""{#MyAppExeName}"""; Flags: runhidden waituntilterminated

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  InstalledExecutable: String;
begin
  Result := '';
  InstalledExecutable := ExpandConstant('{app}\{#MyAppExeName}');
  if FileExists(InstalledExecutable) then
  begin
    { Ask an already running local server to release the executable before }
    { Restart Manager performs its final files-in-use check. }
    Exec(InstalledExecutable, '--shutdown', '', SW_HIDE,
      ewWaitUntilTerminated, ResultCode);
    Sleep(1000);
  end;
end;
