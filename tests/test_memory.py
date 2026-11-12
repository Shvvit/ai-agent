from __future__ import annotations

import pytest

from memory.conversation_memory import ConversationMemory
from memory.manager import MemoryManager


def test_memory_persists_across_manager_instances(tmp_path):
    database = tmp_path / "memory.sqlite3"
    first = MemoryManager(database)
    memory_id = first.remember(
        "Używam lokalnego Qwen do projektu agenta",
        category="project", tags=["AI", "Ollama"], importance=5,
    )
    first.close()
    second = MemoryManager(database)
    entry = second.get(memory_id)
    assert entry is not None
    assert entry.category == "project"
    assert entry.tags == ("AI", "Ollama")
    assert "Qwen" in entry.content
    second.close()


def test_search_ranks_matching_content_and_tags(tmp_path):
    memory = MemoryManager(tmp_path / "memory.sqlite3")
    memory.remember("Mój komputer ma kartę graficzną RTX", category="hardware")
    memory.remember("Projekt wykorzystuje Qwen i Ollama", category="project", tags=["GPU", "AI"])
    memory.remember("Lubię czytać książki", category="personal")
    results = memory.search("Ollama AI", limit=2)
    assert len(results) == 1
    assert results[0].category == "project"
    memory.close()


def test_memory_delete_and_clear_preserve_pinned_by_default(tmp_path):
    memory = MemoryManager(tmp_path / "memory.sqlite3")
    first = memory.remember("zwykła notatka")
    pinned = memory.remember("ważna notatka", pinned=True)
    assert memory.forget(first) is True
    assert memory.forget(first) is False
    assert memory.clear() == 0
    assert memory.get(pinned) is not None
    assert memory.clear(include_pinned=True) == 1
    assert memory.get(pinned) is None
    memory.close()


def test_memory_validates_inputs(tmp_path):
    memory = MemoryManager(tmp_path / "memory.sqlite3")
    with pytest.raises(ValueError, match="nie może być pusta"):
        memory.remember(" ")
    with pytest.raises(ValueError, match="1–5"):
        memory.remember("notatka", importance=9)
    with pytest.raises(ValueError, match="30 tagów"):
        memory.remember("notatka", tags=[f"tag-{i}" for i in range(31)])
    memory.close()


def test_conversation_memory_is_bounded_and_ephemeral():
    memory = ConversationMemory(max_messages=2)
    memory.add("user", "pierwsza")
    memory.add("assistant", "druga")
    memory.add("user", "trzecia")
    assert [item["content"] for item in memory.to_messages()] == ["druga", "trzecia"]
    memory.clear()
    assert memory.to_messages() == []
    with pytest.raises(ValueError, match="tylko user"):
        memory.add("system", "nie dodawaj")


def test_empty_memory_search_returns_empty(tmp_path):
    memory = MemoryManager(tmp_path / "memory.sqlite3")
    memory.remember("tekst")
    assert memory.search("!!!") == []
    memory.close()
