from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from typing import Any, Protocol

import ollama

from config.model_config import ModelConfig
from models.chat import ChatResult, ToolCall
from models.openai_compatible import OpenAICompatibleModel
from models.router import ModelRoute, ModelRouter
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


def _create_model_adapter(settings: ModelConfig) -> Any:
    if settings.provider == "ollama":
        return OllamaModel(settings)
    if settings.provider in {"openrouter", "openai_compatible"}:
        return OpenAICompatibleModel(settings)
    raise ValueError(f"Nieobsługiwany provider: {settings.provider}")


def _build_auto_router(primary: ModelConfig) -> ModelRouter:
    """Build routes from environment JSON; API secrets are read by env-var name."""
    raw_capabilities = os.getenv(
        "AI_ROUTER_PRIMARY_CAPABILITIES",
        "chat,tool_calling,code,reasoning",
    )
    primary_capabilities = frozenset(
        item.strip() for item in raw_capabilities.split(",") if item.strip()
    )
    allowed = {"chat", "tool_calling", "code", "reasoning", "vision"}
    if not primary_capabilities or not primary_capabilities.issubset(allowed):
        raise ValueError("AI_ROUTER_PRIMARY_CAPABILITIES zawiera nieobsługiwane możliwości.")

    routes = [
        ModelRoute(
            name=f"{primary.provider}:{primary.model}",
            model=_create_model_adapter(primary),
            capabilities=primary_capabilities,
            speed_score=3.0,
            reasoning_score=3.0,
            cost_score=3.0,
            context_window=8192,
        )
    ]

    raw_candidates = os.getenv("AI_ROUTER_CANDIDATES", "[]")
    try:
        candidates = json.loads(raw_candidates)
    except json.JSONDecodeError as exc:
        raise ValueError("AI_ROUTER_CANDIDATES musi być poprawną tablicą JSON.") from exc
    if not isinstance(candidates, list) or len(candidates) > 8:
        raise ValueError("AI_ROUTER_CANDIDATES musi zawierać maksymalnie 8 modeli.")

    for index, item in enumerate(candidates):
        if not isinstance(item, dict):
            raise ValueError(f"AI_ROUTER_CANDIDATES[{index}] musi być obiektem.")
        allowed_keys = {
            "provider", "model", "host", "api_key_env", "capabilities",
            "speed_score", "reasoning_score", "cost_score", "context_window",
            "enabled", "name",
        }
        unknown = set(item) - allowed_keys
        if unknown:
            raise ValueError(
                f"Nieznane pola kandydata modelu: {', '.join(sorted(unknown))}."
            )

        provider = str(item.get("provider", "")).strip().lower()
        model_name = str(item.get("model", "")).strip()
        if provider not in {"ollama", "openrouter", "openai_compatible"} or not model_name:
            raise ValueError(f"Kandydat {index} wymaga poprawnych provider i model.")
        capabilities = item.get("capabilities")
        if (
            not isinstance(capabilities, list)
            or not capabilities
            or any(not isinstance(value, str) or value not in allowed for value in capabilities)
            or "chat" not in capabilities
        ):
            raise ValueError(
                f"Kandydat {index} musi jawnie zadeklarować capabilities, w tym chat."
            )

        defaults = {
            "ollama": "http://127.0.0.1:11434",
            "openrouter": "https://openrouter.ai/api/v1",
            "openai_compatible": "https://api.openai.com/v1",
        }
        host = str(item.get("host") or defaults[provider]).rstrip("/")
        if not host.startswith(("http://", "https://")):
            raise ValueError(f"Niepoprawny host dla kandydata {model_name}.")
        api_key = None
        if provider != "ollama":
            key_env = str(
                item.get(
                    "api_key_env",
                    "OPENROUTER_API_KEY" if provider == "openrouter" else "AI_API_KEY",
                )
            )
            api_key = os.getenv(key_env)
            if not api_key:
                raise ValueError(
                    f"Brak klucza w zmiennej {key_env} dla modelu {model_name}."
                )

        candidate_config = ModelConfig(
            provider=provider,
            model=model_name,
            host=host,
            temperature=primary.temperature,
            api_key=api_key,
            timeout=primary.timeout,
        )
        route_name = str(item.get("name") or f"{provider}:{model_name}")
        routes.append(
            ModelRoute(
                name=route_name,
                model=_create_model_adapter(candidate_config),
                capabilities=frozenset(capabilities),
                speed_score=float(item.get("speed_score", 3.0)),
                reasoning_score=float(item.get("reasoning_score", 3.0)),
                cost_score=float(item.get("cost_score", 3.0)),
                context_window=int(item.get("context_window", 8192)),
                enabled=bool(item.get("enabled", True)),
            )
        )

    return ModelRouter(routes=routes, fallback_name=routes[0].name)


