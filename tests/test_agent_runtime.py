from __future__ import annotations

from agents.base import BaseAgent
from models.chat import ChatResult, ToolCall


class FakeToolExecutor:
    def __init__(self):
        self.calls = []

    def execute(self, name, arguments):
        self.calls.append((name, arguments))
        return "tool-ok"


class FakeChatModel:
    def __init__(self, responses, provider="openrouter"):
        self.responses = iter(responses)
        self.config = type("Config", (), {"provider": provider})()

    def chat(self, messages, tools):
        return next(self.responses)


def test_openai_compatible_tool_call_is_executed_and_returned_to_model():
    tool = FakeToolExecutor()
    model = FakeChatModel([
        ChatResult(tool_calls=[ToolCall("read_file", {"path": "notes.txt"}, "call_1")]),
        ChatResult(content="Plik został odczytany."),
    ])
    agent = BaseAgent(model=model, tools=tool)
    answer = agent.run("Przeczytaj notes.txt")
    assert answer == "Plik został odczytany."
    assert tool.calls == [("read_file", {"path": "notes.txt"})]
    assert agent.history[-1] == {"role": "assistant", "content": answer}


def test_tool_budget_blocks_extra_calls_but_keeps_protocol_messages():
    tool = FakeToolExecutor()
    model = FakeChatModel([
        ChatResult(tool_calls=[
            ToolCall("read_file", {"path": "one.txt"}, "call_1"),
            ToolCall("read_file", {"path": "two.txt"}, "call_2"),
        ]),
        ChatResult(content="Pierwsze narzędzie wykonane, drugie zablokowane."),
    ])
    agent = BaseAgent(model=model, tools=tool, max_tool_calls=1)
    answer = agent.run("Odczytaj dwa pliki")
    assert answer.startswith("Pierwsze narzędzie")
    assert len(tool.calls) == 1


def test_legacy_generate_only_model_still_works():
    class LegacyModel:
        def generate(self, messages):
            return "legacy-answer"

    agent = BaseAgent(model=LegacyModel())
    assert agent.run("Cześć") == "legacy-answer"



def test_base_agent_uses_approval_aware_tool_executor():
    from tools.registry import ToolDefinition, ToolRegistry
    from tools.tool_executor import ToolExecutor

    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="confirm_action",
        description="A protected action",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        handler=lambda args: "approved-action-ran",
        requires_approval=True,
    ))
    decisions = []
    executor = ToolExecutor(
        registry=registry,
        granted_capabilities=set(),
        approval_callback=lambda name, args: decisions.append(name) or True,
    )
    model = FakeChatModel([
        ChatResult(tool_calls=[ToolCall("confirm_action", {}, "call_approval")]),
        ChatResult(content="Akcja wykonana po zgodzie."),
    ])
    agent = BaseAgent(model=model, tools=executor)
    assert agent.run("Wykonaj chronioną akcję") == "Akcja wykonana po zgodzie."
    assert decisions == ["confirm_action"]
