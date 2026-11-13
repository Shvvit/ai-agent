"""Adapter lokalnego serwera Ollama."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import ollama

from config.model_config import ModelConfig
from models.providers.base import (
    ModelCapabilities,
    ModelResponse,
    ModelToolCall,
)


@dataclass
class OllamaModel:
    """Tłumaczy SDK Ollama na wspólny kontrakt dostawców modeli."""

    config: ModelConfig = field(default_factory=ModelConfig.from_env)

    @property
    def name(self) -> str:
        return self.config.model

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def host(self) -> str:
        return self.config.host

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(tool_calling=True)

    def generate(self, messages: list[dict[str, Any]]) -> str:
        return self.chat(messages).content

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        client = ollama.Client(host=self.config.host)
        provider_messages: list[dict[str, Any]] = []
        for message in messages:
            item = dict(message)
            if item.get("role") == "tool":
                item.pop("tool_call_id", None)
            if item.get("role") == "assistant" and item.get("tool_calls"):
                item["tool_calls"] = [
                    {
                        "type": "function",
                        "function": call.get("function", {}),
                    }
                    for call in item["tool_calls"]
                ]
            provider_messages.append(item)

        response = client.chat(
            model=self.config.model,
            messages=provider_messages,
            tools=tools or [],
            options={"temperature": self.config.temperature},
        )
        message = response.message
        calls: list[ModelToolCall] = []
        for call in message.tool_calls or []:
            arguments = call.function.arguments or {}
            if not isinstance(arguments, dict):
                arguments = {}
            calls.append(
                ModelToolCall(
                    name=str(call.function.name),
                    arguments=arguments,
                    call_id=getattr(call, "id", None),
                )
            )
        return ModelResponse(
            content=message.content or "",
            tool_calls=tuple(calls),
        )
