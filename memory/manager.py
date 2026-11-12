from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class MemoryEntry:
    id: int
    content: str
    category: str
    tags: tuple[str, ...]
    importance: int
    source: str
    pinned: bool
    created_at: str
    updated_at: str


class MemoryManager:
    """SQLite memory store. Nothing is saved unless remember() is called."""

    def __init__(self, database: str | Path | None = None) -> None:
        self.database = str(database or os.getenv("AI_MEMORY_DB", "data/memory.sqlite3"))
        if self.database != ":memory:":
            database_path = Path(self.database).expanduser()
            database_path.resolve().parent.mkdir(parents=True, exist_ok=True)
            self.database = str(database_path)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.database, check_same_thread=False, timeout=10.0)
        self._connection.row_factory = sqlite3.Row
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            if self.database != ":memory:":
                self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags_json TEXT NOT NULL DEFAULT '[]',
                    importance INTEGER NOT NULL DEFAULT 3,
                    source TEXT NOT NULL DEFAULT 'user',
                    pinned INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            self._connection.execute("CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category)")
            self._connection.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {token.casefold() for token in re.findall(r"[\w-]{2,}", value, flags=re.UNICODE)}

    @staticmethod
    def _entry(row: sqlite3.Row) -> MemoryEntry:
        try:
            tags = json.loads(row["tags_json"])
        except (TypeError, json.JSONDecodeError):
            tags = []
        return MemoryEntry(
            id=int(row["id"]), content=str(row["content"]), category=str(row["category"]),
            tags=tuple(str(tag) for tag in tags if isinstance(tag, str)),
            importance=int(row["importance"]), source=str(row["source"]),
            pinned=bool(row["pinned"]), created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def remember(
        self, content: str, *, category: str = "general", tags: Iterable[str] = (),
        importance: int = 3, source: str = "user", pinned: bool = False,
    ) -> int:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Treść pamięci nie może być pusta.")
        if len(content) > 20000:
            raise ValueError("Pamięć przekracza limit 20000 znaków.")
        if not isinstance(category, str) or not category.strip() or len(category) > 80:
            raise ValueError("Kategoria musi mieć od 1 do 80 znaków.")
        if type(importance) is not int or not 1 <= importance <= 5:
            raise ValueError("Ważność musi mieścić się w zakresie 1–5.")
        if not isinstance(source, str) or not source.strip() or len(source) > 80:
            raise ValueError("Źródło musi mieć od 1 do 80 znaków.")
        if isinstance(tags, str):
            tags = [tags]
        try:
            normalized_tags = sorted({
                tag.strip() for tag in tags
                if isinstance(tag, str) and tag.strip()
            })
        except TypeError as exc:
            raise ValueError("Tagi muszą być listą tekstów.") from exc
        if len(normalized_tags) > 30:
            raise ValueError("Jedna pamięć może mieć maksymalnie 30 tagów.")
        now = self._now()
        with self._lock:
            cursor = self._connection.execute(
                """INSERT INTO memories
                (content, category, tags_json, importance, source, pinned, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (content.strip(), category.strip(), json.dumps(normalized_tags, ensure_ascii=False),
                 importance, source.strip(), int(bool(pinned)), now, now),
            )
            self._connection.commit()
            return int(cursor.lastrowid)

    def get(self, memory_id: int) -> MemoryEntry | None:
        with self._lock:
            row = self._connection.execute("SELECT * FROM memories WHERE id = ?", (int(memory_id),)).fetchone()
        return self._entry(row) if row else None

    def list_memories(self, *, category: str | None = None, limit: int = 100) -> list[MemoryEntry]:
        if not 1 <= limit <= 500:
            raise ValueError("limit musi mieścić się w zakresie 1–500.")
        sql, params = "SELECT * FROM memories", []
        if category is not None:
            sql += " WHERE category = ?"
            params.append(category)
        sql += " ORDER BY pinned DESC, importance DESC, updated_at DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        return [self._entry(row) for row in rows]

    def search(self, query: str, *, limit: int = 5, category: str | None = None) -> list[MemoryEntry]:
        if not 1 <= limit <= 100:
            raise ValueError("limit musi mieścić się w zakresie 1–100.")
        if not isinstance(query, str) or not query.strip():
            return self.list_memories(category=category, limit=limit)
        terms = self._tokens(query)
        if not terms:
            return []
        sql, params = "SELECT * FROM memories", []
        if category is not None:
            sql += " WHERE category = ?"
            params.append(category)
        sql += " ORDER BY pinned DESC, importance DESC, updated_at DESC LIMIT 2000"
        with self._lock:
            rows = self._connection.execute(sql, params).fetchall()
        ranked = []
        for row in rows:
            entry = self._entry(row)
            content_tokens = self._tokens(entry.content)
            tag_tokens = self._tokens(" ".join(entry.tags))
            category_tokens = self._tokens(entry.category)
            matches, tag_matches, category_matches = (
                len(terms & content_tokens), len(terms & tag_tokens), len(terms & category_tokens)
            )
            if matches or tag_matches or category_matches:
                score = matches * 3 + tag_matches * 2 + category_matches + entry.importance * 0.1 + int(entry.pinned)
                ranked.append((score, entry))
        ranked.sort(key=lambda item: (item[0], item[1].updated_at), reverse=True)
        return [entry for _, entry in ranked[:limit]]

    def forget(self, memory_id: int) -> bool:
        with self._lock:
            cursor = self._connection.execute("DELETE FROM memories WHERE id = ?", (int(memory_id),))
            self._connection.commit()
            return cursor.rowcount > 0

    def clear(self, *, category: str | None = None, include_pinned: bool = False) -> int:
        sql, clauses, params = "DELETE FROM memories", [], []
        if category is not None:
            clauses.append("category = ?")
            params.append(category)
        if not include_pinned:
            clauses.append("pinned = 0")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        with self._lock:
            cursor = self._connection.execute(sql, params)
            self._connection.commit()
            return int(cursor.rowcount)

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "MemoryManager":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
