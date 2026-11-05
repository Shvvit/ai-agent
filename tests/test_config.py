from __future__ import annotations

import pytest

from config.model_config import ModelConfig


def test_model_config_reads_valid_environment(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.setenv("AI_MODEL", "qwen3:8b")
    monkeypatch.setenv("AI_HOST", "http://127.0.0.1:11434")
    monkeypatch.setenv("AI_TEMPERATURE", "0.4")
    config = ModelConfig.from_env()
    assert config.model == "qwen3:8b"
    assert config.temperature == 0.4


@pytest.mark.parametrize("host", ["", "file:///etc/passwd", "ftp://example.com", "http://user:pass@example.com"])
def test_model_config_rejects_invalid_hosts(monkeypatch, host):
    monkeypatch.setenv("AI_HOST", host)
    with pytest.raises(ValueError):
        ModelConfig.from_env()


def test_model_config_rejects_invalid_temperature(monkeypatch):
    monkeypatch.setenv("AI_TEMPERATURE", "3.5")
    with pytest.raises(ValueError):
        ModelConfig.from_env()


def test_model_config_rejects_empty_model(monkeypatch):
    monkeypatch.setenv("AI_MODEL", " ")
    with pytest.raises(ValueError):
        ModelConfig.from_env()


@pytest.mark.parametrize("host", [
    "http://127.0.0.1:invalid",
    "http://127.0.0.1:65536",
    "http://127.0.0.1:0",
])
def test_model_config_rejects_invalid_host_ports(monkeypatch, host):
    monkeypatch.setenv("AI_HOST", host)
    with pytest.raises(ValueError, match="AI_HOST"):
        ModelConfig.from_env()


@pytest.mark.parametrize("base_url", [
    "https://api.example.test:invalid/v1",
    "https://api.example.test:65536/v1",
    "https://api.example.test:0/v1",
])
def test_model_config_rejects_invalid_base_url_ports(monkeypatch, base_url):
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_BASE_URL", base_url)
    with pytest.raises(ValueError, match="AI_BASE_URL"):
        ModelConfig.from_env()

