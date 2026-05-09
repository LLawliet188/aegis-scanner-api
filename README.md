# Aegis Scanner API

Production-style FastAPI backend for a cybersecurity SaaS portfolio dashboard. The API accepts authorized scan requests, runs bounded Nmap scans, streams live terminal-style events over WebSockets, and returns structured host, service, and vulnerability data for the React frontend.

## Features

- Versioned FastAPI REST API with `/v1/health`, `/v1/health/detailed`, `/v1/scan`, and `/v1/scan/{scan_id}`
- Backward-compatible legacy REST routes at `/health`, `/scan`, and `/scan/{scan_id}`
- WebSocket stream at `/v1/ws/scan/{scan_id}` for live logs, progress, findings, and completion events
- Real Nmap integration through a safe subprocess boundary plus `python-nmap` XML parsing support
- Target validation for hostnames, IP addresses, and small CIDR ranges
- Default private-network scanning policy to reduce abuse risk
- Structured Pydantic response models for hosts, ports, vulnerabilities, and scan summaries
- CVE enrichment service boundary ready for NVD, OSV, or commercial feeds later
- Docker Compose stack with backend, nginx-served frontend, dedicated reverse proxy, Nmap, healthchecks, and bridge networking
- Test suite covering API lifecycle, WebSocket events, target policy, command safety, and XML parsing

## Architecture

```text
app/
  main.py                 FastAPI app factory, CORS, app state wiring
  api/routes.py           Root endpoint
  api/v1/routes.py        Versioned REST endpoints
  websocket/routes.py     WebSocket scan event stream
  core/config.py          Environment-driven settings
  core/targeting.py       Target and port validation
  models/                 Pydantic API models
  services/
    scan_manager.py       Scan orchestration
    scan_store.py         In-memory scan records
    event_bus.py          Per-scan WebSocket event fanout
    nmap_runner.py        Safe Nmap process execution
    mock_scanner.py       Local/test scanner
    cve_service.py        Future enrichment boundary
  utils/nmap_resolver.py  Portable Nmap executable detection
  utils/nmap_parser.py    Nmap XML to structured findings
tests/                    API, WebSocket, safety, parser tests
```

The current store is intentionally in-memory for portfolio/local development. For production, replace `ScanStore` with Redis, Postgres, or another durable queue-backed store without changing the API contract.

## API

### `GET /`

Returns a small service index with links to `/v1/health` and `/docs`.

### `GET /v1/health`

Returns API status, version, readiness, environment, active scan engine, Nmap availability, and target policy.

### `GET /v1/health/detailed`

Returns readiness plus environment validation, dependency checks, uptime, and basic system diagnostics.

### `POST /v1/scan`

Starts an asynchronous scan.

```json
{
  "target": "127.0.0.1",
  "options": {
    "top_ports": 100,
    "service_detection": true,
    "os_detection": false,
    "vuln_scripts": false,
    "intensity": "standard"
  }
}
```

Response:

```json
{
  "scan_id": "example",
  "status": "queued",
  "target": "127.0.0.1",
  "websocket_url": "/v1/ws/scan/example",
  "message": "Scan accepted and queued."
}
```

### `GET /v1/scan/{scan_id}`

Returns the current scan record and, after completion, the structured result.

### `WS /v1/ws/scan/{scan_id}`

Streams JSON events:

```json
{
  "type": "progress",
  "scan_id": "example",
  "timestamp": "2026-05-09T12:00:00Z",
  "message": "Parsing Nmap XML results",
  "progress": 95,
  "data": null
}
```

Event types are `queued`, `log`, `progress`, `finding`, `completed`, and `error`.

## Environment Variables

Copy `.env.example` to `.env` for local development.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENV_MODE` | `development` | Runtime mode, for example `development`, `docker`, or `production`. Legacy `AEGIS_ENVIRONMENT` is still accepted. |
| `LOG_LEVEL` | `INFO` | Python logging level. Legacy `AEGIS_LOG_LEVEL` is still accepted. |
| `AEGIS_SCAN_ENGINE` | `nmap` | Use `nmap` for real scans or `mock` for local UI/test demos without Nmap. |
| `AEGIS_ALLOWED_TARGET_MODE` | `private` | `private` allows localhost/private IPs; `any` should only be used for authorized networks. |
| `AEGIS_MAX_SCAN_HOSTS` | `16` | Maximum CIDR size accepted by the API. |
| `AEGIS_NMAP_PATH` | empty | Optional explicit path to `nmap.exe`. If unset on Windows, the API checks `C:\Program Files (x86)\Nmap\nmap.exe`, then `C:\Program Files\Nmap\nmap.exe`, then PATH. |
| `AEGIS_ENABLE_OS_DETECTION` | `false` | Enables `-O`; often needs elevated/container capabilities. |
| `AEGIS_ENABLE_VULN_SCRIPTS` | `false` | Enables configured Nmap vuln scripts. Keep opt-in. |
| `AEGIS_NMAP_VULN_SCRIPT_SELECTOR` | `vuln` | Script selector used when vuln scripts are enabled. |
| `ALLOWED_ORIGINS` | localhost frontend/proxy URLs | Comma-separated browser origins allowed to call the API. Required for production. `AEGIS_CORS_ORIGINS` is still accepted for backward compatibility. |
| `AEGIS_LOCAL_HOSTNAMES` | `localhost,host.docker.internal` | Hostnames allowed under private target policy. |
| `VITE_API_URL` | `/v1` in Docker, local backend URL for Vite dev | Frontend API base URL. WebSocket URLs are derived from this same value. |
| `APP_PORT` | `8000` | Public nginx reverse-proxy port used by Docker Compose. |

## Local Development

Install Python 3.12+ and Nmap first. On Windows, the helper scripts use
`python -m uvicorn` and `npm.cmd` so the app works even when PowerShell blocks
activation scripts or `npm.ps1`.

Backend:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_backend.ps1
```

