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
