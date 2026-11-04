from __future__ import annotations

import pytest

from core.task_manager import TaskManager
from core.task_state import TaskStatus


def test_task_lifecycle_persists_across_manager_instances(tmp_path):
    database = tmp_path / "tasks.sqlite3"
    manager = TaskManager(database)
    created = manager.create("Zbuduj moduł i uruchom testy", "Moduł")
    assert created.status is TaskStatus.PENDING

    started = manager.start(created.id)
    assert started.status is TaskStatus.RUNNING
    completed = manager.complete(created.id, "Wszystkie testy przeszły")

    restored = TaskManager(database).get(created.id)
    assert restored == completed
    assert restored.status is TaskStatus.COMPLETED
    assert restored.result == "Wszystkie testy przeszły"
    assert restored.started_at and restored.finished_at


def test_task_state_transitions_are_enforced(tmp_path):
    manager = TaskManager(tmp_path / "tasks.sqlite3")
    task = manager.create("Zadanie")
    with pytest.raises(ValueError):
        manager.complete(task.id, "nie można zakończyć przed startem")
    manager.start(task.id)
    manager.cancel(task.id)
    with pytest.raises(ValueError):
        manager.complete(task.id, "anulowane zadanie nie może się zakończyć")


def test_task_validation_and_missing_ids(tmp_path):
    manager = TaskManager(tmp_path / "tasks.sqlite3")
    with pytest.raises(ValueError):
        manager.create("  ")
    with pytest.raises(KeyError):
        manager.start("missing")
    task = manager.create("Zadanie")
    assert manager.list(status=TaskStatus.PENDING) == [task]


def test_failed_tasks_capture_error(tmp_path):
    manager = TaskManager(tmp_path / "tasks.sqlite3")
    task = manager.create("Zadanie")
    manager.start(task.id)
    failed = manager.fail(task.id, "Ollama offline")
    assert failed.status is TaskStatus.FAILED
    assert failed.error == "Ollama offline"
