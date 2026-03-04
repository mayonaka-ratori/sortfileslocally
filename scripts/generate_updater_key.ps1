<#
.SYNOPSIS
Generates an Ed25519 keypair for the Tauri Updater.

.DESCRIPTION
This script uses the Tauri CLI to generate a new keypair in the user's .tauri directory.
The public key should be added to `tauri.conf.json` and the private key added to GitHub Secrets.
#>

$KeyPath = "$env:USERPROFILE\.tauri\localcurator.key"
$KeyDir = Split-Path $KeyPath -Parent

if (-not (Test-Path $KeyDir)) {
    New-Item -ItemType Directory -Force -Path $KeyDir | Out-Null
}

Write-Host "Generating Tauri Updater Keypair at $KeyPath..."
Write-Host "You may be prompted for a password. Remember it for GitHub Secrets (TAURI_KEY_PASSWORD)."

cargo tauri signer generate -w $KeyPath

Write-Host "--------------------------------------------------------"
Write-Host "SUCCESS: Keys generated."
Write-Host "1. Open $KeyPath.pub and copy the public key to 'tauri.conf.json' -> plugins.updater.pubkey"
Write-Host "2. Copy the contents of $KeyPath to your GitHub Secrets as 'TAURI_PRIVATE_KEY'"
Write-Host "3. If you set a password, add it as 'TAURI_KEY_PASSWORD' to GitHub Secrets"
Write-Host "--------------------------------------------------------"
