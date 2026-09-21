from pathlib import Path
import logging

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def test_existing_company_trade_and_territory_are_migrated_without_new_ids(tmp_path, monkeypatch):
    database = tmp_path / "migration.sqlite3"
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{database}")
    command.upgrade(config, "0003")
    company_id = "11111111-1111-4111-8111-111111111111"
    trade_id = "22222222-2222-4222-8222-222222222222"
    engine = create_engine(f"sqlite:///{database}")
    with engine.begin() as db:
        db.execute(text("INSERT INTO trades VALUES (:id,'Elektro','active','#123456','created','updated')"), {"id": trade_id})
        db.execute(text("INSERT INTO companies VALUES (:id,'Firma','PPS-1',:trade,'active','created','updated')"), {"id": company_id, "trade": trade_id})
        db.execute(text("INSERT INTO territories VALUES (:company,'08',:trade,'primary')"), {"company": company_id, "trade": trade_id})
        db.execute(text("INSERT INTO company_information VALUES (:company,0,'phone','123')"), {"company": company_id})
    engine.dispose()

    command.upgrade(config, "head")
    # Alembic's logging configuration disables already-created application
    # loggers; do not leak that process-global side effect into later tests.
    for logger in logging.Logger.manager.loggerDict.values():
        if isinstance(logger, logging.Logger):
            logger.disabled = False

    engine = create_engine(f"sqlite:///{database}")
    with engine.connect() as db:
        assert db.execute(text("SELECT id, pps_number FROM companies")).one() == (company_id, "PPS-1")
        assert db.execute(text("SELECT company_id, trade_id FROM company_trades")).one() == (company_id, trade_id)
        assert db.execute(text("SELECT company_id, trade_id, postal_code, role FROM territories")).one() == (company_id, trade_id, "08", "primary")
        assert db.execute(text("SELECT company_id, position, value FROM company_information")).one() == (company_id, 0, "123")
    engine.dispose()
