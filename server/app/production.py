"""Local production server, static frontend and lifecycle management."""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import os
import re
import secrets
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text

from .application import application as api_application, create_application
from .database import create_database_engine, data_directory, initialize, prepare_data_directories
from .logging_config import configure_logging
from .initial_seed import INITIAL_SEED_ID, import_initial_seed

HOST, PORT = "127.0.0.1", 8080
URL = f"http://{HOST}:{PORT}/"
BYTE_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")
MAX_FRONTEND_LOG_SIZE = 16 * 1024
HEARTBEAT_TIMEOUT_SECONDS = 15 * 60
HEARTBEAT_CHECK_INTERVAL_SECONDS = 30
TAB_CLOSE_GRACE_SECONDS = 2
frontend_logger = logging.getLogger("plz_map.frontend")
backend_logger = logging.getLogger("plz_map.backend")
general_logger = logging.getLogger("plz_map.general")
CONTROL_FILE_NAME = "server.token"
LOCK_FILE_NAME = "server.lock"


class BrowserLifecycle:
    """Track authenticated browser surfaces and stop after a generous timeout."""

    def __init__(self, shutdown_token: str, request_shutdown, *, clock=time.monotonic,
                 close_grace=TAB_CLOSE_GRACE_SECONDS):
        self.shutdown_token = shutdown_token
        self.request_shutdown = request_shutdown
        self.clock = clock
        self.surfaces: dict[str, float] = {}
        self.lock = threading.Lock()
        self.close_grace = close_grace
        self.close_timer: threading.Timer | None = None

    def register(self) -> str:
        surface_id = secrets.token_urlsafe(24)
        with self.lock:
            if self.close_timer is not None:
                self.close_timer.cancel()
                self.close_timer = None
            self.surfaces[surface_id] = self.clock()
        return surface_id

    def close(self, surface_id: str) -> bool:
        """Forget one browser tab and stop shortly after the last tab closes."""
        with self.lock:
            if self.surfaces.pop(surface_id, None) is None:
                return False
            if self.surfaces:
                return True
            timer = threading.Timer(self.close_grace, self._shutdown_if_still_empty)
            timer.daemon = True
            self.close_timer = timer
            timer.start()
        return True

    def _shutdown_if_still_empty(self) -> None:
        with self.lock:
            if self.surfaces:
                return
            self.close_timer = None
        general_logger.info("Letzter Browsertab geschlossen; Server wird beendet")
        self.request_shutdown()

    def heartbeat(self, surface_id: str) -> bool:
        with self.lock:
            if surface_id not in self.surfaces:
                return False
            self.surfaces[surface_id] = self.clock()
        return True

    def all_surfaces_expired(self, timeout: float = HEARTBEAT_TIMEOUT_SECONDS) -> bool:
        with self.lock:
            return bool(self.surfaces) and all(
                self.clock() - last_seen >= timeout
                for last_seen in self.surfaces.values()
            )

    def monitor(self, *, timeout=HEARTBEAT_TIMEOUT_SECONDS,
                interval=HEARTBEAT_CHECK_INTERVAL_SECONDS) -> None:
        while not self.all_surfaces_expired(timeout):
            time.sleep(interval)
        general_logger.info("Kein Browser-Heartbeat mehr; Server wird beendet")
        self.request_shutdown()


class DesktopActivation:
    """Bridge authenticated HTTP activation requests to the desktop window."""

    def __init__(self):
        self._window = None
        self._lock = threading.Lock()

    def set_window(self, window) -> None:
        with self._lock:
            self._window = window

    def activate(self) -> None:
        with self._lock:
            window = self._window
        if window is None:
            return
        # pywebview implements these operations on its GUI thread.  Different
        # backends expose focus differently, so restoring/showing the native
        # window and focusing its document gives both EdgeChromium and the
        # fallback backends a chance to bring it forward.
        for method_name in ("restore", "show"):
            method = getattr(window, method_name, None)
            if callable(method):
                method()
        evaluate_js = getattr(window, "evaluate_js", None)
        if callable(evaluate_js):
            evaluate_js("window.focus()")


@dataclass(frozen=True)
class ProductionConfig:
    """Complete configuration for one explicit production start profile."""

    profile: str
    host: str
    port: int
    database_url: str
    data_paths: dict[str, Path] | None = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"


