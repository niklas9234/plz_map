import copy
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.transfer import FORMAT, ImportValidationError, SCHEMA_VERSION, export_data, import_data
from app.models import Base


def document():
    trade_id, company_id, manager_id = str(uuid4()), str(uuid4()), str(uuid4())
    return {
        "format": FORMAT, "schemaVersion": SCHEMA_VERSION, "exportedAt": "2026-09-03T10:00:00Z", "applicationVersion": "test",
        "trades": [{"id": trade_id, "name": "Elektro", "status": "active", "color": "#123456",
                    "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-02-01T00:00:00Z"}],
        "companies": [{"id": company_id, "name": "Firma", "ppsNumber": "PPS-01", "tradeId": trade_id,
                       "territories": [{"postalCode": "08", "role": "primary"}],
                       "information": [{"category": "phone", "value": "123"}], "status": "inactive",
                       "createdAt": "2026-03-01T00:00:00Z", "updatedAt": "2026-04-01T00:00:00Z"}],
        "siteManagers": [{"id": manager_id, "name": "Alex Bau", "territories": ["08", "LUX"],
                          "status": "active", "createdAt": "2026-03-01T00:00:00Z",
                          "updatedAt": "2026-04-01T00:00:00Z"}],
    }


def test_round_trip_and_validate_mode_on_every_database(database_engine):
    source = document()
    with database_engine.connect() as db:
        assert import_data(db, source, "validate")["written"] is False
        assert import_data(db, source) == {"trades": 1, "companies": 1, "siteManagers": 1, "written": True}
        exported = export_data(db)
    for key in ("trades", "companies", "siteManagers"):
        assert exported[key] == source[key]


def test_sqlite_export_populates_a_separate_empty_database(database_engine):
    """Exercise the actual pilot hand-off: SQLite file -> JSON -> clean target."""
    source_document = document()
    sqlite = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(sqlite)
    try:
        with sqlite.connect() as source:
            import_data(source, source_document)
            exported = export_data(source)

        with database_engine.connect() as target:
            assert import_data(target, exported) == {
                "trades": 1, "companies": 1, "siteManagers": 1, "written": True,
            }
            imported = export_data(target)

            assert target.execute(text("SELECT company_id, postal_code, trade_id, role FROM territories")).one() == (
                source_document["companies"][0]["id"], "08",
                source_document["trades"][0]["id"], "primary",
            )
            assert target.execute(text("SELECT company_id, position, category, value FROM company_information")).one() == (
                source_document["companies"][0]["id"], 0, "phone", "123",
            )

        assert imported["trades"] == exported["trades"]
        assert imported["companies"] == exported["companies"]
        assert imported["siteManagers"] == exported["siteManagers"]
    finally:
        sqlite.dispose()


def test_incompatible_schema_version_has_an_actionable_error():
    incompatible = document()
    incompatible["schemaVersion"] = SCHEMA_VERSION + 1

    engine = create_engine("sqlite+pysqlite:///:memory:")
    try:
        with engine.connect() as connection:
            with pytest.raises(ImportValidationError, match=r"inkompatibel.*unterstützt wird nur Version"):
                import_data(connection, incompatible, "validate")
    finally:
        engine.dispose()


def test_export_contract_does_not_expose_machine_specific_metadata(database_engine):
    with database_engine.connect() as db:
        import_data(db, document())
        exported = export_data(db)

    assert set(exported) == {
        "format", "schemaVersion", "exportedAt", "applicationVersion", "trades", "companies", "siteManagers",
    }
    serialized = str(exported).lower()
    assert "sqlite" not in serialized
    assert "postgres" not in serialized
    assert "log" not in serialized
    assert "tmp" not in serialized


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


def test_database_allows_multiple_site_managers_in_the_same_area(database_engine):
    source = document()
    second = copy.deepcopy(source["siteManagers"][0])
    second["id"], second["name"] = str(uuid4()), "Sam Bau"
    source["siteManagers"].append(second)
    with database_engine.connect() as db:
        assert import_data(db, source)["siteManagers"] == 2
