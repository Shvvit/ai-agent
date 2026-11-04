from __future__ import annotations

import sqlite3
import uuid
from pathlib import Path
from threading import RLock

from core.task_state import TaskRecord, TaskStatus, utc_now


class TaskManager:
    """Trwały rejestr zadań z kontrolą dozwolonych przejść stanów."""

    _TERMINAL = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}

    def __init__(self, database: str | Path = "data/tasks.sqlite3") -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _initialize(self) -> None:
        with self._lock, self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN
                    ('pending','running','completed','failed','cancelled')),
                result TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status_updated ON tasks(status, updated_at DESC)")

    @staticmethod
    def _record(row: sqlite3.Row | None) -> TaskRecord | None:
        if row is None:
            return None
        return TaskRecord(
            id=row["id"], title=row["title"], description=row["description"],
            status=TaskStatus(row["status"]), result=row["result"], error=row["error"],
            created_at=row["created_at"], updated_at=row["updated_at"],
            started_at=row["started_at"], finished_at=row["finished_at"],
        )

    def create(self, description: str, title: str | None = None) -> TaskRecord:
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Opis zadania nie może być pusty.")
        description = description.strip()
        if len(description) > 20000:
            raise ValueError("Opis zadania może mieć maksymalnie 20000 znaków.")
        clean_title = (title or description.splitlines()[0][:120]).strip()
        if not clean_title:
            clean_title = "Nowe zadanie"
        if len(clean_title) > 120:
            raise ValueError("Tytuł zadania może mieć maksymalnie 120 znaków.")
        now, task_id = utc_now(), str(uuid.uuid4())
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT INTO tasks(id,title,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (task_id, clean_title, description, TaskStatus.PENDING.value, now, now),
            )
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        record = self._record(row)
        assert record is not None
        return record

    def get(self, task_id: str) -> TaskRecord | None:
        with self._lock, self._connect() as db:
            return self._record(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

    def list(self, status: TaskStatus | None = None, limit: int = 100) -> list[TaskRecord]:
        limit = max(1, min(int(limit), 500))
        with self._lock, self._connect() as db:
            if status is None:
                rows = db.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            else:
                rows = db.execute("SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC LIMIT ?",
                                  (status.value, limit)).fetchall()
        return [self._record(row) for row in rows if row is not None]  # type: ignore[misc]

    def start(self, task_id: str) -> TaskRecord:
        now = utc_now()
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE tasks SET status=?, started_at=?, updated_at=? WHERE id=? AND status=?",
                (TaskStatus.RUNNING.value, now, now, task_id, TaskStatus.PENDING.value),
            )
            if cursor.rowcount != 1:
                self._raise_transition_error(db, task_id, "rozpocząć")
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        record = self._record(row)
        assert record is not None
        return record

    def complete(self, task_id: str, result: str) -> TaskRecord:
        if not isinstance(result, str):
            raise ValueError("Wynik zadania musi być tekstem.")
        return self._finish(task_id, TaskStatus.COMPLETED, result=result)

    def fail(self, task_id: str, error: str) -> TaskRecord:
        if not isinstance(error, str) or not error.strip():
            raise ValueError("Opis błędu nie może być pusty.")
        return self._finish(task_id, TaskStatus.FAILED, error=error[:8000])

    def cancel(self, task_id: str) -> TaskRecord:
        now = utc_now()
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE tasks SET status=?, updated_at=?, finished_at=? WHERE id=? AND status IN (?,?)",
                (TaskStatus.CANCELLED.value, now, now, task_id,
                 TaskStatus.PENDING.value, TaskStatus.RUNNING.value),
            )
            if cursor.rowcount != 1:
                self._raise_transition_error(db, task_id, "anulować")
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        record = self._record(row)
        assert record is not None
        return record

    def _finish(self, task_id: str, status: TaskStatus, *, result: str | None = None,
                error: str | None = None) -> TaskRecord:
        now = utc_now()
        with self._lock, self._connect() as db:
            cursor = db.execute(
                "UPDATE tasks SET status=?, result=?, error=?, updated_at=?, finished_at=? "
                "WHERE id=? AND status=?",
                (status.value, result, error, now, now, task_id, TaskStatus.RUNNING.value),
            )
            if cursor.rowcount != 1:
                self._raise_transition_error(db, task_id, "zakończyć")
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        record = self._record(row)
        assert record is not None
        return record

    @staticmethod
    def _raise_transition_error(db: sqlite3.Connection, task_id: str, action: str) -> None:
        row = db.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise KeyError("Nie znaleziono zadania.")
        raise ValueError(f"Nie można {action} zadania w stanie {row['status']}.")
