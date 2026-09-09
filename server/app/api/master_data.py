"""CRUD endpoints for mutable company and trade master data."""

from __future__ import annotations

from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any
from urllib.parse import parse_qs
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from ..models import Company, CompanyInformation, SiteManager, SiteManagerTerritory, Territory, Trade

STATUSES = {"active", "inactive"}
ROLES = {"primary", "alternative"}
CATEGORIES = {"address", "phone", "contact", "other"}
TRADE_WRITE_FIELDS = {"name", "color", "status"}
COMPANY_WRITE_FIELDS = {"name", "ppsNumber", "tradeId", "territories", "information", "status"}
SITE_MANAGER_WRITE_FIELDS = {"name", "territories", "status"}


class ApiError(ValueError):
    def __init__(self, status: HTTPStatus, code: str, message: str, fields: list[str] | None = None):
        self.status, self.code, self.message, self.fields = status, code, message, fields
        super().__init__(message)

    def payload(self) -> dict[str, Any]:
        result: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.fields:
            result["fields"] = self.fields
        return result


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _trade_json(trade: Trade) -> dict[str, Any]:
    return {"id": trade.id, "name": trade.name, "color": trade.color, "status": trade.status,
            "createdAt": trade.created_at, "updatedAt": trade.updated_at}


def _company_json(company: Company) -> dict[str, Any]:
    return {
        "id": company.id, "name": company.name, "ppsNumber": company.pps_number,
        "tradeId": company.trade_id,
        "territories": [{"postalCode": item.postal_code, "role": item.role}
                        for item in sorted(company.territories, key=lambda item: item.postal_code)],
        "information": [{"category": item.category, "value": item.value}
                        for item in sorted(company.information, key=lambda item: item.position)],
        "status": company.status, "createdAt": company.created_at, "updatedAt": company.updated_at,
    }


def _site_manager_json(site_manager: SiteManager) -> dict[str, Any]:
    return {
        "id": site_manager.id,
        "name": site_manager.name,
        "territories": [{"postalCode": item.postal_code} for item in sorted(
            site_manager.territories, key=lambda item: item.postal_code
        )],
        "status": site_manager.status,
        "createdAt": site_manager.created_at,
        "updatedAt": site_manager.updated_at,
    }


def _body(payload: Any, allowed: set[str], partial: bool = False) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApiError(HTTPStatus.BAD_REQUEST, "invalid_json", "Ein JSON-Objekt wird erwartet.")
    unknown = set(payload) - allowed
    if unknown:
        raise ApiError(HTTPStatus.BAD_REQUEST, "unknown_fields", "Unbekannte Felder.", sorted(unknown))
    if not partial and not payload:
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Pflichtfelder fehlen.")
    return payload


def _required_text(payload: dict[str, Any], key: str, current: str | None = None) -> str:
    value = payload.get(key, current)
    if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > 255:
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Validierung fehlgeschlagen.", [key])
    return value


def _status(payload: dict[str, Any], current: str = "active") -> str:
    value = payload.get("status", current)
    if value not in STATUSES:
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Validierung fehlgeschlagen.", ["status"])
    return value


def _uuid(value: Any, field: str) -> str:
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Validierung fehlgeschlagen.", [field])


def _validate_color(value: Any) -> None:
    if value is not None and (not isinstance(value, str) or len(value) != 7 or value[0] != "#"
                              or any(character not in "0123456789abcdefABCDEF" for character in value[1:])):
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Validierung fehlgeschlagen.", ["color"])


