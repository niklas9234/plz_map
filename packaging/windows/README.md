# Windows-Paket erstellen und in Intune erkennen

## Build

Die Releaseversion wird dem Buildskript einmal als numerische Version mit drei
oder vier Komponenten übergeben:

```powershell
.\packaging\windows\build.ps1 -Version 1.2.3
```

Das Skript verwendet denselben Wert für die Datei- und Produktversion von
`PLZ-Karte.exe`, für `AppVersion` und für den Dateinamen des Inno-Setup-Pakets.

## Intune Detection Rule

In Microsoft Intune wird für die Win32-App eine **manuelle Erkennungsregel** vom
Typ **Registrierung** angelegt:

| Einstellung | Wert |
| --- | --- |
| Schlüsselpfad | `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{702FD881-85A7-4DB8-A28F-A8070BCF77B9}_is1` |
| Wertname | `DisplayVersion` |
| Erkennungsmethode | Zeichenfolgenvergleich |
| Operator | Gleich |
| Wert | Die an `build.ps1` übergebene Releaseversion, zum Beispiel `1.2.3` |
| Mit einer 32-Bit-App auf 64-Bit-Clients verknüpft | Nein |

Die unveränderte Inno-Setup-`AppId` sorgt dafür, dass der Uninstall-Schlüssel
über Releases hinweg stabil bleibt. Bei jedem Intune-Paket muss der erwartete
`DisplayVersion`-Wert auf genau die Version gesetzt werden, mit der der
Installer gebaut wurde.
