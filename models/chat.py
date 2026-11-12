from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    """Provider-independent function call returned by a chat model."""

    name: str
    arguments: dict[str, Any]
    id: str = ""


@dataclass
class ChatResult:
    """Normalized assistant response shared by all model providers."""

    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw_message: Any = None
