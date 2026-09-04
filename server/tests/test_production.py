import io
import json
from pathlib import Path

from app import production
from app.production import DesktopWindowApi, static_application


def request(app, path, method="GET", range_header=None, payload=None):
    response = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = dict(headers)

    body = json.dumps(payload).encode("utf-8") if payload is not None else b""
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    if range_header is not None:
        environ["HTTP_RANGE"] = range_header
    body = b"".join(app(environ, start_response))
    return response, body


def test_static_frontend_root_and_head(tmp_path):
    (tmp_path / "index.html").write_text("Hallo", encoding="utf-8")
    app = static_application(tmp_path, "secret", lambda: None)
    response, body = request(app, "/")
    assert response["status"] == "200 OK"
    assert body == b"Hallo"
    assert response["headers"]["Accept-Ranges"] == "bytes"
    assert response["headers"]["Content-Length"] == "5"
    response, body = request(app, "/", "HEAD")
    assert response["status"] == "200 OK"
    assert body == b""
    assert response["headers"]["Accept-Ranges"] == "bytes"
    assert response["headers"]["Content-Length"] == "5"


def test_static_frontend_byte_ranges(tmp_path):
    content = bytes(range(256)) * 4
    (tmp_path / "map.pmtiles").write_bytes(content)
    app = static_application(tmp_path, "secret", lambda: None)

    cases = [
        ("bytes=0-126", 0, 126),
        ("bytes=300-399", 300, 399),
        ("bytes=100-", 100, len(content) - 1),
        ("bytes=-75", len(content) - 75, len(content) - 1),
    ]
    for range_header, start, end in cases:
        response, body = request(app, "/map.pmtiles", range_header=range_header)
        assert response["status"] == "206 Partial Content"
        assert response["headers"]["Accept-Ranges"] == "bytes"
        assert response["headers"]["Content-Range"] == (
            f"bytes {start}-{end}/{len(content)}"
        )
        assert response["headers"]["Content-Length"] == str(end - start + 1)
        assert body == content[start:end + 1]


def test_static_frontend_range_head_has_no_body(tmp_path):
    content = bytes(range(200))
    (tmp_path / "map.pmtiles").write_bytes(content)
    app = static_application(tmp_path, "secret", lambda: None)

    response, body = request(app, "/map.pmtiles", "HEAD", "bytes=0-126")

    assert response["status"] == "206 Partial Content"
    assert response["headers"]["Content-Length"] == "127"
    assert response["headers"]["Content-Range"] == "bytes 0-126/200"
    assert body == b""


def test_static_frontend_rejects_invalid_and_unsatisfiable_ranges(tmp_path):
    content = bytes(range(200))
    (tmp_path / "map.pmtiles").write_bytes(content)
    app = static_application(tmp_path, "secret", lambda: None)

    range_headers = (
        "bytes=200-",
        "not-a-range",
        "bytes=10-5",
        "bytes=0-1,10-11",
    )
    for range_header in range_headers:
        response, body = request(app, "/map.pmtiles", range_header=range_header)
        assert response["status"] == "416 Range Not Satisfiable"
        assert response["headers"]["Content-Range"] == "bytes */200"
        assert response["headers"]["Content-Length"] == "0"
        assert body == b""


def test_static_frontend_range_does_not_read_or_return_entire_file(
    tmp_path, monkeypatch
):
    content = bytes(range(256)) * 16
    candidate = tmp_path / "map.pmtiles"
    candidate.write_bytes(content)
    app = static_application(tmp_path, "secret", lambda: None)
    read_bytes_called = False
    original_read_bytes = Path.read_bytes

    def tracked_read_bytes(path):
        nonlocal read_bytes_called
        if path == candidate:
            read_bytes_called = True
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", tracked_read_bytes)
    response, body = request(app, "/map.pmtiles", range_header="bytes=500-549")

    assert response["status"] == "206 Partial Content"
    assert body == content[500:550]
    assert len(body) < len(content)
    assert not read_bytes_called


def test_static_frontend_rejects_traversal(tmp_path):
    app = static_application(tmp_path, "secret", lambda: None)
    response, _ = request(app, "/../secret.txt")
    assert response["status"] == "404 Not Found"


def test_static_frontend_serves_development_icon_without_copy(tmp_path):
    frontend = tmp_path / "src" / "app"
    frontend.mkdir(parents=True)
    (tmp_path / "PLZ-Karte.ico").write_bytes(b"icon")
    app = static_application(frontend, "secret", lambda: None)

    response, body = request(app, "/PLZ-Karte.ico")

    assert response["status"] == "200 OK"
    assert response["headers"]["Content-Type"] == "image/vnd.microsoft.icon"
    assert body == b"icon"


def test_shutdown_requires_token(tmp_path):
    called = []
    app = static_application(tmp_path, "secret", lambda: called.append(True))
    response, _ = request(app, "/api/system/shutdown", "POST")
    assert response["status"] == "403 Forbidden"
    assert not called


def test_frontend_log_endpoint_records_messages(tmp_path, monkeypatch):
    app = static_application(tmp_path, "secret", lambda: None)
    messages = []
    monkeypatch.setattr(production.frontend_logger, "info", messages.append)

    response, body = request(
        app,
        "/api/logs/frontend",
        "POST",
        payload={"level": "info", "message": "Frontend geladen"},
    )

    assert response["status"] == "204 No Content"
    assert body == b""
    assert messages == ["Frontend geladen"]


def test_frontend_log_endpoint_rejects_invalid_entries(tmp_path):
    app = static_application(tmp_path, "secret", lambda: None)

    response, _ = request(
        app,
        "/api/logs/frontend",
        "POST",
        payload={"level": "debug", "message": "not permitted"},
    )

    assert response["status"] == "400 Bad Request"


def test_desktop_window_api_controls_window():
    calls = []

    class Window:
        def minimize(self): calls.append("minimize")
        def maximize(self): calls.append("maximize")
        def restore(self): calls.append("restore")
        def destroy(self): calls.append("destroy")

    api = DesktopWindowApi()
    api.window = Window()
    api.minimize()
    api.toggle_maximize()
    api.toggle_maximize()
    api.close()

    assert calls == ["minimize", "maximize", "restore", "destroy"]
