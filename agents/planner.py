
from __future__ import annotations

from dataclasses import dataclass

from agents.base import BaseAgent


@dataclass
class Planner:
    """Tworzy uporządkowany plan realizacji zadania."""

    agent: BaseAgent

    def create_plan(self, task: str) -> str:
        if not task.strip():
            raise ValueError("Zadanie nie może być puste.")

        prompt = (
            "Przygotuj plan realizacji poniższego zadania.\n"
            "Podziel je na ponumerowane kroki.\n"
            "Każdy krok powinien mieć konkretny rezultat.\n"
            "Uwzględnij sposób sprawdzenia, czy zadanie się udało.\n"
            "Na tym etapie tylko planuj — niczego nie wykonuj.\n\n"
            f"ZADANIE:\n{task}"
        )

        return self.agent.run(prompt)
