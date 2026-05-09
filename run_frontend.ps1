$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

$NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $NpmCommand) {
    throw "npm.cmd was not found. Install Node.js LTS, then reopen PowerShell."
}

$FrontendEnv = Join-Path $Root "frontend\.env"
$FrontendEnvExample = Join-Path $Root "frontend\.env.example"
if (-not (Test-Path $FrontendEnv) -and (Test-Path $FrontendEnvExample)) {
    Copy-Item $FrontendEnvExample $FrontendEnv
}

& $NpmCommand.Source --prefix frontend install

& $NpmCommand.Source --prefix frontend run dev
