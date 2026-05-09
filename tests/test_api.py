import time


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["scan_engine"] == "mock"


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["health"] == "/health"


def test_scan_lifecycle(client):
    response = client.post("/scan", json={"target": "127.0.0.1", "options": {"top_ports": 10}})
    assert response.status_code == 202
    scan_id = response.json()["scan_id"]

    record = None
    for _ in range(30):
        record_response = client.get(f"/scan/{scan_id}")
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
    response = client.post("/scan", json={"target": "scanme.nmap.org"})
    assert response.status_code == 400
    assert "private scanning policy" in response.json()["detail"]


def test_websocket_streams_scan_events(client):
    response = client.post("/scan", json={"target": "localhost", "options": {"top_ports": 10}})
    assert response.status_code == 202
    scan_id = response.json()["scan_id"]

    with client.websocket_connect(f"/ws/scan/{scan_id}") as websocket:
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
