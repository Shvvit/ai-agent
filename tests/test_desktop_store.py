from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from apps.desktop.main import SessionStore


def test_desktop_session_store_persists_sessions_and_messages(tmp_path):
    store = SessionStore(tmp_path / "sessions.sqlite3")
    session_id = store.create_session()
    store.add_message(session_id, "user", "Zaprojektuj interfejs")
    store.add_message(session_id, "assistant", "Przygotuję projekt.")
    sessions = store.list_sessions()
    assert sessions[0]["id"] == session_id
    assert sessions[0]["title"] == "Zaprojektuj interfejs"
    messages = store.get_messages(session_id)
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "Zaprojektuj interfejs"
    store.close()


def test_desktop_session_store_keeps_conversations_separate(tmp_path):
    store = SessionStore(tmp_path / "sessions.sqlite3")
    first = store.create_session()
    second = store.create_session()
    store.add_message(first, "user", "Pierwsza rozmowa")
    store.add_message(second, "user", "Druga rozmowa")
    assert [m["content"] for m in store.get_messages(first)] == ["Pierwsza rozmowa"]
    assert [m["content"] for m in store.get_messages(second)] == ["Druga rozmowa"]
    store.close()
