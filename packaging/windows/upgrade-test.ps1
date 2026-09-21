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
$Executable = Join-Path $env:LOCALAPPDATA "Programs\PLZ-Karte\PLZ-Karte.exe"

function Install-Version([string] $Installer) {
    $process = Start-Process (Resolve-Path $Installer) -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Installer schlug mit Exitcode $($process.ExitCode) fehl: $Installer" }
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
    Start-Application
    $after = Snapshot
    if ($before -cne $after) {
        throw "Stammdaten unterscheiden sich nach dem Upgrade.`nVorher: $before`nNachher: $after"
    }
    if (-not (Test-Path (Join-Path $DataDirectory "plz_map.sqlite3"))) { throw "Die erwartete SQLite-Datei fehlt." }
    Write-Host "Upgrade-Abnahme erfolgreich: Unternehmen, Gewerke, Gebiete, Bauleiter und Unternehmensinformationen sind unverändert."
} finally {
    try { Stop-Application } catch { }
}
