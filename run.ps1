# TCRM dev server - run with venv (no Docker)
# Usage: .\run.ps1   or   powershell -ExecutionPolicy Bypass -File .\run.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = "d:\tcrm"

Set-Location $ProjectRoot
$env:PYTHONPATH = "$ProjectRoot\tcrm-src"

$python = "$ProjectRoot\venv\Scripts\python.exe"
$config = "$ProjectRoot\tcrm.conf"

if (-not (Test-Path $python)) {
    Write-Error "Venv not found at $python. Create it with: python -m venv venv"
    exit 1
}
if (-not (Test-Path $config)) {
    Write-Error "Config not found: $config"
    exit 1
}

Write-Host "=========================================="
Write-Host "  TCRM - Connect . Grow . Win"
Write-Host "  Starting server on http://localhost:8069"
Write-Host "=========================================="
Write-Host ""

& $python -m tcrm -c $config
