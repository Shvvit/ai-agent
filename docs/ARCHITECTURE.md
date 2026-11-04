# Architektura Własne AI

## Warstwy
- `api/app.py`: FastAPI, REST API, obsługa czatu, pamięci, zadań i diagnostyki.
- `apps/web/static`: interfejs przeglądarkowy; dane z API są wstawiane przez `textContent`, nie przez `innerHTML`.
- `agents/base.py`: niezależna od dostawcy pętla agenta, historia i function calling.
- `models/providers/base.py`: wspólny kontrakt adapterów, możliwości modelu i znormalizowane wywołania narzędzi.
- `models/providers/openai_compatible.py`: adapter HTTP dla API zgodnych z OpenAI Chat Completions.
- `agents/base.py::OllamaModel`: adapter lokalnej Ollama.
- `models/factory.py`: wybór adaptera na podstawie konfiguracji.
- `agents/planner.py`: przygotowanie planu dla zadania.
- `core/engine.py`: plan → wykonanie → weryfikacja wybranych rezultatów → ograniczone próby naprawy.
- `core/task_manager.py`: trwały rejestr zadań SQLite i kontrola przejść stanów.
- `models/registry.py`, `models/router.py`: rejestr modeli Ollama i regułowy routing profili.
- `tools`: operacje workspace, runner Pythona i opcjonalne wyszukiwanie WWW.
- `memory/manager.py`: lokalna pamięć leksykalna SQLite.

## Przepływ czatu
1. API waliduje wiadomość i zapisuje rozmowę.
2. Komendy pamięci są obsługiwane lokalnie bez wywołania LLM.
3. Dla Ollama router może wybrać profil modelu; routing nie jest obecnie dostępny dla innych adapterów.
4. Istotne wpisy pamięci trafiają do promptu jako kontekst.
5. Fabryka dostawców tworzy adapter. Agent używa wspólnego kontraktu `ModelProvider`, a adapter tłumaczy wiadomości i odpowiedzi na format konkretnego API.
6. Agent obsługuje dozwolone wywołania narzędzi i zapisuje odpowiedź.

## Przepływ zadania
1. Zadanie trafia do kolejki SQLite ze stanem `pending`.
2. Wykonanie zmienia stan na `running`.
3. Engine generuje plan, wykonuje zadanie i sprawdza rezultat, jeśli istnieje możliwe do sprawdzenia kryterium.
4. Zadanie kończy się jako `completed` lub `failed`; stan i wynik są zapisywane.
5. Zadania oczekujące można anulować. Aktywnego wywołania modelu nie można obecnie przerwać.

## Granice
- Dostępne adaptery: Ollama oraz API zgodne z OpenAI Chat Completions. Kompatybilność zależy od implementacji endpointu i jego obsługi tool calling.
- Adapter OpenAI-compatible wymaga `AI_API_KEY`; klucz jest pobierany ze środowiska i ukrywany w reprezentacji konfiguracji.
- Lista modeli i routing profili są obecnie specyficzne dla Ollama.
- Delegowanie specjalistów jest sekwencyjne i korzysta z tego samego modelu.
- Model routing jest regułowy; nie uruchamia benchmarków.
- Wyszukiwanie WWW wymaga klucza Tavily lub Brave; pełna przeglądarka nie jest dostępna.
- Python runner nie stanowi izolacji OS.
- Zdalny serwer jest blokowany do czasu wdrożenia uwierzytelniania.
