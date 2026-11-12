from __future__ import annotations

from core.engine import AgentEngine
from core.task_manager import TaskManager
from memory.manager import MemoryManager


def main() -> None:
    """Uruchamia interaktywny terminal agenta Własne AI."""
    print("=" * 48)
    print("WŁASNE AI — agent w terminalu")
    print("Wpisz zadanie i naciśnij Enter.")
    print("Komendy: /help, /remember, /memory, /search, /forget, /tasks, /task, /retry, /clear, /exit")
    print("=" * 48)

    memory = MemoryManager()
    tasks = TaskManager()
    engine = AgentEngine(memory=memory, task_manager=tasks)
    try:
        while True:
            try:
                task = input("\nTy > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nZamykanie Własne AI.")
                break
            if not task:
                continue

            command = task.lower()
            if command in {"/exit", "/quit"}:
                print("Zamykanie Własne AI.")
                break
            if command == "/help":
                print(
                    "\nDostępne komendy:"
                    "\n  /help             — wyświetla pomoc"
                    "\n  /remember TEKST   — zapisuje notatkę do pamięci długoterminowej"
                    "\n  /memory           — wyświetla zapisane notatki"
                    "\n  /search TEKST     — wyszukuje w pamięci"
                    "\n  /forget ID        — usuwa notatkę o podanym ID"
                    "\n  /tasks            — pokazuje ostatnie zadania"
                    "\n  /task ID          — pokazuje szczegóły zadania"
                    "\n  /clear            — czyści historię bieżącej rozmowy"
                    "\n  /exit             — kończy działanie"
                )
                continue
            if task.startswith("/remember "):
                content = task[len("/remember "):].strip()
                try:
                    memory_id = memory.remember(content, category="user_note", source="cli")
                    print(f"Zapisano notatkę w pamięci (ID: {memory_id}).")
                except ValueError as exc:
                    print(f"Nie zapisano: {exc}")
                continue
            if command == "/memory":
                entries = memory.list_memories(limit=30)
                if not entries:
                    print("Pamięć jest pusta.")
                for entry in entries:
                    print(f"[{entry.id}] ({entry.category}, ważność {entry.importance}) {entry.content}")
                continue
            if task.startswith("/search "):
                query = task[len("/search "):].strip()
                entries = memory.search(query, limit=10)
                if not entries:
                    print("Nie znaleziono pasujących notatek.")
                for entry in entries:
                    print(f"[{entry.id}] ({entry.category}) {entry.content}")
                continue
            if task.startswith("/forget "):
                raw_id = task[len("/forget "):].strip()
                try:
                    deleted = memory.forget(int(raw_id))
                    print("Usunięto notatkę." if deleted else "Nie znaleziono notatki o takim ID.")
                except ValueError:
                    print("Podaj prawidłowe ID, np. /forget 3.")
                continue
            if command == "/tasks":
                records = tasks.list_tasks(limit=20)
                if not records:
                    print("Brak zapisanych zadań.")
                for record in records:
                    print(f"[{record.id}] {record.status.value.upper()} — {record.title}")
                continue
            if task.startswith("/task "):
                task_id = task[len("/task "):].strip()
                record = tasks.get(task_id)
                if record is None:
                    print("Nie znaleziono zadania o takim ID.")
                else:
                    print(f"ID: {record.id}\nStatus: {record.status.value}\nTytuł: {record.title}")
                    print(f"Opis: {record.description}\nPlan: {record.plan}")
                    print(f"Wynik: {record.result}\nBłąd: {record.error}")
                continue
            if task.startswith("/retry "):
                task_id = task[len("/retry "):].strip()
                try:
                    result = engine.retry(task_id)
                    print(f"Ponowiono zadanie {result.task_id}.")
                    print(f"\nOdpowiedź:\n{result.answer}")
                    print(f"Weryfikacja: {result.verification}")
                    print("Status: " + ("SUKCES" if result.success else "NIEPOTWIERDZONE"))
                except (KeyError, ValueError, RuntimeError) as exc:
                    print(f"Nie można ponowić zadania: {exc}")
                continue
            if command == "/clear":
                engine.agent.history.clear()
                print("Historia bieżącej rozmowy została wyczyszczona. Pamięć i historia zadań pozostały bez zmian.")
                continue

            try:
                print("\nWłasne AI > Pracuję nad zadaniem...")
                result = engine.run(task)
                if result.task_id:
                    print(f"\nID zadania: {result.task_id}")
                print(f"\nPlan:\n{result.plan}")
                print(f"\nOdpowiedź:\n{result.answer}")
                print(f"\nWeryfikacja: {result.verification}")
                print("Status: " + ("SUKCES" if result.success else "NIEPOTWIERDZONE"))
            except Exception as exc:
                print(
                    f"\nBłąd: {type(exc).__name__}: {exc}"
                    "\nSprawdź, czy wybrany provider/model jest dostępny."
                )
    finally:
        memory.close()
        tasks.close()


if __name__ == "__main__":
    main()
