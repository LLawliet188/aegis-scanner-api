"""Concurrent scan load tests.

Submits multiple /v1/scan requests in parallel and validates that:
- All requests are accepted (202)
- All scans reach 'completed' within a timeout
- p99 latency for submission stays under threshold
- Failure rate is zero
"""
import concurrent.futures
import time

from fastapi.testclient import TestClient


def _submit_and_wait(client: TestClient, target: str, wait_timeout: float = 30.0) -> dict:
    """Submit a scan, poll until completion, return the final record."""
    t0 = time.perf_counter()
    resp = client.post("/v1/scan", json={"target": target, "options": {"top_ports": 10}})
    assert resp.status_code == 202, f"Expected 202, got {resp.status_code}: {resp.text}"
    scan_id = resp.json()["scan_id"]
    submission_ms = (time.perf_counter() - t0) * 1000

    deadline = time.time() + wait_timeout
    while time.time() < deadline:
        record = client.get(f"/v1/scan/{scan_id}").json()
        if record["status"] in ("completed", "failed"):
            return {"record": record, "submission_ms": submission_ms}
        time.sleep(0.05)
    raise TimeoutError(f"Scan {scan_id} did not complete within {wait_timeout}s")


def test_ten_concurrent_scan_submissions(sync_client):
    """10 parallel POSTs must all return 202 within 3 seconds total."""
    n = 10
    start = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(sync_client.post, "/v1/scan",
                               json={"target": "127.0.0.1", "options": {"top_ports": 10}}) for _ in range(n)]
        responses = [f.result(timeout=10) for f in futures]

    total_elapsed = time.perf_counter() - start
    assert total_elapsed < 3.0, f"Batch submission took {total_elapsed:.2f}s (limit 3s)"

    for resp in responses:
        assert resp.status_code == 202, f"Got {resp.status_code}: {resp.text}"

    latencies_ms = [r.elapsed.total_seconds() * 1000 for r in responses]
    latencies_ms.sort()
    p99 = latencies_ms[int(len(latencies_ms) * 0.99)]
    assert p99 < 2000, f"p99 submission latency {p99:.1f}ms exceeds 2000ms"


def test_ten_concurrent_scans_complete(sync_client):
    """10 concurrent scans must all reach 'completed' with 0% failure rate."""
    n = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(_submit_and_wait, sync_client, "127.0.0.1") for _ in range(n)]
        results = [f.result(timeout=60) for f in futures]

    for r in results:
        record = r["record"]
        assert record["status"] == "completed", (
            f"Scan {record.get('scan_id')} failed: {record.get('error')}"
        )
        assert record["result"]["summary"]["open_ports"] == 2


def test_twenty_concurrent_scans_failure_rate(sync_client):
    """20 concurrent scans — failure rate must be 0%."""
    n = 20
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(_submit_and_wait, sync_client, "127.0.0.1") for _ in range(n)]
        results = [f.result(timeout=60) for f in futures]

    failures = [r for r in results if r["record"]["status"] == "failed"]
    failure_rate = len(failures) / n
    assert failure_rate == 0.0, f"Failure rate {failure_rate:.0%} ({len(failures)}/{n} failed)"


def test_scan_latency_profile(sync_client):
    """Sequential end-to-end scan latency must remain under 2 seconds (mock scanner)."""
    latencies = []
    for _ in range(5):
        r = _submit_and_wait(sync_client, "127.0.0.1")
        latencies.append(r["submission_ms"])

    avg = sum(latencies) / len(latencies)
    assert avg < 2000, f"Average scan latency {avg:.1f}ms exceeds 2000ms"
