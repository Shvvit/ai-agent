from __future__ import annotations

import os
from urllib.parse import urlsplit
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    """Ustawienia modelu pobierane ze zmiennych środowiskowych."""

    provider: str = "ollama"
    model: str = "qwen3:8b"
    host: str = "http://127.0.0.1:11434"
    temperature: float = 0.2

    @classmethod
    def from_env(cls) -> ModelConfig:
        provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()
        model = os.getenv("AI_MODEL", "qwen3:8b").strip()
        host = os.getenv("AI_HOST", "http://127.0.0.1:11434").strip()
        raw_temperature = os.getenv("AI_TEMPERATURE", "0.2")

        if provider != "ollama":
            raise ValueError(
                f"Nieobsługiwany provider: {provider}. "
                "Obecnie dostępny jest ollama."
            )
        if not model or len(model) > 128 or any(ch in model for ch in "\\r\\n"):
            raise ValueError("AI_MODEL musi mieć od 1 do 128 znaków i nie może zawierać nowych linii.")
        parsed_host = urlsplit(host)
        if parsed_host.scheme not in {"http", "https"} or not parsed_host.hostname:
            raise ValueError("AI_HOST musi być poprawnym adresem HTTP lub HTTPS.")
        if parsed_host.username or parsed_host.password or parsed_host.query or parsed_host.fragment:
            raise ValueError("AI_HOST nie może zawierać danych logowania, query ani fragmentu.")
        try:
            temperature = float(raw_temperature)
        except ValueError as exc:
            raise ValueError("AI_TEMPERATURE musi być liczbą.") from exc
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("AI_TEMPERATURE musi mieścić się w zakresie 0–2.")
        return cls(provider=provider, model=model, host=host, temperature=temperature)
