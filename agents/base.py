from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import ollama

from config.model_config import ModelConfig
from models.chat import ChatResult, ToolCall
from models.openai_compatible import OpenAICompatibleModel
from tools.tool_executor import ToolExecutor


class LanguageModel(Protocol):
    """Minimal interface for pluggable language models."""

    def generate(self, messages: list[dict[str, str]]) -> str:
        ...


@dataclass
class OllamaModel:
    """Adapter for local Ollama models, including native tool calling."""

    config: ModelConfig = field(default_factory=ModelConfig.from_env)

    @property
    def name(self) -> str:
        return self.config.model

    @property
    def host(self) -> str:
        return self.config.host

    def chat(self, messages: list[dict[str, Any]], tools: list[dict] | None = None) -> ChatResult:
        client = ollama.Client(host=self.config.host, timeout=self.config.timeout)
        response = client.chat(
            model=self.config.model,
            messages=messages,
            tools=tools or [],
            options={"temperature": self.config.temperature},
        )
        message = response.message
        calls = []
        for call in getattr(message, "tool_calls", None) or []:
            function = call.function
            arguments = getattr(function, "arguments", {}) or {}
            if not isinstance(arguments, dict):
                raise ValueError("Ollama zwróciła niepoprawne argumenty narzędzia.")
            calls.append(
                ToolCall(
                    name=str(function.name),
                    arguments=arguments,
                    id=str(getattr(call, "id", "") or ""),
                )
            )
        return ChatResult(
            content=message.content or "",
            tool_calls=calls,
            raw_message=message,
        )

    def generate(self, messages: list[dict[str, str]]) -> str:
        return self.chat(messages).content


def build_model(config: ModelConfig | None = None) -> Any:
    """Create a provider adapter from explicit or environment configuration."""
    settings = config or ModelConfig.from_env()
    if settings.provider == "ollama":
        return OllamaModel(settings)
    if settings.provider in {"openrouter", "openai_compatible"}:
        return OpenAICompatibleModel(settings)
    raise ValueError(f"Nieobsługiwany provider: {settings.provider}")


@dataclass
class BaseAgent:
    """Agent with conversation history and a provider-neutral tool loop."""

    model: Any = field(default_factory=build_model)
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
        """Describe the small, allow-listed tool surface exposed to the model."""
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
                    "description": "Uruchamia plik Python z workspace i zwraca wynik oraz kod wyjścia.",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                        "required": ["path"],
                    },
                },
            },
        ]

    def _request(self, messages: list[dict[str, Any]]) -> ChatResult:
        chat = getattr(self.model, "chat", None)
        if callable(chat):
            result = chat(messages, self._tool_definitions())
            if isinstance(result, ChatResult):
                return result
            raise TypeError("Model.chat musi zwracać models.chat.ChatResult.")
        generate = getattr(self.model, "generate", None)
        if callable(generate):
            return ChatResult(content=str(generate(messages)))
        raise TypeError("Model musi implementować chat() lub generate().")

    def run(self, task: str) -> str:
        """Execute a task and handle tool calls from local or cloud providers."""
        task = task.strip()
        if not task:
            raise ValueError("Zadanie nie może być puste.")

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            *self.history,
            {"role": "user", "content": task},
        ]

        calls_executed = 0
        while True:
            result = self._request(messages)
            if not result.tool_calls:
                answer = result.content
                self.history.extend(
                    [
                        {"role": "user", "content": task},
                        {"role": "assistant", "content": answer},
                    ]
                )
                return answer

            # Preserve the provider's assistant tool-call message so that the
            # next request follows that provider's expected conversation format.
            if result.raw_message is not None:
                messages.append(result.raw_message)
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": result.content,
                        "tool_calls": [
                            {
                                "id": call.id,
                                "type": "function",
                                "function": {
                                    "name": call.name,
                                    "arguments": call.arguments,
                                },
                            }
                            for call in result.tool_calls
                        ],
                    }
                )

            for call in result.tool_calls:
                if calls_executed >= self.max_tool_calls:
                    messages.append(
                        {
                            "role": "user",
                            "content": "Osiągnięto limit wywołań narzędzi. Zakończ odpowiedź na podstawie dotychczasowych wyników.",
                        }
                    )
                    break

                try:
                    output = self.tools.execute(call.name, call.arguments)
                except Exception as exc:
                    output = f"Błąd narzędzia: {type(exc).__name__}: {exc}"
                calls_executed += 1

                if getattr(self.model, "config", None) and self.model.config.provider == "ollama":
                    messages.append(
                        {"role": "tool", "tool_name": call.name, "content": output}
                    )
                else:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": call.name,
                            "content": output,
                        }
                    )

            if calls_executed >= self.max_tool_calls:
                # One final no-tools request gives the model a chance to report
                # what happened instead of silently dropping the last result.
                result = self._request(messages)
                answer = result.content or "Zatrzymano zadanie po osiągnięciu limitu narzędzi."
                self.history.extend(
                    [{"role": "user", "content": task}, {"role": "assistant", "content": answer}]
                )
                return answer
