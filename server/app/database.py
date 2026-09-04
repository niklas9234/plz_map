"""Database configuration shared by local SQLite and server PostgreSQL."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url

from .models import Base

APPLICATION_NAME = "PLZ-Karte"


def data_directory() -> Path:
    override = os.environ.get("PLZ_MAP_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / APPLICATION_NAME


def log_directory() -> Path:
    """Return the log location, using the requested shared Windows folder."""
    override = os.environ.get("PLZ_MAP_LOG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        drive = os.environ.get("SystemDrive", "C:")
        return Path(f"{drive}\\") / "Logs" / APPLICATION_NAME
    return data_directory() / "logs"


def prepare_data_directories() -> dict[str, Path]:
    root = data_directory()
    paths = {"root": root, "backups": root / "backups", "logs": log_directory()}
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def database_url() -> str:
    """Return the single database setting, defaulting to the local SQLite file."""
    configured = os.environ.get("DATABASE_URL")
    if configured:
        return configured
    legacy = os.environ.get("PLZ_MAP_DATABASE")
    path = Path(legacy).expanduser() if legacy else data_directory() / "plz_map.sqlite3"
    return f"sqlite:///{path}"


def create_database_engine(url: str | None = None) -> Engine:
    configured_url = url or database_url()
    parsed_url = make_url(configured_url)
    if parsed_url.get_backend_name() == "sqlite" and parsed_url.database not in {None, "", ":memory:"}:
        Path(parsed_url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(configured_url)
    if engine.dialect.name == "sqlite":
        @event.listens_for(engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()
    return engine


def initialize(engine: Engine) -> None:
    """Create a fresh schema; deployed databases are upgraded with Alembic."""
    Base.metadata.create_all(engine)
