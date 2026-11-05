from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TaskRecord:
    id: str
    title: str
    description: str
    status: TaskStatus
    result: str | None
    error: str | None
    created_at: str
    updated_at: str
    started_at: str | None
    finished_at: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
