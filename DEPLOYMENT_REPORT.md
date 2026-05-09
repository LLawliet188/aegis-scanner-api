# Aegis Scanner — Production Deployment Report

## Architecture Overview

```text
Browser
  │
  │  http://localhost:8000  (or public cloud URL)
  ▼
nginx reverse proxy  (aegis-scanner-nginx)
  ├── /              → frontend nginx (static SPA)
  ├── /v1/*          → FastAPI backend (REST)
  └── /v1/ws/scan/*  → FastAPI backend (WebSocket, proxy_buffering off)

backend  (aegis-scanner-backend)
  ├── FastAPI + uvicorn
  ├── nmap installed in image (apt-get)
  ├── in-memory ScanStore (LRU, max 1000 records)
  ├── in-memory EventBus (history per scan, auto-cleaned 30s post-completion)
  ├── MetricsCollector (thread-safe counters)
  └── RequestIDMiddleware (X-Request-ID correlation)

frontend  (aegis-scanner-frontend)
  └── React/Vite production build served by nginx
```

## Changes Made

### Critical Bug Fixes

| Fix | File | Description |
|-----|------|-------------|
| ScanStore memory leak | `app/services/scan_store.py` | Added LRU `OrderedDict` with `max_size=1000` eviction so the process cannot OOM on long-lived deployments. |
| EventBus memory leak | `app/services/event_bus.py` | Added `cleanup(scan_id)` called 30 s after scan completion; releases `_history` and `_subscribers` entries. |
| Task GC bug | `app/services/scan_manager.py` | `asyncio.create_task()` result is now stored in `self._tasks` dict; a `done_callback` removes it on completion. |

### Observability (Phase 3)

| Feature | Endpoint / File | Notes |
|---------|----------------|-------|
| Metrics collector | `app/services/metrics.py` | Thread-safe counters: uptime, requests_total, errors_total, active_scans, scans_total. |
| JSON metrics | `GET /v1/metrics` | Returns `MetricsResponse` JSON. |
| Prometheus metrics | `GET /v1/metrics` (Accept: text/plain) | Returns Prometheus text exposition format. |
| Request ID | `app/middleware/request_id.py` | `RequestIDMiddleware` attaches `X-Request-ID` to every request and echoes it in the response header. |
| Enriched health | `GET /v1/health/detailed` | Now includes `memory` (RSS/VMS MB, %) and `cpu_percent` via `psutil`. |
| Structured logging | `app/core/logging.py` (pre-existing) | JSON logs per request including `request_id`, method, path, status, duration_ms. |

### Scan Manager Hardening

- **Concurrency limiter** — `asyncio.Semaphore(20)` caps parallel nmap processes to prevent resource exhaustion.
- **Metrics wiring** — `scan_started()` / `scan_finished()` called around every scan to track active count.
- **Graceful cleanup** — EventBus history released after 30 s post-completion, allowing late WebSocket clients to drain first.

### nginx Hardening

- Added `proxy_buffering off; proxy_cache off;` to the WebSocket path — eliminates stalled frames on buffering-enabled nginx builds.
- Added `proxy_next_upstream` retry logic for the REST path (error/timeout/5xx, max 2 tries) — transparent failover on transient backend errors.
- Reduced health check intervals from 30 s → 15 s for faster startup detection in CI.

### Docker / Compose Hardening

- `stop_grace_period: 30s` on the backend — gives in-flight scans time to finish before SIGKILL.
- uvicorn started with `--timeout-graceful-shutdown 25` — matches the compose stop_grace_period.
- Stricter nmap binary validation in `docker/start-backend.sh` — checks `nmap --version` output contains "nmap".
- Removed dead `python-nmap` dependency (the codebase uses subprocess nmap, not the Python wrapper).

### Deployment Config

- Added `render.yaml` — Render.com Blueprint for one-click backend Docker deployment.
- Frontend: deploy to Vercel by importing the repo, setting Root Directory = `frontend`, and setting `VITE_API_URL=https://<backend>.onrender.com/v1`.

## Load Test Results

All tests run against the mock scanner (deterministic, no nmap required).
Run with: `pytest tests/load/ -v`

| Test | Concurrency | Result |
|------|-------------|--------|
| `test_ten_concurrent_scan_submissions` | 10 parallel POSTs | Pass — all 202, total < 3 s |
| `test_ten_concurrent_scans_complete` | 10 parallel scans end-to-end | Pass — 0% failure rate |
| `test_twenty_concurrent_scans_failure_rate` | 20 parallel scans | Pass — 0% failure rate |
| `test_scan_latency_profile` | 5 sequential scans | Pass — avg < 2 000 ms |
| `test_five_concurrent_websocket_streams` | 5 concurrent WS | Pass — all delivered `completed` |
| `test_ten_concurrent_websocket_streams` | 10 concurrent WS | Pass — 0% failure rate |
| `test_websocket_delivers_ordered_events` | 1 WS | Pass — correct lifecycle order |
| `test_websocket_late_connect_receives_history` | 1 WS (post-scan) | Pass — history replayed |
| `test_websocket_disconnect_reconnect` | 1 WS (reconnect) | Pass — history replayed on reconnect |
| `test_health_burst_traffic` | 50 concurrent GETs | Pass — 0% failure rate |
| `test_concurrent_mixed_traffic` | 20 mixed requests | Pass |

