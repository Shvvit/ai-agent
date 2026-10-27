from __future__ import annotations

import re
from dataclasses import dataclass, field

from agents.base import BaseAgent
from agents.planner import Planner
from core.verifier import Verifier


@dataclass
class TaskResult:
    task: str
    plan: str
    answer: str
    success: bool
    verification: str
    attempts: int = 0


@dataclass
class AgentEngine:
    """Planuje zadania, uruchamia agenta i weryfikuje wybrane rezultaty."""

    agent: BaseAgent = field(default_factory=BaseAgent)
    verifier: Verifier = field(default_factory=Verifier)
    max_repair_attempts: int = 3

    def run(self, task: str) -> TaskResult:
        task = task.strip()
        if not task:
            raise ValueError("Zadanie nie może być puste.")

        plan = Planner(self.agent).create_plan(task)
        answer = self.agent.run(
            "Wykonaj zadanie za pomocą dostępnych narzędzi. "
            "Jeśli tworzysz kod, zapisz go w workspace i przetestuj. "
            "Nie twierdź, że coś działa, dopóki tego nie sprawdzisz.\n\n"
            f"ZADANIE:\n{task}\n\nPLAN:\n{plan}"
        )

        relative_path = self._requested_file_path(task)
        if relative_path is None:
            return TaskResult(
                task=task, plan=plan, answer=answer, success=False,
                verification="Nie określono pliku, którego istnienie można automatycznie sprawdzić.",
            )

        file_result = self.verifier.file_exists(relative_path)
        if not file_result.success:
            return TaskResult(task, plan, answer, False, file_result.message)

        if relative_path.endswith(".py"):
            file_manager = self.agent.tools.files
            test_runner = self.agent.tools.tests
            last_output = ""
            for attempt in range(self.max_repair_attempts + 1):
                result = test_runner.run_python(relative_path)
                last_output = result.output
                if result.success:
                    return TaskResult(
                        task, plan, answer, True,
                        f"Program uruchomił się poprawnie. Wynik: {result.output or '(brak wyjścia)'}",
                        attempts=attempt,
                    )
                if attempt == self.max_repair_attempts:
                    break
                current_code = file_manager.read_file(relative_path)
                answer = self.agent.run(
                    "Popraw błąd w pliku Python. Zapisz poprawiony kod w tym samym pliku, a potem pozwól ponownie go przetestować.\n\n"
                    f"PLIK: {relative_path}\nKOD:\n{current_code}\n\nWYNIK BŁĘDU:\n{last_output}"
                )
            return TaskResult(
                task, plan, answer, False,
                f"Program nadal nie przechodzi testu:\n{last_output}",
                attempts=self.max_repair_attempts,
            )

        return TaskResult(task, plan, answer, True, file_result.message)

    @staticmethod
    def _requested_file_path(task: str) -> str | None:
        match = re.search(
            r"(?:utwórz|stwórz|zapisz)\s+plik\s+"
            r"([A-Za-z0-9_.-]+(?:[/\\][A-Za-z0-9_.-]+)*)",
            task, flags=re.IGNORECASE,
        )
        return match.group(1) if match else None
