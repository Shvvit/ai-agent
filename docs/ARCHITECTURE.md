# Architektura Własne AI

## Warstwy
- `api/app.py`: FastAPI, REST API, obsługa czatu, pamięci, zadań i diagnostyki.
- `apps/web/static`: interfejs przeglądarkowy; dane z API są wstawiane przez `textContent`, nie przez `innerHTML`.
- `agents/base.py`: pętla modelu Ollama, historia i function calling.
- `agents/planner.py`: przygotowanie planu dla zadania.
- `core/engine.py`: plan → wykonanie → weryfikacja wybranych rezultatów → ograniczone próby naprawy.
- `core/task_manager.py`: trwały rejestr zadań SQLite i kontrola przejść stanów.
- `models`: normalizacja listy modeli i regułowy routing profili.
- `tools`: operacje workspace, runner Pythona i opcjonalne wyszukiwanie WWW.
- `memory/manager.py`: lokalna pamięć leksykalna SQLite.

## Przepływ czatu
1. API waliduje wiadomość i zapisuje rozmowę.
2. Komendy pamięci są obsługiwane lokalnie bez wywołania LLM.
3. Router wybiera profil modelu, jeżeli dostępny jest skonfigurowany model.
4. Istotne wpisy pamięci trafiają do promptu jako kontekst.
5. Agent wysyła wiadomość do Ollama, obsługuje dozwolone wywołania narzędzi i zapisuje odpowiedź.

## Przepływ zadania
1. Zadanie trafia do kolejki SQLite ze stanem `pending`.
2. Wykonanie zmienia stan na `running`.
3. Engine generuje plan, wykonuje zadanie i sprawdza rezultat, jeśli istnieje możliwe do sprawdzenia kryterium.
4. Zadanie kończy się jako `completed` lub `failed`; stan i wynik są zapisywane.
5. Zadania oczekujące można anulować. Aktywnego wywołania modelu nie można obecnie przerwać.

## Granice
- Delegowanie specjalistów jest sekwencyjne i korzysta z tego samego modelu.
- Model routing jest regułowy; nie uruchamia benchmarków.
- Wyszukiwanie WWW wymaga klucza Tavily lub Brave; pełna przeglądarka nie jest dostępna.
- Python runner nie stanowi izolacji OS.
- Zdalny serwer jest blokowany do czasu wdrożenia uwierzytelniania.
