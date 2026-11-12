from __future__ import annotations

import pytest

from agents.base import BaseAgent
from agents.team import AgentTeam
from models.chat import ChatResult, ToolCall
from tools.tool_executor import ToolExecutor


class FakeTeam:
    def __init__(self):
        self.calls = []

    def run(self, role, task):
        self.calls.append((role, task))
        return f"{role}: {task}"

    def run_many(self, tasks):
        self.calls.append(("many", tasks))
        return [f"{item['role']}: {item['task']}" for item in tasks]


class FakeModel:
    def __init__(self, results):
        self.results = iter(results)
        self.seen_tools = []

    def chat(self, messages, tools):
        self.seen_tools.append(tools)
        return next(self.results)


def test_delegation_tools_are_advertised_by_default():
    agent = BaseAgent(model=FakeModel([ChatResult(content="ok")]))
    names = {
        item["function"]["name"]
        for item in agent._tool_definitions()
    }
    assert {"write_file", "read_file", "run_python", "delegate_task", "delegate_tasks"} <= names


def test_specialist_agent_has_no_tools_or_recursive_delegation():
    agent = BaseAgent(
        model=FakeModel([ChatResult(content="analysis")]),
        enable_tools=False,
        enable_delegation=False,
    )
    assert agent._tool_definitions() == []
    assert agent.run("Przeanalizuj problem") == "analysis"


def test_tool_executor_dispatches_single_delegation(tmp_path):
    team = FakeTeam()
    executor = ToolExecutor(agent_team=team)
    result = executor.execute("delegate_task", {"role": "reviewer", "task": "Sprawdź kod"})
    assert result == "reviewer: Sprawdź kod"
    assert team.calls == [("reviewer", "Sprawdź kod")]


def test_tool_executor_dispatches_multiple_delegations(tmp_path):
    team = FakeTeam()
    executor = ToolExecutor(agent_team=team)
    tasks = [
        {"role": "researcher", "task": "Zbadaj A"},
        {"role": "programmer", "task": "Oceń B"},
    ]
    result = executor.execute("delegate_tasks", {"tasks": tasks})
    assert "researcher: Zbadaj A" in result
    assert "programmer: Oceń B" in result
    assert team.calls == [("many", tasks)]


def test_base_agent_executes_delegation_tool_call():
    team = FakeTeam()
    executor = ToolExecutor(agent_team=team)
    model = FakeModel([
        ChatResult(tool_calls=[
            ToolCall("delegate_task", {"role": "reviewer", "task": "Oceń architekturę"}, "call_1")
        ]),
        ChatResult(content="Recenzent wskazał dwa ryzyka."),
    ])
    agent = BaseAgent(model=model, tools=executor)
    answer = agent.run("Poproś recenzenta o analizę")
    assert answer == "Recenzent wskazał dwa ryzyka."
    assert team.calls == [("reviewer", "Oceń architekturę")]
    assert any(
        item["function"]["name"] == "delegate_task"
        for item in model.seen_tools[0]
    )


def test_agent_team_default_factory_disables_tools_and_recursion(monkeypatch):
    import agents.base as base_module

    class Model:
        def chat(self, messages, tools):
            assert tools == []
            return ChatResult(content="specjalistyczna analiza")

    monkeypatch.setattr(base_module, "build_model", lambda: Model())
    result = AgentTeam().run("researcher", "Zbadaj wymagania")
    assert result == "specjalistyczna analiza"


def test_agent_team_rejects_non_object_task_entries():
    team = AgentTeam(agent_factory=lambda prompt: None)
    with pytest.raises(ValueError, match="obiektem"):
        team.run_many(["not-a-dict"])


def test_base_agent_rejects_zero_tool_budget():
    with pytest.raises(ValueError, match="większe od zera"):
        BaseAgent(model=FakeModel([]), max_tool_calls=0)