def local_desktop_config() -> ProductionConfig:
    """Build the safe, zero-configuration desktop profile."""
    paths = prepare_data_directories()
    try:
        # Port 0 asks the operating system for a currently free port.  A fixed
        # port can still be selected for this process/user session when needed.
        port = int(os.environ.get("PLZ_MAP_LOCAL_PORT", "0"))
    except ValueError as error:
        raise RuntimeError("PLZ_MAP_LOCAL_PORT muss eine ganze Zahl sein") from error
    if not 0 <= port <= 65535:
        raise RuntimeError("PLZ_MAP_LOCAL_PORT muss zwischen 0 und 65535 liegen")
    return ProductionConfig(
        profile="local-desktop",
        host=HOST,
        port=port,
        database_url=f"sqlite:///{paths['root'] / 'plz_map.sqlite3'}",
        data_paths=paths,
    )


def server_config() -> ProductionConfig:
    """Build the central server profile exclusively from environment settings."""
    try:
        database = os.environ["DATABASE_URL"]
    except KeyError as error:
        raise RuntimeError("DATABASE_URL muss für das Serverprofil gesetzt sein") from error
    host = os.environ.get("PLZ_MAP_HOST", "0.0.0.0")
    try:
        port = int(os.environ.get("PLZ_MAP_PORT", "8000"))
    except ValueError as error:
        raise RuntimeError("PLZ_MAP_PORT muss eine ganze Zahl sein") from error
    if not 1 <= port <= 65535:
        raise RuntimeError("PLZ_MAP_PORT muss zwischen 1 und 65535 liegen")
    return ProductionConfig("server", host, port, database)


def frontend_directory() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS")) / "frontend"
    return Path(__file__).resolve().parents[2] / "src" / "app"


def parse_byte_range(value: str, size: int) -> tuple[int, int] | None:
    """Return the inclusive bounds for one satisfiable HTTP byte range."""
    match = BYTE_RANGE_RE.fullmatch(value)
    if match is None:
        return None
    first, last = match.groups()
    if not first and not last:
        return None
    try:
        if first:
            start = int(first)
            if start >= size:
                return None
            end = min(int(last), size - 1) if last else size - 1
            if start > end:
                return None
            return start, end

        suffix_length = int(last)
        if suffix_length == 0 or size == 0:
            return None
        return max(size - suffix_length, 0), size - 1
    except ValueError:
        # Python limits conversion of extremely long integer strings. Such a
        # header cannot describe a range satisfiable by a local file anyway.
        return None


