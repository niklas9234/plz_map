# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

root = Path(SPECPATH).parents[1]
version_file = root / "build" / "windows" / "version-info.txt"

if not os.environ.get("PLZ_MAP_VERSION"):
    raise RuntimeError("PLZ_MAP_VERSION muss vom Windows-Build gesetzt werden.")
if not version_file.is_file():
    raise RuntimeError(f"Windows-Versionsdatei fehlt: {version_file}")

a = Analysis(
    [str(root / "server" / "run.py")],
    pathex=[str(root / "server")],
    binaries=[],
    datas=[
        (str(root / "src" / "app"), "frontend"),
        (
            str(root / "src" / "app" / "data" / "pmtiles" / "germany-luxembourg.pmtiles"),
            "frontend/data/pmtiles",
        ),
        (str(root / "PLZ-Karte.ico"), "frontend"),
        # production.run_database_migrations() resolves these paths relative
        # to the bundled server root (sys._MEIPASS in a PyInstaller build).
        # Alembic cannot discover or run the revisions when only its Python
        # package is collected.
        (str(root / "server" / "alembic.ini"), "."),
        (str(root / "server" / "migrations"), "migrations"),
        (str(root / "server" / "data" / "plz_map.sqlite3.gz.b64"), "database"),
    ],
    # Alembic loads migrations/env.py dynamically, so PyInstaller cannot see
    # imports that are only referenced from that file during static analysis.
    hiddenimports=["logging.config"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PLZ-Karte",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(root / "PLZ-Karte.ico"),
    version=str(version_file),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="PLZ-Karte")
