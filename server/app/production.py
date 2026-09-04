"""Local production server, static frontend and lifecycle management."""

from __future__ import annotations

import argparse
import logging
import mimetypes
import re
import secrets
import signal
import sys
import threading
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from pathlib import Path
from wsgiref.simple_server import WSGIRequestHandler, make_server

from .application import application as api_application
from .database import create_database_engine, database_url, initialize, prepare_data_directories

HOST, PORT = "127.0.0.1", 8080
URL = f"http://{HOST}:{PORT}/"
BYTE_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


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

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET")
        if path.startswith("/api/"):
            if path == "/api/system/shutdown" and method == "POST":
                supplied = environ.get("HTTP_X_PLZ_MAP_TOKEN", "")
                if not secrets.compare_digest(supplied, shutdown_token):
                    start_response("403 Forbidden", [("Content-Length", "0")])
                    return [b""]
                threading.Thread(target=request_shutdown, daemon=True).start()
                start_response("204 No Content", [("Content-Length", "0")])
                return [b""]
            return api_application(environ, start_response)
        if method not in {"GET", "HEAD"}:
            start_response("405 Method Not Allowed", [("Allow", "GET, HEAD"), ("Content-Length", "0")])
            return [b""]
        relative = "index.html" if path == "/" else path.lstrip("/")
        candidate = (frontend / relative).resolve()
        if frontend not in candidate.parents or not candidate.is_file():
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


def run(open_browser: bool = False) -> int:
    paths = prepare_data_directories()
    url = database_url()
    control_file = paths["root"] / "server.token"
    logging.basicConfig(
        filename=paths["logs"] / "plz-map.log", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s", encoding="utf-8",
    )
    if url.startswith("sqlite:///") and not url.endswith(":memory:"):
        backup_database(Path(url.removeprefix("sqlite:///")), paths["backups"])
    engine = create_database_engine(url)
    initialize(engine)
    engine.dispose()

    token = secrets.token_urlsafe(32)
    server = make_server(HOST, PORT, lambda *_: [], handler_class=WSGIRequestHandler)
    server.set_app(static_application(frontend_directory(), token, server.shutdown))
    control_file.write_text(token, encoding="utf-8")
    logging.info("Server gestartet: %s", URL)

    def stop_on_signal(_signum, _frame):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop_on_signal)
    signal.signal(signal.SIGINT, stop_on_signal)
    if open_browser:
        threading.Timer(0.4, webbrowser.open, args=(URL,)).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()
        control_file.unlink(missing_ok=True)
        logging.info("Server sauber beendet")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Lokaler Produktionsserver der PLZ-Karte")
    parser.add_argument("--open-browser", action="store_true", help="Standardbrowser beim Start öffnen")
    parser.add_argument("--shutdown", action="store_true", help="laufenden Server sauber beenden")
    args = parser.parse_args()
    control = prepare_data_directories()["root"] / "server.token"
    if args.shutdown:
        return 0 if request_running_server_stop(control) else 1
    return run(args.open_browser)


if __name__ == "__main__":
    raise SystemExit(main())
