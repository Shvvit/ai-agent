from __future__ import annotations

from core.engine import AgentEngine


def main() -> None:
    """Uruchamia interaktywny terminal agenta Własne AI."""
    print("=" * 48)
    print("WŁASNE AI — agent w terminalu")
    print("Wpisz zadanie i naciśnij Enter.")
    print("Komendy: /help, /clear, /exit")
    print("=" * 48)
    engine = AgentEngine()
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
            print("\nDostępne komendy:\n  /help  — wyświetla pomoc\n  /clear — czyści historię rozmowy\n  /exit  — kończy działanie\n\nPozostałe wpisy są traktowane jako zadania dla agenta.")
            continue
        if command == "/clear":
            engine.agent.history.clear()
            print("Historia rozmowy została wyczyszczona.")
            continue
        try:
            print("\nWłasne AI > Pracuję nad zadaniem...")
            result = engine.run(task)
            print(f"\nPlan:\n{result.plan}")
            print(f"\nOdpowiedź:\n{result.answer}")
            print(f"\nWeryfikacja: {result.verification}")
            print("Status: " + ("SUKCES" if result.success else "NIEPOTWIERDZONE"))
        except Exception as exc:
            print(f"\nBłąd: {type(exc).__name__}: {exc}\nSprawdź, czy Ollama działa i czy wybrany model jest dostępny.")


if __name__ == "__main__":
    main()
