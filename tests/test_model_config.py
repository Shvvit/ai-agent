from __future__ import annotations

import pytest

from config.model_config import ModelConfig


def test_ollama_defaults(monkeypatch):
    for name in ("AI_PROVIDER", "AI_MODEL", "AI_HOST", "AI_BASE_URL", "AI_API_KEY", "OPENROUTER_API_KEY", "AI_TEMPERATURE", "AI_TIMEOUT"):
        monkeypatch.delenv(name, raising=False)
    config = ModelConfig.from_env()
    assert config.provider == "ollama"
    assert config.model == "qwen3:8b"
    assert config.host == "http://127.0.0.1:11434"


def test_openrouter_configuration(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.setenv("AI_MODEL", "openai/gpt-4.1-mini")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    config = ModelConfig.from_env()
    assert config.host == "https://openrouter.ai/api/v1"
    assert config.api_key == "test-key"


def test_openrouter_requires_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(ValueError, match="Brak klucza API"):
        ModelConfig.from_env()


@pytest.mark.parametrize("host", ["", "file:///tmp", "not-a-url"])
def test_invalid_host_is_rejected(monkeypatch, host):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("AI_HOST", host)
    with pytest.raises(ValueError, match="HTTP"):
        ModelConfig.from_env()
