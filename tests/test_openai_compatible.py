from __future__ import annotations

import httpx
import pytest

from config.model_config import ModelConfig
from models.openai_compatible import OpenAICompatibleModel


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.request = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, headers, json):
        self.request = (url, headers, json)
        return self.response


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def raise_for_status(self):
        if self.status >= 400:
            raise httpx.HTTPStatusError("bad response", request=None, response=None)

    def json(self):
        return self.payload


def test_openrouter_normalizes_tool_calls(monkeypatch):
    response = FakeResponse({
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "write_file", "arguments": '{"path":"a.txt","content":"ok"}'}
                }]
            }
        }]
    })
    fake = FakeClient(response)
    monkeypatch.setattr("models.openai_compatible.httpx.Client", lambda **kwargs: fake)
    config = ModelConfig(
        provider="openrouter",
        model="test/model",
        host="https://openrouter.ai/api/v1",
        api_key="secret",
    )
    result = OpenAICompatibleModel(config).chat([{"role": "user", "content": "create"}], [{"type": "function"}])
    assert result.tool_calls[0].name == "write_file"
    assert result.tool_calls[0].arguments == {"path": "a.txt", "content": "ok"}
    assert fake.request[0].endswith("/chat/completions")
    assert fake.request[1]["Authorization"] == "Bearer secret"


def test_invalid_tool_arguments_raise(monkeypatch):
    response = FakeResponse({
        "choices": [{
            "message": {
                "role": "assistant",
                "tool_calls": [{
                    "id": "call_1",
                    "function": {"name": "write_file", "arguments": "not-json"}
                }]
            }
        }]
    })
    monkeypatch.setattr("models.openai_compatible.httpx.Client", lambda **kwargs: FakeClient(response))
    config = ModelConfig(provider="openrouter", model="test", host="https://openrouter.ai/api/v1", api_key="secret")
    with pytest.raises(ValueError, match="niepoprawny JSON"):
        OpenAICompatibleModel(config).chat([{"role": "user", "content": "x"}])


def test_provider_error_is_not_hidden(monkeypatch):
    response = FakeResponse({}, status=429)
    monkeypatch.setattr("models.openai_compatible.httpx.Client", lambda **kwargs: FakeClient(response))
    config = ModelConfig(provider="openrouter", model="test", host="https://openrouter.ai/api/v1", api_key="secret")
    with pytest.raises(httpx.HTTPStatusError):
        OpenAICompatibleModel(config).chat([{"role": "user", "content": "x"}])