Frontend:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_frontend.ps1
```

One-click Windows startup:

```powershell
powershell -ExecutionPolicy Bypass -File .\run_project.ps1
```

This opens backend and frontend in separate PowerShell windows.

Manual backend commands:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Manual frontend commands:

```powershell
npm.cmd --prefix frontend install
npm.cmd --prefix frontend run dev
```

If Nmap is not installed locally, use `AEGIS_SCAN_ENGINE=mock` for frontend integration work. Real scan requests automatically use `AEGIS_NMAP_PATH`, common Windows install paths, or PATH. If Nmap cannot be found, scan requests fail clearly with: `Nmap not installed. Install Nmap or set AEGIS_NMAP_PATH.`

Run tests:

```bash
pytest -q
```

## Docker

Build and run:

```bash
docker compose up
```

Use `docker compose up --build` after changing Dockerfiles or source that should force a fresh image rebuild.

The full stack will be available at:

```text
Frontend: http://localhost:8000
Backend:  http://localhost:8000/v1
WebSocket: ws://localhost:8000/v1/ws/scan/{scan_id}
```

The compose file uses normal bridge networking and starts three services:

- `backend`: FastAPI + Nmap, with startup validation that runs `nmap --version`.
- `frontend`: static Vite build served by nginx.
- `nginx`: public ingress that routes `/` to the frontend and `/v1/*` plus `/v1/ws/*` to the backend.

The browser uses same-origin `/v1` API paths in containerized deployment, so no host-specific frontend rebuild is needed for the default local Docker stack.

The backend image includes Nmap. The container sets `AEGIS_NMAP_PATH=/usr/bin/nmap` and refuses to start silently if `nmap --version` fails.

Use environment variables or a local `.env` file to override ports, CORS origins, target policy, and frontend API URLs.

## CI

GitHub Actions runs on every push and pull request. The workflow installs backend dependencies, validates Python imports, runs the backend test suite, installs frontend dependencies, lints the frontend, builds the Vite app, builds the Docker Compose stack, starts it, checks `http://localhost:8000/v1/health` through nginx, and opens a basic WebSocket connection through the same proxy.

Do not use `network_mode: host` for this project by default. It behaves differently across Linux, macOS, and Windows and can make the portfolio harder to reproduce.

### Scanning the Host from Docker

Inside a container, `127.0.0.1` means the API container itself. To scan a service running on your host machine, use:

```text
host.docker.internal
```

The compose file includes:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

This keeps Linux Docker behavior aligned with Docker Desktop behavior.

## Nmap, Firewalls, and Permissions

Localhost tests should work with service detection when ports are open and the OS firewall allows loopback connections. For LAN targets, the target host firewall must allow inbound probes to the scanned ports, and the scanner host must be allowed to send outbound traffic.

OS detection (`-O`) may require raw socket privileges. In Docker this usually means adding capabilities such as `NET_RAW` and sometimes `NET_ADMIN`. Those are intentionally not enabled by default. Turn them on only for controlled labs.

Nmap vulnerability scripts can be noisy or intrusive depending on the script. This backend keeps them opt-in through `AEGIS_ENABLE_VULN_SCRIPTS=true` plus the request option `vuln_scripts=true`.

## Cloud Deployment Notes

Many cloud platforms restrict or prohibit port scanning from managed services. Serverless platforms, PaaS containers, and free-tier app hosts are usually the wrong place to run Nmap scans.

For production-style deployment:

- Use a VPS or self-hosted scanner node where scanning is permitted by the provider.
- Scan only assets you own or have written permission to test.
- Keep `AEGIS_ALLOWED_TARGET_MODE=private` unless the scanner is deployed in an authorized environment.
- Add authentication, authorization, quotas, and rate limiting before exposing the API publicly.
- Put the API behind HTTPS and a reverse proxy.
- Store scan records in a durable backend such as Postgres and stream events through Redis if multiple workers are added.
- Separate the control plane from scanner workers if scans become long-running or multi-tenant.

Provider examples change over time, so check the current acceptable use policy before scanning from AWS, Azure, GCP, Render, Fly.io, Railway, or similar platforms.

## Frontend Connectivity

The React dashboard lives in `frontend/`. From the project root, run
`powershell -ExecutionPolicy Bypass -File .\run_frontend.ps1`, or use
`npm.cmd --prefix frontend run dev` directly. Run the backend separately with
`.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload`.

The React frontend uses these environment variables:

```env
VITE_API_URL=http://127.0.0.1:8000/v1
```

Expected frontend flow:

1. `POST ${VITE_API_URL}/scan` with target and options.
2. Read `scan_id` from the response.
3. Open the WebSocket URL derived from `VITE_API_URL`.
4. Render `log` events as terminal output.
5. Render `progress` events in progress UI.
6. Render `finding` events immediately.
7. On `completed`, use the included result payload or call `GET ${VITE_API_URL}/scan/${scan_id}` for the canonical record.

CORS must include the frontend dev origin, usually `http://localhost:5173` for Vite.

## Security Roadmap

This portfolio backend includes placeholders and boundaries for the next production steps:

- Auth middleware and user-scoped scan records
- Per-user rate limits and scan concurrency limits
- API keys or OAuth/JWT integration
- Persistent scan queue with worker isolation
- CVE enrichment cache
- Audit logging
- Tenant-level target allowlists

These are intentionally not overbuilt yet; the current code focuses on a clean, stable, readable foundation.
