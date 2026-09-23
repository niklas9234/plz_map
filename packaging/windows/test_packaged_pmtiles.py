"""Integration check for the PMTiles archive in a PyInstaller directory."""

from __future__ import annotations

import io
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server"))

from app.production import static_application  # noqa: E402


ARCHIVE_URL = "/data/pmtiles/germany-luxembourg.pmtiles"
ARCHIVE_RELATIVE_PATH = Path("frontend/data/pmtiles/germany-luxembourg.pmtiles")


def request(app, method: str, *, byte_range: str | None = None):
    response: dict[str, object] = {}

    def start_response(status, headers):
        response["status"] = status
        response["headers"] = dict(headers)

    environ = {
        "PATH_INFO": ARCHIVE_URL,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": "0",
        "wsgi.input": io.BytesIO(),
    }
    if byte_range is not None:
        environ["HTTP_RANGE"] = byte_range
    body = b"".join(app(environ, start_response))
    return response, body


def verify_package(package_directory: Path) -> None:
    bundled_root = package_directory.resolve() / "_internal"
    frontend = bundled_root / "frontend"
    archive = bundled_root / ARCHIVE_RELATIVE_PATH
    if not archive.is_file():
        raise AssertionError(f"PMTiles-Archiv fehlt im Paket: {archive}")
    size = archive.stat().st_size
    if size == 0:
        raise AssertionError(f"PMTiles-Archiv ist im Paket leer: {archive}")

    app = static_application(frontend, "packaging-test", lambda: None)
    response, body = request(app, "HEAD")
    assert response["status"] == "200 OK", response
    assert response["headers"]["Content-Length"] == str(size), response
    assert response["headers"]["Accept-Ranges"] == "bytes", response
    assert body == b""

    last = min(31, size - 1)
    response, body = request(app, "GET", byte_range=f"bytes=0-{last}")
    assert response["status"] == "206 Partial Content", response
    assert response["headers"]["Content-Range"] == f"bytes 0-{last}/{size}", response
    assert response["headers"]["Content-Length"] == str(last + 1), response
    with archive.open("rb") as archive_file:
        assert body == archive_file.read(last + 1)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(f"Aufruf: {Path(sys.argv[0]).name} <PyInstaller-Paketverzeichnis>")
    verify_package(Path(sys.argv[1]))
    print(f"PMTiles-Pakettest erfolgreich: {ARCHIVE_URL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
