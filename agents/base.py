from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import ollama

from config.model_config import ModelConfig
from models.providers import ModelCapabilities, ModelProvider, ModelResponse, ModelToolCall
from tools.tool_executor import ToolExecutor


@dataclass
class OllamaModel:
    """Adapter Ollama tłumaczący SDK dostawcy na wspólny kontrakt modeli."""

    config: ModelConfig = field(default_factory=ModelConfig.from_env)

    @property
    def name(self) -> str:
        return self.config.model

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def host(self) -> str:
        return self.config.host

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(tool_calling=True)

    def generate(self, messages: list[dict[str, Any]]) -> str:
        return self.chat(messages).content

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> ModelResponse:
        client = ollama.Client(host=self.config.host)
        response = client.chat(
            model=self.config.model,
            messages=messages,
            tools=tools or [],
            options={"temperature": self.config.temperature},
        )
        message = response.message
        calls: list[ModelToolCall] = []
        for call in message.tool_calls or []:
            arguments = call.function.arguments or {}
            if not isinstance(arguments, dict):
                arguments = {}
            calls.append(
                ModelToolCall(
                    name=str(call.function.name),
                    arguments=arguments,
                    call_id=getattr(call, "id", None),
                )
            )
        return ModelResponse(
            content=message.content or "",
            tool_calls=tuple(calls),
        )


@dataclass
class BaseAgent:
    """Agent z historią rozmowy i narzędziami do pracy z plikami."""

    model: ModelProvider = field(default_factory=OllamaModel)
    system_prompt: str = (
        "Jesteś agentem Własne AI. Odpowiadasz po polsku. "
        "Realizujesz zadania za pomocą dostępnych narzędzi, gdy jest to "
        "możliwe. Po wykonaniu działania sprawdzasz jego wynik. "
        "Nie twierdź, że wykonałeś coś, czego nie zrobiłeś."
    )
    history: list[dict[str, str]] = field(default_factory=list)
    tools: ToolExecutor = field(default_factory=ToolExecutor)
    max_tool_calls: int = 5
    allow_delegation: bool = True

    def _tool_definitions(self) -> list[dict]:
        """Opis narzędzi udostępnianych modelowi."""

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
                    "name": "list_files",
                    "description": "Wyświetla pliki w workspace.",
                    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": []},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_files",
                    "description": "Wyszukuje tekst w plikach workspace.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "path": {"type": "string"}}, "required": ["query"]},
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
        if self.allow_delegation:
            definitions.append({
                "type": "function",
                "function": {
                    "name": "delegate_task",
                    "description": "Deleguje podzadanie do agenta specjalistycznego (planner, analyst, coder lub reviewer).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "enum": ["planner", "analyst", "coder", "reviewer"]},
                            "task": {"type": "string", "description": "Konkretne podzadanie dla agenta."},
                        },
                        "required": ["role", "task"],
                    },
                },
            })
        definitions.append({
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Uruchamia wyłącznie dozwolone, diagnostyczne komendy bez powłoki (np. ollama list, python --version, git status). Nie wykonuje dowolnych poleceń.",
                "parameters": {
                    "type": "object",
                    "properties": {"command": {"type": "string", "description": "Jedna komenda z bezpiecznej allowlisty."}},
                    "required": ["command"],
                },
            },
        })
        if self.tools.web_search_available:
            definitions.append({
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Wyszukuje aktualne informacje w Internecie i zwraca tytuły, adresy oraz krótkie fragmenty wyników.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string", "description": "Zapytanie do wyszukiwarki."}},
                        "required": ["query"],
                    },
                },
            })
        return definitions

    def _delegate(self, arguments: dict) -> str:
        if not self.allow_delegation:
            raise ValueError("Zagnieżdżone delegowanie jest wyłączone.")
        if not isinstance(arguments, dict):
            raise ValueError("Argumenty delegowania muszą być obiektem.")
        role = arguments.get("role")
        task = arguments.get("task")
        role_prompts = {
            "planner": "Jesteś agentem-planistą. Rozbij zadanie na uporządkowane, wykonalne kroki i wskaż ryzyka.",
            "analyst": "Jesteś analitykiem. Zbadaj problem, założenia, przypadki brzegowe i możliwe rozwiązania.",
            "coder": "Jesteś agentem programistycznym. Wykonuj konkretne prace w workspace, sprawdzaj pliki i uruchamiaj testy, jeśli to potrzebne.",
            "reviewer": "Jesteś niezależnym recenzentem. Szukaj błędów, luk bezpieczeństwa i niezgodności z wymaganiami; nie zakładaj, że praca jest poprawna.",
        }
        if role not in role_prompts:
            raise ValueError("Nieznana rola agenta.")
        if not isinstance(task, str) or not task.strip() or len(task) > 12000:
            raise ValueError("Podzadanie musi być tekstem o długości 1–12000 znaków.")
        specialist = BaseAgent(
            model=self.model,
            system_prompt=role_prompts[role] + " Odpowiadaj po polsku i jasno oddziel fakty od przypuszczeń.",
            history=[],
            tools=self.tools,
            max_tool_calls=min(3, self.max_tool_calls),
            allow_delegation=False,
        )
        return specialist.run(task.strip())

    def run(self, task: str) -> str:
        """Wykonuje zadanie, obsługując wywołania narzędzi przez Ollama."""

        task = task.strip()
        if not task:
            raise ValueError("Zadanie nie może być puste.")

        messages = [
            {"role": "system", "content": self.system_prompt},
            *self.history,
            {"role": "user", "content": task},
        ]

        for _ in range(self.max_tool_calls + 1):
            response = self.model.chat(messages, tools=self._tool_definitions())
            if not response.tool_calls:
                answer = response.content
                self.history.extend(
                    [
                        {"role": "user", "content": task},
                        {"role": "assistant", "content": answer},
                    ]
                )
                return answer

            messages.append(
                {
                    "role": "assistant",
                    "content": response.content,
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": call.arguments,
                            },
                            **({"id": call.call_id} if call.call_id else {}),
                        }
                        for call in response.tool_calls
                    ],
                }
            )

            for call in response.tool_calls:
                name = call.name
                arguments = call.arguments
                try:
                    if name == "delegate_task":
                        result = self._delegate(arguments)
                    else:
                        result = self.tools.execute(name, arguments)
                except Exception as exc:
                    result = f"Błąd narzędzia: {type(exc).__name__}: {exc}"

                tool_message = {"role": "tool", "content": result, "tool_name": name}
                if call.call_id:
                    tool_message["tool_call_id"] = call.call_id
                messages.append(tool_message)

        return (
            "Zatrzymano zadanie po osiągnięciu limitu wywołań narzędzi. "
            "Sprawdź dotychczasowe wyniki przed ponowną próbą."
        )
