from __future__ import annotations

import os
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
        if not model:
            raise ValueError("AI_MODEL nie może być pusty.")
        try:
            temperature = float(raw_temperature)
        except ValueError as exc:
            raise ValueError("AI_TEMPERATURE musi być liczbą.") from exc
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("AI_TEMPERATURE musi mieścić się w zakresie 0–2.")
        return cls(provider=provider, model=model, host=host, temperature=temperature)