def static_application(
    frontend: Path, shutdown_token: str, request_shutdown, api_app=None, lifecycle=None,
    activation=None,
):
    frontend = frontend.resolve()
    development_icon = frontend.parents[1] / "PLZ-Karte.ico"
    configured_api = api_app or api_application

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET")
        if path == "/api/logs/frontend" and method == "POST":
            try:
                length = int(environ.get("CONTENT_LENGTH") or 0)
                if length <= 0 or length > MAX_FRONTEND_LOG_SIZE:
                    raise ValueError("invalid content length")
                payload = json.loads(environ["wsgi.input"].read(length))
                if not isinstance(payload, dict):
                    raise ValueError("invalid log entry")
                level = str(payload.get("level", "info")).lower()
                message = (
                    str(payload.get("message", ""))
                    .replace("\r", " ")
                    .replace("\n", " ")[:4000]
                )
                if not message or level not in {"info", "warning", "error"}:
                    raise ValueError("invalid log entry")
                getattr(frontend_logger, level)(message)
                start_response("204 No Content", [("Content-Length", "0")])
                return [b""]
            except (ValueError, TypeError, json.JSONDecodeError):
                start_response("400 Bad Request", [("Content-Length", "0")])
                return [b""]
        if path.startswith("/api/"):
            if path == "/api/system/status" and method == "GET":
                supplied = environ.get("HTTP_X_PLZ_MAP_TOKEN", "")
                if not secrets.compare_digest(supplied, shutdown_token):
                    start_response("403 Forbidden", [("Content-Length", "0")])
                    return [b""]
                start_response("204 No Content", [("Content-Length", "0")])
                return [b""]
            if path == "/api/system/activate" and method == "POST" and activation:
                supplied = environ.get("HTTP_X_PLZ_MAP_TOKEN", "")
                if not secrets.compare_digest(supplied, shutdown_token):
                    start_response("403 Forbidden", [("Content-Length", "0")])
                    return [b""]
                threading.Thread(target=activation.activate, daemon=True).start()
                start_response("204 No Content", [("Content-Length", "0")])
                return [b""]
            if path == "/api/system/session" and method == "POST" and lifecycle:
                payload = json.dumps({
                    "surfaceId": lifecycle.register(),
                    "token": shutdown_token,
                    "heartbeatInterval": HEARTBEAT_CHECK_INTERVAL_SECONDS,
                }).encode("utf-8")
                start_response("200 OK", [
                    ("Content-Type", "application/json"),
                    ("Cache-Control", "no-store"),
                    ("Content-Length", str(len(payload))),
                ])
                return [payload]
            if path == "/api/system/heartbeat" and method == "POST" and lifecycle:
                supplied = environ.get("HTTP_X_PLZ_MAP_TOKEN", "")
                surface_id = environ.get("HTTP_X_PLZ_MAP_SURFACE", "")
                if (not secrets.compare_digest(supplied, shutdown_token)
                        or not lifecycle.heartbeat(surface_id)):
                    start_response("403 Forbidden", [("Content-Length", "0")])
                    return [b""]
                start_response("204 No Content", [("Content-Length", "0")])
                return [b""]
            if path == "/api/system/session/close" and method == "POST" and lifecycle:
                supplied = environ.get("HTTP_X_PLZ_MAP_TOKEN", "")
                surface_id = environ.get("HTTP_X_PLZ_MAP_SURFACE", "")
                if (not secrets.compare_digest(supplied, shutdown_token)
                        or not lifecycle.close(surface_id)):
                    start_response("403 Forbidden", [("Content-Length", "0")])
                    return [b""]
                start_response("204 No Content", [("Content-Length", "0")])
                return [b""]
            if path == "/api/system/shutdown" and method == "POST":
                supplied = environ.get("HTTP_X_PLZ_MAP_TOKEN", "")
                if not secrets.compare_digest(supplied, shutdown_token):
                    start_response("403 Forbidden", [("Content-Length", "0")])
                    return [b""]
                threading.Thread(target=request_shutdown, daemon=True).start()
                start_response("204 No Content", [("Content-Length", "0")])
                return [b""]
            backend_logger.info("API-Anfrage: %s %s", method, path)
            return configured_api(environ, start_response)
        if method not in {"GET", "HEAD"}:
            start_response("405 Method Not Allowed", [("Allow", "GET, HEAD"), ("Content-Length", "0")])
            return [b""]
        relative = "index.html" if path == "/" else path.lstrip("/")
        candidate = (frontend / relative).resolve()
        if (
            relative == "PLZ-Karte.ico"
            and not candidate.is_file()
            and development_icon.is_file()
        ):
            candidate = development_icon
        outside_frontend = frontend not in candidate.parents and candidate != development_icon
        if outside_frontend or not candidate.is_file():
            start_response("404 Not Found", [("Content-Length", "0")])
            return [b""]
        size = candidate.stat().st_size
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        range_value = environ.get("HTTP_RANGE")
        if range_value is not None:
            bounds = parse_byte_range(range_value, size)
            if bounds is None:
                start_response(
                    "416 Range Not Satisfiable",
                    [
                        ("Accept-Ranges", "bytes"),
                        ("Content-Range", f"bytes */{size}"),
                        ("Content-Length", "0"),
                    ],
                )
                return [b""]
            start, end = bounds
            content_length = end - start + 1
            headers = [
                ("Content-Type", content_type),
                ("Accept-Ranges", "bytes"),
                ("Content-Range", f"bytes {start}-{end}/{size}"),
                ("Content-Length", str(content_length)),
            ]
            start_response("206 Partial Content", headers)
            if method == "HEAD":
                return []
            with candidate.open("rb") as static_file:
                static_file.seek(start)
                return [static_file.read(content_length)]

        headers = [
            ("Content-Type", content_type),
            ("Accept-Ranges", "bytes"),
            ("Content-Length", str(size)),
        ]
        start_response("200 OK", headers)
        return [] if method == "HEAD" else [candidate.read_bytes()]

    app.browser_lifecycle = lifecycle
    return app


