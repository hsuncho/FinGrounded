from __future__ import annotations

import threading

from conftest import FakeServices, wait_until


def test_ready_when_services_loaded_and_db_ok(make_client):
    client = make_client()
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").json() == {"status": "ready"}


def test_not_ready_when_db_down(make_client):
    client = make_client(db_ok=False)
    assert client.get("/healthz").status_code == 200 
    res = client.get("/readyz")
    assert res.status_code == 503
    assert res.json()["status"] == "db_unavailable"


def test_loading_state_serves_health_but_not_requests(make_client):
    release = threading.Event()

    def slow_loader():
        release.wait(timeout=2)
        return FakeServices()

    client = make_client(loader=slow_loader)
    try:
        assert client.get("/healthz").status_code == 200
        assert client.get("/readyz").json() == {"status": "loading"}
        assert client.post("/api/ask", json={"question": "질문"}).status_code == 503
    finally:
        release.set()
    wait_until(lambda: client.get("/readyz").status_code == 200)


def test_load_failure_marks_liveness_failed(make_client):
    def broken_loader():
        raise RuntimeError("model download failed")

    client = make_client(loader=broken_loader)
    wait_until(lambda: client.get("/healthz").status_code == 503)
    assert client.get("/readyz").status_code == 503
