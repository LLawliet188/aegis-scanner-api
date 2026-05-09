# Aegis Scanner Frontend

React + Vite dashboard for the FastAPI scanner backend in this repository.

## Environment

Copy `.env.example` to `.env` when running locally:

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_WS_URL=ws://127.0.0.1:8000
```

## Run Locally on Windows

From the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_frontend.ps1
```

Or run npm through `npm.cmd` directly to avoid the PowerShell `npm.ps1`
execution-policy block:

```powershell
npm.cmd --prefix frontend install
npm.cmd --prefix frontend run dev
```

## Build

```powershell
npm.cmd --prefix frontend run build
```
