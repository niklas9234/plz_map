import logging

from app.logging_config import configure_logging


def test_configure_logging_creates_separate_log_files(tmp_path):
    loggers = configure_logging(tmp_path)

    loggers["general"].info("allgemeines Ereignis")
    loggers["backend"].info("Backend-Ereignis")
    loggers["frontend"].error("Frontend-Ereignis")
    for logger in loggers.values():
        for handler in logger.handlers:
            handler.flush()

    assert "allgemeines Ereignis" in (tmp_path / "general.log").read_text(encoding="utf-8")
    assert "Backend-Ereignis" in (tmp_path / "backend.log").read_text(encoding="utf-8")
    assert "Frontend-Ereignis" in (tmp_path / "frontend.log").read_text(encoding="utf-8")
