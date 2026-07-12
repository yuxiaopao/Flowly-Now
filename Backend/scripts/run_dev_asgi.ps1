# Start Django ASGI server (HTTP + WebSocket via Channels/Daphne)
$ErrorActionPreference = "Stop"

$BackendRoot = Split-Path -Parent $PSScriptRoot
$ProjectRoot = Split-Path -Parent $BackendRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Daphne = Join-Path $ProjectRoot ".venv\Scripts\daphne.exe"

if (-not (Test-Path $Daphne)) {
    Write-Error "daphne not found at $Daphne. Run: pip install -r requirements.txt"
}

$portInUse = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($portInUse) {
    Write-Warning "Port 8000 is already in use (PID $($portInUse.OwningProcess)). Stop runserver/Daphne first."
    exit 1
}

Set-Location $BackendRoot
Write-Host "Starting Daphne ASGI on http://127.0.0.1:8000 (WebSocket enabled)"
& $Daphne -b 127.0.0.1 -p 8000 config.asgi:application
