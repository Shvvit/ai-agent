# Rozwiązywanie problemów

## Ollama offline
1. Uruchom aplikację Ollama.
2. W terminalu wykonaj `ollama list`.
3. Jeśli modelu nie ma, wykonaj np. `ollama pull qwen3:8b`.
4. Sprawdź `AI_HOST`; domyślnie to `http://127.0.0.1:11434`.

## Brak modeli
Sprawdź `/api/models` i upewnij się, że nazwa w `AI_MODEL` jest zgodna z nazwą z Ollama. Router profili wymaga, aby model profilu był zainstalowany.

## Błąd importu lub zależności
Użyj wspieranej wersji Pythona 3.12 lub 3.13 i uruchom ponownie instalator projektu. Dla testów: `python -m pip install -e ".[dev,web]"`.

## Zadanie pozostaje pending
Zadanie nie jest uruchamiane automatycznie w tle; kliknij Uruchom w panelu zadań. Obecny executor działa synchronicznie.

## Wyszukiwanie WWW
Ustaw `AI_WEB_SEARCH_PROVIDER=tavily` lub `brave` oraz `AI_WEB_SEARCH_API_KEY`. Bez obu ustawień narzędzie jest wyłączone.

## Zdalny dostęp
Zdalne wiązanie serwera jest celowo blokowane. Nie wystawiaj aplikacji publicznie, dopóki nie zostanie dodane uwierzytelnianie i bezpieczny model sesji.
