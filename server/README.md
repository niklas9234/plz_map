# Python-Backend

Dieses Verzeichnis ist für die geplante gemeinsame Datenhaltung vorgesehen.
Das bestehende Frontend bleibt davon getrennt unter `src/app`.

## Vorgesehene Verantwortlichkeiten

- `app/api/`: HTTP-Endpunkte, zum Beispiel `/api/companies`
- `app/models/`: persistente Datenbankmodelle
- `app/schemas/`: validierte API-Ein- und Ausgaben
- `migrations/`: versionierte Änderungen am Datenbankschema
- `tests/`: automatisierte Backendtests

Das Backend verwendet SQLAlchemy und bleibt mit SQLite sowie PostgreSQL kompatibel. Der lokale
Produktionsstart bindet ausschließlich an `127.0.0.1:8080` und liefert das
Frontend aus `src/app/` mit aus. Start aus dem Repository-Wurzelverzeichnis:

```sh
PYTHONPATH=server python server/run.py --server
```

Ohne `--server` startet das Programm als eigenständige Desktopanwendung in einer
nativen WebView (dafür wird `pywebview` aus den Windows-Buildabhängigkeiten
benötigt). Mit `--shutdown` wird eine laufende Instanz kontrolliert beendet. Der Server nimmt
dann keine neuen Anfragen mehr an, beendet die aktuelle Anfrage und schließt
erst danach Server und Datenbankverbindungen.

Die Python-Abhängigkeiten werden mit `pip install -r server/requirements.txt`
installiert. `GET /api/admin/export` lädt den vollständigen Export herunter. Ein Import wird
als JSON-Body an `POST /api/admin/import?mode=validate` (nur prüfen) oder
`POST /api/admin/import?mode=empty` (in eine leere Datenbank übernehmen)
gesendet. Die Datenbankverbindung kann mit `DATABASE_URL` gesetzt werden.

Beim ersten Start einer leeren Datenbank importiert das Backend die gebündelten
Stammdaten aus `src/app/companies.json`. Import und Versionsmarkierung werden in
einer gemeinsamen Transaktion geschrieben. Die dauerhafte Markierung verhindert
auch nach einem Programmupdate oder nach dem Löschen aller Fachdaten einen
erneuten Seed-Import; vorhandene Datenbanken werden grundsätzlich nicht befüllt.
Umfang und abgelehnte Datensätze werden in das Anwendungslog geschrieben.

## Veränderliche Daten

Programmdateien und Benutzerdaten sind strikt getrennt. Ohne explizite
Konfiguration liegen Datenbank, Start-Backups und Logs unter Windows in
`%LOCALAPPDATA%\PLZ-Karte\` (unter Linux in
`$XDG_DATA_HOME/PLZ-Karte/`, sonst `~/.local/share/PLZ-Karte/`). Eine vorhandene
Datenbank wird bei jedem Start mit der SQLite-Backup-API konsistent nach
`backups/` gesichert; die zehn jüngsten Sicherungen bleiben erhalten. Logs
liegen in `logs/`. Für Tests oder Administration kann das gesamte Stammverzeichnis
mit `PLZ_MAP_DATA_DIR` überschrieben werden. Die Datenbank wird einheitlich über
`DATABASE_URL` konfiguriert, beispielsweise `sqlite:////tmp/plz-map.sqlite3`
oder `postgresql+psycopg://user:password@host/database`. Ohne Variable wird die
beschriebene lokale SQLite-Datei verwendet. `PLZ_MAP_DATABASE` wird für bestehende
lokale Installationen vorläufig weiterhin als SQLite-Pfad akzeptiert.

Die vollständig getrennte Containerkonfiguration für den Serverbetrieb liegt
unter `deploy/server/`; die lokale Installation benötigt weder Docker noch
PostgreSQL.
