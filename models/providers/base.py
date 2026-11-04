"""Wspólny kontrakt dostawców modeli dla Własne AI.

Moduły agenta nie powinny zależeć od konkretnego SDK (np. ollama).
Każdy adapter dostawcy tłumaczy własne API na poniższe typy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ModelToolCall:
    """Znormalizowane wywołanie narzędzia zwrócone przez model."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    """Jednolita odpowiedź modelu niezależna od dostawcy."""

    content: str = ""
    tool_calls: tuple[ModelToolCall, ...] = ()


@dataclass(frozen=True)
class ModelCapabilities:
    """Deklarowane możliwości adaptera/modelu.

    Są to deklaracje dostawcy lub konfiguracji, a nie wynik benchmarku.
    """

    tool_calling: bool = False
    streaming: bool = False
    vision: bool = False
    audio_input: bool = False
    audio_output: bool = False
    video_input: bool = False
    context_window: int | None = None


@runtime_checkable
class ModelProvider(Protocol):
    """Kontrakt adaptera modelu używany przez rdzeń agenta."""

    @property
    def name(self) -> str:
        """Nazwa modelu lub identyfikator skonfigurowanego endpointu."""

    @property
    def provider_name(self) -> str:
        """Stabilny identyfikator dostawcy, np. 'ollama' lub 'openai'."""

    @property
    def capabilities(self) -> ModelCapabilities:
        """Możliwości dostępne dla aktualnej konfiguracji."""

    def generate(self, messages: list[dict[str, Any]]) -> str:
        """Generuje zwykłą odpowiedź tekstową."""

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        """Prowadzi turę rozmowy i zwraca znormalizowane wywołania narzędzi."""
