"""Versioned, database-independent backup import and export."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

FORMAT = "plz-map-data-export"
SCHEMA_VERSION = 1
STATUS = {"active", "inactive"}
ROLES = {"primary", "alternative"}
POSTAL_CODE = re.compile(r"^\d{2}$")


class ImportValidationError(ValueError):
    """The complete import was rejected before any persistent change."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


def application_version() -> str:
    try:
        return version("plz-map-backend")
    except PackageNotFoundError:
        return "development"


def _timestamp(value: str, path: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        errors.append(f"{path}: muss ein RFC-3339-Zeitpunkt sein")
        return
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError
    except ValueError:
        errors.append(f"{path}: muss einen Zeitzonenbezug enthalten")


def _uuid(value: Any, path: str, errors: list[str]) -> None:
    try:
        if not isinstance(value, str) or str(UUID(value)) != value.lower():
            raise ValueError
    except (ValueError, AttributeError):
        errors.append(f"{path}: muss eine UUID sein")


def export_data(connection: Connection) -> dict[str, Any]:
    """Read one consistent snapshot and retain every domain field verbatim."""
    started_snapshot = not connection.in_transaction()
    if started_snapshot:
        connection.begin()
    trades = [
        {"id": row["id"], "name": row["name"], "status": row["status"],
         "color": row["color"], "createdAt": row["created_at"], "updatedAt": row["updated_at"]}
        for row in connection.execute(text("SELECT * FROM trades ORDER BY id")).mappings()
    ]
    companies = []
    for row in connection.execute(text("SELECT * FROM companies ORDER BY id")).mappings():
        territories = [dict(item) for item in connection.execute(text(
            "SELECT postal_code AS \"postalCode\", role FROM territories "
            "WHERE company_id=:company_id ORDER BY postal_code"
        ), {"company_id": row["id"]}).mappings()]
        information = [dict(item) for item in connection.execute(text(
            "SELECT category, value FROM company_information "
            "WHERE company_id=:company_id ORDER BY position"
        ), {"company_id": row["id"]}).mappings()]
        companies.append({
            "id": row["id"], "name": row["name"], "ppsNumber": row["pps_number"],
            "tradeId": row["trade_id"], "territories": territories,
            "information": information, "status": row["status"],
            "createdAt": row["created_at"], "updatedAt": row["updated_at"],
        })
    result = {"format": FORMAT, "schemaVersion": SCHEMA_VERSION,
              "exportedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
              "applicationVersion": application_version(), "trades": trades, "companies": companies}
    if started_snapshot:
        connection.commit()
    return result


def validate_import(document: Any) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(document, dict):
        raise ImportValidationError(["$: muss ein JSON-Objekt sein"])
    allowed_top = {"format", "schemaVersion", "exportedAt", "applicationVersion", "trades", "companies"}
    unknown = set(document) - allowed_top
    if unknown:
        errors.append(f"$: unbekannte Felder: {', '.join(sorted(unknown))}")
    if document.get("format") != FORMAT:
        errors.append(f"format: erwartet '{FORMAT}'")
    if document.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion: unterstützt wird nur {SCHEMA_VERSION}")
    # Reject an incompatible envelope before interpreting payload records.
    if errors:
        raise ImportValidationError(errors)
    _timestamp(document.get("exportedAt"), "exportedAt", errors)
    if not isinstance(document.get("applicationVersion"), str) or not document.get("applicationVersion"):
        errors.append("applicationVersion: muss eine nichtleere Zeichenkette sein")
    trades = document.get("trades")
    companies = document.get("companies")
    if not isinstance(trades, list): errors.append("trades: muss eine Liste sein"); trades = []
    if not isinstance(companies, list): errors.append("companies: muss eine Liste sein"); companies = []

    trade_ids: set[str] = set(); trade_names: set[str] = set()
    trade_fields = {"id", "name", "status", "color", "createdAt", "updatedAt"}
    for index, trade in enumerate(trades):
        path = f"trades[{index}]"
        if not isinstance(trade, dict): errors.append(f"{path}: muss ein Objekt sein"); continue
        if set(trade) != trade_fields: errors.append(f"{path}: Felder entsprechen nicht dem Schema")
        _uuid(trade.get("id"), f"{path}.id", errors)
        if trade.get("id") in trade_ids: errors.append(f"{path}.id: doppelte UUID")
        trade_ids.add(trade.get("id"))
        name = trade.get("name")
        if not isinstance(name, str) or not name.strip() or name != name.strip(): errors.append(f"{path}.name: ungültiger Name")
        elif name.casefold() in trade_names: errors.append(f"{path}.name: Gewerkname ist nicht eindeutig")
        else: trade_names.add(name.casefold())
        if trade.get("status") not in STATUS: errors.append(f"{path}.status: ungültiger Status")
        if trade.get("color") is not None and not isinstance(trade.get("color"), str): errors.append(f"{path}.color: ungültig")
        _timestamp(trade.get("createdAt"), f"{path}.createdAt", errors); _timestamp(trade.get("updatedAt"), f"{path}.updatedAt", errors)

    company_ids: set[str] = set(); pps_numbers: set[str] = set(); primaries: set[tuple[str, str]] = set()
    company_fields = {"id", "name", "ppsNumber", "tradeId", "territories", "information", "status", "createdAt", "updatedAt"}
    for index, company in enumerate(companies):
        path = f"companies[{index}]"
        if not isinstance(company, dict): errors.append(f"{path}: muss ein Objekt sein"); continue
        if set(company) != company_fields: errors.append(f"{path}: Felder entsprechen nicht dem Schema")
        _uuid(company.get("id"), f"{path}.id", errors); _uuid(company.get("tradeId"), f"{path}.tradeId", errors)
        if company.get("id") in company_ids: errors.append(f"{path}.id: doppelte UUID")
        company_ids.add(company.get("id"))
        if company.get("tradeId") not in trade_ids: errors.append(f"{path}.tradeId: unbekanntes Gewerk")
        for field in ("name", "ppsNumber"):
            value = company.get(field)
            if not isinstance(value, str) or not value.strip() or value != value.strip(): errors.append(f"{path}.{field}: ungültig")
        pps = company.get("ppsNumber")
        if isinstance(pps, str) and pps in pps_numbers: errors.append(f"{path}.ppsNumber: nicht eindeutig")
        elif isinstance(pps, str): pps_numbers.add(pps)
        if company.get("status") not in STATUS: errors.append(f"{path}.status: ungültiger Status")
        territories = company.get("territories")
        if not isinstance(territories, list) or not territories: errors.append(f"{path}.territories: mindestens eine Zuordnung erforderlich"); territories = []
        codes: set[str] = set()
        for pos, territory in enumerate(territories):
            item_path = f"{path}.territories[{pos}]"
            if not isinstance(territory, dict) or set(territory) != {"postalCode", "role"}: errors.append(f"{item_path}: ungültige Felder"); continue
            code, role = territory.get("postalCode"), territory.get("role")
            if not isinstance(code, str) or not (POSTAL_CODE.fullmatch(code) or code == "LUX"): errors.append(f"{item_path}.postalCode: zweistelliger String oder LUX erwartet")
            if code in codes: errors.append(f"{item_path}.postalCode: doppelte Zuordnung")
            codes.add(code)
            if role not in ROLES: errors.append(f"{item_path}.role: ungültige Gebietsrolle")
            key = (company.get("tradeId"), code)
            if role == "primary" and key in primaries: errors.append(f"{item_path}: Vorzugsdienstleister für Gewerk und Gebiet ist nicht eindeutig")
            elif role == "primary": primaries.add(key)
        information = company.get("information")
        if not isinstance(information, list): errors.append(f"{path}.information: muss eine Liste sein"); information = []
        for pos, item in enumerate(information):
            if (not isinstance(item, dict) or set(item) != {"category", "value"}
                    or item.get("category") not in {"address", "phone", "contact", "other"}
                    or not isinstance(item.get("value"), str) or not item["value"].strip()
                    or item["value"] != item["value"].strip()):
                errors.append(f"{path}.information[{pos}]: ungültige Kategorie oder ungültiger Wert")
        _timestamp(company.get("createdAt"), f"{path}.createdAt", errors); _timestamp(company.get("updatedAt"), f"{path}.updatedAt", errors)
    if errors: raise ImportValidationError(errors)
    return document


def import_data(connection: Connection, document: Any, mode: str = "empty") -> dict[str, int | bool]:
    if mode not in {"empty", "validate"}:
        raise ImportValidationError(["mode: erlaubt sind 'empty' und 'validate'"])
    data = validate_import(document)
    counts = {"trades": len(data["trades"]), "companies": len(data["companies"])}
    if mode == "validate": return {**counts, "written": False}
    try:
        if connection.in_transaction():
            connection.commit()
        transaction = connection.begin()
        if any(connection.execute(text(f"SELECT EXISTS(SELECT 1 FROM {table})")).scalar() for table in ("trades", "companies")):
            raise ImportValidationError(["Die Zieldatenbank ist nicht leer."])
        for trade in data["trades"]:
            connection.execute(text("INSERT INTO trades (id, name, status, color, created_at, updated_at) VALUES (:id, :name, :status, :color, :created_at, :updated_at)"), {
                "id": trade["id"], "name": trade["name"],
                "status": trade["status"], "color": trade["color"], "created_at": trade["createdAt"], "updated_at": trade["updatedAt"],
            })
        for company in data["companies"]:
            connection.execute(text("INSERT INTO companies (id, name, pps_number, trade_id, status, created_at, updated_at) VALUES (:id, :name, :pps_number, :trade_id, :status, :created_at, :updated_at)"), {
                "id": company["id"], "name": company["name"], "pps_number": company["ppsNumber"], "trade_id": company["tradeId"],
                "status": company["status"], "created_at": company["createdAt"], "updated_at": company["updatedAt"],
            })
            connection.execute(text("INSERT INTO territories (company_id, postal_code, trade_id, role) VALUES (:company_id, :postal_code, :trade_id, :role)"), [
                {"company_id": company["id"], "postal_code": item["postalCode"], "trade_id": company["tradeId"], "role": item["role"]}
                for item in company["territories"]
            ])
            if company["information"]:
                connection.execute(text("INSERT INTO company_information (company_id, position, category, value) VALUES (:company_id, :position, :category, :value)"), [
                    {"company_id": company["id"], "position": pos, "category": item["category"], "value": item["value"]}
                    for pos, item in enumerate(company["information"])
                ])
        transaction.commit()
    except Exception:
        connection.rollback()
        raise
    return {**counts, "written": True}


def dumps(connection: Connection) -> bytes:
    return json.dumps(export_data(connection), ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
