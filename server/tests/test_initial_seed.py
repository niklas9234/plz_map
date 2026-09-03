import json
import logging
import sqlite3

import pytest

import app.initial_seed as initial_seed
from app.database import initialize
from app.initial_seed import INITIAL_SEED_ID, import_initial_seed


def connection():
    result = sqlite3.connect(":memory:")
    result.row_factory = sqlite3.Row
    result.execute("PRAGMA foreign_keys = ON")
    initialize(result)
    return result


def legacy_seed():
    timestamp = "2026-09-01T00:00:00Z"
    return {
        "schemaVersion": 1,
        "trades": [],
        "companies": [{
            "name": "Firma", "ppsNumber": "PPS-1", "trade": "Elektro",
            "territories": [{"postalCode": "08", "role": "primary"}],
            "information": [], "status": "active",
            "createdAt": timestamp, "updatedAt": timestamp,
        }],
    }


def write_seed(tmp_path, document):
    path = tmp_path / "companies.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def test_initial_seed_normalizes_names_and_generates_stable_ids(tmp_path):
    path = write_seed(tmp_path, legacy_seed())
    first = connection()
    result = import_initial_seed(first, path)
    company = first.execute("SELECT id, trade_id FROM companies").fetchone()
    trade = first.execute("SELECT id, name FROM trades").fetchone()

    second = connection()
    import_initial_seed(second, path)
    second_company = second.execute("SELECT id, trade_id FROM companies").fetchone()

    assert result == {"written": True, "seedId": INITIAL_SEED_ID, "trades": 1,
                      "companies": 1, "rejected": 0}
    assert trade["name"] == "Elektro"
    assert company["trade_id"] == trade["id"]
    assert tuple(company) == tuple(second_company)


def test_seed_marker_prevents_reimport_after_user_deletes_data(tmp_path):
    db = connection()
    path = write_seed(tmp_path, legacy_seed())
    import_initial_seed(db, path)
    db.execute("DELETE FROM companies")
    db.execute("DELETE FROM trades")
    db.commit()

    result = import_initial_seed(db, path)

    assert result["reason"] == "already-initialized"
    assert db.execute("SELECT count(*) FROM companies").fetchone()[0] == 0


def test_existing_database_is_permanently_excluded_from_initial_seed(tmp_path):
    db = connection()
    path = write_seed(tmp_path, legacy_seed())
    db.execute("INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?)",
               ("5ee3bdcf-3f8a-5ff2-86c0-5a4d6d3d306f", "Bestand", "active", None,
                "2026-09-01T00:00:00Z", "2026-09-01T00:00:00Z"))
    db.commit()

    assert import_initial_seed(db, path)["reason"] == "database-not-empty"
    db.execute("DELETE FROM trades")
    db.commit()
    assert import_initial_seed(db, path)["reason"] == "already-initialized"


def test_invalid_seed_rolls_back_and_logs_rejections(tmp_path, caplog):
    document = legacy_seed()
    document["companies"][0]["territories"] = []
    db = connection()

    with caplog.at_level(logging.ERROR), pytest.raises(Exception):
        import_initial_seed(db, write_seed(tmp_path, document))

    assert db.execute("SELECT count(*) FROM companies").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM application_metadata").fetchone()[0] == 0
    assert "Datensatz abgelehnt" in caplog.text


def test_interrupted_write_rolls_back_every_seed_row(tmp_path, monkeypatch):
    db = connection()

    def interrupted_write(connection, data):
        trade = data["trades"][0]
        connection.execute("INSERT INTO trades VALUES (?, ?, ?, ?, ?, ?)",
                           (trade["id"], trade["name"], trade["status"], trade["color"],
                            trade["createdAt"], trade["updatedAt"]))
        raise RuntimeError("simulierter Abbruch")

    monkeypatch.setattr(initial_seed, "write_validated_data", interrupted_write)
    with pytest.raises(RuntimeError, match="simulierter Abbruch"):
        import_initial_seed(db, write_seed(tmp_path, legacy_seed()))

    assert db.execute("SELECT count(*) FROM trades").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM application_metadata").fetchone()[0] == 0
