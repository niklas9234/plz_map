$ErrorActionPreference = "Stop"
$Root = (Resolve-Path "$PSScriptRoot\..\..").Path
Set-Location $Root
py -m pip install -r packaging\windows\requirements-build.txt
py -m PyInstaller --noconfirm --clean packaging\windows\plz-map.spec
& "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe" packaging\windows\installer.iss
