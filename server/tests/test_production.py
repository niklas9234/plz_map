import io
import json
import os
import socket
import sys
import threading
from pathlib import Path

from sqlalchemy import inspect, text

from app import production
from app.database import create_database_engine
from app.models import Base
from app.production import static_application


def test_local_desktop_profile_is_loopback_sqlite_without_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("PLZ_MAP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "postgresql://must/not/be/used")

    config = production.local_desktop_config()

    assert config.profile == "local-desktop"
    assert config.host == "127.0.0.1"
    assert config.port == 0
    assert config.database_url == f"sqlite:///{tmp_path / 'plz_map.sqlite3'}"
    assert config.data_paths == {
        "root": tmp_path,
        "backups": tmp_path / "backups",
        "logs": tmp_path / "logs",
    }
    assert all(path.is_dir() for path in config.data_paths.values())


def test_local_desktop_profile_accepts_session_port(tmp_path, monkeypatch):
    monkeypatch.setenv("PLZ_MAP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("PLZ_MAP_LOCAL_PORT", "8765")

    assert production.local_desktop_config().port == 8765


def test_server_profile_reads_environment_and_does_not_import_webview(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://plz_map@example/plz_map")
    monkeypatch.setenv("PLZ_MAP_HOST", "10.20.30.40")
    monkeypatch.setenv("PLZ_MAP_PORT", "9000")
    sys.modules.pop("webview", None)

    config = production.server_config()

    assert config.profile == "server"
    assert config.host == "10.20.30.40"
    assert config.port == 9000
    assert config.database_url == "postgresql+psycopg://plz_map@example/plz_map"
    assert config.data_paths is None
    assert "webview" not in sys.modules


def test_server_profile_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    try:
        production.server_config()
    except RuntimeError as error:
        assert "DATABASE_URL" in str(error)
    else:
        raise AssertionError("server profile accepted a missing DATABASE_URL")


def test_local_server_uses_complete_local_profile(monkeypatch):
    config = production.ProductionConfig(
        "local-desktop", "127.0.0.1", 8080, "sqlite:///:memory:", None,
    )
    class FakeServer:
        server_address = ("127.0.0.1", 8080)

    resources = (FakeServer(), None, object())
    calls = []
    monkeypatch.setattr(production, "local_desktop_config", lambda: config)
    monkeypatch.setattr(production, "prepare_server", lambda value: calls.append(value) or resources)
    monkeypatch.setattr(production, "_serve", lambda *values: calls.append(values))
    monkeypatch.setattr(production.webbrowser, "open", lambda url: calls.append(url) or True)

    assert production.run_local_server() == 0
    assert calls == [config, "http://127.0.0.1:8080/", resources]


def test_local_server_can_leave_browser_closed(monkeypatch):
    config = production.ProductionConfig(
        "local-desktop", "127.0.0.1", 8080, "sqlite:///:memory:", None,
    )

    class FakeServer:
        server_address = ("127.0.0.1", 8080)

    resources = (FakeServer(), None, object())
    monkeypatch.setattr(production, "local_desktop_config", lambda: config)
    monkeypatch.setattr(production, "prepare_server", lambda _config: resources)
    monkeypatch.setattr(production, "_serve", lambda *_values: None)
    monkeypatch.setattr(
        production.webbrowser, "open",
        lambda _url: (_ for _ in ()).throw(AssertionError("Browser wurde geöffnet")),
    )

    assert production.run_local_server(open_browser=False) == 0


def test_default_start_opens_local_application_in_desktop_window(monkeypatch):
    calls = []
    monkeypatch.setattr(sys, "argv", ["run.py"])
    monkeypatch.setattr(
        production,
        "run_local_server",
        lambda **_options: (_ for _ in ()).throw(AssertionError("Browser wurde geöffnet")),
    )
    monkeypatch.setattr(
        production,
        "run_desktop",
        lambda: calls.append("desktop") or 0,
    )

    assert production.main() == 0
    assert calls == ["desktop"]


def test_desktop_window_close_stops_server(monkeypatch):
    stopped = threading.Event()
    closed_handlers = []

    class EventHook:
        def __iadd__(self, handler):
            closed_handlers.append(handler)
            return self

    class Events:
        closed = EventHook()
        loaded = EventHook()

    class Window:
        events = Events()

        @staticmethod
        def evaluate_js(_script):
            pass

    class Server:
        server_address = ("127.0.0.1", 8080)

        @staticmethod
        def serve_forever():
            stopped.wait(2)

        @staticmethod
        def shutdown():
            stopped.set()

        @staticmethod
        def server_close():
            pass

    class Engine:
        @staticmethod
        def dispose():
            pass

    class Webview:
        @staticmethod
        def create_window(*_args, **_kwargs):
            return Window()

        @staticmethod
        def start(**_kwargs):
            closed_handlers[0]()

    monkeypatch.setitem(sys.modules, "webview", Webview)
    monkeypatch.setattr(production, "local_desktop_config", lambda: object())
    monkeypatch.setattr(production, "prepare_server", lambda _config: (Server(), None, Engine()))

    assert production.run_desktop() == 0
    assert stopped.is_set()


def test_prepare_server_disposes_engine_when_port_binding_fails(monkeypatch):
    config = production.ProductionConfig(
        "local-desktop", "127.0.0.1", 8080, "sqlite:///:memory:", None,
    )

    class FakeEngine:
        disposed = False

        def dispose(self):
            self.disposed = True

    engine = FakeEngine()
    monkeypatch.setattr(production, "initialize_logging", lambda _config: None)
    monkeypatch.setattr(production, "initialize_database", lambda _config: engine)
    monkeypatch.setattr(
        production, "make_server",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("Port belegt")),
    )

    try:
        production.prepare_server(config)
    except OSError as error:
        assert str(error) == "Port belegt"
    else:
        raise AssertionError("Fehler beim Binden wurde verschluckt")
    assert engine.disposed is True


def test_prepare_server_binds_local_profile_only_to_loopback(tmp_path, monkeypatch):
    config = production.ProductionConfig(
        "local-desktop", "127.0.0.1", 8080, "sqlite:///:memory:",
        {"root": tmp_path, "backups": tmp_path / "backups", "logs": tmp_path / "logs"},
    )
    captured = {}

    class FakeServer:
        server_address = ("127.0.0.1", 8080)
        shutdown = staticmethod(lambda: None)

        def set_app(self, app):
            self.app = app

    def fake_make_server(host, port, app, handler_class):
        captured.update(host=host, port=port)
        return FakeServer()

    monkeypatch.setattr(production, "make_server", fake_make_server)
    monkeypatch.setattr(production, "initialize_logging", lambda _config: None)
    server, control, engine = production.prepare_server(config)
    try:
        assert captured == {"host": "127.0.0.1", "port": 8080}
        assert server.app is not None
        assert control == tmp_path / "server.token"
        saved_control = json.loads(control.read_text(encoding="utf-8"))
        assert saved_control["port"] == 8080
        assert saved_control["token"]
    finally:
        engine.dispose()


def test_local_profile_starts_when_standard_port_is_occupied(tmp_path, monkeypatch):
    occupied = socket.socket()
    occupied.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    occupied.bind((production.HOST, production.PORT))
    occupied.listen()
    monkeypatch.setenv("PLZ_MAP_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("PLZ_MAP_LOCAL_PORT", raising=False)
    monkeypatch.setattr(production, "initialize_logging", lambda _config: None)
    monkeypatch.setattr(production, "initialize_database", lambda _config: FakeEngine())
    monkeypatch.setattr(production, "create_wsgi_application", lambda *_args: lambda *_args: [])

    class FakeEngine:
        def dispose(self):
            pass

    server = None
    try:
        server, control, engine = production.prepare_server(production.local_desktop_config())
        assert server.server_address[0] == production.HOST
        assert server.server_address[1] != production.PORT
        assert json.loads(control.read_text(encoding="utf-8"))["port"] == server.server_address[1]
    finally:
        occupied.close()
        if server is not None:
            server.server_close()
            control.unlink(missing_ok=True)
            engine.dispose()


def test_separate_users_store_their_own_server_ports(tmp_path, monkeypatch):
    class FakeEngine:
        def dispose(self):
            pass

    monkeypatch.setattr(production, "initialize_logging", lambda _config: None)
    monkeypatch.setattr(production, "initialize_database", lambda _config: FakeEngine())
    monkeypatch.setattr(production, "create_wsgi_application", lambda *_args: lambda *_args: [])
    resources = []
    try:
        for user, expected_port in (("user-a", 0), ("user-b", 0)):
            root = tmp_path / user
            root.mkdir()
            config = production.ProductionConfig(
                "local-desktop", production.HOST, expected_port, "sqlite:///:memory:",
                {"root": root, "backups": root / "backups", "logs": root / "logs"},
            )
            resources.append(production.prepare_server(config))

        first_server, first_control, _ = resources[0]
        second_server, second_control, _ = resources[1]
        first = json.loads(first_control.read_text(encoding="utf-8"))
        second = json.loads(second_control.read_text(encoding="utf-8"))
        assert first_control != second_control
        assert first["port"] == first_server.server_address[1]
        assert second["port"] == second_server.server_address[1]
        assert first["port"] != second["port"]
        assert first["token"] != second["token"]
    finally:
        for server, control, engine in resources:
            server.server_close()
            control.unlink(missing_ok=True)
            engine.dispose()


def test_shutdown_uses_port_and_token_of_selected_user(tmp_path, monkeypatch):
    first_control = tmp_path / "user-a" / "server.token"
    second_control = tmp_path / "user-b" / "server.token"
    first_control.parent.mkdir()
    second_control.parent.mkdir()
    first_control.write_text(json.dumps({"pid": os.getpid(), "port": 49101, "token": "first"}), encoding="utf-8")
    second_control.write_text(json.dumps({"pid": os.getpid(), "port": 49102, "token": "second"}), encoding="utf-8")
    calls = []

    class Response:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

    def fake_urlopen(request, timeout):
        calls.append((request.full_url, request.get_header("X-plz-map-token"), timeout))
        return Response()

    monkeypatch.setattr(production.urllib.request, "urlopen", fake_urlopen)

    assert production.request_running_server_stop(second_control)
    assert calls == [("http://127.0.0.1:49102/api/system/shutdown", "second", 3)]


def test_initialize_database_imports_seed_for_desktop_profile(tmp_path, monkeypatch):
    database = tmp_path / "plz-map.sqlite3"
    config = production.ProductionConfig(
        "local-desktop", "127.0.0.1", 8080, f"sqlite:///{database}",
        {"root": tmp_path, "backups": tmp_path / "backups", "logs": tmp_path / "logs"},
    )
    imported = []
    monkeypatch.setattr(production, "run_database_migrations", lambda _url: None)
    monkeypatch.setattr(
        production,
        "import_initial_seed",
        lambda connection: imported.append(
            connection.execute("PRAGMA foreign_keys").fetchone()[0]
        ),
    )

    engine = production.initialize_database(config)

    try:
        assert imported == [1]
    finally:
        engine.dispose()


def test_initialize_database_creates_seed_metadata_and_imports_bundled_data(tmp_path):
    database = tmp_path / "plz-map.sqlite3"
    config = production.ProductionConfig(
        "local-desktop", "127.0.0.1", 8080, f"sqlite:///{database}",
        {"root": tmp_path, "backups": tmp_path / "backups", "logs": tmp_path / "logs"},
    )

    engine = production.initialize_database(config)

    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT value FROM application_metadata WHERE key = 'initial_seed'"
            ).scalar_one() == production.INITIAL_SEED_ID
            assert connection.exec_driver_sql("SELECT count(*) FROM trades").scalar_one() > 0
            assert connection.exec_driver_sql("SELECT count(*) FROM companies").scalar_one() > 0
    finally:
        engine.dispose()


def test_migrations_adopt_an_unversioned_legacy_schema(tmp_path):
    database = tmp_path / "legacy.sqlite3"
    url = f"sqlite:///{database}"
    legacy_engine = create_database_engine(url)
    Base.metadata.create_all(legacy_engine)
    with legacy_engine.begin() as connection:
        # Alembic creates this table before executing 0001. SQLite can leave it
        # empty when that migration then fails on a pre-existing legacy table.
        connection.execute(text(
            "CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        ))
        connection.execute(text(
            "INSERT INTO application_metadata (key, value, created_at) "
            "VALUES ('legacy', 'preserved', '2026-01-01T00:00:00Z')"
        ))
    legacy_engine.dispose()

    production.run_database_migrations(url)

    migrated_engine = create_database_engine(url)
    try:
        assert set(inspect(migrated_engine).get_table_names()) >= {
            "alembic_version", "application_metadata", "trades", "companies",
            "territories", "company_information", "site_managers",
            "site_manager_territories",
        }
        with migrated_engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0006"
            assert connection.execute(text(
                "SELECT value FROM application_metadata WHERE key = 'legacy'"
            )).scalar_one() == "preserved"
    finally:
        migrated_engine.dispose()


def test_initialize_database_does_not_seed_server_profile(monkeypatch):
    config = production.ProductionConfig(
        "server", "0.0.0.0", 8000, "sqlite:///:memory:", None,
    )
    monkeypatch.setattr(production, "run_database_migrations", lambda _url: None)
    monkeypatch.setattr(
        production, "import_initial_seed",
        lambda _connection: (_ for _ in ()).throw(AssertionError("server profile was seeded")),
    )

    engine = production.initialize_database(config)

    engine.dispose()


def request(app, path, method="GET", range_header=None, payload=None, headers=None):
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
    for name, value in (headers or {}).items():
        environ[f"HTTP_{name.upper().replace('-', '_')}"] = value
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


def test_static_application_forwards_master_data_routes(tmp_path):
    calls = []

    def api_app(environ, start_response):
        calls.append((environ["REQUEST_METHOD"], environ["PATH_INFO"]))
        start_response("200 OK", [("Content-Type", "application/json")])
        return [b"[]"]

    app = static_application(tmp_path, "secret", lambda: None, api_app)

    for path in ("/api/companies", "/api/trades"):
        response, body = request(app, path)
        assert response["status"] == "200 OK"
        assert body == b"[]"
    assert calls == [("GET", "/api/companies"), ("GET", "/api/trades")]


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


def test_authenticated_shutdown_stops_server(tmp_path):
    called = threading.Event()
    app = static_application(tmp_path, "secret", called.set)

    response, _ = request(
        app, "/api/system/shutdown", "POST",
        headers={"X-PLZ-Map-Token": "secret"},
    )

    assert response["status"] == "204 No Content"
    assert called.wait(1)


def test_heartbeat_is_authenticated_and_refreshes_surface(tmp_path):
    now = [100.0]
    lifecycle = production.BrowserLifecycle(
        "secret", lambda: None, clock=lambda: now[0],
    )
    app = static_application(tmp_path, "secret", lambda: None, lifecycle=lifecycle)
    response, body = request(app, "/api/system/session", "POST")
    session = json.loads(body)
    assert response["status"] == "200 OK"

    now[0] = 200.0
    response, _ = request(app, "/api/system/heartbeat", "POST", headers={
        "X-PLZ-Map-Token": "wrong",
        "X-PLZ-Map-Surface": session["surfaceId"],
    })
    assert response["status"] == "403 Forbidden"
    response, _ = request(app, "/api/system/heartbeat", "POST", headers={
        "X-PLZ-Map-Token": "secret",
        "X-PLZ-Map-Surface": session["surfaceId"],
    })
    assert response["status"] == "204 No Content"
    assert lifecycle.surfaces[session["surfaceId"]] == 200.0


def test_closing_last_browser_surface_requests_shutdown(tmp_path):
    stopped = threading.Event()
    lifecycle = production.BrowserLifecycle(
        "secret", stopped.set, close_grace=0.01,
    )
    app = static_application(tmp_path, "secret", stopped.set, lifecycle=lifecycle)
    first = json.loads(request(app, "/api/system/session", "POST")[1])
    second = json.loads(request(app, "/api/system/session", "POST")[1])

    response, _ = request(app, "/api/system/session/close", "POST", headers={
        "X-PLZ-Map-Token": "secret",
        "X-PLZ-Map-Surface": first["surfaceId"],
    })
    assert response["status"] == "204 No Content"
    assert not stopped.wait(0.03)

    response, _ = request(app, "/api/system/session/close", "POST", headers={
        "X-PLZ-Map-Token": "secret",
        "X-PLZ-Map-Surface": second["surfaceId"],
    })
    assert response["status"] == "204 No Content"
    assert stopped.wait(1)


def test_new_browser_surface_cancels_pending_shutdown():
    stopped = threading.Event()
    lifecycle = production.BrowserLifecycle(
        "secret", stopped.set, close_grace=0.05,
    )
    surface = lifecycle.register()

    assert lifecycle.close(surface)
    lifecycle.register()

    assert not stopped.wait(0.1)


def test_closing_browser_surface_requires_valid_credentials(tmp_path):
    lifecycle = production.BrowserLifecycle("secret", lambda: None)
    app = static_application(tmp_path, "secret", lambda: None, lifecycle=lifecycle)
    surface = lifecycle.register()

    response, _ = request(app, "/api/system/session/close", "POST", headers={
        "X-PLZ-Map-Token": "wrong",
        "X-PLZ-Map-Surface": surface,
    })

    assert response["status"] == "403 Forbidden"
    assert surface in lifecycle.surfaces


def test_heartbeat_timeout_requests_controlled_shutdown(monkeypatch):
    now = [0.0]
    stopped = []
    lifecycle = production.BrowserLifecycle(
        "secret", lambda: stopped.append(True), clock=lambda: now[0],
    )
    lifecycle.register()

    def advance(_interval):
        now[0] = production.HEARTBEAT_TIMEOUT_SECONDS

    monkeypatch.setattr(production.time, "sleep", advance)
    lifecycle.monitor()

    assert stopped == [True]


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
