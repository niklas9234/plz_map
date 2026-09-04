from pathlib import Path

from app import database


def test_windows_logs_use_requested_c_drive_folder(monkeypatch):
    monkeypatch.delenv("PLZ_MAP_LOG_DIR", raising=False)
    monkeypatch.setattr(database.sys, "platform", "win32")
    monkeypatch.setenv("SystemDrive", "C:")

    assert database.log_directory() == Path("C:\\") / "Logs" / "PLZ-Karte"


def test_log_directory_can_be_overridden(tmp_path, monkeypatch):
    target = tmp_path / "custom-logs"
    monkeypatch.setenv("PLZ_MAP_LOG_DIR", str(target))

    assert database.log_directory() == target
