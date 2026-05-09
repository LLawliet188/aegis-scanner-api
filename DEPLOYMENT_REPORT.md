# Aegis Scanner Deployment Report

## Summary

This hardening pass turns the repository into a reproducible full-stack deployment target:

```bash
docker compose up
```

The stack starts a FastAPI backend with Nmap, a built React/Vite frontend, and a dedicated nginx ingress that serves the UI and proxies API/WebSocket traffic.

## Validation Performed

- Backend tests passed: `19 passed`.
- Frontend lint passed.
- Frontend production build passed.
- Python import compilation passed.
- Dependency checks passed: `pip check` and `npm audit --audit-level=high`.
- Docker Compose build passed.
- Docker Compose runtime startup passed.
- nginx-routed `/v1/health` and `/v1/health/detailed` passed.
- nginx-routed WebSocket sanity check passed.
- Backend container Nmap check passed with `/usr/bin/nmap --version`.

## Issues Fixed

### Critical

- Added a dedicated nginx reverse proxy service so the Docker stack has one production-style ingress instead of exposing backend and frontend separately.
- Added Docker runtime validation to CI, including stack build, stack startup, health check through nginx, and WebSocket route sanity check.
- Added backend container startup validation for Nmap with `nmap --version`, so missing Nmap does not fail silently.

### High

- Removed the separate frontend WebSocket setting. WebSocket URLs are now derived from `VITE_API_URL`, which keeps browser configuration to one API base.
- Updated Docker Compose service names and routing so nginx can reliably reach `backend:8000` and `frontend:80`.
- Added same-origin Docker defaults with `VITE_API_URL=/v1`, making the default containerized deployment portable.

### Medium

- Updated README and frontend docs to match the new nginx ingress and CI behavior.
- Added healthchecks for backend, frontend, and nginx services.
- Added production proxy timeout settings for long-running scan streams.
- Removed the tracked frontend runtime env file from version control and kept `.env.example` as the committed template.

### Low

- Kept local Windows scripts intact for non-Docker development.
- Preserved legacy API routes while keeping `/v1/*` as the preferred API surface.

## Architecture Overview

```text
Browser
  |
  | http://localhost:8000
  v
nginx reverse proxy
  |-- /          -> frontend nginx static server
  |-- /v1/*      -> FastAPI backend
  |-- /v1/ws/*   -> FastAPI backend WebSocket endpoint

backend
  |-- FastAPI app
  |-- Nmap installed in image
  |-- startup check: nmap --version

frontend
  |-- React/Vite production build
  |-- served by nginx
```

## Docker Topology

`docker-compose.yml` defines:

- `backend`: builds the Python image, installs Nmap, exposes port `8000` only to the Docker network, and checks `/v1/health`.
- `frontend`: builds the Vite app with `VITE_API_URL=/v1`, serves static files with nginx, and exposes port `80` only to the Docker network.
- `nginx`: public ingress on `${APP_PORT:-8000}`, routes frontend/API/WebSocket traffic, and checks `/healthz`.

All services share the `aegis` bridge network. The backend also maps `host.docker.internal` for portable host scanning from Docker Desktop and Linux Docker.

## CI/CD Workflow

`.github/workflows/ci.yml` runs on `push` and `pull_request`.

It validates:

- Python dependency installation
- Python import compilation
- backend tests
- frontend dependency installation
- frontend lint
- frontend production build
- Docker Compose build
- Docker Compose runtime startup
- nginx-routed health check at `http://localhost:8000/v1/health`
- nginx-routed WebSocket sanity check at `ws://localhost:8000/v1/ws/scan/not-found`

The pipeline fails if any validation step fails.

## Environment

Required deployment variables are documented in `.env.example`.

Important defaults:

- `ENV_MODE=docker`
- `LOG_LEVEL=INFO`
- `AEGIS_SCAN_ENGINE=nmap`
- `AEGIS_NMAP_PATH=/usr/bin/nmap` in Docker Compose
- `ALLOWED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000`
- `VITE_API_URL=/v1`
- `APP_PORT=8000`

For local Windows development outside Docker, `frontend/.env` can point directly at the local backend:

```env
VITE_API_URL=http://127.0.0.1:8000/v1
```

## Deployment Instructions

1. Clone the repository.
2. Optional: copy `.env.example` to `.env` and adjust values.
3. Start the stack:

```bash
docker compose up
```

4. Open the app:

```text
http://localhost:8000
```

5. Check backend readiness:

```text
http://localhost:8000/v1/health
```

## Verification Checklist

- Backend container starts and reports healthy.
- Frontend container starts and reports healthy.
- nginx container starts and reports healthy.
- `/v1/health` responds through nginx.
- `/v1/health/detailed` responds through nginx.
- `/v1/ws/scan/{scan_id}` upgrades through nginx.
- Nmap is present inside the backend container.
- Frontend uses `VITE_API_URL` for REST and WebSocket traffic.
- CI passes backend, frontend, Docker build, and Docker runtime checks.

## Known Limitations

- Scan records are stored in memory. A production multi-user SaaS should replace this with Redis, Postgres, or another durable store.
- Authentication, authorization, quotas, and tenant-scoped target allowlists are not implemented yet.
- OS detection may require extra container capabilities such as `NET_RAW`; those are intentionally not enabled by default.
- Cloud providers may restrict network scanning. Deploy scanner workers only where scanning is explicitly authorized.
