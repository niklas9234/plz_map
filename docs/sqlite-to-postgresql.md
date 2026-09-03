# Umzug von SQLite in eine leere PostgreSQL-Installation

Die PostgreSQL-Installation muss bereits migriert sein und leere fachliche
Tabellen besitzen.

1. Lokal **Daten exportieren** wählen oder den Export abrufen:
   ```sh
   curl --fail --output plz-map-export.json http://127.0.0.1:8080/api/admin/export
   ```
2. Die unveränderte Datei am Ziel vollständig validieren:
   ```sh
   curl --fail --request POST --header 'Content-Type: application/json' \
     --data-binary @plz-map-export.json \
     'https://ziel.example/api/admin/import?mode=validate'
   ```
3. Nur nach `written: false` und korrekten Zählern in die leere Datenbank
   übernehmen:
   ```sh
   curl --fail --request POST --header 'Content-Type: application/json' \
     --data-binary @plz-map-export.json \
     'https://ziel.example/api/admin/import?mode=empty'
   ```
4. Antwortzähler vergleichen und das Ziel erneut exportieren. `trades` und
   `companies` müssen identisch sein; nur `exportedAt` und
   `applicationVersion` dürfen abweichen. Danach die Ansichten prüfen.

`empty` ersetzt oder mischt nie vorhandene Daten. Tabellen nicht direkt
kopieren: Nur der versionierte Import erhält Validierung und Atomarität.
