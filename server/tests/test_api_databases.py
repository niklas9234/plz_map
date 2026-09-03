import io
import json

from app.application import create_application
from test_transfer import document


def request(app, path, method="GET", payload=None):
    body = json.dumps(payload).encode() if payload is not None else b""
    response = {}
    environ = {"PATH_INFO": path.split("?", 1)[0], "QUERY_STRING": path.partition("?")[2],
               "REQUEST_METHOD": method, "CONTENT_LENGTH": str(len(body)), "wsgi.input": io.BytesIO(body)}
    result = b"".join(app(environ, lambda status, headers: response.update(status=status, headers=dict(headers))))
    return response, result


def test_import_and_export_api_on_every_database(database_engine):
    app = create_application(database_engine)
    response, body = request(app, "/api/admin/import?mode=empty", "POST", document())
    assert response["status"] == "200 OK"
    assert json.loads(body)["written"] is True
    response, body = request(app, "/api/admin/export")
    assert response["status"] == "200 OK"
    assert json.loads(body)["companies"][0]["ppsNumber"] == "PPS-01"
