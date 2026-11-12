from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable


@dataclass(frozen=True)
class ModelRoute:
    """A model adapter plus the capabilities and trade-offs used for routing."""

    name: str
    model: Any
    capabilities: frozenset[str] = frozenset({"chat"})
    speed_score: float = 3.0
    reasoning_score: float = 3.0
    cost_score: float = 3.0
    context_window: int = 8192
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Nazwa modelu nie może być pusta.")
        for field_name in ("speed_score", "reasoning_score", "cost_score"):
            value = getattr(self, field_name)
            if not 1.0 <= value <= 5.0:
                raise ValueError(f"{field_name} musi mieścić się w zakresie 1–5.")
        if self.context_window < 1:
            raise ValueError("context_window musi być większe od zera.")


@dataclass
class ModelRouter:
    """Select a model using declared capabilities and transparent heuristics."""

    routes: list[ModelRoute]
    last_selected: str | None = field(default=None, init=False)
    last_provider: str | None = field(default=None, init=False)

    CODE_PATTERN = re.compile(
        r"\b(code|coding|python|program|programuj|kod|debug|bug|błąd|testy|refactor|refaktoryz)\b",
        re.IGNORECASE,
    )
    REASONING_PATTERN = re.compile(
        r"\b(analy[sz]|compare|porównaj|zaprojektuj|architektur|strateg|dlaczego|wyjaśnij|plan|optymaliz)\w*",
        re.IGNORECASE,
    )

    def __post_init__(self) -> None:
        if not self.routes:
            raise ValueError("ModelRouter wymaga co najmniej jednego modelu.")
        names = [route.name for route in self.routes]
        if len(names) != len(set(names)):
            raise ValueError("Nazwy modeli w routerze muszą być unikalne.")

    @staticmethod
    def _task_text(messages: list[dict[str, Any]]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                content = message.get("content", "")
                return content if isinstance(content, str) else str(content)
        return ""

    @classmethod
    def _requirements(cls, task: str, tools: list[dict] | None) -> set[str]:
        required = {"chat"}
        if tools:
            required.add("tool_calling")
        if cls.CODE_PATTERN.search(task):
            required.add("code")
        if cls.REASONING_PATTERN.search(task) or len(task) > 1200:
            required.add("reasoning")
        return required

    def select(
        self,
        task: str,
        *,
        required_capabilities: Iterable[str] = (),
        prefer_fast: bool = False,
        prefer_low_cost: bool = False,
    ) -> ModelRoute:
        required = set(required_capabilities)
        required.add("chat")
        eligible = [
            route for route in self.routes
            if route.enabled and required.issubset(route.capabilities)
        ]
        if not eligible:
            raise RuntimeError(
                "Brak aktywnego modelu obsługującego wymagane możliwości: "
                + ", ".join(sorted(required))
            )

        wants_code = "code" in required
        wants_reasoning = "reasoning" in required

        def score(route: ModelRoute) -> tuple[float, float, str]:
            value = 0.0
            if wants_code:
                value += route.reasoning_score * 0.7
            if wants_reasoning:
                value += route.reasoning_score * 1.2
            value += route.speed_score * (1.0 if prefer_fast else 0.25)
            value += route.cost_score * (1.0 if prefer_low_cost else 0.25)
            return (value, route.context_window, route.name)

        selected = max(eligible, key=score)
        self.last_selected = selected.name
        self.last_provider = getattr(
            getattr(selected.model, "config", None), "provider", None
        )
        return selected

    def chat(self, messages: list[dict[str, Any]], tools: list[dict] | None = None):
        task = self._task_text(messages)
        required = self._requirements(task, tools)
        route = self.select(task, required_capabilities=required)
        chat = getattr(route.model, "chat", None)
        if callable(chat):
            return chat(messages, tools or [])
        if tools:
            raise RuntimeError(f"Model {route.name} nie obsługuje wywołań narzędzi.")
        generate = getattr(route.model, "generate", None)
        if callable(generate):
            from models.chat import ChatResult
            return ChatResult(content=str(generate(messages)))
        raise TypeError(f"Model {route.name} nie implementuje chat() ani generate().")

    def generate(self, messages: list[dict[str, Any]]) -> str:
        result = self.chat(messages, tools=[])
        return str(getattr(result, "content", result))
