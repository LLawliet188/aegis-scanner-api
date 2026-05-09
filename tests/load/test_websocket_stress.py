"""WebSocket stress tests.

Tests multiple concurrent WebSocket connections, long-running scan streams,
and disconnect/reconnect behaviour.
"""
import concurrent.futures
import threading
import time

import pytest
from fastapi.testclient import TestClient


def _run_full_ws_scan(client: TestClient, target: str = "127.0.0.1") -> dict:
    """Submit a scan and consume the WebSocket stream until completion. Thread-safe."""
    resp = client.post("/v1/scan", json={"target": target, "options": {"top_ports": 10}})
    assert resp.status_code == 202
    scan_id = resp.json()["scan_id"]

    events = []
    with client.websocket_connect(f"/v1/ws/scan/{scan_id}") as ws:
        for _ in range(50):
            event = ws.receive_json()
            events.append(event)
            if event["type"] in ("completed", "error"):
                break

    return {"scan_id": scan_id, "events": events}


def test_five_concurrent_websocket_streams(sync_client):
    """5 concurrent WS streams must all deliver a 'completed' event."""
    n = 5
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(_run_full_ws_scan, sync_client) for _ in range(n)]
        results = [f.result(timeout=30) for f in futures]

    for r in results:
        event_types = {e["type"] for e in r["events"]}
        assert "completed" in event_types, f"Scan {r['scan_id']} stream missing 'completed' event"


def test_ten_concurrent_websocket_streams(sync_client):
    """10 concurrent WS streams — all must succeed with 0% failure rate."""
    n = 10
    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(_run_full_ws_scan, sync_client) for _ in range(n)]
        results = [f.result(timeout=60) for f in futures]

    failures = [r for r in results if "completed" not in {e["type"] for e in r["events"]}]
    assert len(failures) == 0, f"{len(failures)}/{n} WebSocket streams failed"


def test_websocket_delivers_ordered_events(sync_client):
    """Events must arrive in the expected lifecycle order."""
    result = _run_full_ws_scan(sync_client)
    events = result["events"]

    event_types = [e["type"] for e in events]
    assert event_types[0] == "queued", f"First event was '{event_types[0]}', expected 'queued'"
    assert event_types[-1] in ("completed", "error"), f"Last event was '{event_types[-1]}'"
    assert "progress" in event_types, "Missing 'progress' events"
    assert "finding" in event_types, "Missing 'finding' events"


def test_websocket_unknown_scan_returns_error(sync_client):
    """Connecting to an unknown scan ID must return a structured error and close."""
    with sync_client.websocket_connect("/v1/ws/scan/doesnotexist00000000000000000000") as ws:
        event = ws.receive_json()
        assert event["type"] == "error"
        assert "not found" in event["message"].lower()


def test_websocket_late_connect_receives_history(sync_client):
    """A client that connects after scan completion must still receive all events."""
    resp = sync_client.post("/v1/scan", json={"target": "127.0.0.1", "options": {"top_ports": 10}})
    assert resp.status_code == 202
    scan_id = resp.json()["scan_id"]

    # Wait for the scan to finish before connecting
    deadline = time.time() + 20
    while time.time() < deadline:
        record = sync_client.get(f"/v1/scan/{scan_id}").json()
        if record["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)

    with sync_client.websocket_connect(f"/v1/ws/scan/{scan_id}") as ws:
        events = []
        for _ in range(50):
            event = ws.receive_json()
            events.append(event)
            if event["type"] in ("completed", "error"):
                break

    assert any(e["type"] == "completed" for e in events), "Late client did not receive 'completed'"


def test_websocket_disconnect_reconnect(sync_client):
    """A client can disconnect and reconnect and still receive history."""
    resp = sync_client.post("/v1/scan", json={"target": "127.0.0.1", "options": {"top_ports": 10}})
    scan_id = resp.json()["scan_id"]

    # First connection — just grab the first event then disconnect
    with sync_client.websocket_connect(f"/v1/ws/scan/{scan_id}") as ws:
        first_event = ws.receive_json()
        assert first_event["type"] == "queued"
    # Socket closed by context manager exit

    # Second connection — should receive history from the beginning
    with sync_client.websocket_connect(f"/v1/ws/scan/{scan_id}") as ws:
        events = []
        for _ in range(50):
            event = ws.receive_json()
            events.append(event)
            if event["type"] in ("completed", "error"):
                break

    assert events[0]["type"] == "queued", "History replay should start with 'queued'"
    assert any(e["type"] in ("completed", "error") for e in events), "Second connection never reached terminal event"
