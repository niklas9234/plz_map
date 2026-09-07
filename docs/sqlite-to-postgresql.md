# Pilotdaten von SQLite nach PostgreSQL übergeben

Der verbindliche Übergabeweg ist ausschließlich der versionierte JSON-Export
über `GET /api/admin/export` und der Import über `POST /api/admin/import`.
SQLite-Dateien oder einzelne Tabellen dürfen nicht auf den Server kopiert
werden. Der Export enthält alle veränderlichen Stammdaten einschließlich IDs,
Status, Zeitstempeln, Gewerk- und Gebietsbeziehungen, Farben und geordneten
Zusatzinformationen. Logs, temporäre Dateien und lokale Dateipfade gehören
nicht zum Format.

## 1. Lokale Sicherung und Export

1. Die lokale Anwendung beenden, damit die SQLite-Datei konsistent ist.
2. Das gesamte lokale Datenverzeichnis gemäß dem in `CONFIGURATION.md`
   dokumentierten Speicherort auf ein separates Medium kopieren. Diese Kopie
   bis zur Abnahme der Migration unverändert aufbewahren.
3. Die Anwendung wieder starten und in **Verwalten** auf **Daten exportieren**
   klicken. Alternativ den identischen API-Endpunkt verwenden:

   ```sh
   curl --fail --remote-header-name --remote-name \
     http://127.0.0.1:8080/api/admin/export
   ```

   Der vom Server vorgegebene Dateiname enthält das Tagesdatum und die
   `SCHEMA_VERSION`, zum Beispiel
   `plz-map-export-2026-09-07-schema-v1.json`. Die JSON-Datei unverändert
   übertragen und zusätzlich sichern.

## 2. Leeren PostgreSQL-Server migrieren

PostgreSQL muss erreichbar sein und darf noch keine fachlichen Datensätze
enthalten. Im Backend-Container laufen die Migrationen beim Start automatisch.
Bei einem manuellen Deployment werden sie explizit gestartet:

```sh
cd server
DATABASE_URL='postgresql+psycopg://plz_map:…@db/plz_map' alembic upgrade head
```

Danach die vier fachlichen Tabellen kontrollieren:

```sql
SELECT 'trades' AS tabelle, count(*) FROM trades
UNION ALL SELECT 'companies', count(*) FROM companies
UNION ALL SELECT 'territories', count(*) FROM territories
UNION ALL SELECT 'company_information', count(*) FROM company_information;
```

Alle vier Zähler müssen `0` sein. Der Import verweigert andernfalls die
Übernahme und nennt die belegten Tabellen.

## 3. Erst validieren, dann importieren

Die unveränderte Datei zunächst ohne Schreibzugriff vollständig prüfen:

```sh
curl --fail --request POST --header 'Content-Type: application/json' \
  --data-binary @plz-map-export-2026-09-07-schema-v1.json \
  'https://ziel.example/api/admin/import?mode=validate'
```

Nur wenn die Antwort die erwarteten Zähler sowie `"written": false` enthält,
den atomaren Import ausführen:

```sh
curl --fail --request POST --header 'Content-Type: application/json' \
  --data-binary @plz-map-export-2026-09-07-schema-v1.json \
  'https://ziel.example/api/admin/import?mode=empty'
```

Eine nicht unterstützte `schemaVersion` wird mit HTTP 422 und einer
verständlichen Versionsmeldung abgelehnt. Die Exportdatei nicht von Hand an
eine andere Version anpassen.

## 4. Ergebnis abnehmen

1. Die gemeldeten `trades`- und `companies`-Zähler mit dem lokalen Bestand
   vergleichen.
2. Die obige SQL-Zählabfrage erneut ausführen; insbesondere müssen auch
   `territories` und `company_information` plausibel sein.
3. Am Ziel erneut `/api/admin/export` abrufen. Die Arrays `trades` und
   `companies` müssen mit dem Übergabeexport übereinstimmen; nur die
   Exportmetadaten `exportedAt` und `applicationVersion` dürfen abweichen.
4. In der Oberfläche mindestens je ein aktives und inaktives Unternehmen,
   eine primäre und alternative Gebietszuordnung, die PPS-Nummer, das Gewerk,
   die Farbe und geordnete Kontaktinformationen stichprobenartig prüfen.

## 5. Rückfall

Bei einer fehlgeschlagenen Abnahme keine Daten zusammenführen. Den Zielserver
stoppen und die neu befüllte PostgreSQL-Datenbank verwerfen beziehungsweise
aus einem vor dem Import erzeugten PostgreSQL-Snapshot wiederherstellen. Für
den lokalen Betrieb die Anwendung beenden, das aktuelle Datenverzeichnis
separat archivieren und die in Schritt 1 erstellte Sicherung vollständig an
ihren ursprünglichen Ort zurückkopieren. Danach die lokale Anwendung starten
und Zähler sowie Stichproben erneut prüfen. Der gesicherte JSON-Export bleibt
die Grundlage für einen erneuten Übergabeversuch.
