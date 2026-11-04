from __future__ import annotations

import pytest

from config.model_config import ModelConfig
from models.factory import create_model_provider
from models.providers import (
    ModelCapabilities,
    ModelResponse,
    ModelToolCall,
    OpenAICompatibleModel,
)


def test_provider_contract_types_are_provider_neutral():
    call = ModelToolCall(name="read_file", arguments={"path": "notes.txt"}, call_id="call_1")
    response = ModelResponse(content="Odczytuję plik.", tool_calls=(call,))
    assert response.tool_calls[0].call_id == "call_1"
    assert ModelCapabilities(tool_calling=True).tool_calling is True


def test_factory_creates_ollama_adapter():
    from models.providers import OllamaModel

    provider = create_model_provider(ModelConfig(provider="ollama", model="qwen3:8b"))
    assert isinstance(provider, OllamaModel)
    assert provider.provider_name == "ollama"


def test_factory_creates_openai_compatible_adapter():
    config = ModelConfig(
        provider="openai_compatible",
        model="example-model",
        api_key="test-secret",
        base_url="https://api.example.test/v1",
    )
    provider = create_model_provider(config)
    assert isinstance(provider, OpenAICompatibleModel)
    assert provider.provider_name == "openai_compatible"
    assert provider.name == "example-model"
    assert "test-secret" not in repr(config)
    assert "test-secret" not in repr(provider)


def test_openai_compatible_adapter_normalizes_tool_calls(monkeypatch):
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": "",
                        "tool_calls": [{
                            "id": "call_abc",
                            "function": {
                                "name": "read_file",
                                "arguments": "{\"path\": \"hello.txt\"}",
                            },
                        }],
                    }
                }]
            }

    class FakeClient:
        def __init__(self, timeout):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers, json):
            captured["url"] = url
            captured["headers"] = headers
            captured["payload"] = json
            return FakeResponse()

    import httpx

    monkeypatch.setattr(httpx, "Client", FakeClient)
    model = OpenAICompatibleModel(
        model="test-model",
        base_url="https://api.example.test/v1/",
        api_key="secret",
    )
    result = model.chat(
        [
            {"role": "user", "content": "Odczytaj plik."},
            {"role": "tool", "tool_name": "read_file", "tool_call_id": "call_old", "content": "ok"},
        ],
        tools=[{"type": "function", "function": {"name": "read_file"}}],
    )

    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].arguments == {"path": "hello.txt"}
    assert result.tool_calls[0].call_id == "call_abc"
    assert captured["url"] == "https://api.example.test/v1/chat/completions"
    assert captured["payload"]["messages"][1] == {
        "role": "tool",
        "tool_call_id": "call_old",
        "content": "ok",
    }
    assert captured["headers"]["Authorization"] == "Bearer secret"


@pytest.mark.parametrize("base_url", [
    "ftp://api.example.test/v1",
    "https://user:password@api.example.test/v1",
    "https://api.example.test/v1?token=secret",
    "https://api.example.test/v1#fragment",
    "https://api.example.test:invalid/v1",
    "https://api.example.test/v1 with-space",
])
def test_openai_compatible_adapter_rejects_unsafe_or_invalid_base_url(base_url):
    with pytest.raises(ValueError):
        OpenAICompatibleModel(
            model="test-model",
            base_url=base_url,
            api_key="secret",
        )


def test_openai_compatible_adapter_rejects_tool_response_without_call_id():
    model = OpenAICompatibleModel(model="test-model", api_key="secret")
    with pytest.raises(ValueError, match="tool_call_id"):
        model.chat([{"role": "tool", "tool_name": "read_file", "content": "ok"}])


def test_model_config_requires_api_key_for_openai_compatible(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="AI_API_KEY"):
        ModelConfig.from_env()


def test_model_config_reads_openai_compatible_environment(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_API_KEY", "secret")
    monkeypatch.setenv("AI_BASE_URL", "https://api.example.test/v1")
    config = ModelConfig.from_env()
    assert config.provider == "openai_compatible"
    assert config.base_url == "https://api.example.test/v1"
    assert config.api_key == "secret"
