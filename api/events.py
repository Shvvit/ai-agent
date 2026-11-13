from __future__ import annotations

import asyncio
from typing import Any


class EventHub:
    """In-process fan-out for the loopback OpenCode-compatible SSE endpoint."""

    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._sequences: dict[str, int] = {}

    def next_sequence(self, aggregate_id: str) -> int:
        sequence = self._sequences.get(aggregate_id, 0) + 1
        self._sequences[aggregate_id] = sequence
        return sequence

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: dict[str, Any]) -> None:
        for queue in tuple(self._subscribers):
            await queue.put(event)