def _company_parts(payload: dict[str, Any], company: Company | None = None):
    name = _required_text(payload, "name", company.name if company else None)
    pps = _required_text(payload, "ppsNumber", company.pps_number if company else None)
    trade_id = _uuid(payload.get("tradeId", company.trade_id if company else None), "tradeId")
    status = _status(payload, company.status if company else "active")
    territories = payload.get("territories")
    information = payload.get("information")
    if territories is None and company:
        territories = [{"postalCode": item.postal_code, "role": item.role} for item in company.territories]
    if information is None and company:
        information = [{"category": item.category, "value": item.value} for item in company.information]
    errors: list[str] = []
    if not isinstance(territories, list) or not territories:
        errors.append("territories")
        territories = []
    seen: set[str] = set()
    for index, item in enumerate(territories):
        code = item.get("postalCode") if isinstance(item, dict) else None
        role = item.get("role") if isinstance(item, dict) else None
        if not isinstance(item, dict) or set(item) != {"postalCode", "role"} or not isinstance(code, str) or not (len(code) == 2 and code.isdigit() or code == "LUX") or role not in ROLES or code in seen:
            errors.append(f"territories[{index}]")
        seen.add(code)
    if not isinstance(information, list):
        errors.append("information")
        information = []
    for index, item in enumerate(information):
        if (not isinstance(item, dict) or set(item) != {"category", "value"}
                or item.get("category") not in CATEGORIES or not isinstance(item.get("value"), str)
                or not item["value"].strip() or item["value"] != item["value"].strip()):
            errors.append(f"information[{index}]")
    if errors:
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Validierung fehlgeschlagen.", errors)
    return name, pps, trade_id, status, territories, information


def _site_manager_parts(payload: dict[str, Any], site_manager: SiteManager | None = None):
    name = _required_text(payload, "name", site_manager.name if site_manager else None)
    status = _status(payload, site_manager.status if site_manager else "active")
    territories = payload.get("territories")
    if territories is None and site_manager:
        territories = [{"postalCode": item.postal_code} for item in site_manager.territories]
    errors: list[str] = []
    if not isinstance(territories, list) or not territories:
        errors.append("territories")
        territories = []
    codes: list[str] = []
    seen: set[str] = set()
    for index, item in enumerate(territories):
        # Accept plain strings as well, so older UI builds remain compatible.
        code = item if isinstance(item, str) else item.get("postalCode") if isinstance(item, dict) else None
        valid_fields = isinstance(item, str) or isinstance(item, dict) and set(item) == {"postalCode"}
        if not valid_fields or not isinstance(code, str) or not (len(code) == 2 and code.isdigit() or code == "LUX") or code in seen:
            errors.append(f"territories[{index}]")
        else:
            codes.append(code)
        if isinstance(code, str):
            seen.add(code)
    if errors:
        raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Validierung fehlgeschlagen.", errors)
    return name, status, codes


def _commit(session: Session, conflict_message: str) -> None:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise ApiError(HTTPStatus.CONFLICT, "conflict", conflict_message)


def _ensure_pps_available(session: Session, pps_number: str, current_id: str | None = None) -> None:
    statement = select(Company.id).where(func.lower(Company.pps_number) == pps_number.casefold())
    if current_id:
        statement = statement.where(Company.id != current_id)
    if session.scalar(statement):
        raise ApiError(HTTPStatus.CONFLICT, "conflict", "Die PPS-Nummer wird bereits verwendet.")


def handle_master_data(engine, path: str, method: str, query_string: str, payload: Any):
    """Return ``(status, payload)`` when a master-data route matches, else None."""
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2 or parts[0] != "api" or parts[1] not in {"companies", "trades", "site-managers"}:
        return None
    resource = parts[1]
    with Session(engine) as session:
        if resource == "trades":
            return _trades(session, parts[2:], method, query_string, payload)
        if resource == "site-managers":
            return _site_managers(session, parts[2:], method, query_string, payload)
        return _companies(session, parts[2:], method, query_string, payload)


