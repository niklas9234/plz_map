# PLZ-Karte

Browserbasierte Karte zur Suche von Unternehmen und zur Anzeige ihrer
Postleitzahlgebiete in Deutschland und Luxemburg.

## Projektstruktur

```text
.
├── src/app/                 Statisches JavaScript-Frontend
│   └── data/pmtiles/        Lokaler Ablageort der großen Basiskarte
├── server/                  Vorbereitete Python-Backend-Struktur
│   ├── app/
│   │   ├── api/             HTTP-Endpunkte
│   │   ├── models/          Datenbankmodelle
│   │   └── schemas/         Ein- und Ausgabemodelle
│   ├── migrations/          Künftige Datenbankmigrationen
│   └── tests/               Backendtests
└── bereinigung/             Bestehende Werkzeuge und Zwischendaten
```

Das Frontend bleibt ohne Build-Schritt ausführbar. Das Verzeichnis `server/`
bildet die Grenze für das geplante Python-Backend; es enthält bewusst noch
keine Framework- oder Datenbankentscheidung.

## Lokaler Start des Frontends

1. Die Datei `germany-luxembourg.pmtiles` nach
   `src/app/data/pmtiles/` kopieren.
2. Einen statischen Webserver im Projektverzeichnis starten:

   ```sh
   python -m http.server 8000
   ```

3. `http://localhost:8000` im Browser öffnen. Die Startseite im
   Projektverzeichnis leitet automatisch zur Anwendung unter `src/app/`
   weiter. Dadurch funktioniert der Einstieg auch bei statischen Hosts, die
   das Repository-Verzeichnis als Dokumentenwurzel verwenden.

Die PMTiles-Datei wird nicht in Git aufgenommen. Weitere Karteneinstellungen
sind in `CONFIGURATION.md` beschrieben.

## Windows-Installation (ohne Docker und Python)

Das konkrete Paketierungsziel ist **Windows 10/11 (64 Bit)**. Das Setup enthält
den Python-Interpreter, das Backend und das Frontend; auf dem Zielrechner werden
weder Docker noch eine Python-Installation benötigt.

1. `PLZ-Karte-1.0.0-Setup.exe` ausführen und den Installationsdialog abschließen.
2. Über **PLZ-Karte starten** im Startmenü starten. Diese Verknüpfung öffnet den
   Standardbrowser. Die optionale Desktop-Verknüpfung tut dasselbe.
3. Vor Abmeldung, Neustart oder Update **PLZ-Karte beenden** im Startmenü wählen.
   Dadurch werden laufende Datenbankoperationen kontrolliert abgeschlossen. Es
   ist keine Eingabeaufforderung erforderlich.

Ein Update wird durch Ausführen des neueren Setups in dasselbe Verzeichnis
installiert. Vorher ist die Anwendung über **PLZ-Karte beenden** zu schließen.
Das Setup ersetzt ausschließlich unveränderliche Programmdateien unter
`%LOCALAPPDATA%\Programs\PLZ-Karte`; Datenbank, Backups und Logs bleiben separat
unter `%LOCALAPPDATA%\PLZ-Karte` erhalten.

Zur Deinstallation in den Windows-Einstellungen **Apps > Installierte Apps >
PLZ-Karte > Deinstallieren** wählen. Der Deinstaller beendet zunächst den
Server und entfernt nur die Programmdateien. Benutzerdaten bleiben absichtlich
unter `%LOCALAPPDATA%\PLZ-Karte` erhalten und können für eine Neuinstallation
übernommen werden. Sollen sie endgültig entfernt werden, kann dieser Ordner
anschließend im Explorer gelöscht werden.

### Windows-Paket erstellen

Auf einem Windows-Buildrechner werden Python 3.12, PowerShell und Inno Setup 6
benötigt. `packaging\windows\build.ps1` installiert mit demselben
Python-Interpreter die Laufzeitabhängigkeiten aus `server\requirements.txt` und
die Buildabhängigkeiten aus `packaging\windows\requirements-build.txt`, erzeugt
die eigenständige Anwendung und anschließend das Setup in `dist-installer\`.
Vor dem Build muss die nicht versionierte
PMTiles-Datei in `src\app\data\pmtiles\` liegen, wenn sie Teil des Installers
sein soll.

## Fachliche Spezifikation

Das verbindliche [Datenmodell](docs/data-model.md) beschreibt Unternehmen,
zweistellige PLZ-Gebiete, erweiterbare Gewerke und den Lebenszyklus von
Datensätzen. Der darauf aufbauende [API-Vertrag](docs/api.md) dient als Grundlage
für die noch ausstehende Backend- und Datenbankimplementierung.

Das [Exportformat](docs/export-format.md) und die getrennte
[SQLite-zu-PostgreSQL-Anleitung](docs/sqlite-to-postgresql.md) beschreiben die
portable Datensicherung und den Systemumzug.
