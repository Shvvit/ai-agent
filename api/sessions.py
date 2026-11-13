from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any


class SessionRepository:
    """SQLite-backed OpenCode-compatible conversation/session storage."""

    def __init__(self, path: Path, directory: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        directory.mkdir(parents=True, exist_ok=True)
        self.directory = directory.resolve()
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, check_same_thread=False, timeout=15)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript("""
            CREATE TABLE IF NOT EXISTS opencode_sessions (
                id TEXT PRIMARY KEY, title TEXT NOT NULL,
                created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS opencode_messages (
                id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                role TEXT NOT NULL, model_id TEXT NOT NULL,
                provider_id TEXT NOT NULL, parts_json TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY(session_id) REFERENCES opencode_sessions(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_opencode_messages_session
            ON opencode_messages(session_id, created_at);
        """)
        # Upgrade IDs from early bridge builds so they satisfy the pinned
        # OpenCode protocol without losing the associated local history.
        with self._lock:
            sessions = self._db.execute("SELECT id FROM opencode_sessions WHERE id NOT LIKE 'ses%'").fetchall()
            for row in sessions:
                old_id = row["id"]
                new_id = f"ses_{old_id}"
                self._db.execute("UPDATE opencode_messages SET session_id=? WHERE session_id=?", (new_id, old_id))
                self._db.execute("UPDATE opencode_sessions SET id=? WHERE id=?", (new_id, old_id))
            messages = self._db.execute("SELECT id FROM opencode_messages WHERE substr(id,1,4) != 'msg_'").fetchall()
            for row in messages:
                self._db.execute("UPDATE opencode_messages SET id=? WHERE id=?", (f"msg_{row['id']}", row["id"]))
        self._db.commit()

    @staticmethod
    def _now() -> int:
        return int(time.time() * 1000)

    def create(self, title: str = "New session") -> dict[str, Any]:
        now = self._now()
        item = {"id": f"ses_{uuid.uuid4().hex}", "title": title[:120], "created_at": now, "updated_at": now}
        with self._lock:
            self._db.execute(
                "INSERT INTO opencode_sessions VALUES(?,?,?,?)",
                (item["id"], item["title"], now, now),
            )
            self._db.commit()
        return item

    def get(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM opencode_sessions WHERE id=?", (session_id,)).fetchone()
        return dict(row) if row else None

    def list(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute("SELECT * FROM opencode_sessions ORDER BY updated_at DESC").fetchall()
        return [dict(row) for row in rows]

    def update_title(self, session_id: str, title: str) -> bool:
        with self._lock:
            cursor = self._db.execute(
                "UPDATE opencode_sessions SET title=?, updated_at=? WHERE id=?",
                (title[:120], self._now(), session_id),
            )
            self._db.commit()
        return cursor.rowcount > 0

    def add_message(
        self,
        session_id: str,
        role: str,
        parts: list[dict[str, Any]],
        model_id: str,
        provider_id: str,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        item = {
            "id": message_id or f"msg_{uuid.uuid4().hex}", "session_id": session_id, "role": role,
            "model_id": model_id, "provider_id": provider_id,
            "parts": parts, "created_at": self._now(),
        }
        with self._lock:
            self._db.execute(
                "INSERT INTO opencode_messages VALUES(?,?,?,?,?,?,?)",
                (item["id"], session_id, role, model_id, provider_id,
                 json.dumps(parts, ensure_ascii=False), item["created_at"]),
            )
            self._db.execute("UPDATE opencode_sessions SET updated_at=? WHERE id=?", (item["created_at"], session_id))
            self._db.commit()
        return item

    def messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._db.execute(
                "SELECT * FROM opencode_messages WHERE session_id=? ORDER BY created_at,rowid",
                (session_id,),
            ).fetchall()
        return [{
            "id": row["id"], "session_id": row["session_id"], "role": row["role"],
            "model_id": row["model_id"], "provider_id": row["provider_id"],
            "parts": json.loads(row["parts_json"]), "created_at": row["created_at"],
        } for row in rows]

    def delete(self, session_id: str) -> bool:
        with self._lock:
            self._db.execute("DELETE FROM opencode_messages WHERE session_id=?", (session_id,))
            cursor = self._db.execute("DELETE FROM opencode_sessions WHERE id=?", (session_id,))
            self._db.commit()
        return cursor.rowcount > 0

    def close(self) -> None:
        with self._lock:
            self._db.close()
