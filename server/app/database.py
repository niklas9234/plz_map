"""SQLite connection and schema used by the master-data API."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


APPLICATION_NAME = "PLZ-Karte"


def data_directory() -> Path:
    """Return a writable, update-safe directory for all mutable application data."""
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


def prepare_data_directories() -> dict[str, Path]:
    root = data_directory()
    paths = {"root": root, "backups": root / "backups", "logs": root / "logs"}
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    database_path = Path(path or os.environ.get("PLZ_MAP_DATABASE", data_directory() / "plz_map.sqlite3"))
    if str(database_path) != ":memory:":
        database_path.parent.mkdir(parents=True, exist_ok=True)
    database = str(database_path)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS trades (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL COLLATE NOCASE UNIQUE,
            status TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
            color TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS companies (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            pps_number TEXT NOT NULL UNIQUE,
            trade_id TEXT NOT NULL REFERENCES trades(id),
            status TEXT NOT NULL CHECK (status IN ('active', 'inactive')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS territories (
            company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            postal_code TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('primary', 'alternative')),
            PRIMARY KEY (company_id, postal_code)
        );
        CREATE TABLE IF NOT EXISTS company_information (
            company_id TEXT NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            position INTEGER NOT NULL,
            category TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (company_id, position)
        );
        CREATE TABLE IF NOT EXISTS application_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- SQLite cannot express this cross-table uniqueness rule as an index.
        CREATE TRIGGER IF NOT EXISTS territories_primary_insert
        BEFORE INSERT ON territories WHEN NEW.role = 'primary'
        BEGIN
          SELECT RAISE(ABORT, 'primary territory conflict') WHERE EXISTS (
            SELECT 1 FROM territories t
            JOIN companies existing ON existing.id = t.company_id
            JOIN companies incoming ON incoming.id = NEW.company_id
            WHERE t.postal_code = NEW.postal_code AND t.role = 'primary'
              AND existing.trade_id = incoming.trade_id
          );
        END;
        """
    )
    connection.commit()
