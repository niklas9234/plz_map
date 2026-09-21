param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidatePattern('^\d+\.\d+\.\d+(?:\.\d+)?$')]
    [string] $Version
)

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

$VersionParts = @($Version.Split('.') | ForEach-Object { [int] $_ })
while ($VersionParts.Count -lt 4) {
    $VersionParts += 0
}
if ($VersionParts | Where-Object { $_ -gt 65535 }) {
    throw "Jede Versionskomponente muss zwischen 0 und 65535 liegen."
}
$FileVersion = $VersionParts -join ', '
$VersionInfoDirectory = Join-Path $Root "build\windows"
$VersionInfoPath = Join-Path $VersionInfoDirectory "version-info.txt"
New-Item -ItemType Directory -Force -Path $VersionInfoDirectory | Out-Null
$VersionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($FileVersion),
    prodvers=($FileVersion),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040704B0',
        [
          StringStruct(u'CompanyName', u'PLZ-Karte'),
          StringStruct(u'FileDescription', u'PLZ-Karte'),
          StringStruct(u'FileVersion', u'$Version'),
          StringStruct(u'InternalName', u'PLZ-Karte'),
          StringStruct(u'OriginalFilename', u'PLZ-Karte.exe'),
          StringStruct(u'ProductName', u'PLZ-Karte'),
          StringStruct(u'ProductVersion', u'$Version')
        ]
      )
    ]),
    VarFileInfo([VarStruct(u'Translation', [1031, 1200])])
  ]
)
"@
[System.IO.File]::WriteAllText(
    $VersionInfoPath,
    $VersionInfo,
    [System.Text.UTF8Encoding]::new($false)
)

$env:PLZ_MAP_VERSION = $Version
Invoke-CheckedPython @("-m", "PyInstaller", "--noconfirm", "--clean", "packaging\windows\plz-map.spec")
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "/DMyAppVersion=$Version" packaging\windows\installer.iss
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup fehlgeschlagen."
}
