from __future__ import annotations

import importlib

from fastapi.testclient import TestClient


def test_web_home_and_health(monkeypatch, tmp_path):
    module = importlib.import_module("api.app")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "agent.sqlite3")
    monkeypatch.setattr(module, "WORKSPACE", tmp_path / "workspace")
    with TestClient(module.app) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert "Własne AI" in home.text
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"


def test_conversation_lifecycle(monkeypatch, tmp_path):
    module = importlib.import_module("api.app")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "agent.sqlite3")
    monkeypatch.setattr(module, "WORKSPACE", tmp_path / "workspace")
    with TestClient(module.app) as client:
        created = client.post("/api/conversations", json={"title": "Test"})
        assert created.status_code == 200
        conversation_id = created.json()["id"]
        listed = client.get("/api/conversations")
        assert listed.status_code == 200
        assert any(item["id"] == conversation_id for item in listed.json()["conversations"])
        messages = client.get(f"/api/conversations/{conversation_id}/messages")
        assert messages.status_code == 200
        assert messages.json()["messages"] == []
        deleted = client.delete(f"/api/conversations/{conversation_id}")
        assert deleted.status_code == 200
        assert client.get(f"/api/conversations/{conversation_id}/messages").status_code == 404


def test_chat_uses_agent_and_persists_messages(monkeypatch, tmp_path):
    module = importlib.import_module("api.app")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "agent.sqlite3")
    monkeypatch.setattr(module, "WORKSPACE", tmp_path / "workspace")

    class FakeAgent:
        def __init__(self, **kwargs):
            self.history = kwargs["history"]

        def run(self, message):
            assert message == "Cześć"
            return "Witaj!"

    monkeypatch.setattr(module, "BaseAgent", FakeAgent)
    with TestClient(module.app) as client:
        response = client.post("/api/chat", json={"message": "Cześć"})
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Witaj!"
        messages = client.get(f"/api/conversations/{data['conversation_id']}/messages").json()["messages"]
        assert [item["role"] for item in messages] == ["user", "assistant"]
        assert [item["content"] for item in messages] == ["Cześć", "Witaj!"]


def test_chat_rejects_empty_message():
    module = importlib.import_module("api.app")
    with TestClient(module.app) as client:
        response = client.post("/api/chat", json={"message": "   "})
        assert response.status_code == 422


def test_memory_api_lifecycle(monkeypatch, tmp_path):
    module = importlib.import_module("api.app")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "agent.sqlite3")
    with TestClient(module.app) as client:
        created = client.post("/api/memory", json={"content": "Używam lokalnego modelu Qwen."})
        assert created.status_code == 200
        memory_id = created.json()["memory"]["id"]
        listed = client.get("/api/memory")
        assert listed.status_code == 200
        assert listed.json()["memories"][0]["content"] == "Używam lokalnego modelu Qwen."
        deleted = client.delete(f"/api/memory/{memory_id}")
        assert deleted.status_code == 200
        assert client.get("/api/memory").json()["memories"] == []


def test_memory_api_rejects_empty_content(monkeypatch, tmp_path):
    module = importlib.import_module("api.app")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "agent.sqlite3")
    with TestClient(module.app) as client:
        response = client.post("/api/memory", json={"content": "  "})
        assert response.status_code == 422



def test_memory_api_clear_all(monkeypatch, tmp_path):
    module = importlib.import_module("api.app")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "agent.sqlite3")
    with TestClient(module.app) as client:
        for content in ("first fact", "second fact"):
            assert client.post("/api/memory", json={"content": content}).status_code == 200
        cleared = client.delete("/api/memory")
        assert cleared.status_code == 200
        assert cleared.json()["deleted"] == 2
        assert client.get("/api/memory").json()["memories"] == []


def test_memory_slash_commands(monkeypatch, tmp_path):
    module = importlib.import_module("api.app")
    monkeypatch.setattr(module, "DB_PATH", tmp_path / "agent.sqlite3")

    class UnexpectedAgent:
        def __init__(self, **kwargs):
            raise AssertionError("Slash commands must not call the language model.")

    monkeypatch.setattr(module, "BaseAgent", UnexpectedAgent)
    with TestClient(module.app) as client:
        saved = client.post("/api/chat", json={"message": "/remember I use Qwen locally"})
        assert saved.status_code == 200
        assert "Zapamiętano" in saved.json()["answer"]

        listed = client.post("/api/chat", json={"message": "/memory"})
        assert listed.status_code == 200
        assert "I use Qwen locally" in listed.json()["answer"]

        cleared = client.post("/api/chat", json={"message": "/clear_memory"})
        assert cleared.status_code == 200
        assert "Usunięto wpisów: 1" in cleared.json()["answer"]

        empty = client.post("/api/chat", json={"message": "/memory"})
        assert empty.status_code == 200
        assert "Pamięć jest pusta" in empty.json()["answer"]
