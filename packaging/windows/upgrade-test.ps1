param(
    [Parameter(Mandatory)] [string] $InstallerA,
    [Parameter(Mandatory)] [string] $InstallerB,
    [switch] $ConfirmDataDeletion
)

$ErrorActionPreference = "Stop"
if (-not $ConfirmDataDeletion) {
    throw "Der Test löscht %LOCALAPPDATA%\PLZ-Karte. Nur auf einer Wegwerf-VM mit -ConfirmDataDeletion ausführen."
}
$DataDirectory = Join-Path $env:LOCALAPPDATA "PLZ-Karte"
$InstallDirectory = Join-Path $env:ProgramFiles "PLZ-Karte"
$Executable = Join-Path $InstallDirectory "PLZ-Karte.exe"
$StartMenuDirectory = Join-Path $env:ProgramData "Microsoft\Windows\Start Menu\Programs\PLZ-Karte"

function Install-Version([string] $Installer) {
    $process = Start-Process (Resolve-Path $Installer) -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installer schlug mit Exitcode $($process.ExitCode) fehl: $Installer" }
}

function Assert-MachineInstallation {
    if (-not (Test-Path $Executable)) { throw "Die Anwendung wurde nicht unter Program Files installiert: $Executable" }
}

function Assert-UpgradedStartMenu {
    $shortcutPath = Join-Path $StartMenuDirectory "PLZ-Karte.lnk"
    if (-not (Test-Path $shortcutPath)) { throw "Die gemeinsame Startmenüverknüpfung fehlt: $shortcutPath" }

    foreach ($legacyShortcut in "PLZ-Karte starten.lnk", "PLZ-Karte beenden.lnk") {
        $legacyShortcutPath = Join-Path $StartMenuDirectory $legacyShortcut
        if (Test-Path $legacyShortcutPath) { throw "Die alte Startmenüverknüpfung wurde beim Upgrade nicht entfernt: $legacyShortcutPath" }
    }
}

function Uninstall-Application {
    $uninstaller = Join-Path $InstallDirectory "unins000.exe"
    if (-not (Test-Path $uninstaller)) { throw "Uninstaller wurde nicht gefunden: $uninstaller" }
    $process = Start-Process $uninstaller -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Deinstallation schlug mit Exitcode $($process.ExitCode) fehl." }
}

function Start-Application {
    $script:Application = Start-Process $Executable -ArgumentList "--local-server", "--no-browser" -PassThru
    foreach ($attempt in 1..60) {
        try { Invoke-RestMethod "http://127.0.0.1:8080/api/trades" | Out-Null; return } catch { Start-Sleep 1 }
    }
    throw "Die installierte Anwendung wurde nicht innerhalb von 60 Sekunden bereit."
}

function Stop-Application {
    & $Executable --shutdown
    if ($script:Application) { $script:Application.WaitForExit(10000) | Out-Null }
}

function Api-Post([string] $Path, $Body) {
    Invoke-RestMethod "http://127.0.0.1:8080$Path" -Method Post -ContentType "application/json" -Body ($Body | ConvertTo-Json -Depth 10)
}

function Snapshot {
    # Unternehmen enthalten ihre Gewerke-Zuordnungen, Gebiete und Unternehmensinformationen.
    [ordered]@{
        companies = @(Invoke-RestMethod "http://127.0.0.1:8080/api/companies")
        trades = @(Invoke-RestMethod "http://127.0.0.1:8080/api/trades")
        siteManagers = @(Invoke-RestMethod "http://127.0.0.1:8080/api/site-managers")
    } | ConvertTo-Json -Depth 20 -Compress
}

Remove-Item $DataDirectory -Recurse -Force -ErrorAction SilentlyContinue
try {
    Install-Version $InstallerA
    Assert-MachineInstallation
    Start-Application
    $trade = Api-Post "/api/trades" @{ name = "Upgrade-Abnahme"; color = "#a13579" }
    Api-Post "/api/companies" @{
        name = "Upgrade Test GmbH"; ppsNumber = "UPGRADE-ACCEPTANCE"
        tradeAssignments = @(@{ tradeId = $trade.id; territories = @(@{ postalCode = "97"; role = "alternative" }) })
        information = @(@{ category = "address"; value = "Teststraße 1" }, @{ category = "phone"; value = "+49 123 456" })
    } | Out-Null
    Api-Post "/api/site-managers" @{ name = "Upgrade Bauleitung"; territories = @(@{ postalCode = "97" }) } | Out-Null
    $before = Snapshot
    Stop-Application

    Install-Version $InstallerB
    Assert-MachineInstallation
    Assert-UpgradedStartMenu
    Start-Application
    $after = Snapshot
    if ($before -cne $after) {
        throw "Stammdaten unterscheiden sich nach dem Upgrade.`nVorher: $before`nNachher: $after"
    }
    if (-not (Test-Path (Join-Path $DataDirectory "plz_map.sqlite3"))) { throw "Die erwartete SQLite-Datei fehlt." }
    # Intune invokes the uninstaller as SYSTEM. In that context --shutdown
    # cannot see the interactive user's control file. Removing it reproduces
    # that condition and verifies the installer's taskkill fallback.
    Remove-Item (Join-Path $DataDirectory "server.token") -Force
    Uninstall-Application
    if ($script:Application -and -not $script:Application.WaitForExit(10000)) {
        throw "Der laufende Anwendungsprozess wurde bei der Deinstallation nicht beendet."
    }
    if (Test-Path $Executable) { throw "Die Anwendung ist nach der Deinstallation noch vorhanden: $Executable" }
    if (-not (Test-Path (Join-Path $DataDirectory "plz_map.sqlite3"))) { throw "Die SQLite-Datei wurde bei der Deinstallation entfernt." }
    Write-Host "Systeminstallation, Startmenü, Upgrade, Deinstallation und Erhalt der SQLite-Datei erfolgreich geprüft."
} finally {
    try { Stop-Application } catch { }
}
