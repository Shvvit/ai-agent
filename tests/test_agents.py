from __future__ import annotations

import pytest

from agents.base import BaseAgent
from models.providers import ModelResponse


class FakeModel:
    def __init__(self):
        self.calls = []

    def generate(self, messages):
        self.calls.append(messages)
        return "Specjalista zakończył analizę."

    def chat(self, messages, tools=None):
        self.calls.append(messages)
        return ModelResponse(content="Specjalista zakończył analizę.")


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


def test_ollama_agent_executes_specialist_delegation(monkeypatch):
    from types import SimpleNamespace

    import agents.base as base_module
    from config.model_config import ModelConfig

    calls = []

    class FakeClient:
        def chat(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                tool_call = SimpleNamespace(function=SimpleNamespace(
                    name="delegate_task",
                    arguments={"role": "analyst", "task": "Przeanalizuj ryzyko."},
                ))
                return SimpleNamespace(message=SimpleNamespace(tool_calls=[tool_call], content=""))
            if len(calls) == 2:
                return SimpleNamespace(message=SimpleNamespace(tool_calls=[], content="Analiza gotowa."))
            return SimpleNamespace(message=SimpleNamespace(tool_calls=[], content="Wynik końcowy."))

    monkeypatch.setattr(base_module.ollama, "Client", lambda **kwargs: FakeClient())
    agent = BaseAgent(model=base_module.OllamaModel(config=ModelConfig()))
    assert agent.run("Zbadaj ryzyko.") == "Wynik końcowy."
    assert len(calls) == 3
    assert any(
        tool["function"]["name"] == "delegate_task"
        for tool in calls[0]["tools"]
    )
    assert all(
        tool["function"]["name"] != "delegate_task"
        for tool in calls[1]["tools"]
    )


def test_web_search_tool_is_only_advertised_when_configured():
    class Search:
        enabled = True

        def search(self, query):
            return []

    from tools.tool_executor import ToolExecutor

    agent = BaseAgent(model=FakeModel(), tools=ToolExecutor(web_search=Search()))
    names = {item["function"]["name"] for item in agent._tool_definitions()}
    assert "web_search" in names



def test_provider_neutral_agent_preserves_tool_call_id():
    from models.providers import ModelResponse, ModelToolCall

    class ToolModel:
        provider_name = "test"
        name = "test-model"

        def __init__(self):
            self.calls = []

        @property
        def capabilities(self):
            from models.providers import ModelCapabilities
            return ModelCapabilities(tool_calling=True)

        def generate(self, messages):
            return "done"

        def chat(self, messages, tools=None):
            self.calls.append(messages)
            if len(self.calls) == 1:
                return ModelResponse(
                    tool_calls=(
                        ModelToolCall(
                            name="inspect",
                            arguments={"target": "sample"},
                            call_id="call_test_1",
                        ),
                    )
                )
            return ModelResponse(content="Zrobione.")

    class ToolExecutor:
        web_search_available = False

        def execute(self, name, arguments):
            assert name == "inspect"
            assert arguments == {"target": "sample"}
            return "Wynik narzędzia."

    model = ToolModel()
    agent = BaseAgent(model=model, tools=ToolExecutor())
    assert agent.run("Sprawdź próbkę.") == "Zrobione."
    follow_up = model.calls[1]
    assert follow_up[-2]["role"] == "assistant"
    assert follow_up[-2]["tool_calls"][0]["id"] == "call_test_1"
    assert follow_up[-1]["role"] == "tool"
    assert follow_up[-1]["tool_call_id"] == "call_test_1"
