import pytest

from app.application import create_application
from test_api_databases import request


TRADE = {"name": "Elektro", "color": "#72b788", "status": "active"}


def call(app, path, method="GET", payload=None, expected="200 OK"):
    response, body = request(app, path, method, payload)
    assert response["status"] == expected
    import json
    return json.loads(body) if body else None


def test_company_and_trade_crud_have_identical_contract_on_every_database(database_engine):
    app = create_application(database_engine)
    trade = call(app, "/api/trades", "POST", TRADE, "201 Created")
    company_payload = {
        "name": "Beispiel GmbH", "ppsNumber": "PPS-01", "tradeId": trade["id"],
        "territories": [{"postalCode": "08", "role": "primary"}],
        "information": [{"category": "phone", "value": "+49 30 1"}], "status": "active",
    }
    company = call(app, "/api/companies", "POST", company_payload, "201 Created")
    assert call(app, f"/api/companies/{company['id']}") == company
    assert call(app, "/api/companies?query=spiel&postalCode=08") == [company]
    changed = call(app, f"/api/companies/{company['id']}", "PATCH", {"name": "Neu GmbH"})
    assert changed["name"] == "Neu GmbH"
    assert changed["createdAt"] == company["createdAt"]
    assert call(app, f"/api/companies/{company['id']}/deactivate", "POST")["status"] == "inactive"
    call(app, f"/api/companies/{company['id']}", "DELETE", expected="204 No Content")
    call(app, f"/api/trades/{trade['id']}", "DELETE", expected="204 No Content")


def test_validation_and_conflicts_are_database_independent(database_engine):
    app = create_application(database_engine)
    trade = call(app, "/api/trades", "POST", TRADE, "201 Created")
    invalid = {"name": "Firma", "ppsNumber": "PPS", "tradeId": trade["id"], "territories": [], "information": []}
    response, _ = request(app, "/api/companies", "POST", invalid)
    assert response["status"] == "422 Unprocessable Entity"
    response, _ = request(app, "/api/trades", "POST", TRADE)
    assert response["status"] == "409 Conflict"
    response, _ = request(app, "/api/trades", "POST", {**TRADE, "serverOnly": True})
    assert response["status"] == "400 Bad Request"


def test_site_manager_crud_and_filters_work_on_every_database(database_engine):
    app = create_application(database_engine)
    payload = {
        "name": "Anna Beispiel",
        "territories": [{"postalCode": "08"}, {"postalCode": "LUX"}],
        "status": "active",
    }
    site_manager = call(app, "/api/site-managers", "POST", payload, "201 Created")
    assert site_manager["territories"] == payload["territories"]
    assert call(app, f"/api/site-managers/{site_manager['id']}") == site_manager
    assert call(app, "/api/site-managers?status=active&query=beispiel&postalCode=08") == [site_manager]
    assert call(app, "/api/site-managers?query=PPS") == []

    changed = call(app, f"/api/site-managers/{site_manager['id']}", "PATCH", {
        "name": "Anna Neu", "territories": ["10"],
    })
    assert changed["territories"] == [{"postalCode": "10"}]
    assert changed["createdAt"] == site_manager["createdAt"]
    assert call(app, f"/api/site-managers/{site_manager['id']}/deactivate", "POST")["status"] == "inactive"
    assert call(app, "/api/site-managers?status=active") == []
    call(app, f"/api/site-managers/{site_manager['id']}", "DELETE", expected="204 No Content")


@pytest.mark.parametrize("payload", [
    {"name": "", "territories": [{"postalCode": "08"}]},
    {"name": "Anna", "territories": []},
    {"name": "Anna", "territories": [{"postalCode": "8"}]},
    {"name": "Anna", "territories": [{"postalCode": "08"}, {"postalCode": "08"}]},
    {"name": "Anna", "territories": [{"postalCode": "08", "role": "primary"}]},
])
def test_site_manager_validation_rejects_invalid_payload(database_engine, payload):
    app = create_application(database_engine)
    response, _ = request(app, "/api/site-managers", "POST", payload)
    assert response["status"] == "422 Unprocessable Entity"
