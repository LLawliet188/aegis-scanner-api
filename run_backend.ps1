$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    py -3 -m venv .venv
}

$Activate = Join-Path $Root ".venv\Scripts\Activate.ps1"
if (Test-Path $Activate) {
    try {
        . $Activate
    } catch {
        Write-Warning "Could not activate the virtual environment in this shell. Continuing with the venv Python directly."
    }
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt

$EnvPath = Join-Path $Root ".env"
if (-not (Test-Path $EnvPath) -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
}

& $Python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
