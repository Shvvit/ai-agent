from __future__ import annotations

import pytest

from agents.base import BaseAgent


class FakeModel:
    def __init__(self):
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        return "Specjalista zakończył analizę."


def test_delegation_is_exposed_only_when_enabled():
    model = FakeModel()
    assert "delegate_task" in {
        item["function"]["name"] for item in BaseAgent(model=model)._tool_definitions()
    }
    assert "delegate_task" not in {
        item["function"]["name"]
        for item in BaseAgent(model=model, allow_delegation=False)._tool_definitions()
    }


def test_specialist_delegation_uses_isolated_role_prompt():
    model = FakeModel()
    agent = BaseAgent(model=model)
    result = agent._delegate({"role": "reviewer", "task": "Sprawdź rozwiązanie."})
    assert result == "Specjalista zakończył analizę."
    assert len(model.calls) == 1
    messages = model.calls[0]
    assert messages[0]["role"] == "system"
    assert "recenzentem" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "Sprawdź rozwiązanie."}


@pytest.mark.parametrize("arguments", [
    {"role": "unknown", "task": "test"},
    {"role": "reviewer", "task": ""},
    {"role": "reviewer", "task": "x" * 12001},
])
def test_specialist_delegation_validates_input(arguments):
    agent = BaseAgent(model=FakeModel())
    with pytest.raises(ValueError):
        agent._delegate(arguments)


def test_specialist_cannot_delegate_recursively():
    agent = BaseAgent(model=FakeModel(), allow_delegation=False)
    with pytest.raises(ValueError, match="Zagnieżdżone"):
        agent._delegate({"role": "analyst", "task": "test"})
