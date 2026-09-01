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
2. Einen statischen Webserver mit Unterstützung für HTTP-Range-Requests und
   `src/app` als Dokumentenwurzel starten, zum Beispiel mit Node.js:

   ```sh
   npx serve src/app --listen 8000
   ```

3. `http://localhost:8000` im Browser öffnen.

Die PMTiles-Datei wird nicht in Git aufgenommen. Weitere Karteneinstellungen
sind in `CONFIGURATION.md` beschrieben. `python -m http.server` eignet sich
hier nicht, weil der PMTiles-Client Bytebereiche aus dem Kartenarchiv abruft.

## Unternehmensverwaltung im Frontend-Prototyp

Über **Verwalten** lassen sich Unternehmen suchen, nach Gewerk filtern,
anlegen, bearbeiten und löschen. Bis das Python-Backend und PostgreSQL
implementiert sind, speichert der Browser diese Änderungen ausschließlich im
lokalen Speicher (`localStorage`). Die Datei `companies.json` dient beim ersten
Aufruf als Ausgangsdatenbestand. Änderungen sind daher noch nicht zwischen
mehreren Browsern oder Rechnern synchronisiert.
