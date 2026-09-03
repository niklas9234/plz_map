# Separater Serverbetrieb

Diese Compose-Konfiguration ist ausschließlich für den containerisierten
Serverbetrieb bestimmt. Sie verändert weder den lokalen Startbefehl noch dessen
SQLite-Datenverzeichnis. PostgreSQL ist nur im internen Compose-Netz erreichbar;
Nginx liefert das Frontend aus und leitet `/api/` an Gunicorn weiter.

```sh
cd deploy/server
cp .env.example .env
# Passwort in .env ändern
docker compose up --build -d
```

Vor jedem Backendstart führt der Container `alembic upgrade head` aus. Für einen
PostgreSQL-Testlauf kann dessen URL separat übergeben werden:

```sh
TEST_POSTGRESQL_URL='postgresql+psycopg://plz_map:…@localhost/plz_map_test' \
  PYTHONPATH=server pytest server/tests
```
