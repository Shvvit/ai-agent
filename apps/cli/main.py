from __future__ import annotations

from core.engine import AgentEngine
from memory.manager import MemoryManager


def main() -> None:
    """Uruchamia interaktywny terminal agenta Własne AI."""
    print("=" * 48)
    print("WŁASNE AI — agent w terminalu")
    print("Wpisz zadanie i naciśnij Enter.")
    print("Komendy: /help, /remember, /memory, /search, /forget, /clear, /exit")
    print("=" * 48)

    memory = MemoryManager()
    engine = AgentEngine(memory=memory)
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
            if command == "/clear":
                engine.agent.history.clear()
                print("Historia bieżącej rozmowy została wyczyszczona. Pamięć długoterminowa pozostała bez zmian.")
                continue

            try:
                print("\nWłasne AI > Pracuję nad zadaniem...")
                result = engine.run(task)
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


if __name__ == "__main__":
    main()
