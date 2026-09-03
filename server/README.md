# Python-Backend

Dieses Verzeichnis ist für die geplante gemeinsame Datenhaltung vorgesehen.
Das bestehende Frontend bleibt davon getrennt unter `src/app`.

## Vorgesehene Verantwortlichkeiten

- `app/api/`: HTTP-Endpunkte, zum Beispiel `/api/companies`
- `app/models/`: persistente Datenbankmodelle
- `app/schemas/`: validierte API-Ein- und Ausgaben
- `migrations/`: versionierte Änderungen am Datenbankschema
- `tests/`: automatisierte Backendtests

Das Backend verwendet für den Transfer bewusst nur Python-Standardbibliothek
und SQLite. Start aus dem Repository-Wurzelverzeichnis:

```sh
PYTHONPATH=server python server/run.py
```

`GET /api/admin/export` lädt den vollständigen Export herunter. Ein Import wird
als JSON-Body an `POST /api/admin/import?mode=validate` (nur prüfen) oder
`POST /api/admin/import?mode=empty` (in eine leere Datenbank übernehmen)
gesendet. Der Datenbankpfad kann mit `PLZ_MAP_DATABASE` gesetzt werden.
