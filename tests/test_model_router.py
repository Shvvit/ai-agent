from __future__ import annotations

import pytest

from models.chat import ChatResult
from models.router import ModelRoute, ModelRouter


class FakeModel:
    def __init__(self, name):
        self.name = name
        self.calls = 0

    def chat(self, messages, tools):
        self.calls += 1
        return ChatResult(content=self.name)


def test_router_prefers_fast_model_for_simple_chat():
    fast = FakeModel("fast")
    strong = FakeModel("strong")
    router = ModelRouter([
        ModelRoute("fast", fast, frozenset({"chat", "tool_calling", "code", "reasoning"}), speed_score=5, reasoning_score=2, cost_score=5),
        ModelRoute("strong", strong, frozenset({"chat", "tool_calling", "code", "reasoning"}), speed_score=2, reasoning_score=5, cost_score=2),
    ])
    result = router.chat([{"role": "user", "content": "Cześć"}])
    assert result.content == "fast"
    assert router.last_selected == "fast"


def test_router_prefers_reasoning_model_for_architecture_task():
    fast = FakeModel("fast")
    strong = FakeModel("strong")
    router = ModelRouter([
        ModelRoute("fast", fast, frozenset({"chat", "tool_calling", "code", "reasoning"}), speed_score=5, reasoning_score=2, cost_score=5),
        ModelRoute("strong", strong, frozenset({"chat", "tool_calling", "code", "reasoning"}), speed_score=2, reasoning_score=5, cost_score=2),
    ])
    result = router.chat([{"role": "user", "content": "Przeanalizuj i zaprojektuj architekturę agenta"}])
    assert result.content == "strong"
    assert router.last_selected == "strong"


def test_router_requires_tool_calling_capability():
    plain = FakeModel("plain")
    tools = FakeModel("tools")
    router = ModelRouter([
        ModelRoute("plain", plain, frozenset({"chat"})),
        ModelRoute("tools", tools, frozenset({"chat", "tool_calling"})),
    ])
    result = router.chat([{"role": "user", "content": "Odczytaj plik"}], tools=[{"type": "function"}])
    assert result.content == "tools"
    assert plain.calls == 0


def test_router_never_uses_model_missing_hard_capability():
    router = ModelRouter([ModelRoute("plain", FakeModel("plain"), frozenset({"chat"}))])
    with pytest.raises(RuntimeError, match="Brak aktywnego modelu"):
        router.select("zrób kod", required_capabilities={"code"})


def test_router_rejects_duplicate_names_and_invalid_scores():
    with pytest.raises(ValueError, match="unikalne"):
        ModelRouter([
            ModelRoute("same", FakeModel("a")),
            ModelRoute("same", FakeModel("b")),
        ])
    with pytest.raises(ValueError, match="speed_score"):
        ModelRoute("bad", FakeModel("bad"), speed_score=9)


def test_router_supports_generate_only_model():
    class Legacy:
        def generate(self, messages):
            return "legacy"

    router = ModelRouter([ModelRoute("legacy", Legacy(), frozenset({"chat"}))])
    assert router.generate([{"role": "user", "content": "hello"}]) == "legacy"