## Observability Setup

### Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/health` | Lightweight readiness probe |
| `GET /v1/health/detailed` | Full status: dependencies, memory, CPU, uptime |
| `GET /v1/metrics` | JSON operational metrics |
| `GET /v1/metrics` (Accept: text/plain) | Prometheus text format |

### Sample Prometheus scrape config

```yaml
scrape_configs:
  - job_name: aegis-scanner
    static_configs:
      - targets: ["localhost:8000"]
    metrics_path: /v1/metrics
    params:
      _accept: ["text/plain"]
```

### Grafana dashboard panels (suggested)

- `aegis_active_scans` — gauge
- `rate(aegis_requests_total[5m])` — request throughput
- `aegis_errors_total / aegis_requests_total` — error rate
- `aegis_uptime_seconds` — process uptime

## Deployment Environment Details

### Local Docker (default)

```bash
docker compose up        # starts nginx on :8000, backend on internal :8000, frontend on internal :80
```

Required env vars (all have defaults for local):

| Variable | Default | Description |
|----------|---------|-------------|
| `AEGIS_SCAN_ENGINE` | `nmap` | `nmap` or `mock` |
| `AEGIS_ALLOWED_TARGET_MODE` | `private` | `private` or `any` |
| `ALLOWED_ORIGINS` | `http://localhost:8000,...` | CORS allowlist |
| `APP_PORT` | `8000` | Host port nginx binds |
| `VITE_API_URL` | `/v1` | Frontend API base |

### Render.com (backend)

1. Push `render.yaml` to GitHub.
2. Create a new **Blueprint** in the Render dashboard and link the repo.
3. Set `ALLOWED_ORIGINS` to your Vercel frontend URL in the Render environment secrets.
4. The backend URL will be `https://aegis-scanner-backend.onrender.com`.

### Vercel (frontend)

1. Import repo on `vercel.com`, set **Root Directory** to `frontend`.
2. Add env var: `VITE_API_URL=https://aegis-scanner-backend.onrender.com/v1`
3. Deploy. The frontend will connect via REST and WebSocket to the Render backend.

### Post-deploy validation

```bash
# Health check
curl https://aegis-scanner-backend.onrender.com/v1/health

# Detailed health (memory, CPU, uptime)
curl https://aegis-scanner-backend.onrender.com/v1/health/detailed

# Metrics
curl https://aegis-scanner-backend.onrender.com/v1/metrics

# Prometheus format
curl -H "Accept: text/plain" https://aegis-scanner-backend.onrender.com/v1/metrics

# Submit a scan
curl -X POST https://aegis-scanner-backend.onrender.com/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"target":"127.0.0.1"}'
```

## Known Limitations

- **In-memory storage** — scan records live in process memory (max 1 000 via LRU). A production multi-tenant system should persist to Redis or PostgreSQL.
- **Single process** — no horizontal scaling. Adding a second backend replica would require shared storage and an external event bus (e.g., Redis pub/sub).
- **OS detection** — requires `CAP_NET_RAW`. Disabled by default; enabling it in a container requires explicit capability grant.
- **Cloud firewall** — many cloud providers (including Render's free tier) restrict raw socket operations used by nmap. Deploy on a VPS (DigitalOcean Droplet, AWS EC2) or use `AEGIS_SCAN_ENGINE=mock` for a demo deployment.
- **No authentication** — the API has no auth layer. Any client can submit scans. Add API key middleware before exposing publicly.

## Scaling Considerations

| Concern | Current | Recommendation |
|---------|---------|---------------|
| Scan concurrency | `asyncio.Semaphore(20)` in-process | Add queue + Redis-backed worker pool |
| Scan storage | LRU dict (1 000 records) | PostgreSQL or Redis with TTL |
| Event streaming | asyncio queues per process | Redis pub/sub for multi-replica |
| Metrics | In-memory counters | Prometheus + Grafana stack |
| Auth | None | API key or JWT middleware |

## Rollback Strategy

All changes are additive. To roll back to the pre-hardening state:

1. `git revert HEAD` or `git checkout <previous-sha> -- <file>` for individual files.
2. The new endpoints (`/v1/metrics`, richer `/v1/health/detailed`) are purely additive — removing them does not break existing clients.
3. `docker compose down && docker compose build && docker compose up` to redeploy with the reverted image.
4. No database migrations — all state is in-memory and resets on restart.
