"""Local production server, static frontend and lifecycle management."""

from __future__ import annotations

import argparse
import json
import logging
import mimetypes
import re
import secrets
import signal
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

from .application import application as api_application
from .database import create_database_engine, database_url, initialize, prepare_data_directories
from .logging_config import configure_logging

HOST, PORT = "127.0.0.1", 8080
URL = f"http://{HOST}:{PORT}/"
BYTE_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")
MAX_FRONTEND_LOG_SIZE = 16 * 1024
frontend_logger = logging.getLogger("plz_map.frontend")
backend_logger = logging.getLogger("plz_map.backend")
general_logger = logging.getLogger("plz_map.general")


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


def static_application(frontend: Path, shutdown_token: str, request_shutdown):
    frontend = frontend.resolve()
    development_icon = frontend.parents[1] / "PLZ-Karte.ico"

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
            return api_application(environ, start_response)
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


def _prepare_server():
    """Initialize persistent state and return the configured local server."""
    paths = prepare_data_directories()
    configure_logging(paths["logs"])
    url = database_url()
    control_file = paths["root"] / "server.token"
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        backup_database(Path(url.removeprefix("sqlite:///")), paths["backups"])
    engine = create_database_engine(url)
    initialize(engine)
    engine.dispose()

    token = secrets.token_urlsafe(32)
    server = make_server(HOST, PORT, lambda *_: [], handler_class=WSGIRequestHandler)
    server.set_app(static_application(frontend_directory(), token, server.shutdown))
    control_file.write_text(token, encoding="utf-8")
    general_logger.info("Anwendung gestartet; Server: %s; Logs: %s", URL, paths["logs"])

    def stop_on_signal(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_on_signal)
    signal.signal(signal.SIGINT, stop_on_signal)
    return server, control_file


def _serve(server, control_file: Path) -> None:
    try:
        server.serve_forever()
    finally:
        server.server_close()
        control_file.unlink(missing_ok=True)
        general_logger.info("Server sauber beendet")


def run() -> int:
    server, control_file = _prepare_server()
    _serve(server, control_file)
    return 0


class DesktopWindowApi:
    """Actions exposed exclusively to the local desktop frontend."""

    def __init__(self, maximized: bool = False):
        self.window = None
        self._maximized = maximized

    def minimize(self):
        self.window.minimize()

    def toggle_maximize(self):
        if self._maximized:
            self.window.restore()
        else:
            self.window.maximize()
        self._maximized = not self._maximized

    def close(self):
        self.window.destroy()


def run_desktop() -> int:
    """Run the local server inside a native Windows webview window."""
    import webview

    server, control_file = _prepare_server()
    server_thread = threading.Thread(
        target=_serve, args=(server, control_file), name="plz-map-server", daemon=True
    )
    server_thread.start()

    window_api = DesktopWindowApi(maximized=True)
    window = webview.create_window(
        "PLZ-Karte",
        f"{URL}?desktop=1",
        width=1440,
        height=900,
        min_size=(1024, 700),
        maximized=True,
        frameless=True,
        easy_drag=False,
        js_api=window_api,
    )
    window_api.window = window

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
    parser = argparse.ArgumentParser(description="Desktopanwendung der PLZ-Karte")
    parser.add_argument("--server", action="store_true", help="nur den lokalen HTTP-Server starten")
    parser.add_argument("--shutdown", action="store_true", help="laufenden Server sauber beenden")
    args = parser.parse_args()
    control = prepare_data_directories()["root"] / "server.token"
    if args.shutdown:
        return 0 if request_running_server_stop(control) else 1
    return run() if args.server else run_desktop()


if __name__ == "__main__":
    raise SystemExit(main())
