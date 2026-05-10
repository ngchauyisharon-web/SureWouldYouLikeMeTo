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
    assert r.json()["phase"] == "awaiting_answer_mode"
    assert r.json()["choices"] == []

    r_mode = client.post(f"/api/sessions/{sid}/answer-mode", json={"mode": "ai_options"})
    assert r_mode.status_code == 200
    assert r_mode.json()["phase"] == "awaiting_choice"
    assert len(r_mode.json()["choices"]) >= 2

    r2 = client.post(f"/api/sessions/{sid}/choice", json={"choice_index": 0})
    assert r2.status_code == 200

    with client.stream("GET", f"/api/sessions/{sid}/stream") as resp:
        assert resp.status_code == 200
        raw = resp.read().decode("utf-8")
    assert "event: token" in raw
    assert "event: state_patch" in raw
    assert "event: done" in raw


def test_session_free_text_mock_roundtrip() -> None:
    client = TestClient(app)
    r = client.post("/api/sessions", json={"scenario_slug": "ai_overuse"})
    sid = r.json()["session_id"]
    assert client.post(f"/api/sessions/{sid}/answer-mode", json={"mode": "free_text"}).status_code == 200
    assert (
        client.post(f"/api/sessions/{sid}/free-text", json={"text": " I will audit the model outputs "}).status_code
        == 200
    )
    with client.stream("GET", f"/api/sessions/{sid}/stream") as resp:
        assert resp.status_code == 200
        raw = resp.read().decode("utf-8")
    assert "event: token" in raw
    assert "event: state_patch" in raw
    assert "event: done" in raw


def test_neurobot_chat_not_before_mode() -> None:
    client = TestClient(app)
    sid = client.post("/api/sessions", json={"scenario_slug": "ai_overuse"}).json()["session_id"]
    assert client.post(f"/api/sessions/{sid}/neurobot-chat", json={"message": "Hi"}).status_code == 400


def test_neurobot_chat_mock_reply() -> None:
    client = TestClient(app)
    sid = client.post("/api/sessions", json={"scenario_slug": "ai_overuse"}).json()["session_id"]
    assert client.post(f"/api/sessions/{sid}/answer-mode", json={"mode": "free_text"}).status_code == 200
    r = client.post(f"/api/sessions/{sid}/neurobot-chat", json={"message": "What should I watch for?"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("reply")
    assert isinstance(body.get("neural_score"), int)


def test_outcome_image_endpoint() -> None:
    client = TestClient(app)
    sid = client.post("/api/sessions", json={"scenario_slug": "ai_overuse"}).json()["session_id"]
    assert client.get(f"/api/sessions/{sid}/outcome-image").json()["status"] == "idle"


def test_scenario_art_endpoint() -> None:
    client = TestClient(app)
    r = client.post("/api/sessions", json={"scenario_slug": "ai_overuse"})
    body = r.json()
    sid = body["session_id"]
    assert "scenario_art_status" in body
    assert body["scenario_art_status"] == "idle"
    art = client.get(f"/api/sessions/{sid}/scenario-art").json()
    assert art["status"] == "idle"
    assert art.get("b64") is None
    assert art.get("scenario_art_turn_index") is None


def test_answer_mode_includes_pending_scenario_art_when_images_configured(monkeypatch) -> None:
    async def noop_job(*args: object, **kwargs: object) -> None:
        return None

    monkeypatch.setattr("app.main.is_image_generation_configured", lambda: True)
    monkeypatch.setattr("app.main._run_question_art_job", noop_job)
    client = TestClient(app)
    sid = client.post("/api/sessions", json={"scenario_slug": "ai_overuse"}).json()["session_id"]
    r = client.post(f"/api/sessions/{sid}/answer-mode", json={"mode": "free_text"})
    assert r.status_code == 200
    body = r.json()
    assert body.get("scenario_art_status") == "pending"
    assert body.get("scenario_art_turn_index") == 0
