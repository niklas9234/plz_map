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


INITIAL_SEED_ID = "companies-json-2026-09-22-v4"
INITIAL_SEED_KEY = "initial_seed"
STABLE_ID_NAMESPACE = UUID("f90d8dca-2db4-4d17-8380-d94275ae563e")
LEGACY_DEMO_COMPANY_IDS = {
    "e892a721-8890-504a-a8c7-27b9276e6e0b",
    "ee266c9f-afc6-5475-ade8-2bf6f373eb0e",
    "a9559e54-f852-503b-a516-872d14b6e5e2",
    "99dc32a0-6ce2-5153-bed2-e210774df026",
    "f7aadfa9-9ca4-57f7-b78e-f74313405425",
}


def _contains_unchanged_legacy_demo(connection: sqlite3.Connection) -> bool:
    """Identify only the exact, unedited demo company set shipped previously."""
    company_ids = {row[0] for row in connection.execute("SELECT id FROM companies")}
    manager_count = connection.execute("SELECT count(*) FROM site_managers").fetchone()[0]
    return company_ids == LEGACY_DEMO_COMPANY_IDS and manager_count == 0


def _clear_master_data(connection: sqlite3.Connection) -> None:
    """Clear an identified demo seed in foreign-key-safe dependency order."""
    for table in (
        "site_manager_territories", "site_managers", "company_information",
        "territories", "company_trades", "companies", "trades",
    ):
        connection.execute(f"DELETE FROM {table}")


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
        if "tradeAssignments" not in company and company.get("tradeId"):
            company["tradeAssignments"] = [{
                "tradeId": company.pop("tradeId"),
                "territories": company.pop("territories", []),
            }]
        identity = str(company.get("ppsNumber") or company.get("name") or f"record-{index}")
        company["id"] = company.get("id") or _stable_id("company", identity)
        companies.append(company)

    source_site_managers = source.get("siteManagers", [])
    if not isinstance(source_site_managers, list):
        raise ImportValidationError(["siteManagers: muss eine Liste sein"])
    site_managers: list[dict[str, Any]] = []
    for index, original in enumerate(source_site_managers):
        if not isinstance(original, dict):
            raise ImportValidationError([f"siteManagers[{index}]: muss ein Objekt sein"])
        manager = dict(original)
        identity = str(manager.get("name") or f"record-{index}")
        manager["id"] = manager.get("id") or _stable_id("site-manager", identity)
        site_managers.append(manager)

    return validate_import({
        "format": FORMAT,
        "schemaVersion": 3,
        "exportedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "applicationVersion": f"initial-seed:{INITIAL_SEED_ID}",
        "trades": trades,
        "companies": companies,
        "siteManagers": site_managers,
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
        if previous and not (
            previous[0] != INITIAL_SEED_ID
            and _contains_unchanged_legacy_demo(connection)
        ):
            connection.rollback()
            return {"written": False, "reason": "already-initialized", "seedId": previous[0]}

        replacing_demo = bool(previous)
        if replacing_demo:
            _clear_master_data(connection)

        has_data = any(connection.execute(f"SELECT EXISTS(SELECT 1 FROM {table})").fetchone()[0]
                       for table in ("trades", "companies", "site_managers"))
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        if has_data:
            connection.execute("INSERT INTO application_metadata VALUES (?, ?, ?)",
                               (INITIAL_SEED_KEY, INITIAL_SEED_ID, now))
            connection.commit()
            log.info("Initialimport %s übersprungen: Datenbank enthält bereits Fachdaten", INITIAL_SEED_ID)
            return {"written": False, "reason": "database-not-empty", "seedId": INITIAL_SEED_ID}

        data = _normalize(json.loads((path or seed_file()).read_text(encoding="utf-8")))
        write_validated_data(connection, data)
        if replacing_demo:
            connection.execute(
                "UPDATE application_metadata SET value=?, created_at=? WHERE key=?",
                (INITIAL_SEED_ID, now, INITIAL_SEED_KEY),
            )
        else:
            connection.execute("INSERT INTO application_metadata VALUES (?, ?, ?)",
                               (INITIAL_SEED_KEY, INITIAL_SEED_ID, now))
        connection.commit()
        log.info("Initialimport %s abgeschlossen: %d Gewerke, %d Unternehmen, %d Bauleiter, 0 abgelehnt",
                 INITIAL_SEED_ID, len(data["trades"]), len(data["companies"]), len(data["siteManagers"]))
        return {"written": True, "upgradedDemo": replacing_demo, "seedId": INITIAL_SEED_ID,
                "trades": len(data["trades"]), "companies": len(data["companies"]),
                "siteManagers": len(data["siteManagers"]), "rejected": 0}
    except Exception as error:
        connection.rollback()
        if isinstance(error, ImportValidationError):
            for rejection in error.errors:
                log.error("Initialimport %s: Datensatz abgelehnt: %s", INITIAL_SEED_ID, rejection)
        else:
            log.exception("Initialimport %s abgebrochen; alle Änderungen zurückgerollt", INITIAL_SEED_ID)
        raise
