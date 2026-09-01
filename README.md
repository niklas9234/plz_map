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
