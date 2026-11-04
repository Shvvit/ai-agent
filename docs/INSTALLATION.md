# Instalacja i uruchamianie

## Windows 10/11
1. Zainstaluj Python 3.12 lub 3.13 (z dodaniem do PATH) i Ollama.
2. Otwórz PowerShell w katalogu repozytorium.
3. Jeśli skrypty są blokowane, wykonaj: `Set-ExecutionPolicy -Scope Process Bypass`.
4. Uruchom `./install.ps1`.
5. Pobierz model: `ollama pull qwen3:8b`.
6. Uruchom `./start.ps1` i otwórz http://127.0.0.1:8000.

## Linux
Wymagany Python 3.12 lub 3.13 oraz Ollama. Wykonaj `chmod +x install.sh start.sh`, potem `./install.sh`, `ollama pull qwen3:8b` i `./start.sh`.

## Konfiguracja
Zmienne środowiskowe: `AI_MODEL`, `AI_HOST`, `AI_TEMPERATURE`, `AI_AUTO_ROUTING`, `AI_MODEL_CODE`, `AI_MODEL_REASONING`, `AI_MODEL_FAST`, `AI_WORKSPACE`, `AI_DATA_DIR`, `AI_PORT`. Wyszukiwanie WWW wymaga `AI_WEB_SEARCH_PROVIDER` i `AI_WEB_SEARCH_API_KEY`. Domyślnie serwer nasłuchuje tylko na localhost; zdalne wiązanie jest obecnie blokowane, ponieważ uwierzytelnianie nie zostało jeszcze wdrożone. Szczegóły: `SECURITY.md`.

## Diagnostyka
Windows: `.venv/Scripts/python.exe scripts/check_environment.py`. Linux: `.venv/bin/python scripts/check_environment.py`.
