# === LocalCurator Prime Production Build Script (Windows) ===
# Usage: powershell -File scripts/build_production.ps1 [--cpu-only]

param (
    [switch]$CpuOnly = $false
)

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot/.."

$BuildType = if ($CpuOnly) { "--cpu-only" } else { "" }
Write-Host "=== [1/5] Building Backend ($BuildType) ===" -ForegroundColor Cyan
python scripts/build_backend.py $BuildType

Write-Host "=== [2/5] Verifying Sidecar Binary ===" -ForegroundColor Cyan
$Triple = "x86_64-pc-windows-msvc"
$SidecarWrapper = "src-tauri/binaries/localcurator-backend-$Triple.cmd"
$SidecarDir = "src-tauri/binaries/localcurator-backend-dir"

if (-not (Test-Path $SidecarWrapper)) {
    Write-Error "Sidecar wrapper not found: $SidecarWrapper"
}
if (-not (Test-Path $SidecarDir)) {
    Write-Error "Sidecar directory not found: $SidecarDir"
}
Write-Host "  ✅ Sidecar verified."

Write-Host "=== [3/5] Building Frontend ===" -ForegroundColor Cyan
Set-Location web
npm run build
Set-Location ..

Write-Host "=== [4/5] Building Tauri App ===" -ForegroundColor Cyan
# Ensure we use the right platform target
npm run tauri build

Write-Host "=== [5/5] Artifact Verification ===" -ForegroundColor Cyan
$ReleaseDir = "src-tauri/target/release/bundle/msi"
if (-not (Test-Path $ReleaseDir)) {
    $ReleaseDir = "src-tauri/target/release/bundle/exe"
}

if (Test-Path $ReleaseDir) {
    Get-ChildItem $ReleaseDir -Filter "*.msi", "*.exe" | ForEach-Object {
        $Hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
        $Size = [math]::Round($_.Length / 1MB, 2)
        Write-Host "  Artifact: $($_.Name) ($Size MB)"
        Write-Host "  SHA256: $Hash"
    }
} else {
    Write-Warning "Release bundle directory not found. Check src-tauri/target/release/bundle."
}

Write-Host "`n=== BUILD COMPLETE ===" -ForegroundColor Green
