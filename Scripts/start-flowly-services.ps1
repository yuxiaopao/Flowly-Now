# Flowly local services — venv-only Django + Celery
# Usage: powershell -ExecutionPolicy Bypass -File E:\Flowly-now\scripts\start-flowly-services.ps1

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $Root ".venv\Scripts\python.exe"
$Backend = Join-Path $Root "Backend"
$Reports = Join-Path $Root "test-reports"

if (-not (Test-Path $VenvPython)) {
  Write-Error "Missing venv python: $VenvPython"
  exit 1
}

New-Item -ItemType Directory -Force -Path $Reports | Out-Null

function Stop-FlowlyPy {
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object {
      $_.CommandLine -and (
        $_.CommandLine -match 'manage\.py runserver' -or
        $_.CommandLine -match 'celery -A config'
      )
    } |
    ForEach-Object {
      Write-Host "Stopping PID $($_.ProcessId)"
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "=== Stopping existing Django/Celery ==="
Stop-FlowlyPy
Start-Sleep -Seconds 2

# Clear stuck Celery unacked messages (best-effort)
Write-Host "=== Purging Redis celery unacked (best-effort) ==="
& $VenvPython -c @"
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from config.celery import app
import redis
r = redis.from_url(app.conf.broker_url)
print('deleted unacked', r.delete('unacked'), r.delete('unacked_index'))
try:
    print('purge', app.control.purge())
except Exception as e:
    print('purge skip', e)
"@

Write-Host "=== Starting Django (venv) ==="
Start-Process -FilePath $VenvPython `
  -ArgumentList "manage.py runserver 127.0.0.1:8000 --noreload" `
  -WorkingDirectory $Backend `
  -RedirectStandardOutput (Join-Path $Reports "django_runserver.out.txt") `
  -RedirectStandardError (Join-Path $Reports "django_runserver.err.txt") `
  -WindowStyle Hidden

Write-Host "=== Starting Celery solo (venv) ==="
Start-Process -FilePath $VenvPython `
  -ArgumentList "-m celery -A config worker -l INFO -P solo" `
  -WorkingDirectory $Backend `
  -RedirectStandardOutput (Join-Path $Reports "celery_worker.out.txt") `
  -RedirectStandardError (Join-Path $Reports "celery_worker.err.txt") `
  -WindowStyle Hidden

Start-Sleep -Seconds 6

Write-Host "=== Health ==="
try {
  $code = (Invoke-WebRequest -Uri "http://127.0.0.1:8000/admin/" -UseBasicParsing -TimeoutSec 8).StatusCode
  Write-Host "Django admin HTTP $code"
} catch {
  Write-Host "Django NOT ready: $($_.Exception.Message)"
}

Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match 'runserver|celery -A config' } |
  ForEach-Object {
    $cmd = $_.CommandLine
    if ($cmd.Length -gt 140) { $cmd = $cmd.Substring(0, 140) }
    $kind = if ($cmd -match '\\.venv\\') { 'VENV' } else { 'SYSTEM' }
    Write-Host "$kind PID=$($_.ProcessId) $cmd"
  }

Write-Host "Done."
Write-Host "Note: On this Windows setup, venv python may spawn a system-python child that owns :8000."
Write-Host "That is OK as long as the parent is .venv and Backend code is loaded from cwd."
Write-Host "Do NOT kill only the system child — kill both parent+child via this script instead."
