from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import ollama

from config.model_config import ModelConfig
from tools.tool_executor import ToolExecutor


class LanguageModel(Protocol):
    """Interfejs umożliwiający podłączanie różnych modeli AI."""

    def generate(self, messages: list[dict[str, str]]) -> str:
        ...


@dataclass
class OllamaModel:
    """Adapter do lokalnych modeli Ollama."""

    config: ModelConfig = field(default_factory=ModelConfig.from_env)

    @property
    def name(self) -> str:
        return self.config.model

    @property
    def host(self) -> str:
        return self.config.host

    def generate(self, messages: list[dict[str, str]]) -> str:
        client = ollama.Client(host=self.config.host)
        response = client.chat(
            model=self.config.model,
            messages=messages,
            options={"temperature": self.config.temperature},
        )
        return response.message.content or ""


@dataclass
class BaseAgent:
    """Agent z historią rozmowy i narzędziami do pracy z plikami."""

    model: LanguageModel = field(default_factory=OllamaModel)
    system_prompt: str = (
        "Jesteś agentem Własne AI. Odpowiadasz po polsku. "
        "Realizujesz zadania za pomocą dostępnych narzędzi, gdy jest to "
        "możliwe. Po wykonaniu działania sprawdzasz jego wynik. "
        "Nie twierdź, że wykonałeś coś, czego nie zrobiłeś."
    )
    history: list[dict[str, str]] = field(default_factory=list)
    tools: ToolExecutor = field(default_factory=ToolExecutor)
    max_tool_calls: int = 5

    def _tool_definitions(self) -> list[dict]:
        """Opis narzędzi udostępnianych modelowi."""

        return [
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Zapisuje plik wewnątrz workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Odczytuje plik z workspace.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_python",
                    "description": (
                        "Uruchamia plik Python z workspace i zwraca "
                        "wynik wykonania oraz kod wyjścia."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Ścieżka względna do pliku .py",
                            }
                        },
                        "required": ["path"],
                    },
                },
            },
        ]

    def run(self, task: str) -> str:
        """Wykonuje zadanie, obsługując wywołania narzędzi przez Ollama."""

        task = task.strip()
        if not task:
            raise ValueError("Zadanie nie może być puste.")

        if not isinstance(self.model, OllamaModel):
            messages = [
                {"role": "system", "content": self.system_prompt},
                *self.history,
                {"role": "user", "content": task},
            ]
            answer = self.model.generate(messages)
            self.history.extend(
                [
                    {"role": "user", "content": task},
                    {"role": "assistant", "content": answer},
                ]
            )
            return answer

        client = ollama.Client(host=self.model.config.host)
        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history,
            {"role": "user", "content": task},
        ]

        for _ in range(self.max_tool_calls + 1):
            response = client.chat(
                model=self.model.config.model,
                messages=messages,
                tools=self._tool_definitions(),
                options={"temperature": self.model.config.temperature},
            )
            message = response.message

            if not message.tool_calls:
                answer = message.content or ""
                self.history.extend(
                    [
                        {"role": "user", "content": task},
                        {"role": "assistant", "content": answer},
                    ]
                )
                return answer

            messages.append(message)

            for call in message.tool_calls:
                name = call.function.name
                arguments = call.function.arguments

                try:
                    result = self.tools.execute(name, arguments)
                except Exception as exc:
                    result = f"Błąd narzędzia: {type(exc).__name__}: {exc}"

                messages.append(
                    {"role": "tool", "tool_name": name, "content": result}
                )

        return (
            "Zatrzymano zadanie po osiągnięciu limitu wywołań narzędzi. "
            "Sprawdź dotychczasowe wyniki przed ponowną próbą."
        )
