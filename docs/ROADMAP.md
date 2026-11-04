# Status funkcji

## Działające elementy w tej wersji
- lokalny adapter Ollama i wywołania narzędzi function-calling,
- rejestr modeli i regułowy router profili z automatycznym wyborem modelu, gdy profile są skonfigurowane,
- opcjonalne wyszukiwanie WWW przez Tavily/Brave (wymaga klucza API),
- trwała kolejka zadań i panel zarządzania zadaniami, z planowaniem i weryfikacją rezultatów,
- podstawowe delegowanie do ról specjalistycznych (planner/analyst/coder/reviewer), z wyłączonym rekurencyjnym delegowaniem i limitem podzadań,
- webowy interfejs rozmowy po polsku,
- lokalna historia SQLite,
- trwała pamięć faktów SQLite: ręczne dodawanie, wyszukiwanie kontekstowe, usuwanie pojedynczych wpisów i czyszczenie pamięci,
- panel zarządzania pamięcią w ustawieniach,
- odczyt/zapis plików w workspace,
- uruchamianie skryptów Python z limitem czasu,
- podstawowe planowanie i weryfikacja wybranych rezultatów,
- skrypty startowe Windows 10/11 i Linux,
- CI dla Python 3.12 i 3.13.

## Wymaga dalszej implementacji
- pamięć semantyczna/wektorowa, automatyczne wydobywanie faktów i trwałe profile użytkownika,
- zaawansowany koordynator multi-agent: praca równoległa, współdzielony stan zadań, osobne modele/limity i niezależne potwierdzanie wyników,
- benchmark modeli lokalnych, dobór na podstawie rzeczywistych testów i routing wielu dostawców,
- pełna przeglądarka i ekstrakcja treści stron z kontrolą zgód (samo wyszukiwanie WWW jest dostępne opcjonalnie),
- terminal z komendami modyfikującymi i approval workflow (read-only allowlista diagnostyczna już działa),
- obsługa obrazów/audio/wideo,
- streaming odpowiedzi i przerywanie aktywnych zadań (anulowanie oczekujących zadań już działa),
- izolowany sandbox OS (AppContainer/seccomp/kontenery),
- audyt, uwierzytelnianie i bezpieczny tryb zdalny.

Funkcje planowane nie są dostępne. Uruchamianie kodu Python nie jest pełną izolacją bezpieczeństwa.


## Zaimplementowane pozycje
- [x] Trwała kolejka zadań SQLite z kontrolą stanów pending/running/completed/failed/cancelled.
- [x] API i panel WWW do tworzenia, przeglądania, uruchamiania oraz anulowania zadań oczekujących.
- [x] Regułowy routing profili modeli Ollama z testami i fallbackiem.
- [x] Opcjonalne wyszukiwanie WWW Tavily/Brave.
- [x] Ograniczony terminal diagnostyczny read-only z allowlistą i testami.
- [ ] Asynchroniczne worker-y, wznowienie po restarcie, retry policy i prawdziwe przerywanie aktywnych zadań.
