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
