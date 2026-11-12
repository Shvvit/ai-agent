from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ModelConfig:
    """Provider-neutral model settings loaded from environment variables."""

    provider: str = "ollama"
    model: str = "qwen3:8b"
    host: str = "http://127.0.0.1:11434"
    temperature: float = 0.2
    api_key: str | None = None
    timeout: float = 120.0

    @classmethod
    def from_env(cls) -> "ModelConfig":
        provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()
        model = os.getenv("AI_MODEL", "qwen3:8b").strip()
        raw_temperature = os.getenv("AI_TEMPERATURE", "0.2")
        raw_timeout = os.getenv("AI_TIMEOUT", "120")
        api_key = os.getenv("AI_API_KEY") or os.getenv("OPENROUTER_API_KEY")

        defaults = {
            "ollama": "http://127.0.0.1:11434",
            "openrouter": "https://openrouter.ai/api/v1",
            "openai_compatible": "https://api.openai.com/v1",
        }
        if provider not in defaults:
            raise ValueError(
                f"Nieobsługiwany provider: {provider}. "
                f"Dostępne: {', '.join(defaults)}."
            )
        if not model:
            raise ValueError("AI_MODEL nie może być pusty.")

        host = os.getenv("AI_HOST", os.getenv("AI_BASE_URL", defaults[provider])).strip().rstrip("/")
        parsed = urlparse(host)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("AI_HOST / AI_BASE_URL musi być poprawnym adresem HTTP(S).")

        try:
            temperature = float(raw_temperature)
        except ValueError as exc:
            raise ValueError("AI_TEMPERATURE musi być liczbą.") from exc
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("AI_TEMPERATURE musi mieścić się w zakresie 0–2.")

        try:
            timeout = float(raw_timeout)
        except ValueError as exc:
            raise ValueError("AI_TIMEOUT musi być liczbą sekund.") from exc
        if not 1.0 <= timeout <= 600.0:
            raise ValueError("AI_TIMEOUT musi mieścić się w zakresie 1–600 sekund.")

        if provider in {"openrouter", "openai_compatible"} and not api_key:
            raise ValueError(
                "Brak klucza API. Ustaw AI_API_KEY (lub OPENROUTER_API_KEY dla OpenRouter)."
            )

        return cls(
            provider=provider,
            model=model,
            host=host,
            temperature=temperature,
            api_key=api_key,
            timeout=timeout,
        )