def backup_database(database: Path, backup_dir: Path, keep: int = 10) -> None:
    if not database.is_file():
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"plz_map-{stamp}.sqlite3"
    import sqlite3
    source = sqlite3.connect(database)
    destination = sqlite3.connect(target)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()
    for old in sorted(backup_dir.glob("plz_map-*.sqlite3"), reverse=True)[keep:]:
        old.unlink()
    general_logger.info("Datenbanksicherung erstellt: %s", target)


def _read_json_file(path: Path) -> dict | None:
    """Read a file which is replaced atomically by its writer."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def _valid_control(control: dict | None) -> bool:
    return bool(
        control
        and isinstance(control.get("pid"), int)
        and not isinstance(control.get("pid"), bool)
        and control["pid"] > 0
        and isinstance(control.get("token"), str)
        and control["token"]
        and isinstance(control.get("port"), int)
        and not isinstance(control.get("port"), bool)
        and 1 <= control["port"] <= 65535
    )


def _process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        return True
    except (OSError, ValueError):
        return False


def _request_control_endpoint(
    control: dict, path: str, method: str, *, timeout: float = 1
) -> bool:
    try:
        request = urllib.request.Request(
            f"http://{HOST}:{control['port']}{path}", method=method,
            headers={"X-PLZ-Map-Token": control["token"]},
            data=b"" if method == "POST" else None,
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status == 204
    except (KeyError, TypeError, ValueError, OSError, urllib.error.URLError):
        return False


def _running_server_url(control_file: Path) -> str | None:
    control = _read_json_file(control_file)
    if (_valid_control(control) and _process_is_running(control["pid"])
            and _request_control_endpoint(control, "/api/system/status", "GET")):
        return f"http://{HOST}:{control['port']}/"
    return None


def request_running_server_stop(control_file: Path) -> bool:
    control = _read_json_file(control_file)
    return bool(
        _valid_control(control)
        and _process_is_running(control["pid"])
        and _request_control_endpoint(control, "/api/system/shutdown", "POST", timeout=3)
    )


def _write_atomic(path: Path, value: dict) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    try:
        temporary.write_text(json.dumps(value), encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _remove_owned(path: Path | None, pid: int, token: str) -> None:
    if path is not None:
        value = _read_json_file(path)
        if value and value.get("pid") == pid and value.get("token") == token:
            path.unlink(missing_ok=True)


def _acquire_instance_lock(root: Path, token: str) -> tuple[Path, str | None]:
    """Serialize local starts and return either our lock or an existing URL."""
    lock_file = root / LOCK_FILE_NAME
    control_file = root / CONTROL_FILE_NAME
    deadline = time.monotonic() + 5
    payload = {"pid": os.getpid(), "token": token}
    while True:
        existing_url = _running_server_url(control_file)
        if existing_url:
            return lock_file, existing_url
        try:
            descriptor = os.open(lock_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(payload, stream)
            # The previous owner may have vanished just before our create.
            existing_url = _running_server_url(control_file)
            if existing_url:
                _remove_owned(lock_file, os.getpid(), token)
            return lock_file, existing_url
        except FileExistsError:
            owner = _read_json_file(lock_file)
            if (not owner or not isinstance(owner.get("pid"), int)
                    or not _process_is_running(owner["pid"])):
                # Unlink only if the observed owner has not changed meanwhile.
                if _read_json_file(lock_file) == owner:
                    lock_file.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError("Eine lokale PLZ-Karte wird bereits gestartet")
            time.sleep(0.05)


def run_database_migrations(database: str) -> None:
    """Upgrade either profile's database to the bundled Alembic revision."""
    server_root = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(server_root / "alembic.ini"))
    alembic_config.set_main_option("script_location", str(server_root / "migrations"))
    alembic_config.attributes["runtime_database_url"] = database
    # Releases before Alembic support created the complete domain schema with
    # SQLAlchemy's create_all(). Such databases have no migration revision (or
    # an empty alembic_version table after a failed first upgrade), so replaying
    # 0001 would try to create their existing tables. Adopt that known legacy
    # schema at 0001; subsequent migrations remain responsible for upgrades.
    probe = create_database_engine(database)
    try:
        tables = set(inspect(probe).get_table_names())
        domain_tables = {"trades", "companies", "territories", "company_information"}
        revision = None
        if "alembic_version" in tables:
            with probe.connect() as connection:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                ).scalar_one_or_none()
        if domain_tables.issubset(tables) and revision is None:
            command.stamp(alembic_config, "0001")
    finally:
        probe.dispose()
    command.upgrade(alembic_config, "head")


