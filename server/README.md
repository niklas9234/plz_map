# Python-Backend

Das Backend hält die gemeinsam genutzten Stammdaten und liefert die API aus. Es
unterstützt zwei bewusst getrennte Betriebsprofile.

## Lokaler Pilotbetrieb im Browser

Der Standardstart ist für einen einzelnen Arbeitsplatz gedacht:

```sh
pip install -r server/requirements.txt
python server/run.py
```

Dafür sind weder `.env` noch PostgreSQL oder eine manuell gesetzte
`DATABASE_URL` erforderlich. Der Start verwendet SQLite und bindet den
integrierten HTTP-Server fest und ausschließlich an `127.0.0.1:8080`.
Die Anwendung öffnet sich automatisch im Standardbrowser. Daten, Sicherungen und Logs
werden über `prepare_data_directories()` in den plattformspezifischen lokalen
Verzeichnissen angelegt. `--shutdown` beendet diese lokale Instanz kontrolliert.

Unter Windows liegen Daten und Backups standardmäßig in
`%LOCALAPPDATA%\PLZ-Karte\`, Logs in `C:\Logs\PLZ-Karte\`. Unter Linux ist
`$XDG_DATA_HOME/PLZ-Karte/` beziehungsweise `~/.local/share/PLZ-Karte/` der
Standard. Für Tests oder Administration lassen sich diese Orte mit
`PLZ_MAP_DATA_DIR` und `PLZ_MAP_LOG_DIR` überschreiben. Vor jedem lokalen Start
wird eine vorhandene SQLite-Datenbank gesichert; zehn Sicherungen bleiben
erhalten.

### Expliziter lokaler Browserbetrieb

Für Entwicklung und Skripte kann der Browserbetrieb auch ausdrücklich
gestartet werden:

```sh
pip install -r server/requirements.txt
python server/run.py --local-server
```

Danach öffnet sie automatisch `http://127.0.0.1:8080` im Standardbrowser und
zeigt die Adresse im Terminal an. Für einen Start ohne automatisches Öffnen
steht `python server/run.py --local-server --no-browser` bereit. Anders als ein reiner
statischer Entwicklungsserver liefert dieser Prozess auch `/api/companies` und
`/api/trades` aus. Statische Server wie `python -m http.server` oder
`http-server` können diese API-Endpunkte nicht bedienen und liefern dort 404.
Der Startbefehl funktioniert auch direkt in PowerShell; eine Unix-artige
`PYTHONPATH=server`-Zuweisung ist weder erforderlich noch unter PowerShell
gültig.

## Zentraler Mehrbenutzerbetrieb (Server)

Das ausdrücklich gewählte Serverprofil wird so gestartet:

```sh
DATABASE_URL='postgresql+psycopg://USER:PASSWORD@DBHOST/DBNAME' \
PLZ_MAP_HOST='0.0.0.0' PLZ_MAP_PORT='8000' \
python server/run.py --server
```

`DATABASE_URL` ist in diesem Profil verpflichtend. Bind-Adresse und Port stammen
aus `PLZ_MAP_HOST` und `PLZ_MAP_PORT` (Standardwerte `0.0.0.0` und `8000`). Das
Serverprofil importiert oder initialisiert `pywebview` nicht. Für einen
containerisierten Betrieb mit PostgreSQL und Reverse Proxy siehe
[`deploy/server/README.md`](../deploy/server/README.md).

## Gemeinsame Backendfunktionen

Beide Profile verwenden dieselben Funktionen zur Logging-Konfiguration,
Datenbank-/Schema-Initialisierung und Erstellung der WSGI-Anwendung in
`app/production.py`. Das Frontend liegt weiterhin getrennt in `src/app/`.
API-Endpunkte sind unter anderem `GET /api/admin/export` und
`POST /api/admin/import?mode=validate|empty`.

Beim ersten Start einer leeren Datenbank werden die gebündelten Stammdaten aus
`src/app/companies.json` importiert. Import und Versionsmarkierung erfolgen in
einer Transaktion; eine bestehende Datenbank wird nicht erneut befüllt.
