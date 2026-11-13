from __future__ import annotations

import pytest

from memory.manager import MemoryManager


def test_memory_persists_and_searches_relevant_items(tmp_path):
    path = tmp_path / "memory.sqlite3"
    memory = MemoryManager(path)
    first = memory.remember("Użytkownik buduje lokalnego agenta AI.")
    memory.remember("Preferuje cichy komputer.")
    reopened = MemoryManager(path)
    assert reopened.list_memories()[0]["content"] == "Preferuje cichy komputer."
    matches = reopened.search("agent lokalny")
    assert [item["id"] for item in matches] == [first["id"]]


def test_memory_rejects_empty_and_oversized_content(tmp_path):
    memory = MemoryManager(tmp_path / "memory.sqlite3")
    with pytest.raises(ValueError):
        memory.remember("  ")
    with pytest.raises(ValueError):
        memory.remember("x" * 4001)


def test_memory_forget_and_clear(tmp_path):
    memory = MemoryManager(tmp_path / "memory.sqlite3")
    item = memory.remember("Test")
    assert memory.forget(item["id"]) is True
    assert memory.forget(item["id"]) is False
    memory.remember("A")
    memory.remember("B")
    assert memory.clear() == 2
    assert memory.list_memories() == []


def test_memory_caps_retained_items(tmp_path):
    memory = MemoryManager(tmp_path / "memory.sqlite3", max_items=2)
    memory.remember("pierwsza")
    memory.remember("druga")
    memory.remember("trzecia")
    assert [item["content"] for item in memory.list_memories()] == ["trzecia", "druga"]
