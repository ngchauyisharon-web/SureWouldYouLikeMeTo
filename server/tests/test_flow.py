from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    client = TestClient(app)
    assert client.get("/api/health").json() == {"status": "ok"}


def test_scenarios_list() -> None:
    client = TestClient(app)
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    data = r.json()
    assert len(data["scenarios"]) >= 3


def test_session_mock_stream_roundtrip() -> None:
    client = TestClient(app)
    r = client.post("/api/sessions", json={"scenario_slug": "ai_overuse"})
    assert r.status_code == 200
    sid = r.json()["session_id"]

    r2 = client.post(f"/api/sessions/{sid}/choice", json={"choice_index": 0})
    assert r2.status_code == 200

    with client.stream("GET", f"/api/sessions/{sid}/stream") as resp:
        assert resp.status_code == 200
        raw = resp.read().decode("utf-8")
    assert "event: token" in raw
    assert "event: state_patch" in raw
    assert "event: done" in raw
