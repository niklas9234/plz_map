# Python-Backend

Dieses Verzeichnis ist für die geplante gemeinsame Datenhaltung vorgesehen.
Das bestehende Frontend bleibt davon getrennt unter `src/app`.

## Vorgesehene Verantwortlichkeiten

- `app/api/`: HTTP-Endpunkte, zum Beispiel `/api/companies`
- `app/models/`: persistente Datenbankmodelle
- `app/schemas/`: validierte API-Ein- und Ausgaben
- `migrations/`: versionierte Änderungen am Datenbankschema
- `tests/`: automatisierte Backendtests

Das Backend verwendet nur Python-Standardbibliothek und SQLite. Der lokale
Produktionsstart bindet ausschließlich an `127.0.0.1:8080` und liefert das
Frontend aus `src/app/` mit aus. Start aus dem Repository-Wurzelverzeichnis:

```sh
PYTHONPATH=server python server/run.py
```

Mit `--open-browser` wird zusätzlich der Standardbrowser geöffnet. Mit
`--shutdown` wird eine laufende Instanz kontrolliert beendet. Der Server nimmt
dann keine neuen Anfragen mehr an, beendet die aktuelle Anfrage und schließt
erst danach Server und Datenbankverbindungen.

`GET /api/admin/export` lädt den vollständigen Export herunter. Ein Import wird
als JSON-Body an `POST /api/admin/import?mode=validate` (nur prüfen) oder
`POST /api/admin/import?mode=empty` (in eine leere Datenbank übernehmen)
gesendet. Der Datenbankpfad kann mit `PLZ_MAP_DATABASE` gesetzt werden.

## Veränderliche Daten

Programmdateien und Benutzerdaten sind strikt getrennt. Ohne explizite
Konfiguration liegen Datenbank, Start-Backups und Logs unter Windows in
`%LOCALAPPDATA%\PLZ-Karte\` (unter Linux in
`$XDG_DATA_HOME/PLZ-Karte/`, sonst `~/.local/share/PLZ-Karte/`). Eine vorhandene
Datenbank wird bei jedem Start mit der SQLite-Backup-API konsistent nach
`backups/` gesichert; die zehn jüngsten Sicherungen bleiben erhalten. Logs
liegen in `logs/`. Für Tests oder Administration kann das gesamte Stammverzeichnis
mit `PLZ_MAP_DATA_DIR` überschrieben werden.