def build_model(config: ModelConfig | None = None) -> Any:
    """Create one provider adapter or an optional capability-aware model router."""
    settings = config or ModelConfig.from_env()
    routing_mode = os.getenv("AI_ROUTING", "off").strip().lower()
    if routing_mode in {"auto", "automatic"}:
        return _build_auto_router(settings)
    if routing_mode not in {"", "off", "none", "disabled"}:
        raise ValueError("AI_ROUTING musi mieć wartość off lub auto.")
    return _create_model_adapter(settings)


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
    enable_tools: bool = True
    enable_delegation: bool = True

    def __post_init__(self) -> None:
        if self.max_tool_calls < 1:
            raise ValueError("max_tool_calls musi być większe od zera.")

    def _tool_definitions(self) -> list[dict]:
        """Describe the allow-listed tools exposed to the model."""
        if not self.enable_tools:
            return []
        definitions = [
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
        if self.enable_delegation:
            definitions.extend([
                {
                    "type": "function",
                    "function": {
                        "name": "delegate_task",
                        "description": "Przekazuje analizę wyspecjalizowanemu agentowi bez dostępu do narzędzi komputera.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["researcher", "programmer", "reviewer"]},
                                "task": {"type": "string"},
                            },
                            "required": ["role", "task"],
                            "additionalProperties": False,
                        },
                    },
                },
                {
                    "type": "function",
                    "function": {
                        "name": "delegate_tasks",
                        "description": "Deleguje do trzech niezależnych analiz do wyspecjalizowanych agentów.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "tasks": {
                                    "type": "array",
                                    "minItems": 1,
                                    "maxItems": 3,
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "role": {"type": "string", "enum": ["researcher", "programmer", "reviewer"]},
                                            "task": {"type": "string"},
                                        },
                                        "required": ["role", "task"],
                                        "additionalProperties": False,
                                    },
                                }
                            },
                            "required": ["tasks"],
                            "additionalProperties": False,
                        },
                    },
                },
            ])
        return definitions

    def _request(self, messages: list[dict[str, Any]], *, allow_tools: bool = True) -> ChatResult:
        chat = getattr(self.model, "chat", None)
        if callable(chat):
            result = chat(messages, self._tool_definitions() if allow_tools and self.enable_tools else [])
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
            if not result.tool_calls or not self.enable_tools:
                answer = result.content or "Model nie zwrócił odpowiedzi tekstowej."
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

            limit_reached = False
            is_ollama = (
                getattr(getattr(self.model, "config", None), "provider", None) == "ollama"
            )
            for call in result.tool_calls:
                if calls_executed >= self.max_tool_calls:
                    output = "Zablokowano: osiągnięto limit wywołań narzędzi dla tego zadania."
                    limit_reached = True
                else:
                    try:
                        output = self.tools.execute(call.name, call.arguments)
                    except Exception as exc:
                        output = f"Błąd narzędzia: {type(exc).__name__}: {exc}"
                    calls_executed += 1

                if is_ollama:
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

            if limit_reached or calls_executed >= self.max_tool_calls:
                # One final request without tools lets the model summarize the
                # completed calls and prevents unbounded tool-call loops.
                result = self._request(messages, allow_tools=False)
                answer = result.content or "Zatrzymano zadanie po osiągnięciu limitu narzędzi."
                self.history.extend(
                    [{"role": "user", "content": task}, {"role": "assistant", "content": answer}]
                )
                return answer
