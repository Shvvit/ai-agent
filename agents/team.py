from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Protocol


class RunnableAgent(Protocol):
    def run(self, task: str) -> str: ...


PROFILES = {
    "researcher": (
        "Jesteś agentem badawczym. Analizujesz pytanie, oddzielasz fakty od "
        "założeń, wskazujesz niepewność i zwracasz zwięzłe wnioski po polsku. "
        "Nie wykonujesz operacji na komputerze."
    ),
    "programmer": (
        "Jesteś agentem programistycznym. Analizujesz architekturę, proponujesz "
        "konkretne rozwiązania i wskazujesz przypadki brzegowe. Nie wykonujesz "
        "operacji na komputerze ani nie twierdzisz, że uruchomiłeś testy."
    ),
    "reviewer": (
        "Jesteś niezależnym recenzentem. Szukasz błędów logicznych, luk "
        "bezpieczeństwa, niejawnych założeń i brakujących testów. Nie "
        "zatwierdzasz rozwiązania bez uzasadnienia."
    ),
}


@dataclass
class AgentTeam:
    """Bounded specialist delegation inspired by Agent Zero's sub-agent model.

    Delegated agents receive no tools and cannot recursively delegate. The
    default parallelism is one to avoid VRAM spikes on small local GPUs.
    """

    agent_factory: Callable[[str], RunnableAgent] | None = None
    max_parallel: int = 1

    def __post_init__(self) -> None:
        if not 1 <= self.max_parallel <= 3:
            raise ValueError("max_parallel musi mieścić się w zakresie 1–3.")

    def _make_agent(self, role: str) -> RunnableAgent:
        prompt = PROFILES[role]
        if self.agent_factory is not None:
            return self.agent_factory(prompt)

        # Lazy import avoids a circular dependency with ToolExecutor.
        from agents.base import BaseAgent, build_model

        return BaseAgent(
            model=build_model(),
            system_prompt=prompt,
            enable_tools=False,
            enable_delegation=False,
        )

    @staticmethod
    def _validate(role: str, task: str) -> tuple[str, str]:
        normalized_role = str(role or "").strip().lower()
        normalized_task = str(task or "").strip()
        if normalized_role not in PROFILES:
            raise ValueError(
                f"Nieznana rola agenta: {normalized_role or '(pusta)'}. "
                f"Dostępne role: {', '.join(PROFILES)}."
            )
        if not normalized_task:
            raise ValueError("Zadanie delegowane nie może być puste.")
        if len(normalized_task) > 8000:
            raise ValueError("Zadanie delegowane przekracza limit 8000 znaków.")
        return normalized_role, normalized_task

    def run(self, role: str, task: str) -> str:
        normalized_role, normalized_task = self._validate(role, task)
        agent = self._make_agent(normalized_role)
        return agent.run(normalized_task)

    def run_many(self, tasks: list[dict[str, str]]) -> list[str]:
        if not isinstance(tasks, list) or not 1 <= len(tasks) <= 3:
            raise ValueError("delegate_tasks wymaga od 1 do 3 zadań.")
        validated = [self._validate(item.get("role"), item.get("task")) for item in tasks]
        with ThreadPoolExecutor(max_workers=self.max_parallel) as pool:
            futures = [
                pool.submit(self.run, role, task)
                for role, task in validated
            ]
            return [future.result() for future in futures]
