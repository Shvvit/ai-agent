# Bezpieczeństwo

## Domyślne uruchomienie
- Uruchamiaj aplikację przez `start.ps1` lub `start.sh`; serwer nasłuchuje domyślnie wyłącznie na `127.0.0.1`.
- Zdalne wiązanie adresu jest obecnie blokowane przez `scripts/run.py`. Nie jest jeszcze zaimplementowany bezpieczny mechanizm logowania, zarządzania sesją ani ochrony CSRF.
- Nie wystawiaj aplikacji przez port forwarding, tunel ani reverse proxy. Samo ustawienie zmiennej środowiskowej nie dodaje uwierzytelniania.

## Workspace i narzędzia
- Operacje plikowe są ograniczone do katalogu workspace; odrzucane są ścieżki absolutne, traversal i symlinki.
- Wyszukiwanie plików ma limity rozmiaru pliku, całkowitego skanowania i liczby wyników.
- Wyszukiwanie WWW jest wyłączone, dopóki nie podasz dostawcy i klucza API. Klucz przechowuj w zmiennej środowiskowej, nigdy w repozytorium.
- Uruchamianie Pythona przez `run_python` nie jest sandboxem. Proces działa z uprawnieniami konta użytkownika i może czytać lub modyfikować pliki poza workspace, korzystać z sieci i uruchamiać inne procesy. Uruchamiaj tylko kod, któremu ufasz.

## Modele i dane
- Historia rozmów, pamięć i zadania są przechowywane lokalnie w SQLite.
- Kontekst pamięci jest przekazywany do modelu jako dane, a nie jako instrukcje systemowe. Nadal weryfikuj treści wygenerowane przez model.
- Klucze API dostawców przechowuj wyłącznie w zmiennych środowiskowych lub bezpiecznym menedżerze sekretów.

## Co pozostaje do zrobienia
Uwierzytelnianie, role i uprawnienia, audyt działań, approval workflow dla operacji wysokiego ryzyka, sandbox OS (np. AppContainer/seccomp/kontener), ochrona przed SSRF w przeglądarce i bezpieczny dostęp zdalny nie są jeszcze zaimplementowane.
