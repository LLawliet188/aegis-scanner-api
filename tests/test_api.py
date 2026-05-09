import time

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.utils.nmap_resolver import NMAP_NOT_INSTALLED_MESSAGE


def test_v1_health(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["ready"] is True
    assert payload["version"]
    assert payload["scan_engine"] == "mock"


def test_v1_detailed_health(client):
    response = client.get("/v1/health/detailed")
    assert response.status_code == 200
    payload = response.json()
    assert payload["environment_valid"] is True
    assert payload["uptime_seconds"] >= 0
    assert payload["dependencies"]["configuration"]["ok"] is True
    assert "python_version" in payload["system"]


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["health"] == "/v1/health"


def test_v1_scan_lifecycle(client):
    response = client.post("/v1/scan", json={"target": "127.0.0.1", "options": {"top_ports": 10}})
    assert response.status_code == 202
    accepted = response.json()
    scan_id = accepted["scan_id"]
    assert accepted["websocket_url"] == f"/v1/ws/scan/{scan_id}"

    record = None
    for _ in range(30):
        record_response = client.get(f"/v1/scan/{scan_id}")
        assert record_response.status_code == 200
        record = record_response.json()
        if record["status"] == "completed":
            break
        time.sleep(0.05)

    assert record is not None
    assert record["status"] == "completed"
    assert record["result"]["summary"]["open_ports"] == 2
    assert record["result"]["vulnerabilities"][0]["cve_enrichment_status"] == "pending_provider_integration"


def test_scan_rejects_public_target_by_default(client):
    response = client.post("/v1/scan", json={"target": "scanme.nmap.org"})
    assert response.status_code == 400
    assert "private scanning policy" in response.json()["detail"]


def test_v1_websocket_streams_scan_events(client):
    response = client.post("/v1/scan", json={"target": "localhost", "options": {"top_ports": 10}})
    assert response.status_code == 202
    scan_id = response.json()["scan_id"]

    with client.websocket_connect(f"/v1/ws/scan/{scan_id}") as websocket:
        events = []
        for _ in range(20):
            event = websocket.receive_json()
            events.append(event)
            if event["type"] == "completed":
                break

    event_types = {event["type"] for event in events}
    assert "queued" in event_types
    assert "progress" in event_types
    assert "log" in event_types
    assert "finding" in event_types
    assert "completed" in event_types


def test_legacy_scan_routes_remain_available(client):
    response = client.post("/scan", json={"target": "127.0.0.1", "options": {"top_ports": 10}})
    assert response.status_code == 202
    scan_id = response.json()["scan_id"]
    assert response.json()["websocket_url"] == f"/ws/scan/{scan_id}"

    record_response = client.get(f"/scan/{scan_id}")
    assert record_response.status_code == 200


def test_legacy_health_route_remains_available(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_nmap_fails_scan_record_without_crashing(monkeypatch):
    monkeypatch.setenv("AEGIS_SCAN_ENGINE", "nmap")
    monkeypatch.setenv("AEGIS_ALLOWED_TARGET_MODE", "private")
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173")

    def missing_nmap():
        raise RuntimeError(NMAP_NOT_INSTALLED_MESSAGE)

    monkeypatch.setattr("app.services.nmap_runner.get_nmap_path", missing_nmap)
    get_settings.cache_clear()

    app = create_app()
    with TestClient(app) as test_client:
        response = test_client.post("/v1/scan", json={"target": "127.0.0.1", "options": {"top_ports": 10}})
        assert response.status_code == 202
        scan_id = response.json()["scan_id"]

        record = None
        for _ in range(30):
            record_response = test_client.get(f"/v1/scan/{scan_id}")
            assert record_response.status_code == 200
            record = record_response.json()
            if record["status"] == "failed":
                break
            time.sleep(0.05)

        assert record is not None
        assert record["status"] == "failed"
        assert record["error"] == NMAP_NOT_INSTALLED_MESSAGE
