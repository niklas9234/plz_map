import importlib.util
from pathlib import Path
import sys
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Territory, Trade


SCRIPT = Path(__file__).parents[2] / "unternehmensimport" / "import_companies.py"
SPEC = importlib.util.spec_from_file_location("company_csv_import", SCRIPT)
company_csv_import = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = company_csv_import
SPEC.loader.exec_module(company_csv_import)


HEADER = (
    "name;trade;primary_postal_codes;alternative_postal_code\n"
)


def add_trade(engine, name="Elektro"):
    with Session(engine) as session:
        session.add(Trade(
            id=str(uuid4()), name=name, status="active", color="#123456",
            created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z",
        ))
        session.commit()


def write_csv(tmp_path, body):
    path = tmp_path / "unternehmen.csv"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def test_import_appends_company_and_preserves_existing_data(database_engine, tmp_path):
    add_trade(database_engine)
    first = write_csv(tmp_path, "Firma A;Elektro;08;09\n")
    assert company_csv_import.import_companies(first, database_engine) == 1

    second = write_csv(tmp_path, "Firma B;Elektro;;10\n")
    assert company_csv_import.import_companies(second, database_engine) == 1

    with Session(database_engine) as session:
        companies = list(session.scalars(select(Company).order_by(Company.name)))
        assert [company.name for company in companies] == ["Firma A", "Firma B"]
        assert all(company.status == "active" for company in companies)
        assert all(company.pps_number.startswith("IMPORT-") for company in companies)
        assert companies[0].pps_number != companies[1].pps_number
        assert [(item.postal_code, item.role) for item in companies[0].trades[0].territories] == [
            ("08", "primary"), ("09", "alternative")
        ]


def test_check_only_does_not_write(database_engine, tmp_path):
    add_trade(database_engine)
    path = write_csv(tmp_path, "Firma;Elektro;08;\n")
    assert company_csv_import.import_companies(path, database_engine, check_only=True) == 1
    with Session(database_engine) as session:
        assert list(session.scalars(select(Company))) == []


def test_any_invalid_row_prevents_complete_import(database_engine, tmp_path):
    add_trade(database_engine)
    path = write_csv(
        tmp_path,
        "Gültig;Elektro;08;\n"
        "Ungültig;Unbekannt;09;\n",
    )
    with pytest.raises(company_csv_import.ImportError, match="existiert nicht"):
        company_csv_import.import_companies(path, database_engine)
    with Session(database_engine) as session:
        assert list(session.scalars(select(Company))) == []


def test_existing_primary_conflict_is_rejected(database_engine, tmp_path):
    add_trade(database_engine)
    first = write_csv(tmp_path, "Firma A;Elektro;08;\n")
    company_csv_import.import_companies(first, database_engine)
    second = write_csv(tmp_path, "Firma B;Elektro;08;\n")

    with pytest.raises(company_csv_import.ImportError) as error:
        company_csv_import.import_companies(second, database_engine)
    assert "Vorzugsdienstleister" in str(error.value)
    with Session(database_engine) as session:
        assert session.scalar(select(Company).where(Company.name == "Firma B")) is None
        assert session.scalar(select(Territory).where(Territory.postal_code == "08")) is not None
