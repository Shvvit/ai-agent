from memory.manager import MemoryEntry, MemoryManager


class LongTermMemory(MemoryManager):
    """Named facade for durable, user-controlled SQLite memories."""


__all__ = ["LongTermMemory", "MemoryEntry", "MemoryManager"]
