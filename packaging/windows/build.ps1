$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $Root

$Python = & py -3.12 -c "import sys; print(sys.executable)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.12 konnte nicht gefunden werden."
}
$Python = $Python.Trim()

function Invoke-CheckedPython {
    param([string[]] $PythonArguments)

    & $Python @PythonArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Python-Aufruf fehlgeschlagen: $($PythonArguments -join ' ')"
    }
}

Invoke-CheckedPython @("-m", "pip", "install", "-r", "server\requirements.txt")
Invoke-CheckedPython @("-m", "pip", "install", "-r", "packaging\windows\requirements-build.txt")
Invoke-CheckedPython @("-c", "import sqlalchemy; import alembic; import psycopg; import webview")
Invoke-CheckedPython @("-m", "PyInstaller", "--noconfirm", "--clean", "packaging\windows\plz-map.spec")
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" packaging\windows\installer.iss
