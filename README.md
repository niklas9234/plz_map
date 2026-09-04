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

Das konkrete Paketierungsziel ist **Windows 10/11 (64 Bit)**. Das Setup benötigt
Administratorrechte, damit es das gemeinsame Logverzeichnis anlegen und für
Benutzer beschreibbar machen kann. Es enthält
den Python-Interpreter, das Backend und das Frontend; auf dem Zielrechner werden
weder Docker noch eine Python-Installation benötigt.

1. `PLZ-Karte-1.0.0-Setup.exe` ausführen und den Installationsdialog abschließen.
2. Über **PLZ-Karte starten** im Startmenü starten. Die Karte läuft in einem
   eigenen App-Fenster und öffnet kein Browserfenster. Das App-Fenster stellt
   keine Entwicklertools bereit; auch F12 und die üblichen Tastenkombinationen
   zum Öffnen der Entwicklertools sind deaktiviert.
3. Das App-Fenster normal schließen. Dabei wird auch der lokale Server sauber
   beendet. Falls eine Instanz ohne Fenster beendet werden muss, steht weiterhin
   **PLZ-Karte beenden** im Startmenü zur Verfügung.

Ein Update wird durch Ausführen des neueren Setups in dasselbe Verzeichnis
installiert. Vorher ist die Anwendung über **PLZ-Karte beenden** zu schließen.
Das Setup ersetzt ausschließlich unveränderliche Programmdateien unter
`%LOCALAPPDATA%\Programs\PLZ-Karte`; Datenbank und Backups bleiben separat
unter `%LOCALAPPDATA%\PLZ-Karte` erhalten. Die Logs bleiben unter
`C:\Logs\PLZ-Karte` erhalten.

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
die Buildabhängigkeiten einschließlich der nativen WebView aus
`packaging\windows\requirements-build.txt`, erzeugt
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
