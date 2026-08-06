$ErrorActionPreference = "Continue"
$ProjectRoot = "d:\tcrm"
Set-Location $ProjectRoot
$env:PYTHONPATH = "$ProjectRoot\tcrm-src"
$python = "$ProjectRoot\venv\Scripts\python.exe"
$config = "$ProjectRoot\tcrm.conf"

& $python -m tcrm -c $config -d tcrm_master -u tcrm_ai --stop-after-init *>&1
