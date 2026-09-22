# Windows-Release

## Build und Version

Ein Release-Tag hat das Format `vMAJOR.MINOR.PATCH`. Der Workflow
`.github/workflows/windows-release.yml` übergibt den Tag an `build.ps1`; dieses entfernt
das führende `v` und definiert damit `MyAppVersion` für Inno Setup. Ein Build ohne
gültige Version bricht ab. Lokal kann derselbe Build an einem ausgecheckten Tag oder
explizit mit `./packaging/windows/build.ps1 -Version 1.2.3` ausgeführt werden.

Das Ergebnis liegt in `dist-installer/`. Neben dem Installer wird dort
`SHA256SUMS.txt` erzeugt. Der GitHub-Workflow veröffentlicht beide Dateien gemeinsam
als Workflow-Artefakt.

Für die Intune-App ist als Deinstallationsbefehl
`"C:\Program Files\PLZ-Karte\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART`
zu hinterlegen. Der Uninstaller versucht zunächst, die Anwendung kontrolliert zu
beenden. Da ein als SYSTEM ausgeführter Prozess nicht auf die benutzerspezifische
Steuerdatei zugreifen kann, beendet er anschließend noch laufende Instanzen der
`PLZ-Karte.exe`, bevor die Programmdateien entfernt werden.

## Signierung

Für signierte Releases werden die Repository-Secrets
`WINDOWS_SIGNING_CERTIFICATE_BASE64` (Base64-kodierte PFX-Datei) und
`WINDOWS_SIGNING_PASSWORD` gepflegt. Der Workflow legt das Zertifikat nur temporär
auf dem Runner ab. `build.ps1` signiert mit SHA-256 und Zeitstempel sowohl die
Anwendungs-EXE vor dem Packen als auch den fertigen Installer. Fehlt das Zertifikat,
entsteht bewusst ein unsignierter Test-Build; ein öffentliches Release darf daraus
nicht freigegeben werden.

## Upgrade-Abnahme

`upgrade-test.ps1` ist der automatisierte Abnahmetest für zwei bereits gebaute
Installer. Er ist **ausschließlich auf einer Wegwerf-Windows-VM** und für die
Intune-Abnahme in einem Benutzerkontext nach einer Bereitstellung mit dem
Installationsverhalten **System** auszuführen, da er `%LOCALAPPDATA%\PLZ-Karte`
löscht. Der Test prüft die Installation unter `%ProgramFiles%\PLZ-Karte` und die
gemeinsame Startmenüverknüpfung `PLZ-Karte`, startet Version A als angemeldeter
Benutzer und legt über deren API Testdaten in
`%LOCALAPPDATA%\PLZ-Karte\plz_map.sqlite3` an. Nach
dem Update auf Version B prüft er zusätzlich, dass die früheren Verknüpfungen
`PLZ-Karte starten` und `PLZ-Karte beenden` entfernt wurden, und vergleicht
Unternehmen, Gewerke, Gebiete, Bauleiter und Unternehmensinformationen vollständig.
Abschließend simuliert er die fehlende
SYSTEM-Sicht auf die benutzerspezifische Steuerdatei, deinstalliert die noch laufende
Anwendung und prüft, dass der Prozess beendet, die Programmdateien entfernt und die
benutzerspezifische SQLite-Datei erhalten bleibt:

```powershell
./packaging/windows/upgrade-test.ps1 `
  -InstallerA C:\Release\PLZ-Karte-1.2.2-Setup.exe `
  -InstallerB C:\Release\PLZ-Karte-1.2.3-Setup.exe `
  -ConfirmDataDeletion
```

## Freigabe-Checkliste

1. Release-Commit testen und einen annotierten Tag `vMAJOR.MINOR.PATCH` pushen.
2. Erfolgreichen Lauf von **Windows release** und dessen Build-Protokoll prüfen.
3. Prüfen, dass Installer und Anwendungs-EXE eine gültige Herausgebersignatur und
   einen vertrauenswürdigen Zeitstempel besitzen (`Get-AuthenticodeSignature`).
4. `SHA256SUMS.txt` gegen `Get-FileHash <Installer> -Algorithm SHA256` prüfen.
5. Den Upgrade-Abnahmetest auf einem sauberen Intune-Testgerät mit
   Installationsverhalten **System**, dem letzten freigegebenen Installer als Version
   A und dem neuen Artefakt als Version B erfolgreich ausführen. Den Start und den
   Test dabei als normaler vorgesehener Benutzer durchführen.
6. Erst danach GitHub Release anlegen, Installer und Prüfsummendatei anhängen und
   die Prüfsumme in den Release Notes veröffentlichen.
