from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from config.model_config import ModelConfig
from models.chat import ChatResult, ToolCall


@dataclass
class OpenAICompatibleModel:
    """OpenAI Chat Completions adapter for OpenRouter and compatible APIs."""

    config: ModelConfig = field(default_factory=ModelConfig.from_env)

    @property
    def name(self) -> str:
        return self.config.model

    def chat(self, messages: list[dict[str, Any]], tools: list[dict] | None = None) -> ChatResult:
        if not self.config.api_key:
            raise ValueError("Brak klucza API dla wybranego providera.")

        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.provider == "openrouter":
            headers["HTTP-Referer"] = "https://github.com/Shvvit/ai-agent"
            headers["X-Title"] = "Wlasne AI"

        url = f"{self.config.host}/chat/completions"
        with httpx.Client(timeout=self.config.timeout) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("Provider zwrócił odpowiedź bez choices[0].message.") from exc

        calls: list[ToolCall] = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            raw_arguments = function.get("arguments", {})
            if isinstance(raw_arguments, str):
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Model zwrócił niepoprawny JSON argumentów narzędzia {function.get('name', '?')}."
                    ) from exc
            else:
                arguments = raw_arguments
            if not isinstance(arguments, dict):
                raise ValueError("Argumenty wywołania narzędzia muszą być obiektem JSON.")
            name = str(function.get("name") or "").strip()
            if not name:
                raise ValueError("Model zwrócił wywołanie narzędzia bez nazwy.")
            calls.append(ToolCall(name=name, arguments=arguments, id=str(item.get("id") or "")))

        return ChatResult(
            content=str(message.get("content") or ""),
            tool_calls=calls,
            raw_message=message,
        )

    def generate(self, messages: list[dict[str, str]]) -> str:
        """Compatibility helper for callers that only need plain text."""
        return self.chat(messages).content
