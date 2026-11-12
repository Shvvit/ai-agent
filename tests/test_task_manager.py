from __future__ import annotations

import pytest

from core.task_manager import TaskManager
from core.task_state import TaskStatus


def test_task_persists_and_records_state_transitions(tmp_path):
    database = tmp_path / "tasks.sqlite3"
    manager = TaskManager(database)
    task = manager.create("Zbuduj moduł pamięci", title="Moduł pamięci")
    assert task.status is TaskStatus.QUEUED
    manager.transition(task.id, TaskStatus.RUNNING)
    finished = manager.transition(
        task.id, TaskStatus.COMPLETED,
        plan="Plan", result="Gotowe", attempts=1,
    )
    assert finished.status is TaskStatus.COMPLETED
    assert finished.plan == "Plan"
    assert finished.result == "Gotowe"
    assert finished.attempts == 1
    assert [event["event"] for event in manager.events(task.id)] == [
        "created", "running", "completed"
    ]
    manager.close()

    reopened = TaskManager(database)
    assert reopened.get(task.id).status is TaskStatus.COMPLETED
    reopened.close()


def test_task_state_machine_rejects_invalid_transition(tmp_path):
    manager = TaskManager(tmp_path / "tasks.sqlite3")
    task = manager.create("Test")
    with pytest.raises(ValueError, match="Niedozwolona zmiana"):
        manager.transition(task.id, TaskStatus.COMPLETED)
    manager.close()


def test_failed_task_can_be_requeued(tmp_path):
    manager = TaskManager(tmp_path / "tasks.sqlite3")
    task = manager.create("Test")
    manager.transition(task.id, TaskStatus.RUNNING)
    failed = manager.transition(task.id, TaskStatus.FAILED, error="Provider timeout")
    queued = manager.transition(task.id, TaskStatus.QUEUED)
    assert failed.status is TaskStatus.FAILED
    assert queued.status is TaskStatus.QUEUED
    manager.close()


def test_task_manager_validates_description_and_attempts(tmp_path):
    manager = TaskManager(tmp_path / "tasks.sqlite3")
    with pytest.raises(ValueError, match="nie może być pusty"):
        manager.create(" ")
    task = manager.create("Test")
    manager.transition(task.id, TaskStatus.RUNNING)
    with pytest.raises(ValueError, match="ujemna"):
        manager.transition(task.id, TaskStatus.FAILED, attempts=-1)
    manager.close()


def test_list_tasks_can_filter_by_status(tmp_path):
    manager = TaskManager(tmp_path / "tasks.sqlite3")
    first = manager.create("Pierwsze")
    second = manager.create("Drugie")
    manager.transition(second.id, TaskStatus.RUNNING)
    assert [item.id for item in manager.list_tasks(status="running")] == [second.id]
    assert len(manager.list_tasks()) == 2
    manager.close()
