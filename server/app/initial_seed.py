"""One-time, versioned import of the bundled company master data."""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from .transfer import FORMAT, ImportValidationError, validate_import, write_validated_data


INITIAL_SEED_ID = "companies-json-2026-09-03-v2"
INITIAL_SEED_KEY = "initial_seed"
STABLE_ID_NAMESPACE = UUID("f90d8dca-2db4-4d17-8380-d94275ae563e")


def seed_file() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "frontend" / "companies.json"
    return Path(__file__).resolve().parents[2] / "src" / "app" / "companies.json"


def _stable_id(kind: str, identity: str) -> str:
    return str(uuid5(STABLE_ID_NAMESPACE, f"{kind}:{identity.strip().casefold()}"))


def _normalize(source: Any) -> dict[str, Any]:
    if not isinstance(source, dict) or not isinstance(source.get("companies"), list):
        raise ImportValidationError(["$: Seed muss ein Objekt mit einer Unternehmensliste sein"])
    source_trades = source.get("trades", [])
    if not isinstance(source_trades, list):
        raise ImportValidationError(["trades: muss eine Liste sein"])

    trades: list[dict[str, Any]] = []
    by_name: dict[str, str] = {}
    for index, original in enumerate(source_trades):
        if not isinstance(original, dict) or not str(original.get("name", "")).strip():
            raise ImportValidationError([f"trades[{index}]: Gewerkname fehlt"])
        trade = dict(original)
        name = str(trade["name"]).strip()
        trade["name"] = name
        trade["id"] = trade.get("id") or _stable_id("trade", name)
        by_name[name.casefold()] = trade["id"]
        trades.append(trade)

    companies: list[dict[str, Any]] = []
    for index, original in enumerate(source["companies"]):
        if not isinstance(original, dict):
            raise ImportValidationError([f"companies[{index}]: muss ein Objekt sein"])
        company = dict(original)
        legacy_name = str(company.pop("trade", "")).strip()
        if not company.get("tradeId") and legacy_name:
            key = legacy_name.casefold()
            if key not in by_name:
                timestamp = company.get("createdAt") or company.get("updatedAt") or "1970-01-01T00:00:00Z"
                trade_id = _stable_id("trade", legacy_name)
                trades.append({"id": trade_id, "name": legacy_name, "status": "active", "color": None,
                               "createdAt": timestamp, "updatedAt": timestamp})
                by_name[key] = trade_id
            company["tradeId"] = by_name[key]
        identity = str(company.get("ppsNumber") or company.get("name") or f"record-{index}")
        company["id"] = company.get("id") or _stable_id("company", identity)
        companies.append(company)

    return validate_import({
        "format": FORMAT,
        "schemaVersion": 1,
        "exportedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "applicationVersion": f"initial-seed:{INITIAL_SEED_ID}",
        "trades": trades,
        "companies": companies,
    })


def import_initial_seed(connection: sqlite3.Connection, path: Path | None = None,
                        logger: logging.Logger | None = None) -> dict[str, int | str | bool]:
    """Import bundled data exactly once, and atomically record that decision."""
    log = logger or logging.getLogger(__name__)
    try:
        connection.execute("BEGIN IMMEDIATE")
        previous = connection.execute(
            "SELECT value FROM application_metadata WHERE key=?", (INITIAL_SEED_KEY,)
        ).fetchone()
        if previous:
            connection.rollback()
            return {"written": False, "reason": "already-initialized", "seedId": previous[0]}

        has_data = any(connection.execute(f"SELECT EXISTS(SELECT 1 FROM {table})").fetchone()[0]
                       for table in ("trades", "companies"))
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if has_data:
            connection.execute("INSERT INTO application_metadata VALUES (?, ?, ?)",
                               (INITIAL_SEED_KEY, INITIAL_SEED_ID, now))
            connection.commit()
            log.info("Initialimport %s übersprungen: Datenbank enthält bereits Fachdaten", INITIAL_SEED_ID)
            return {"written": False, "reason": "database-not-empty", "seedId": INITIAL_SEED_ID}

        data = _normalize(json.loads((path or seed_file()).read_text(encoding="utf-8")))
        write_validated_data(connection, data)
        connection.execute("INSERT INTO application_metadata VALUES (?, ?, ?)",
                           (INITIAL_SEED_KEY, INITIAL_SEED_ID, now))
        connection.commit()
        log.info("Initialimport %s abgeschlossen: %d Gewerke, %d Unternehmen, 0 abgelehnt",
                 INITIAL_SEED_ID, len(data["trades"]), len(data["companies"]))
        return {"written": True, "seedId": INITIAL_SEED_ID,
                "trades": len(data["trades"]), "companies": len(data["companies"]), "rejected": 0}
    except Exception as error:
        connection.rollback()
        if isinstance(error, ImportValidationError):
            for rejection in error.errors:
                log.error("Initialimport %s: Datensatz abgelehnt: %s", INITIAL_SEED_ID, rejection)
        else:
            log.exception("Initialimport %s abgebrochen; alle Änderungen zurückgerollt", INITIAL_SEED_ID)
        raise
