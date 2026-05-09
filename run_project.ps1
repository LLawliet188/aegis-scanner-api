$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendScript = Join-Path $Root "run_backend.ps1"
$FrontendScript = Join-Path $Root "run_frontend.ps1"

if (-not (Test-Path $BackendScript)) {
    throw "Backend startup script not found: $BackendScript"
}

if (-not (Test-Path $FrontendScript)) {
    throw "Frontend startup script not found: $FrontendScript"
}

Write-Host "Starting AEGIS backend and frontend in separate PowerShell windows..."
Write-Host "Backend:  http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:5173"

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "`"$BackendScript`""
)

Start-Sleep -Seconds 2

Start-Process powershell.exe -ArgumentList @(
    "-NoExit",
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    "`"$FrontendScript`""
)
