# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH).parents[1]

a = Analysis(
    [str(root / "server" / "run.py")],
    pathex=[str(root / "server")],
    binaries=[],
    datas=[
        (str(root / "src" / "app"), "frontend"),
        (str(root / "PLZ-Karte.ico"), "frontend"),
        # production.run_database_migrations() resolves these paths relative
        # to the bundled server root (sys._MEIPASS in a PyInstaller build).
        # Alembic cannot discover or run the revisions when only its Python
        # package is collected.
        (str(root / "server" / "alembic.ini"), "."),
        (str(root / "server" / "migrations"), "migrations"),
    ],
    hiddenimports=[],
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
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, name="PLZ-Karte")
