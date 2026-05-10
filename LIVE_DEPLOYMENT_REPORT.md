# Aegis Scanner Live Deployment Report

## Public URLs

- Backend: `https://aegis-scanner-api.onrender.com`
- Frontend: `https://aegis-scanner-api.vercel.app`
- API base used by the frontend bundle: `https://aegis-scanner-api.onrender.com/v1`

## Deployment Architecture

- Render runs the FastAPI backend from the root `Dockerfile`.
- Vercel serves the React/Vite frontend from `frontend/`.
- Frontend REST calls use `VITE_API_URL=https://aegis-scanner-api.onrender.com/v1`.
- Frontend WebSockets derive from that URL as `wss://aegis-scanner-api.onrender.com/v1`.
- Public demo backend uses `AEGIS_SCAN_ENGINE=mock` to avoid cloud provider restrictions around real network scanning.

## Required Production Environment

Render backend:

```env
ENV_MODE=production
LOG_LEVEL=INFO
AEGIS_SCAN_ENGINE=mock
AEGIS_ALLOWED_TARGET_MODE=private
AEGIS_NMAP_PATH=/usr/bin/nmap
AEGIS_ENABLE_OS_DETECTION=false
AEGIS_ENABLE_VULN_SCRIPTS=false
ALLOWED_ORIGINS=https://aegis-scanner-api.vercel.app
```

Vercel frontend:

```env
VITE_API_URL=https://aegis-scanner-api.onrender.com/v1
```

## Validation Results

Validated on May 10, 2026:

- Frontend URL responded with the Vite app HTML: `200 OK`.
- Frontend bundle contains backend API base: `https://aegis-scanner-api.onrender.com/v1`.
- Backend `/v1/health` responded: `200 OK`.
- Backend `/v1/health/detailed` responded: `200 OK`.
- Backend `/v1/metrics` JSON responded: `200 OK`.
- Backend `/v1/metrics` with `Accept: text/plain` responded with Prometheus text: `200 OK`.
- Backend scan request succeeded directly: `202 Accepted`.
- Public WebSocket stream succeeded over `wss://aegis-scanner-api.onrender.com/v1/ws/scan/{scan_id}`.
- WebSocket scan events observed: `queued`, `progress`, `log`, `finding`, `completed`.

## Incident Found

Critical integration issue: Render CORS is still configured with the placeholder origin.

Evidence:

- `Origin: https://example.vercel.app` receives `Access-Control-Allow-Origin: https://example.vercel.app`.
- `Origin: https://aegis-scanner-api.vercel.app` does not receive `Access-Control-Allow-Origin`.
- Browser preflight from `https://aegis-scanner-api.vercel.app` to `/v1/scan` returns `400 Bad Request`.

Impact:

- Backend is healthy.
- Frontend is deployed.
- WebSocket route is healthy.
- Browser scan requests from the live frontend will fail until Render `ALLOWED_ORIGINS` is updated.

## Rectification

Update Render service `aegis-scanner-api` environment variable:

```env
ALLOWED_ORIGINS=https://aegis-scanner-api.vercel.app
```

Then run:

```text
Manual Deploy -> Deploy latest commit
```

Repository-side rectification has also been committed in `render.yaml` so future blueprint syncs use the real Vercel origin instead of the placeholder.

## Revalidation Commands

After Render redeploys, these must pass:

```bash
curl -i -X OPTIONS https://aegis-scanner-api.onrender.com/v1/scan \
  -H "Origin: https://aegis-scanner-api.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"

curl https://aegis-scanner-api.onrender.com/v1/health
curl https://aegis-scanner-api.onrender.com/v1/metrics
```

Expected CORS header:

```text
access-control-allow-origin: https://aegis-scanner-api.vercel.app
```

## Known Cloud Limitations

- Render demo deployment intentionally uses the mock scanner.
- Real Nmap scanning from cloud infrastructure may violate provider rules or fail due to network restrictions.
- Render free services may sleep when idle, causing slow first response after inactivity.
