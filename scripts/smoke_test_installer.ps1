param (
    [Parameter(Mandatory = $true)]
    [string]$InstallerPath
)

$ErrorActionPreference = "SilentlyContinue"
$ExeName = "localcurator-prime.exe"

function Cleanup {
    Write-Host "Cleaning up processes..."
    Get-Process | Where-Object { $_.Name -match "^localcurator-prime" -or $_.Name -match "^localcurator-backend" } | Stop-Process -Force -ErrorAction SilentlyContinue

    if ($InstallerPath -match "\.msi$") {
        Write-Host "Uninstalling MSI..."
        Start-Process -FilePath "msiexec.exe" -ArgumentList "/x `"$InstallerPath`" /quiet" -Wait -NoNewWindow
    }
}

if ($InstallerPath -match "\.msi$") {
    Write-Host "Installing MSI: $InstallerPath"
    Start-Process -FilePath "msiexec.exe" -ArgumentList "/i `"$InstallerPath`" /quiet /norestart" -Wait -NoNewWindow
    
    $ProgramFilesPath = Join-Path ${env:ProgramFiles} "LocalCurator Prime"
    $LocalAppDataPath = Join-Path ${env:LOCALAPPDATA} "LocalCurator Prime"
    
    if (Test-Path "$ProgramFilesPath\$ExeName") {
        $LaunchPath = "$ProgramFilesPath\$ExeName"
    }
    elseif (Test-Path "$LocalAppDataPath\$ExeName") {
        $LaunchPath = "$LocalAppDataPath\$ExeName"
    }
    else {
        Write-Host "Could not find installed executable."
        Cleanup
        exit 1
    }
}
else {
    Write-Host "Running EXE directly"
    $LaunchPath = $InstallerPath
}

Write-Host "Launching: $LaunchPath"
Start-Process -FilePath $LaunchPath

$Timeout = 60
$Interval = 2
$Elapsed = 0
$HealthOk = $false

Write-Host "Polling backend /health for $Timeout seconds..."

while ($Elapsed -lt $Timeout) {
    try {
        $Response = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -ErrorAction Stop
        if ($Response.status -eq "ok" -or $Response.status -eq "ok") {
            $HealthOk = $true
            Write-Host "Backend is healthy!"
            break
        }
    }
    catch {
        Write-Host "Backend not ready yet... (${Elapsed}s)"
    }
    
    Start-Sleep -Seconds $Interval
    $Elapsed += $Interval
}

Cleanup

if ($HealthOk) {
    Write-Host "Smoke test PASSED."
    exit 0
}
else {
    Write-Host "Smoke test FAILED: Backend did not respond within $Timeout seconds."
    exit 1
}
