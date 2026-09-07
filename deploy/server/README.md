# Zentraler Mehrbenutzerbetrieb

Diese Compose-Konfiguration ist ausschließlich für den zentralen Serverbetrieb
bestimmt. Sie verändert weder den lokalen Desktopstart noch dessen SQLite- und
Logverzeichnisse. PostgreSQL ist nur im internen Compose-Netz erreichbar; Nginx
liefert das Frontend aus und leitet `/api/` an das Backend weiter.

## Konfiguration und Start

Die eingecheckte `.env.example` enthält ausschließlich Variablennamen und
unverfängliche Portwerte, aber kein Kennwort. Das Datenbankkennwort muss lokal
ergänzt werden und darf nicht eingecheckt werden:

```sh
cd deploy/server
cp .env.example .env
# POSTGRES_PASSWORD in .env auf einen zufälligen Wert setzen
chmod 600 .env
docker compose up --build -d
```

Compose setzt die interne `DATABASE_URL` aus diesem Laufzeitgeheimnis zusammen.
Der Container führt vor jedem Gunicorn-Start `alembic upgrade head` aus. Die
Bind-Adresse des Backends bleibt im Container-Netz; veröffentlicht wird nur der
mit `HTTP_PORT` konfigurierte Nginx-Port.

## Getrennter PostgreSQL-Testlauf

```sh
TEST_POSTGRESQL_URL='postgresql+psycopg://USER:PASSWORD@HOST/TESTDB' \
  PYTHONPATH=server pytest server/tests
```

Die lokale Pilotinstallation ist separat in [`server/README.md`](../../server/README.md)
beschrieben und benötigt weder Docker noch `.env`.
