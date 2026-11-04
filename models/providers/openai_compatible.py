"""Adapter dla API zgodnych z formatem OpenAI Chat Completions.

Może obsługiwać OpenAI oraz serwery lokalne/chmurowe implementujące
ten sam kontrakt HTTP. Nie zakłada, że każdy endpoint jest identyczny.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx

from models.providers.base import (
    ModelCapabilities,
    ModelResponse,
    ModelToolCall,
)


@dataclass
class OpenAICompatibleModel:
    """Dostawca modeli przez kompatybilny endpoint Chat Completions."""

    model: str
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    temperature: float = 0.2
    timeout: float = 90.0

    def __post_init__(self) -> None:
        self.model = self.model.strip()
        self.base_url = self.base_url.rstrip("/")
        if not self.model or len(self.model) > 256:
            raise ValueError("Nazwa modelu musi mieć od 1 do 256 znaków.")
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("Adres API musi zaczynać się od http:// lub https://.")
        if not 0.0 <= self.temperature <= 2.0:
            raise ValueError("Temperatura musi mieścić się w zakresie 0–2.")
        if not 1.0 <= self.timeout <= 600.0:
            raise ValueError("Timeout musi mieścić się w zakresie 1–600 sekund.")

    @classmethod
    def from_env(cls) -> OpenAICompatibleModel:
        """Tworzy adapter z ustawień środowiskowych."""

        model = os.getenv("AI_MODEL", "").strip()
        base_url = os.getenv(
            "AI_BASE_URL",
            "https://api.openai.com/v1",
        ).strip()
        api_key = os.getenv("AI_API_KEY", "").strip()
        try:
            temperature = float(os.getenv("AI_TEMPERATURE", "0.2"))
            timeout = float(os.getenv("AI_REQUEST_TIMEOUT", "90"))
        except ValueError as exc:
            raise ValueError("Temperatura i timeout muszą być liczbami.") from exc
        if not api_key:
            raise ValueError("Brakuje AI_API_KEY dla dostawcy API.")
        return cls(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            timeout=timeout,
        )

    @property
    def name(self) -> str:
        return self.model

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(tool_calling=True)

    def generate(self, messages: list[dict]) -> str:
        return self.chat(messages).content

    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
    ) -> ModelResponse:
        normalized_messages: list[dict] = []
        for message in messages:
            item = dict(message)
            if item.get("role") == "tool":
                call_id = item.get("tool_call_id")
                if not call_id:
                    raise ValueError("Odpowiedź narzędzia nie zawiera tool_call_id.")
                item = {
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": item.get("content", ""),
                }
            normalized_messages.append(item)

        payload = {
            "model": self.model,
            "messages": normalized_messages,
            "temperature": self.temperature,
        }
        if tools:
            payload["tools"] = tools

        headers = {"Authorization": f"Bearer {self.api_key}"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise RuntimeError(
                f"Dostawca modelu zwrócił HTTP {status}."
            ) from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"Nie udało się połączyć z dostawcą modelu: {type(exc).__name__}."
            ) from exc
        except ValueError as exc:
            raise RuntimeError("Dostawca zwrócił niepoprawny JSON.") from exc

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Odpowiedź dostawcy nie zawiera choices[0].message.") from exc

        content = message.get("content") or ""
        if not isinstance(content, str):
            raise RuntimeError("Treść odpowiedzi modelu ma nieobsługiwany format.")

        calls: list[ModelToolCall] = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            name = function.get("name")
            raw_arguments = function.get("arguments", "{}")
            if not isinstance(name, str) or not name:
                raise RuntimeError("Model zwrócił wywołanie narzędzia bez nazwy.")
            if isinstance(raw_arguments, str):
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"Model zwrócił niepoprawne argumenty narzędzia: {name}."
                    ) from exc
            else:
                arguments = raw_arguments
            if not isinstance(arguments, dict):
                raise RuntimeError(
                    f"Argumenty narzędzia {name} nie są obiektem JSON."
                )
            calls.append(ModelToolCall(name=name, arguments=arguments, call_id=item.get("id")))

        return ModelResponse(content=content, tool_calls=tuple(calls))
