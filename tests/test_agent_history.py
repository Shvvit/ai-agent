from __future__ import annotations

import pytest

from agents.base import BaseAgent
from models.chat import ChatResult


class SequentialModel:
    def __init__(self):
        self.counter = 0

    def chat(self, messages, tools):
        self.counter += 1
        return ChatResult(content=f"answer-{self.counter}")


def test_history_is_trimmed_to_configured_limit():
    agent = BaseAgent(model=SequentialModel(), max_history_messages=4)
    for index in range(4):
        agent.run(f"question-{index}")
    assert len(agent.history) == 4
    assert agent.history[0]["content"] == "question-2"
    assert agent.history[-1]["content"] == "answer-4"


def test_history_limit_must_keep_at_least_one_turn():
    with pytest.raises(ValueError, match="co najmniej 2"):
        BaseAgent(model=SequentialModel(), max_history_messages=1)
