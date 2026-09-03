import copy
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.transfer import FORMAT, ImportValidationError, SCHEMA_VERSION, export_data, import_data


def document():
    trade_id, company_id = str(uuid4()), str(uuid4())
    return {
        "format": FORMAT, "schemaVersion": SCHEMA_VERSION, "exportedAt": "2026-09-03T10:00:00Z", "applicationVersion": "test",
        "trades": [{"id": trade_id, "name": "Elektro", "status": "active", "color": "#123456",
                    "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-02-01T00:00:00Z"}],
        "companies": [{"id": company_id, "name": "Firma", "ppsNumber": "PPS-01", "tradeId": trade_id,
                       "territories": [{"postalCode": "08", "role": "primary"}],
                       "information": [{"category": "phone", "value": "123"}], "status": "inactive",
                       "createdAt": "2026-03-01T00:00:00Z", "updatedAt": "2026-04-01T00:00:00Z"}],
    }


def test_round_trip_and_validate_mode_on_every_database(database_engine):
    source = document()
    with database_engine.connect() as db:
        assert import_data(db, source, "validate")["written"] is False
        assert import_data(db, source) == {"trades": 1, "companies": 1, "written": True}
        exported = export_data(db)
    for key in ("trades", "companies"):
        assert exported[key] == source[key]


def test_invalid_late_record_is_atomic_on_every_database(database_engine):
    invalid = document()
    duplicate = copy.deepcopy(invalid["companies"][0]); duplicate["id"] = str(uuid4())
    invalid["companies"].append(duplicate)
    with database_engine.connect() as db:
        with pytest.raises(ImportValidationError):
            import_data(db, invalid)
        assert db.execute(text("SELECT count(*) FROM trades")).scalar_one() == 0


def test_database_enforces_case_insensitive_trade_names(database_engine):
    source = document()
    with database_engine.connect() as db:
        import_data(db, source)
        with pytest.raises(IntegrityError):
            with db.begin():
                db.execute(text("INSERT INTO trades (id,name,status,color,created_at,updated_at) VALUES (:id,'ELEKTRO','active','#654321','now','now')"), {"id": str(uuid4())})


def test_database_enforces_unique_pps_number(database_engine):
    source = document()
    with database_engine.connect() as db:
        import_data(db, source)
        with pytest.raises(IntegrityError):
            with db.begin():
                db.execute(text("INSERT INTO companies (id,name,pps_number,trade_id,status,created_at,updated_at) VALUES (:id,'Zweite','PPS-01',:trade,'active','now','now')"),
                           {"id": str(uuid4()), "trade": source["trades"][0]["id"]})


def test_database_enforces_trade_relationship(database_engine):
    with database_engine.connect() as db:
        with pytest.raises(IntegrityError):
            with db.begin():
                db.execute(text("INSERT INTO companies (id,name,pps_number,trade_id,status,created_at,updated_at) VALUES (:id,'Firma','PPS-X',:trade,'active','now','now')"),
                           {"id": str(uuid4()), "trade": str(uuid4())})


def test_database_allows_only_one_primary_per_trade_and_area(database_engine):
    source = document()
    with database_engine.connect() as db:
        import_data(db, source)
        company_id = str(uuid4())
        with pytest.raises(IntegrityError):
            with db.begin():
                db.execute(text("INSERT INTO companies (id,name,pps_number,trade_id,status,created_at,updated_at) VALUES (:id,'Zweite','PPS-02',:trade,'active','now','now')"),
                           {"id": company_id, "trade": source["trades"][0]["id"]})
                db.execute(text("INSERT INTO territories (company_id,postal_code,trade_id,role) VALUES (:id,'08',:trade,'primary')"),
                           {"id": company_id, "trade": source["trades"][0]["id"]})
