from __future__ import annotations

import os
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from core.task_state import TaskStatus


@dataclass(frozen=True)
class TaskRecord:
    id: str
    title: str
    description: str
    status: TaskStatus
    plan: str
    result: str
    error: str
    attempts: int
    created_at: str
    updated_at: str


class TaskManager:
    """Persistent task ledger with validated state transitions."""

    TRANSITIONS = {
        TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
        TaskStatus.RUNNING: {
            TaskStatus.COMPLETED, TaskStatus.FAILED,
            TaskStatus.PAUSED, TaskStatus.CANCELLED,
        },
        TaskStatus.PAUSED: {
            TaskStatus.QUEUED, TaskStatus.RUNNING, TaskStatus.CANCELLED,
        },
        TaskStatus.FAILED: {TaskStatus.QUEUED},
        TaskStatus.COMPLETED: set(),
        TaskStatus.CANCELLED: {TaskStatus.QUEUED},
    }

    def __init__(self, database: str | Path | None = None) -> None:
        self.database = str(database or os.getenv("AI_TASK_DB", "data/tasks.sqlite3"))
        if self.database != ":memory:":
            Path(self.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.database, check_same_thread=False, timeout=10)
        self._db.row_factory = sqlite3.Row
        with self._lock:
            self._db.execute("PRAGMA foreign_keys = ON")
            if self.database != ":memory:":
                self._db.execute("PRAGMA journal_mode = WAL")
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan TEXT NOT NULL DEFAULT '',
                    result TEXT NOT NULL DEFAULT '',
                    error TEXT NOT NULL DEFAULT '',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            self._db.execute("""
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    event TEXT NOT NULL,
                    details TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                )
            """)
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
            self._db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_updated ON tasks(updated_at)")
            self._db.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _record(row: sqlite3.Row) -> TaskRecord:
        return TaskRecord(
            id=str(row["id"]), title=str(row["title"]),
            description=str(row["description"]), status=TaskStatus(row["status"]),
            plan=str(row["plan"]), result=str(row["result"]),
            error=str(row["error"]), attempts=int(row["attempts"]),
            created_at=str(row["created_at"]), updated_at=str(row["updated_at"]),
        )

    def create(self, description: str, *, title: str | None = None) -> TaskRecord:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Opis zadania nie może być pusty.")
        if len(description) > 20000:
            raise ValueError("Opis zadania przekracza limit 20000 znaków.")
        if title is not None and not isinstance(title, str):
            raise ValueError("Tytuł zadania musi być tekstem.")
        normalized_title = (title or description.strip().splitlines()[0][:100]).strip()
        if not normalized_title:
            normalized_title = "Nowe zadanie"
        if len(normalized_title) > 100:
            raise ValueError("Tytuł zadania może mieć maksymalnie 100 znaków.")
        now, task_id = self._now(), str(uuid.uuid4())
        with self._lock:
            self._db.execute(
                """INSERT INTO tasks
                (id,title,description,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?)""",
                (task_id, normalized_title, description.strip(), TaskStatus.QUEUED.value, now, now),
            )
            self._db.execute(
                "INSERT INTO task_events(task_id,event,details,created_at) VALUES(?,?,?,?)",
                (task_id, "created", "Task added to queue", now),
            )
            self._db.commit()
        return self.get(task_id)

    def get(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM tasks WHERE id = ?", (str(task_id),)).fetchone()
        return self._record(row) if row else None

    def list_tasks(
        self, *, status: TaskStatus | str | None = None, limit: int = 50
    ) -> list[TaskRecord]:
        if not 1 <= limit <= 500:
            raise ValueError("limit musi mieścić się w zakresie 1–500.")
        sql, params = "SELECT * FROM tasks", []
        if status is not None:
            normalized = TaskStatus(status)
            sql += " WHERE status = ?"
            params.append(normalized.value)
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._db.execute(sql, params).fetchall()
        return [self._record(row) for row in rows]

    def transition(
        self,
        task_id: str,
        status: TaskStatus | str,
        *,
        plan: str | None = None,
        result: str | None = None,
        error: str | None = None,
        attempts: int | None = None,
    ) -> TaskRecord:
        new_status = TaskStatus(status)
        now = self._now()
        with self._lock:
            row = self._db.execute("SELECT * FROM tasks WHERE id = ?", (str(task_id),)).fetchone()
            if row is None:
                raise KeyError(f"Nie znaleziono zadania {task_id}.")
            current = TaskStatus(row["status"])
            if new_status not in self.TRANSITIONS[current]:
                raise ValueError(f"Niedozwolona zmiana statusu: {current.value} -> {new_status.value}.")
            if attempts is not None and (
                type(attempts) is not int or attempts < 0
            ):
                raise ValueError("Liczba prób nie może być ujemna ani nieliczbowa.")
            self._db.execute(
                """UPDATE tasks SET status=?, plan=?, result=?, error=?, attempts=?, updated_at=?
                WHERE id=?""",
                (
                    new_status.value,
                    row["plan"] if plan is None else plan,
                    row["result"] if result is None else result,
                    row["error"] if error is None else error,
                    row["attempts"] if attempts is None else attempts,
                    now,
                    str(task_id),
                ),
            )
            details = error or result or plan or ""
            self._db.execute(
                "INSERT INTO task_events(task_id,event,details,created_at) VALUES(?,?,?,?)",
                (str(task_id), new_status.value, details[:4000], now),
            )
            self._db.commit()
        return self.get(task_id)

    def events(self, task_id: str) -> list[dict[str, str]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT event, details, created_at FROM task_events WHERE task_id=? ORDER BY id",
                (str(task_id),),
            ).fetchall()
        return [dict(row) for row in rows]

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def __enter__(self) -> "TaskManager":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