def initialize_database(config: ProductionConfig):
    """Run the shared database migration and schema initialization step."""
    if (config.data_paths and config.database_url.startswith("sqlite:///")
            and not config.database_url.endswith(":memory:")):
        backup_database(
            Path(config.database_url.removeprefix("sqlite:///")),
            config.data_paths["backups"],
        )
    run_database_migrations(config.database_url)
    engine = create_database_engine(config.database_url)
    initialize(engine)
    # The desktop edition starts with the bundled pilot data.  This step used
    # to live in the old desktop-only startup function and was accidentally
    # dropped when the desktop and server startup paths were merged.  Keep it
    # deliberately limited to the managed local SQLite database: centrally
    # operated databases are populated through the documented import process.
    if (config.data_paths and config.database_url.startswith("sqlite:///")
            and not config.database_url.endswith(":memory:")):
        import sqlite3
        database = Path(config.database_url.removeprefix("sqlite:///"))
        seed_connection = sqlite3.connect(database)
        try:
            seed_connection.execute("PRAGMA foreign_keys = ON")
            import_initial_seed(seed_connection)
        finally:
            seed_connection.close()
    return engine


def initialize_logging(config: ProductionConfig) -> None:
    """Configure persistent desktop logs or standard server logging."""
    if config.data_paths:
        configure_logging(config.data_paths["logs"])
    else:
        logging.basicConfig(level=logging.INFO)


def create_wsgi_application(
    config: ProductionConfig, engine, shutdown_token: str, request_shutdown,
    activation=None,
):
    """Build the shared static/API WSGI application."""
    lifecycle = (
        BrowserLifecycle(shutdown_token, request_shutdown) if config.data_paths else None
    )
    return static_application(
        frontend_directory(), shutdown_token, request_shutdown,
        create_application(engine), lifecycle, activation,
    )


def prepare_server(
    config: ProductionConfig, *, token: str | None = None, lock_file: Path | None = None
):
    """Initialize logging, database and WSGI, then bind the configured server."""
    initialize_logging(config)
    engine = initialize_database(config)

    token = token or secrets.token_urlsafe(32)
    activation = DesktopActivation() if config.data_paths else None
    try:
        server = make_server(
            config.host, config.port, lambda *_: [], handler_class=WSGIRequestHandler
        )
    except Exception:
        # Database initialization happens before binding the socket. Do not
        # retain its connection pool when the port is already occupied (or
        # binding fails for another reason).
        engine.dispose()
        raise
    application = create_wsgi_application(
        config, engine, token, server.shutdown, activation,
    )
    server.set_app(application)
    server.browser_lifecycle = getattr(application, "browser_lifecycle", None)
    control_file = config.data_paths["root"] / "server.token" if config.data_paths else None
    if control_file:
        _write_atomic(
            control_file,
            {"pid": os.getpid(), "port": server.server_address[1], "token": token},
        )
    server._plz_instance_token = token
    server._plz_lock_file = lock_file
    server.desktop_activation = activation
    actual_url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    general_logger.info("Anwendung gestartet; Server: %s", actual_url)

    def stop_on_signal(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_on_signal)
    signal.signal(signal.SIGINT, stop_on_signal)
    return server, control_file, engine


def _serve(server, control_file: Path | None, engine) -> None:
    try:
        server.serve_forever()
    finally:
        server.server_close()
        token = getattr(server, "_plz_instance_token", "")
        _remove_owned(control_file, os.getpid(), token)
        _remove_owned(getattr(server, "_plz_lock_file", None), os.getpid(), token)
        engine.dispose()
        general_logger.info("Server sauber beendet")


def run_server() -> int:
    """Start the central, environment-configured multi-user server."""
    server, control_file, engine = prepare_server(server_config())
    _serve(server, control_file, engine)
    return 0