def _site_managers(session: Session, rest: list[str], method: str, query_string: str, payload: Any):
    eager = (selectinload(SiteManager.territories),)
    if not rest and method == "GET":
        params = parse_qs(query_string)
        statement = select(SiteManager).options(*eager).order_by(SiteManager.name)
        status = params.get("status", [None])[0]
        if status is not None:
            if status not in STATUSES:
                raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Ungültiger Status.", ["status"])
            statement = statement.where(SiteManager.status == status)
        query = params.get("query", [None])[0]
        if query:
            statement = statement.where(func.lower(SiteManager.name).contains(query.casefold()))
        postal_code = params.get("postalCode", [None])[0]
        if postal_code:
            statement = statement.where(SiteManager.territories.any(SiteManagerTerritory.postal_code == postal_code))
        return HTTPStatus.OK, [_site_manager_json(item) for item in session.scalars(statement)]
    if not rest and method == "POST":
        data = _body(payload, SITE_MANAGER_WRITE_FIELDS)
        name, status, territories = _site_manager_parts(data)
        timestamp = _now()
        site_manager = SiteManager(id=str(uuid4()), name=name, status=status,
                                   created_at=timestamp, updated_at=timestamp)
        site_manager.territories = [SiteManagerTerritory(postal_code=code) for code in territories]
        session.add(site_manager)
        _commit(session, "Der Bauleiter konnte nicht gespeichert werden.")
        return HTTPStatus.CREATED, _site_manager_json(site_manager)
    if not rest:
        return None
    site_manager = session.scalar(select(SiteManager).options(*eager).where(SiteManager.id == rest[0]))
    if not site_manager:
        raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "Der Bauleiter wurde nicht gefunden.")
    if len(rest) == 1 and method == "GET":
        return HTTPStatus.OK, _site_manager_json(site_manager)
    if len(rest) == 1 and method == "PATCH":
        data = _body(payload, SITE_MANAGER_WRITE_FIELDS, True)
        name, status, territories = _site_manager_parts(data, site_manager)
        site_manager.name, site_manager.status, site_manager.updated_at = name, status, _now()
        site_manager.territories = [SiteManagerTerritory(postal_code=code) for code in territories]
        _commit(session, "Der Bauleiter konnte nicht gespeichert werden.")
        return HTTPStatus.OK, _site_manager_json(site_manager)
    if len(rest) == 1 and method == "DELETE":
        session.delete(site_manager)
        session.commit()
        return HTTPStatus.NO_CONTENT, None
    if len(rest) == 2 and method == "POST" and rest[1] in {"activate", "deactivate"}:
        site_manager.status = "active" if rest[1] == "activate" else "inactive"
        site_manager.updated_at = _now()
        session.commit()
        return HTTPStatus.OK, _site_manager_json(site_manager)
    return None


def _trades(session: Session, rest: list[str], method: str, query_string: str, payload: Any):
    if not rest and method == "GET":
        status = parse_qs(query_string).get("status", [None])[0]
        if status is not None and status not in STATUSES:
            raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Ungültiger Status.", ["status"])
        statement = select(Trade).order_by(Trade.name)
        if status: statement = statement.where(Trade.status == status)
        return HTTPStatus.OK, [_trade_json(item) for item in session.scalars(statement)]
    if not rest and method == "POST":
        data = _body(payload, TRADE_WRITE_FIELDS)
        _validate_color(data.get("color"))
        timestamp = _now()
        trade = Trade(id=str(uuid4()), name=_required_text(data, "name"), color=data.get("color"),
                      status=_status(data), created_at=timestamp, updated_at=timestamp)
        session.add(trade); _commit(session, "Gewerkname oder Farbe wird bereits verwendet.")
        return HTTPStatus.CREATED, _trade_json(trade)
    if not rest:
        return None
    trade = session.get(Trade, rest[0])
    if not trade: raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "Das Gewerk wurde nicht gefunden.")
    if len(rest) == 1 and method == "GET": return HTTPStatus.OK, _trade_json(trade)
    if len(rest) == 1 and method == "PATCH":
        data = _body(payload, TRADE_WRITE_FIELDS, True)
        trade.name = _required_text(data, "name", trade.name)
        if "color" in data: _validate_color(data["color"]); trade.color = data["color"]
        trade.status = _status(data, trade.status); trade.updated_at = _now()
        _commit(session, "Gewerkname oder Farbe wird bereits verwendet.")
        return HTTPStatus.OK, _trade_json(trade)
    if len(rest) == 1 and method == "DELETE":
        if session.scalar(select(func.count()).select_from(Company).where(Company.trade_id == trade.id)):
            raise ApiError(HTTPStatus.CONFLICT, "trade_in_use", "Ein verwendetes Gewerk kann nicht gelöscht werden.")
        session.delete(trade); session.commit(); return HTTPStatus.NO_CONTENT, None
    if len(rest) == 2 and method == "POST" and rest[1] in {"activate", "deactivate"}:
        trade.status = "active" if rest[1] == "activate" else "inactive"; trade.updated_at = _now(); session.commit()
        return HTTPStatus.OK, _trade_json(trade)
    return None


