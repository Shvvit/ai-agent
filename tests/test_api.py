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