def run_local_server(*, open_browser: bool = True) -> int:
    """Serve the complete local application in the user's browser."""
    config = local_desktop_config()
    if config.data_paths is None:
        server, control_file, engine = prepare_server(config)
        url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
        if open_browser:
            webbrowser.open(url)
        _serve(server, control_file, engine)
        return 0
    token = secrets.token_urlsafe(32)
    lock_file, existing_url = _acquire_instance_lock(config.data_paths["root"], token)
    if existing_url:
        if open_browser:
            webbrowser.open(existing_url)
        return 0
    try:
        server, control_file, engine = prepare_server(config, token=token, lock_file=lock_file)
    except Exception:
        _remove_owned(lock_file, os.getpid(), token)
        raise
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    print(f"PLZ-Karte läuft unter {url}", flush=True)
    print("Zum Beenden Strg+C drücken.", flush=True)
    if open_browser:
        webbrowser.open(url)
    lifecycle = getattr(server, "browser_lifecycle", None)
    if lifecycle:
        threading.Thread(
            target=lifecycle.monitor,
            name="plz-map-heartbeat-monitor",
            daemon=True,
        ).start()
    _serve(server, control_file, engine)
    return 0


def run_desktop() -> int:
    """Run the local server inside a native Windows webview window."""
    config = local_desktop_config()
    if config.data_paths is None:
        raise RuntimeError("Das Desktopprofil benötigt ein benutzerspezifisches Datenverzeichnis")
    token = secrets.token_urlsafe(32)
    root = config.data_paths["root"]
    lock_file, existing_url = _acquire_instance_lock(root, token)
    if existing_url:
        control = _read_json_file(root / CONTROL_FILE_NAME)
        if control:
            _request_control_endpoint(control, "/api/system/activate", "POST", timeout=3)
        return 0
    try:
        server, control_file, engine = prepare_server(
            config, token=token, lock_file=lock_file,
        )
    except Exception:
        _remove_owned(lock_file, os.getpid(), token)
        raise

    try:
        import webview
    except Exception:
        server.server_close()
        engine.dispose()
        _remove_owned(control_file, os.getpid(), token)
        _remove_owned(lock_file, os.getpid(), token)
        raise
    server_thread = threading.Thread(
        target=_serve, args=(server, control_file, engine), name="plz-map-server", daemon=True
    )
    server_thread.start()

    try:
        window = webview.create_window(
            "PLZ-Karte",
            f"http://{server.server_address[0]}:{server.server_address[1]}/?desktop=1",
            width=1440,
            height=900,
            min_size=(1024, 700),
            maximized=True,
            frameless=False,
        )
    except Exception:
        server.shutdown()
        server_thread.join(timeout=5)
        raise
    activation = getattr(server, "desktop_activation", None)
    if activation:
        activation.set_window(window)

    def stop_server():
        if server_thread.is_alive():
            threading.Thread(target=server.shutdown, daemon=True).start()

    def disable_inspection_shortcuts():
        window.evaluate_js(
            """
            window.addEventListener('keydown', event => {
              const inspectionShortcut = event.key === 'F12' ||
                ((event.ctrlKey || event.metaKey) && event.shiftKey &&
                 ['I', 'J', 'C'].includes(event.key.toUpperCase()));
              if (inspectionShortcut) {
                event.preventDefault();
                event.stopImmediatePropagation();
              }
            }, true);
            """
        )

    window.events.closed += stop_server
    window.events.loaded += disable_inspection_shortcuts
    try:
        # debug=False prevents pywebview from exposing its developer tools.
        webview.start(gui="edgechromium", debug=False, private_mode=True)
    finally:
        if server_thread.is_alive():
            server.shutdown()
        server_thread.join(timeout=5)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lokale PLZ-Karte")
    parser.add_argument("--server", action="store_true", help="zentralen Server aus Umgebungsvariablen starten")
    parser.add_argument(
        "--local-server",
        action="store_true",
        help="lokale Anwendung samt API im Browser starten",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="mit --local-server keinen Browser automatisch öffnen",
    )
    parser.add_argument("--shutdown", action="store_true", help="laufenden Server sauber beenden")
    args = parser.parse_args()
    if args.shutdown:
        control = data_directory() / "server.token"
        return 0 if request_running_server_stop(control) else 1
    if args.server and args.local_server:
        parser.error("--server und --local-server können nicht kombiniert werden")
    if args.no_browser and not args.local_server:
        parser.error("--no-browser kann nur mit --local-server verwendet werden")
    if args.server:
        return run_server()
    if args.local_server:
        return run_local_server(open_browser=not args.no_browser)
    # The installed Windows shortcut starts the executable without arguments.
    # A native window has a reliable close event and can therefore shut the
    # local server down deterministically. Browser mode remains an explicit
    # fallback for environments where WebView2 is unavailable.
    return run_desktop()


if __name__ == "__main__":
    raise SystemExit(main())
