"""API resilience tests.

Validates the API under burst traffic, invalid input injection, and edge cases.
All tests use synchronous TestClient so the FastAPI lifespan runs correctly.
"""
import concurrent.futures
import time

from fastapi.testclient import TestClient


def test_health_burst_traffic(sync_client):
    """50 concurrent /v1/health requests must all return 200 with 0% failure rate."""
    n = 50
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(sync_client.get, "/v1/health") for _ in range(n)]
        responses = [f.result(timeout=10) for f in futures]

    failures = [r for r in responses if r.status_code != 200]
    assert len(failures) == 0, f"{len(failures)}/{n} health checks failed"

    for resp in responses:
        assert resp.json()["status"] in ("ok", "degraded")


def test_metrics_endpoint_available(sync_client):
    """GET /v1/metrics must return a valid JSON payload."""
    resp = sync_client.get("/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "uptime_seconds" in data
    assert "requests_total" in data
    assert "active_scans" in data
    assert data["uptime_seconds"] >= 0


def test_metrics_prometheus_format(sync_client):
    """GET /v1/metrics with Accept: text/plain must return Prometheus text format."""
    resp = sync_client.get("/v1/metrics", headers={"accept": "text/plain"})
    assert resp.status_code == 200
    body = resp.text
    assert "aegis_requests_total" in body
    assert "aegis_uptime_seconds" in body
    assert "# TYPE" in body


def test_invalid_target_injection(sync_client):
    """Shell-injection characters in target must be rejected with 422 or 400."""
    bad_targets = [
        "127.0.0.1; rm -rf /",
        "localhost && cat /etc/passwd",
        "$(id)",
        "http://scanme.nmap.org",
        "",
    ]
    for target in bad_targets:
        resp = sync_client.post("/v1/scan", json={"target": target})
        assert resp.status_code in (400, 422), (
            f"Target {target!r} was not rejected (got {resp.status_code})"
        )


def test_public_target_rejected_by_default(sync_client):
    """Public hostnames must be blocked by the default private-only policy."""
    resp = sync_client.post("/v1/scan", json={"target": "scanme.nmap.org"})
    assert resp.status_code == 400
    assert "private scanning policy" in resp.json()["detail"]


def test_oversized_cidr_rejected(sync_client):
    """CIDR ranges exceeding max_scan_hosts must be rejected."""
    resp = sync_client.post("/v1/scan", json={"target": "10.0.0.0/8"})
    assert resp.status_code in (400, 422)


def test_unknown_scan_id_returns_404(sync_client):
    """GET /v1/scan/{id} for a non-existent ID must return 404."""
    resp = sync_client.get("/v1/scan/nonexistentid00000000000000000")
    assert resp.status_code == 404


def test_malformed_json_body_returns_422(sync_client):
    """A POST with no body must return 422 Unprocessable Entity."""
    resp = sync_client.post(
        "/v1/scan",
        content=b"this is not json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422


def test_detailed_health_includes_memory(sync_client):
    """GET /v1/health/detailed must include memory and CPU fields."""
    resp = sync_client.get("/v1/health/detailed")
    assert resp.status_code == 200
    data = resp.json()
    assert "memory" in data
    assert "cpu_percent" in data
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] > 0


def test_request_id_header_echoed(sync_client):
    """Responses must echo X-Request-ID (generated or client-supplied)."""
    resp = sync_client.get("/v1/health")
    assert "x-request-id" in resp.headers

    custom_id = "test-correlation-12345"
    resp2 = sync_client.get("/v1/health", headers={"X-Request-ID": custom_id})
    assert resp2.headers.get("x-request-id") == custom_id


def test_concurrent_mixed_traffic(sync_client):
    """Simultaneous health + scan + metrics requests must all succeed."""

    def health():
        r = sync_client.get("/v1/health")
        assert r.status_code == 200

    def scan():
        r = sync_client.post("/v1/scan", json={"target": "127.0.0.1"})
        assert r.status_code == 202

    def met():
        r = sync_client.get("/v1/metrics")
        assert r.status_code == 200

    tasks = [health] * 10 + [scan] * 5 + [met] * 5
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        futures = [pool.submit(fn) for fn in tasks]
        for f in futures:
            f.result(timeout=30)


def test_metrics_counts_requests(sync_client):
    """requests_total counter must increment after requests."""
    before = sync_client.get("/v1/metrics").json()["requests_total"]
    for _ in range(5):
        sync_client.get("/v1/health")
    after = sync_client.get("/v1/metrics").json()["requests_total"]
    assert after > before
