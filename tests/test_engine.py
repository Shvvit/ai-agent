from __future__ import annotations

from agents.base import BaseAgent
from core.engine import AgentEngine
from memory.manager import MemoryManager


class FakeTextModel:
    def __init__(self, answers):
        self.answers = iter(answers)
        self.user_prompts = []

    def generate(self, messages):
        self.user_prompts.append(messages[-1]["content"])
        return next(self.answers)


def test_normal_question_is_not_reported_as_failed(tmp_path):
    agent = BaseAgent(model=FakeTextModel(["Plan", "Odpowiedź na pytanie"]))
    result = AgentEngine(agent=agent).run("Wyjaśnij, czym jest pamięć RAM.")
    assert result.success is True
    assert result.verified is False
    assert "nie został niezależnie zweryfikowany" in result.verification


def test_empty_task_is_rejected():
    agent = BaseAgent(model=FakeTextModel([]))
    try:
        AgentEngine(agent=agent).run("   ")
    except ValueError as exc:
        assert "nie może być puste" in str(exc)
    else:
        raise AssertionError("Empty task should be rejected")


def test_python_file_task_is_verified(tmp_path):
    from tools.file_manager import FileManager
    from tools.test_runner import TestRunner
    from tools.tool_executor import ToolExecutor
    from core.verifier import Verifier

    files = FileManager(tmp_path / "workspace")
    files.write_file("hello.py", "print('hello')\n")
    tools = ToolExecutor(file_manager=files, test_runner=TestRunner(workspace=files.workspace, allow_unsafe_execution=True))
    agent = BaseAgent(model=FakeTextModel(["Plan", "Utworzono hello.py"]), tools=tools)
    result = AgentEngine(agent=agent, verifier=Verifier(files.workspace)).run(
        "Utwórz plik hello.py"
    )
    assert result.success is True
    assert result.verified is True
    assert result.attempts == 0


def test_relevant_long_term_memory_is_added_to_planning_and_execution(tmp_path):
    memory = MemoryManager(tmp_path / "memory.sqlite3")
    memory.remember(
        "Użytkownik rozwija agenta AI z lokalnym Qwen3 i Ollama",
        category="project",
    )
    model = FakeTextModel(["Plan z kontekstem", "Odpowiedź z kontekstem"])
    agent = BaseAgent(model=model)
    engine = AgentEngine(agent=agent, memory=memory)
    result = engine.run("Pomóż rozwinąć projekt agenta AI")
    assert result.success is True
    assert "Qwen3" in model.user_prompts[0]
    assert "Qwen3" in model.user_prompts[1]
    memory.close()


def test_python_file_is_not_executed_without_opt_in(tmp_path):
    from tools.file_manager import FileManager
    from tools.test_runner import TestRunner
    from tools.tool_executor import ToolExecutor
    from core.verifier import Verifier

    files = FileManager(tmp_path / "workspace")
    files.write_file("safe.py", "print('should not run')\n")
    tools = ToolExecutor(file_manager=files, test_runner=TestRunner(workspace=files.workspace))
    agent = BaseAgent(model=FakeTextModel(["Plan", "Plik utworzony"]), tools=tools)
    result = AgentEngine(agent=agent, verifier=Verifier(files.workspace)).run(
        "Utwórz plik safe.py"
    )
    assert result.success is False
    assert result.verified is False
    assert "domyślnie wyłączone" in result.verification
