from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_site_manager_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    database = tmp_path / "migration.sqlite"
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database}")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database}")
    assert {"site_managers", "site_manager_territories"} <= set(inspect(engine).get_table_names())
    with engine.begin() as connection:
        for identifier in ("1", "2"):
            connection.execute(text("INSERT INTO site_managers VALUES (:id,:name,'active','now','now')"),
                               {"id": identifier, "name": f"Bauleiter {identifier}"})
            connection.execute(text("INSERT INTO site_manager_territories VALUES (:id,'08')"), {"id": identifier})
    command.downgrade(config, "0002")
    assert "site_managers" not in inspect(engine).get_table_names()
