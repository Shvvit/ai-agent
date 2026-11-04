"""Fabryka adapterów dostawców modeli."""

from __future__ import annotations

from agents.base import OllamaModel
from config.model_config import ModelConfig
from models.providers import ModelProvider, OpenAICompatibleModel


def create_model_provider(config: ModelConfig) -> ModelProvider:
    """Buduje adapter wskazany przez konfigurację.

    Fabryka jest jedynym miejscem, w którym aplikacja mapuje nazwę
    dostawcy na konkretną implementację.
    """

    if config.provider == "ollama":
        return OllamaModel(config=config)
    if config.provider == "openai_compatible":
        return OpenAICompatibleModel(
            model=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
            temperature=config.temperature,
            timeout=config.request_timeout,
        )
    raise ValueError(f"Nieobsługiwany provider: {config.provider}")
