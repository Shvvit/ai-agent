from __future__ import annotations

from agents.base import BaseAgent
from agents.planner import Planner
from models.chat import ChatResult


class FakeModel:
    def __init__(self):
        self.tools_seen = []

    def chat(self, messages, tools):
        self.tools_seen.append(tools)
        return ChatResult(content="Plan gotowy")


def test_planner_does_not_expose_tools_to_model():
    model = FakeModel()
    agent = BaseAgent(model=model)
    plan = Planner(agent).create_plan("Wyjaśnij działanie pamięci RAM")
    assert plan == "Plan gotowy"
    assert model.tools_seen == [[]]
