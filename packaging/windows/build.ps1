param(
    [string] $Version = $env:PLZ_MAP_VERSION,
    [string] $SigningCertificate = $env:WINDOWS_SIGNING_CERTIFICATE,
    [string] $SigningPassword = $env:WINDOWS_SIGNING_PASSWORD
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $Root

if (-not $Version) {
    $Version = (& git describe --tags --exact-match HEAD 2>$null)
}
$Version = "$Version".Trim() -replace '^v', ''
if ($Version -notmatch '^\d+\.\d+\.\d+([.-][0-9A-Za-z.-]+)?$') {
    throw "Eine Releaseversion (z. B. 1.2.3 oder v1.2.3) muss per -Version, PLZ_MAP_VERSION oder Git-Tag angegeben werden."
}

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

function Invoke-SignTool {
    param([string] $Path)
    if (-not $SigningCertificate) { return }
    if (-not (Test-Path $SigningCertificate)) { throw "Signaturzertifikat nicht gefunden: $SigningCertificate" }
    $SignTool = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin" -Filter signtool.exe -Recurse |
        Where-Object FullName -Match '\\x64\\signtool\.exe$' | Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $SignTool) { throw "signtool.exe wurde nicht gefunden." }
    & $SignTool.FullName sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f $SigningCertificate /p $SigningPassword $Path
    if ($LASTEXITCODE -ne 0) { throw "Signierung fehlgeschlagen: $Path" }
}

Invoke-SignTool "$Root\dist\PLZ-Karte\PLZ-Karte.exe"
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" "/DMyAppVersion=$Version" packaging\windows\installer.iss
if ($LASTEXITCODE -ne 0) { throw "Inno Setup fehlgeschlagen." }
$Installer = Join-Path $Root "dist-installer\PLZ-Karte-$Version-Setup.exe"
Invoke-SignTool $Installer
Get-FileHash $Installer -Algorithm SHA256 | ForEach-Object { "$($_.Hash.ToLower())  $(Split-Path $_.Path -Leaf)" } |
    Set-Content (Join-Path $Root "dist-installer\SHA256SUMS.txt") -Encoding ascii
