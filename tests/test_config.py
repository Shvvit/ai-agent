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
