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
frontend_logger = logging.getLogger("plz_map.frontend")
backend_logger = logging.getLogger("plz_map.backend")
general_logger = logging.getLogger("plz_map.general")


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
    return ProductionConfig(
        profile="local-desktop",
        host=HOST,
        port=PORT,
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


def static_application(frontend: Path, shutdown_token: str, request_shutdown, api_app=None):
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


def request_running_server_stop(control_file: Path) -> bool:
    try:
        token = control_file.read_text(encoding="utf-8").strip()
        request = urllib.request.Request(
            f"http://{HOST}:{PORT}/api/system/shutdown", method="POST",
            headers={"X-PLZ-Map-Token": token}, data=b"",
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status == 204
    except (OSError, urllib.error.URLError):
        return False


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


def create_wsgi_application(config: ProductionConfig, engine, shutdown_token: str, request_shutdown):
    """Build the shared static/API WSGI application."""
    return static_application(
        frontend_directory(), shutdown_token, request_shutdown, create_application(engine)
    )


def prepare_server(config: ProductionConfig):
    """Initialize logging, database and WSGI, then bind the configured server."""
    initialize_logging(config)
    engine = initialize_database(config)

    token = secrets.token_urlsafe(32)
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
    server.set_app(create_wsgi_application(config, engine, token, server.shutdown))
    control_file = config.data_paths["root"] / "server.token" if config.data_paths else None
    if control_file:
        control_file.write_text(token, encoding="utf-8")
    general_logger.info("Anwendung gestartet; Server: %s", config.url)

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
        if control_file:
            control_file.unlink(missing_ok=True)
        engine.dispose()
        general_logger.info("Server sauber beendet")


def run_server() -> int:
    """Start the central, environment-configured multi-user server."""
    server, control_file, engine = prepare_server(server_config())
    _serve(server, control_file, engine)
    return 0


def run_local_server(*, open_browser: bool = True) -> int:
    """Serve the complete local application in the user's browser."""
    server, control_file, engine = prepare_server(local_desktop_config())
    url = f"http://{server.server_address[0]}:{server.server_address[1]}/"
    print(f"PLZ-Karte läuft unter {url}", flush=True)
    print("Zum Beenden Strg+C drücken.", flush=True)
    if open_browser:
        webbrowser.open(url)
    _serve(server, control_file, engine)
    return 0


def run_desktop() -> int:
    """Run the local server inside a native Windows webview window."""
    import webview

    config = local_desktop_config()
    server, control_file, engine = prepare_server(config)
    server_thread = threading.Thread(
        target=_serve, args=(server, control_file, engine), name="plz-map-server", daemon=True
    )
    server_thread.start()

    window = webview.create_window(
        "PLZ-Karte",
        f"{config.url}?desktop=1",
        width=1440,
        height=900,
        min_size=(1024, 700),
        maximized=True,
        frameless=False,
    )

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
    # Keep that default aligned with the intended browser-based user experience;
    # run_desktop remains available internally for now, but is not the packaged
    # application's default entry point.
    return run_local_server()


if __name__ == "__main__":
    raise SystemExit(main())
