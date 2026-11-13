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
    with pytest.raises(ValueError):
        manager.cancel(task.id)
    manager.complete(task.id, "zadanie zakończone")

    queued = manager.create("Zadanie do anulowania")
    manager.cancel(queued.id)
    with pytest.raises(ValueError):
        manager.start(queued.id)


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


from core.engine import AgentEngine
from core.verifier import Verifier


def test_engine_reports_unverifiable_task_separately(tmp_path):
    class FakeAgent:
        def run(self, prompt):
            return "Plan" if "Przygotuj plan" in prompt else "Odpowiedź"

    outcome = AgentEngine(agent=FakeAgent(), verifier=Verifier(tmp_path)).run("Wyjaśnij pojęcie")
    assert outcome.success is True
    assert outcome.verified is False
    assert "nie ma automatycznego kryterium" in outcome.verification


def test_engine_does_not_claim_missing_file_was_created(tmp_path):
    class FakeAgent:
        def run(self, prompt):
            return "Plan" if "Przygotuj plan" in prompt else "Plik gotowy"

    outcome = AgentEngine(agent=FakeAgent(), verifier=Verifier(tmp_path)).run("Utwórz plik wynik.txt")
    assert outcome.success is False
    assert outcome.verified is False
    assert "Nie znaleziono pliku" in outcome.verification


def test_verifier_rejects_traversal_and_windows_absolute_paths(tmp_path):
    verifier = Verifier(tmp_path)
    assert verifier.file_exists("../outside.txt").success is False
    assert verifier.file_exists("C:\\Users\\Public\\outside.txt").success is False


def test_verifier_rejects_symlink_escape(tmp_path):
    outside = tmp_path.parent / "outside-verifier.txt"
    outside.write_text("secret", encoding="utf-8")
    link = tmp_path / "escape.txt"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        return
    verifier = Verifier(tmp_path)
    assert verifier.file_exists("escape.txt").success is False
