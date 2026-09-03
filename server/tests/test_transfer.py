import copy
import sqlite3
from uuid import uuid4

import pytest

from app.database import initialize
from app.transfer import FORMAT, ImportValidationError, export_data, import_data


def connection():
    result = sqlite3.connect(":memory:")
    result.row_factory = sqlite3.Row
    result.execute("PRAGMA foreign_keys = ON")
    initialize(result)
    return result


def document():
    trade_id, company_id = str(uuid4()), str(uuid4())
    return {
        "format": FORMAT, "schemaVersion": 1, "exportedAt": "2026-09-03T10:00:00Z", "applicationVersion": "test",
        "trades": [{"id": trade_id, "name": "Elektro", "status": "active", "color": "#123456",
                    "createdAt": "2026-01-01T00:00:00Z", "updatedAt": "2026-02-01T00:00:00Z"}],
        "companies": [{"id": company_id, "name": "Firma", "ppsNumber": "PPS-01", "tradeId": trade_id,
                       "territories": [{"postalCode": "08", "role": "primary"}],
                       "information": [{"category": "Telefon", "value": "123"}], "status": "inactive",
                       "createdAt": "2026-03-01T00:00:00Z", "updatedAt": "2026-04-01T00:00:00Z"}],
    }


def test_round_trip_preserves_domain_data():
    db, source = connection(), document()
    assert import_data(db, source) == {"trades": 1, "companies": 1, "written": True}
    exported = export_data(db)
    for key in ("trades", "companies"):
        assert exported[key] == source[key]


def test_validate_mode_does_not_write():
    db = connection()
    assert import_data(db, document(), "validate")["written"] is False
    assert db.execute("SELECT count(*) FROM companies").fetchone()[0] == 0


def test_invalid_late_record_leaves_database_empty():
    db, invalid = connection(), document()
    duplicate = copy.deepcopy(invalid["companies"][0]); duplicate["id"] = str(uuid4())
    invalid["companies"].append(duplicate)
    with pytest.raises(ImportValidationError):
        import_data(db, invalid)
    assert db.execute("SELECT count(*) FROM trades").fetchone()[0] == 0


def test_empty_mode_refuses_existing_domain_data():
    db, source = connection(), document()
    import_data(db, source)
    with pytest.raises(ImportValidationError, match="nicht leer"):
        import_data(db, source)