def _companies(session: Session, rest: list[str], method: str, query_string: str, payload: Any):
    eager = (selectinload(Company.territories), selectinload(Company.information))
    if not rest and method == "GET":
        params = parse_qs(query_string)
        statement = select(Company).options(*eager).order_by(Company.name)
        status = params.get("status", [None])[0]
        if status is not None:
            if status not in STATUSES: raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Ungültiger Status.", ["status"])
            statement = statement.where(Company.status == status)
        query = params.get("query", [None])[0]
        if query: statement = statement.where(func.lower(Company.name).contains(query.casefold()) | func.lower(Company.pps_number).contains(query.casefold()))
        trade_id = params.get("tradeId", [None])[0]
        if trade_id: statement = statement.where(Company.trade_id == trade_id)
        postal_code = params.get("postalCode", [None])[0]
        if postal_code: statement = statement.where(Company.territories.any(Territory.postal_code == postal_code))
        return HTTPStatus.OK, [_company_json(item) for item in session.scalars(statement)]
    if not rest and method == "POST":
        data = _body(payload, COMPANY_WRITE_FIELDS); values = _company_parts(data)
        if not session.get(Trade, values[2]): raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Das Gewerk existiert nicht.", ["tradeId"])
        _ensure_pps_available(session, values[1])
        timestamp = _now(); company = Company(id=str(uuid4()), name=values[0], pps_number=values[1], trade_id=values[2], status=values[3], created_at=timestamp, updated_at=timestamp)
        company.territories = [Territory(postal_code=x["postalCode"], role=x["role"], trade_id=values[2]) for x in values[4]]
        company.information = [CompanyInformation(position=i, **x) for i, x in enumerate(values[5])]
        session.add(company); _commit(session, "PPS-Nummer oder Vorzugsgebiet wird bereits verwendet.")
        return HTTPStatus.CREATED, _company_json(company)
    if not rest: return None
    company = session.scalar(select(Company).options(*eager).where(Company.id == rest[0]))
    if not company: raise ApiError(HTTPStatus.NOT_FOUND, "not_found", "Das Unternehmen wurde nicht gefunden.")
    if len(rest) == 1 and method == "GET": return HTTPStatus.OK, _company_json(company)
    if len(rest) == 1 and method == "PATCH":
        data = _body(payload, COMPANY_WRITE_FIELDS, True); values = _company_parts(data, company)
        if not session.get(Trade, values[2]): raise ApiError(HTTPStatus.UNPROCESSABLE_ENTITY, "validation_error", "Das Gewerk existiert nicht.", ["tradeId"])
        _ensure_pps_available(session, values[1], company.id)
        company.name, company.pps_number, company.trade_id, company.status = values[:4]; company.updated_at = _now()
        company.territories = [Territory(postal_code=x["postalCode"], role=x["role"], trade_id=values[2]) for x in values[4]]
        company.information = [CompanyInformation(position=i, **x) for i, x in enumerate(values[5])]
        _commit(session, "PPS-Nummer oder Vorzugsgebiet wird bereits verwendet.")
        return HTTPStatus.OK, _company_json(company)
    if len(rest) == 1 and method == "DELETE": session.delete(company); session.commit(); return HTTPStatus.NO_CONTENT, None
    if len(rest) == 2 and method == "POST" and rest[1] in {"activate", "deactivate"}:
        company.status = "active" if rest[1] == "activate" else "inactive"; company.updated_at = _now(); session.commit()
        return HTTPStatus.OK, _company_json(company)
    return None
