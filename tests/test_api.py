from __future__ import annotations

from fastapi.testclient import TestClient

from api.app import create_app


def test_health_and_session_lifecycle(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        health = client.get("/global/health")
        assert health.status_code == 200
        assert health.json()["healthy"] is True
        assert health.json()["backend"] == "wlasneai"

        created = client.post("/session", json={"title": "Test session"})
        assert created.status_code == 200
        session = created.json()
        assert session["title"] == "Test session"
        assert session["projectID"] == "wlasneai"

        listed = client.get("/session")
        assert listed.status_code == 200
        assert any(item["id"] == session["id"] for item in listed.json())

        fetched = client.get(f"/session/{session['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == session["id"]

        deleted = client.delete(f"/session/{session['id']}")
        assert deleted.status_code == 200
        assert client.get(f"/session/{session['id']}").status_code == 404


def test_opencode_server_info_contract(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app, base_url="http://127.0.0.1:43123") as client:
        response = client.get("/api/info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["version"] == "0.1.0"
    assert isinstance(payload["pid"], int) and payload["pid"] > 0
    assert payload["urls"] == ["http://127.0.0.1:43123"]
    assert payload["paths"] == {"tmp": str(tmp_path / "tmp")}


def test_opencode_project_and_location_contract(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        projects = client.get("/api/project")
        location = client.get("/api/location")

    assert projects.status_code == 200
    project = projects.json()[0]
    assert project["id"] == "wlasneai"
    assert project["canonical"] == str(tmp_path / "workspace")
    assert set(project["time"]) == {"created", "updated", "active"}
    assert isinstance(project["sandboxes"], list)

    assert location.status_code == 200
    assert location.json() == {
        "directory": str(tmp_path / "workspace"),
        "project": {
            "id": "wlasneai",
            "directory": str(tmp_path / "workspace"),
            "canonical": str(tmp_path / "workspace"),
        },
    }


def test_opencode_session_lifecycle_contract(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        created = client.post("/api/session", json={"title": "OpenCode session"})
        assert created.status_code == 200
        session = created.json()["data"]
        assert session["id"].startswith("ses")
        assert session["projectID"] == "wlasneai"
        assert session["title"] == "OpenCode session"
        assert session["location"]["directory"] == str(tmp_path / "workspace")
        assert session["tokens"] == {
            "input": 0,
            "output": 0,
            "reasoning": 0,
            "cache": {"read": 0, "write": 0},
        }

        session_id = session["id"]
        listed = client.get("/api/session")
        assert listed.status_code == 200
        assert listed.json()["data"] == [session]
        assert listed.json()["cursor"] == {}
        assert client.get(f"/api/session/{session_id}").json()["data"] == session
        assert client.delete(f"/api/session/{session_id}").status_code == 204
        assert client.get(f"/api/session/{session_id}").status_code == 404


def test_opencode_agent_provider_model_and_boot_catalog_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("AI_MODEL", "qwen3:8b")
    app = create_app(tmp_path)
    directory = str(tmp_path / "workspace")
    with TestClient(app) as client:
        config = client.get("/api/config").json()
        agents = client.get("/api/agent").json()
        commands = client.get("/api/command").json()
        providers = client.get("/api/provider").json()
        models = client.get("/api/model").json()
        default_model = client.get("/api/model/default").json()

    assert config == {"location": {"directory": directory}, "data": []}
    assert commands == {"location": {"directory": directory}, "data": []}
    assert agents["location"]["directory"] == directory
    assert agents["data"][0]["id"] == "wlasneai"
    assert agents["data"][0]["request"] == {"settings": {}, "headers": {}, "body": {}}
    assert agents["data"][0]["mode"] == "primary"
    assert agents["data"][0]["permissions"] == []

    assert providers["location"]["directory"] == directory
    assert {item["id"] for item in providers["data"]} == {"ollama", "openrouter", "openai_compatible"}
    assert models["location"]["directory"] == directory
    model = models["data"][0]
    assert model["id"] == "qwen3:8b"
    assert model["providerID"] == "ollama"
    assert model["capabilities"] == {"tools": True, "input": ["text"], "output": ["text"]}
    assert default_model["data"] == model


def test_opencode_message_history_contract(tmp_path, monkeypatch):
    from api import app as api_app

    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("AI_MODEL", "qwen3:8b")

    class FakeAgent:
        def __init__(self, **kwargs):
            pass

        def run(self, prompt):
            return f"Odpowiedź: {prompt}"

    monkeypatch.setattr(api_app, "BaseAgent", FakeAgent)
    monkeypatch.setattr(api_app, "build_model", lambda config: object())
    app = create_app(tmp_path)
    with TestClient(app) as client:
        session_id = client.post("/api/session", json={}).json()["data"]["id"]
        client.post(
            f"/session/{session_id}/message",
            json={"parts": [{"type": "text", "text": "Cześć"}]},
        )
        response = client.get(f"/api/session/{session_id}/message")

    assert response.status_code == 200
    messages = response.json()["data"]
    assert [item["type"] for item in messages] == ["user", "assistant"]
    assert messages[0]["text"] == "Cześć"
    assert messages[1]["content"] == [{"type": "text", "text": "Odpowiedź: Cześć"}]
    assert messages[1]["model"] == {"id": "qwen3:8b", "providerID": "ollama"}


def test_opencode_prompt_runs_agent_and_emits_protocol_events(tmp_path, monkeypatch):
    from api import app as api_app

    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("AI_MODEL", "qwen3:8b")

    class FakeAgent:
        def __init__(self, **kwargs):
            pass

        def run(self, prompt):
            return f"Odpowiedź: {prompt}"

    monkeypatch.setattr(api_app, "BaseAgent", FakeAgent)
    monkeypatch.setattr(api_app, "build_model", lambda config: object())
    app = create_app(tmp_path)
    events = []

    async def capture_event(event):
        events.append(event)

    app.state.event_hub.publish = capture_event
    with TestClient(app) as client:
        session_id = client.post("/api/session", json={}).json()["data"]["id"]
        response = client.post(
            f"/api/session/{session_id}/prompt",
            json={"id": "msg_test-prompt", "text": "Cześć"},
        )
        history = client.get(f"/api/session/{session_id}/message").json()["data"]

    assert response.status_code == 200
    assert response.json()["data"]["id"] == "msg_test-prompt"
    assert [item["type"] for item in history] == ["user", "assistant"]
    assert history[1]["content"] == [{"type": "text", "text": "Odpowiedź: Cześć"}]
    assert [item["type"] for item in events] == [
        "session.inbox.enqueued",
        "session.inbox.delivered",
        "session.execution.started",
        "session.step.started",
        "session.text.started",
        "session.text.delta",
        "session.text.ended",
        "session.step.ended",
        "session.execution.succeeded",
    ]
    durable = [item for item in events if item["type"] != "session.text.delta"]
    assert [item["durable"]["seq"] for item in durable] == list(range(1, len(durable) + 1))


def test_message_endpoint_rejects_unknown_session(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        response = client.post(
            "/session/missing/message",
            json={"parts": [{"type": "text", "text": "Hello"}]},
        )
        assert response.status_code == 404


def test_message_endpoint_rejects_empty_prompt(tmp_path):
    app = create_app(tmp_path)
    with TestClient(app) as client:
        session = client.post("/session", json={}).json()
        response = client.post(
            f"/session/{session['id']}/message",
            json={"parts": [{"type": "text", "text": "  "}]},
        )
        assert response.status_code == 400

def test_embedded_bridge_starts_on_loopback_and_stops(tmp_path, monkeypatch):
    from api import server

    monkeypatch.setattr(server, "create_app", lambda: create_app(tmp_path))
    bridge = server.start_bridge(timeout=5)
    try:
        assert bridge.host == "127.0.0.1"
        assert bridge.port > 0
        assert bridge.base_url.startswith("http://127.0.0.1:")
        assert __import__("os").environ["OPENCODE_SERVER_URL"] == bridge.base_url
    finally:
        bridge.stop()
    assert not bridge.thread.is_alive()
