# Status funkcji

## Działające elementy w tej wersji
- lokalny adapter Ollama i wywołania narzędzi function-calling,
- webowy interfejs rozmowy po polsku,
- lokalna historia SQLite,
- odczyt/zapis plików w workspace,
- uruchamianie skryptów Python z limitem czasu,
- podstawowe planowanie i weryfikacja wybranych rezultatów,
- skrypty startowe Windows 10/11 i Linux,
- CI dla Python 3.12 i 3.13.

## Wymaga dalszej implementacji
- pamięć semantyczna i trwałe profile użytkownika,
- wieloagentowe delegowanie i koordynator,
- routing i benchmark modeli lokalnych/zewnętrznych,
- wyszukiwanie WWW i przeglądarka z kontrolą zgód,
- terminal z allowlistą komend i potwierdzeniami,
- obsługa obrazów/audio/wideo,
- streaming odpowiedzi i anulowanie zadań,
- izolowany sandbox OS (AppContainer/seccomp/kontenery),
- audyt, uwierzytelnianie i bezpieczny tryb zdalny.

Funkcje planowane nie są dostępne. Uruchamianie kodu Python nie jest pełną izolacją bezpieczeństwa.
