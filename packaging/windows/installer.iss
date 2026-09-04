#define MyAppName "PLZ-Karte"
#define MyAppVersion "1.0.0"
#define MyAppExeName "PLZ-Karte.exe"

[Setup]
AppId={{702FD881-85A7-4DB8-A28F-A8070BCF77B9}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={localappdata}\Programs\PLZ-Karte
DefaultGroupName=PLZ-Karte
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist-installer
OutputBaseFilename=PLZ-Karte-{#MyAppVersion}-Setup
Compression=lzma2
SolidCompression=yes
CloseApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\..\PLZ-Karte.ico

[Files]
Source: "..\..\dist\PLZ-Karte\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
Name: "C:\Logs\PLZ-Karte"; Permissions: users-modify

[Icons]
Name: "{group}\PLZ-Karte starten"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{group}\PLZ-Karte beenden"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--shutdown"; WorkingDir: "{app}"
Name: "{autodesktop}\PLZ-Karte"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Symbole:"; Flags: unchecked

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "PLZ-Karte jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--shutdown"; Flags: runhidden waituntilterminated skipifdoesntexist
