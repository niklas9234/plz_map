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


def test_site_manager_crud_filters_and_shared_territories(database_engine):
    app = create_application(database_engine)
    first = call(app, "/api/site-managers", "POST", {"name": "Alex Bau", "territories": ["08", "LUX"], "status": "active"}, "201 Created")
    second = call(app, "/api/site-managers", "POST", {"name": "Sam Leitung", "territories": ["08"], "status": "inactive"}, "201 Created")
    assert call(app, "/api/site-managers?postalCode=08") == [first, second]
    assert call(app, "/api/site-managers?query=alex&status=active") == [first]
    assert call(app, "/api/site-managers?query=LUX") == []
    changed = call(app, f"/api/site-managers/{first['id']}", "PATCH", {"territories": ["82"]})
    assert changed["territories"] == ["82"]
    assert call(app, f"/api/site-managers/{first['id']}/deactivate", "POST")["status"] == "inactive"
    call(app, f"/api/site-managers/{first['id']}", "DELETE", expected="204 No Content")


@pytest.mark.parametrize("territories", [[], ["8"], ["082"], [8], ["08", "08"]])
def test_site_manager_rejects_invalid_territories(database_engine, territories):
    app = create_application(database_engine)
    response, _ = request(app, "/api/site-managers", "POST", {"name": "Alex", "territories": territories})
    assert response["status"] == "422 Unprocessable Entity"
