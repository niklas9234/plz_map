"""Small dependency-free WSGI application for transfer administration."""

from __future__ import annotations

import json
import logging
from datetime import date
from http import HTTPStatus
from urllib.parse import parse_qs

from .database import create_database_engine, initialize
from .transfer import ImportValidationError, SCHEMA_VERSION, dumps, import_data

logger = logging.getLogger("plz_map.backend")


def _json(start_response, status: HTTPStatus, payload: object):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    start_response(f"{status.value} {status.phrase}", [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))])
    return [body]


def create_application(engine=None):
    """Build an API app; injecting an engine lets every backend share tests."""
    configured_engine = engine or create_database_engine()
    initialize(configured_engine)

    def app(environ, start_response):
        path, method = environ.get("PATH_INFO", ""), environ.get("REQUEST_METHOD", "GET")
        connection = configured_engine.connect()
        try:
            if path == "/api/admin/export" and method == "GET":
                body = dumps(connection)
                logger.info("Stammdaten exportiert")
                filename = f"plz-map-export-{date.today().isoformat()}-schema-v{SCHEMA_VERSION}.json"
                start_response("200 OK", [("Content-Type", "application/json; charset=utf-8"),
                                          ("Content-Disposition", f'attachment; filename="{filename}"'),
                                          ("Content-Length", str(len(body)))])
                return [body]
            if path == "/api/admin/import" and method == "POST":
                try:
                    length = int(environ.get("CONTENT_LENGTH") or 0)
                    document = json.loads(environ["wsgi.input"].read(length))
                    mode = parse_qs(environ.get("QUERY_STRING", "")).get("mode", ["empty"])[0]
                    result = import_data(connection, document, mode)
                    logger.info("Stammdatenimport abgeschlossen; Modus: %s", mode)
                    return _json(start_response, HTTPStatus.OK, result)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    logger.warning("Stammdatenimport wegen ungültigem JSON abgelehnt")
                    return _json(start_response, HTTPStatus.BAD_REQUEST, {"code": "invalid_json", "message": "Ungültiges JSON."})
                except ImportValidationError as error:
                    logger.warning("Stammdatenimport wegen Validierungsfehlern abgelehnt")
                    return _json(start_response, HTTPStatus.UNPROCESSABLE_ENTITY,
                                 {"code": "invalid_import", "message": "Import wurde abgelehnt.", "fields": error.errors})
            return _json(start_response, HTTPStatus.NOT_FOUND, {"code": "not_found", "message": "Endpunkt nicht gefunden."})
        finally:
            connection.close()
    return app


_default_application = None


def application(environ, start_response):
    global _default_application
    if _default_application is None:
        _default_application = create_application()
    return _default_application(environ, start_response)
