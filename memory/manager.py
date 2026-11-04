from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


class MemoryManager:
    """Trwała, lokalna pamięć faktów użytkownika w SQLite."""

    def __init__(self, db_path: str | Path, max_items: int = 2000) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_items = max(1, int(max_items))
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(id DESC)")

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[\w-]{2,}", text.casefold()))

    def remember(self, content: str) -> dict[str, Any]:
        if not isinstance(content, str):
            raise TypeError("Treść pamięci musi być tekstem.")
        content = content.strip()
        if not content:
            raise ValueError("Pamięć nie może być pusta.")
        if len(content) > 4000:
            raise ValueError("Pamięć może mieć maksymalnie 4000 znaków.")
        with self._connect() as db:
            cursor = db.execute("INSERT INTO memories(content) VALUES (?)", (content,))
            db.execute(
                "DELETE FROM memories WHERE id NOT IN "
                "(SELECT id FROM memories ORDER BY id DESC LIMIT ?)",
                (self.max_items,),
            )
            row = db.execute(
                "SELECT id, content, created_at FROM memories WHERE id=?",
                (cursor.lastrowid,),
            ).fetchone()
        return dict(row)

    def list_memories(self, limit: int = 200) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, content, created_at FROM memories ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def search(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        tokens = self._tokens(query)
        if not tokens:
            return []
        ranked = []
        for item in self.list_memories(limit=500):
            content_tokens = self._tokens(item["content"])
            matched = {
                query_token for query_token in tokens
                if any(
                    content_token == query_token
                    or (len(query_token) >= 4 and content_token.startswith(query_token[:4]))
                    or (len(content_token) >= 4 and query_token.startswith(content_token[:4]))
                    for content_token in content_tokens
                )
            }
            if matched:
                ranked.append((len(matched), item["id"], item))
        ranked.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return [item for _, _, item in ranked[:max(1, min(int(limit), 50))]]

    def forget(self, memory_id: int) -> bool:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM memories WHERE id=?", (int(memory_id),))
        return cursor.rowcount > 0

    def clear(self) -> int:
        with self._connect() as db:
            cursor = db.execute("DELETE FROM memories")
        return cursor.rowcount
