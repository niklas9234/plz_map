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


def test_default_database_url_uses_local_data_directory(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("PLZ_MAP_DATABASE", raising=False)
    monkeypatch.setenv("PLZ_MAP_DATA_DIR", str(tmp_path))

    assert database.database_url() == f"sqlite:///{tmp_path / 'plz_map.sqlite3'}"


def test_prepare_data_directories_creates_local_layout(tmp_path, monkeypatch):
    monkeypatch.setenv("PLZ_MAP_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PLZ_MAP_LOG_DIR", str(tmp_path / "logs"))

    paths = database.prepare_data_directories()

    assert paths == {
        "root": tmp_path / "data",
        "backups": tmp_path / "data" / "backups",
        "logs": tmp_path / "logs",
    }
    assert all(path.is_dir() for path in paths.values())
