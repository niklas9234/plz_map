"""Central logging configuration for the desktop application."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
MAX_LOG_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 3


def _handler(path: Path) -> RotatingFileHandler:
    handler = RotatingFileHandler(
        path, maxBytes=MAX_LOG_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    return handler


def configure_logging(log_dir: Path) -> dict[str, logging.Logger]:
    """Create separate general, backend and frontend rotating log files."""
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()
    root.setLevel(logging.INFO)
    root.addHandler(_handler(log_dir / "backend.log"))

    configured = {}
    for channel, filename in (
        ("general", "general.log"),
        ("frontend", "frontend.log"),
    ):
        logger = logging.getLogger(f"plz_map.{channel}")
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()
        logger.setLevel(logging.INFO)
        logger.propagate = False
        logger.addHandler(_handler(log_dir / filename))
        configured[channel] = logger

    configured["backend"] = logging.getLogger("plz_map.backend")
    return configured
