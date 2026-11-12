from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class ConversationMemory:
    """Bounded in-process chat history; never persisted to disk."""

    max_messages: int = 40
    messages: deque[dict[str, str]] = field(default_factory=deque)

    def __post_init__(self) -> None:
        if self.max_messages < 2:
            raise ValueError("max_messages musi wynosić co najmniej 2.")
        self.messages = deque(self.messages, maxlen=self.max_messages)

    def add(self, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Do historii rozmowy można dodać tylko user lub assistant.")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Treść wiadomości nie może być pusta.")
        self.messages.append({"role": role, "content": content.strip()})

    def extend(self, messages: list[dict[str, str]]) -> None:
        for message in messages:
            self.add(message.get("role", ""), message.get("content", ""))

    def to_messages(self) -> list[dict[str, str]]:
        return list(self.messages)

    def clear(self) -> None:
        self.messages.clear()
