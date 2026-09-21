#!/usr/bin/env python3
"""Atomically append companies from a semicolon-separated CSV file."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from app.database import create_database_engine  # noqa: E402
from app.models import Company, Territory, Trade  # noqa: E402


COLUMNS = (
    "name", "trade", "primary_postal_codes", "alternative_postal_code",
)
POSTAL_CODE = re.compile(r"^\d{2}$")


class ImportError(ValueError):
    """A CSV or existing-data conflict that prevents the complete import."""


@dataclass(frozen=True)
class CompanyRow:
    line: int
    name: str
    trade_id: str
    trade_name: str
    territories: tuple[tuple[str, str], ...]


def _split(value: str, delimiter: str) -> list[str]:
    return [item.strip() for item in value.split(delimiter) if item.strip()]


def _read_csv(path: Path, trades: dict[str, Trade]) -> tuple[list[CompanyRow], list[str]]:
    errors: list[str] = []
    rows: list[CompanyRow] = []
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as error:
        raise ImportError(f"CSV-Datei kann nicht gelesen werden: {error}") from error

    with handle:
        reader = csv.DictReader(handle, delimiter=";")
        if reader.fieldnames != list(COLUMNS):
            actual = ", ".join(reader.fieldnames or []) or "keine"
            raise ImportError(
                "CSV-Kopfzeile ist ungültig. Erwartet: " + ", ".join(COLUMNS)
                + f". Gefunden: {actual}."
            )
        for line, raw in enumerate(reader, start=2):
            if not any((value or "").strip() for value in raw.values()):
                continue
            values = {key: (value or "").strip() for key, value in raw.items()}
            row_errors: list[str] = []
            name = values["name"]
            if not name or len(name) > 255:
                row_errors.append("name fehlt oder ist länger als 255 Zeichen")
            trade = trades.get(values["trade"].casefold())
            if not trade:
                row_errors.append(f"Gewerk '{values['trade']}' existiert nicht")

            primary = _split(values["primary_postal_codes"], ",")
            alternative = _split(values["alternative_postal_code"], ",")
            territories = [(code, "primary") for code in primary]
            territories += [(code, "alternative") for code in alternative]
            if not territories:
                row_errors.append("mindestens ein PLZ-Gebiet ist erforderlich")
            seen_codes: set[str] = set()
            for code, _role in territories:
                if not (POSTAL_CODE.fullmatch(code) or code == "LUX"):
                    row_errors.append(f"ungültiges PLZ-Gebiet '{code}'")
                if code in seen_codes:
                    row_errors.append(f"PLZ-Gebiet '{code}' ist doppelt angegeben")
                seen_codes.add(code)

            if row_errors:
                errors.extend(f"Zeile {line}: {message}" for message in row_errors)
                continue
            rows.append(CompanyRow(
                line, name, trade.id, trade.name, tuple(territories),
            ))
    if not rows and not errors:
        errors.append("Die CSV-Datei enthält keine Unternehmen.")
    return rows, errors


def _validate_conflicts(session: Session, rows: list[CompanyRow]) -> list[str]:
    errors: list[str] = []
    existing_primaries = set(session.execute(
        select(Territory.trade_id, Territory.postal_code)
        .where(Territory.role == "primary")
    ).all())
    batch_primaries: set[tuple[str, str]] = set()

    for row in rows:
        for code, role in row.territories:
            if role != "primary":
                continue
            key = (row.trade_id, code)
            if key in existing_primaries:
                errors.append(
                    f"Zeile {row.line}: Für Gewerk '{row.trade_name}' und Gebiet '{code}' "
                    "gibt es bereits einen Vorzugsdienstleister"
                )
            elif key in batch_primaries:
                errors.append(
                    f"Zeile {row.line}: Vorzugsgebiet '{code}' für Gewerk "
                    f"'{row.trade_name}' ist in der CSV doppelt"
                )
            batch_primaries.add(key)
    return errors


def import_companies(
    path: Path, database_url: str | Engine | None = None, check_only: bool = False
) -> int:
    owns_engine = not isinstance(database_url, Engine)
    engine = create_database_engine(database_url) if owns_engine else database_url
    try:
        with Session(engine) as session:
            trades = {
                trade.name.casefold(): trade
                for trade in session.scalars(select(Trade).order_by(func.lower(Trade.name)))
            }
            rows, errors = _read_csv(path, trades)
            errors.extend(_validate_conflicts(session, rows))
            if errors:
                raise ImportError("Import abgelehnt:\n- " + "\n- ".join(errors))
            if check_only:
                return len(rows)

            now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            for row in rows:
                company_id = str(uuid4())
                company = Company(
                    id=company_id, name=row.name,
                    pps_number=f"IMPORT-{company_id}",
                    trade_id=row.trade_id, status="active",
                    created_at=now, updated_at=now,
                )
                company.territories = [
                    Territory(postal_code=code, role=role, trade_id=row.trade_id)
                    for code, role in row.territories
                ]
                session.add(company)
            session.commit()
            return len(rows)
    except IntegrityError as error:
        raise ImportError(
            "Import wegen eines Datenbankkonflikts vollständig zurückgerollt. "
            "Die Daten wurden möglicherweise parallel geändert."
        ) from error
    except SQLAlchemyError as error:
        raise ImportError(f"Datenbankfehler; Import vollständig zurückgerollt: {error}") from error
    finally:
        if owns_engine:
            engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unternehmen aus einer CSV-Datei ergänzen.")
    parser.add_argument(
        "csv_file", nargs="?", type=Path,
        default=Path(__file__).with_name("unternehmen.csv"),
        help="CSV-Datei (Standard: unternehmensimport/unternehmen.csv)",
    )
    parser.add_argument("--check", action="store_true", help="Nur prüfen, nichts schreiben")
    parser.add_argument(
        "--database-url", default=os.environ.get("DATABASE_URL"),
        help="SQLAlchemy-Datenbank-URL (sonst DATABASE_URL bzw. lokale App-Datenbank)",
    )
    args = parser.parse_args(argv)
    try:
        count = import_companies(args.csv_file, args.database_url, args.check)
    except ImportError as error:
        print(error, file=sys.stderr)
        return 1
    action = "Prüfung erfolgreich" if args.check else "Import erfolgreich"
    print(f"{action}: {count} Unternehmen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
