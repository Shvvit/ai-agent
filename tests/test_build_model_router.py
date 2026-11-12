from __future__ import annotations

import json

import pytest

import agents.base as base_module
from config.model_config import ModelConfig
from models.chat import ChatResult
from models.router import ModelRouter


class FakeAdapter:
    def __init__(self, label):
        self.label = label

    def chat(self, messages, tools):
        return ChatResult(content=self.label)


def test_build_model_can_create_auto_router(monkeypatch):
    monkeypatch.setenv("AI_ROUTING", "auto")
    monkeypatch.setenv("AI_ROUTER_PRIMARY_CAPABILITIES", "chat,tool_calling,code,reasoning")
    monkeypatch.setenv("CLOUD_TEST_KEY", "test-secret")
    monkeypatch.setenv("AI_ROUTER_CANDIDATES", json.dumps([{
        "name": "cloud-reasoner",
        "provider": "openrouter",
        "model": "test/reasoner",
        "api_key_env": "CLOUD_TEST_KEY",
        "capabilities": ["chat", "tool_calling", "code", "reasoning"],
        "speed_score": 2,
        "reasoning_score": 5,
        "cost_score": 1,
    }]))
    monkeypatch.setattr(base_module, "OllamaModel", lambda config: FakeAdapter("local"))
    monkeypatch.setattr(base_module, "OpenAICompatibleModel", lambda config: FakeAdapter("cloud"))
    router = base_module.build_model(ModelConfig())
    assert isinstance(router, ModelRouter)
    simple = router.chat([{"role": "user", "content": "Cześć"}])
    complex_result = router.chat([{"role": "user", "content": "Przeanalizuj i zaprojektuj architekturę"}])
    assert simple.content == "local"
    assert complex_result.content == "cloud"
    assert router.last_selected == "cloud-reasoner"


def test_auto_router_requires_explicit_candidate_capabilities(monkeypatch):
    monkeypatch.setenv("AI_ROUTING", "auto")
    monkeypatch.setenv("AI_ROUTER_CANDIDATES", json.dumps([{"provider": "ollama", "model": "qwen3:8b"}]))
    monkeypatch.setattr(base_module, "OllamaModel", lambda config: FakeAdapter("local"))
    with pytest.raises(ValueError, match="capabilities"):
        base_module.build_model(ModelConfig())


def test_router_rejects_missing_candidate_api_key(monkeypatch):
    monkeypatch.setenv("AI_ROUTING", "auto")
    monkeypatch.delenv("MISSING_CLOUD_KEY", raising=False)
    monkeypatch.setenv("AI_ROUTER_CANDIDATES", json.dumps([{
        "provider": "openrouter",
        "model": "test/model",
        "api_key_env": "MISSING_CLOUD_KEY",
        "capabilities": ["chat", "tool_calling"],
    }]))
    monkeypatch.setattr(base_module, "OllamaModel", lambda config: FakeAdapter("local"))
    with pytest.raises(ValueError, match="Brak klucza"):
        base_module.build_model(ModelConfig())


def test_invalid_routing_mode_is_rejected(monkeypatch):
    monkeypatch.setenv("AI_ROUTING", "magic")
    with pytest.raises(ValueError, match="AI_ROUTING"):
        base_module.build_model(ModelConfig())
