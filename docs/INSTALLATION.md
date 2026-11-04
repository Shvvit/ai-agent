# Instalacja i uruchamianie

Wymagany jest Python 3.12 lub 3.13. Ollama jest potrzebna tylko wtedy, gdy używasz domyślnego lokalnego dostawcy `ollama`. Możesz zamiast niej skonfigurować zewnętrzny lub lokalny endpoint zgodny z OpenAI Chat Completions.

## Windows 10/11 — Ollama
1. Zainstaluj Python 3.12 lub 3.13 (z dodaniem do PATH) i Ollama.
2. Otwórz PowerShell w katalogu repozytorium.
3. Jeśli skrypty są blokowane, wykonaj: `Set-ExecutionPolicy -Scope Process Bypass`.
4. Uruchom `./install.ps1`.
5. Pobierz model: `ollama pull qwen3:8b`.
6. Uruchom `./start.ps1` i otwórz http://127.0.0.1:8000.

## Linux — Ollama
Wymagany Python 3.12 lub 3.13 oraz Ollama. Wykonaj `chmod +x install.sh start.sh`, potem `./install.sh`, `ollama pull qwen3:8b` i `./start.sh`.

## Dostawca zgodny z OpenAI Chat Completions
Po instalacji zależności ustaw zmienne środowiskowe przed uruchomieniem.

PowerShell:
```powershell
$env:AI_PROVIDER = "openai_compatible"
$env:AI_MODEL = "nazwa-modelu"
$env:AI_BASE_URL = "https://api.openai.com/v1"
$env:AI_API_KEY = "klucz-api"
./start.ps1
```

Linux:
```bash
export AI_PROVIDER=openai_compatible
export AI_MODEL=nazwa-modelu
export AI_BASE_URL=https://api.openai.com/v1
export AI_API_KEY=klucz-api
./start.sh
```

Dla endpointów lokalnych ustaw odpowiedni `AI_BASE_URL`. Nie każdy serwer zgodny z częścią formatu OpenAI obsługuje również wywołania narzędzi.

## Konfiguracja
Zmienne środowiskowe: `AI_PROVIDER`, `AI_MODEL`, `AI_HOST`, `AI_BASE_URL`, `AI_API_KEY`, `AI_TEMPERATURE`, `AI_REQUEST_TIMEOUT`, `AI_AUTO_ROUTING`, `AI_MODEL_CODE`, `AI_MODEL_REASONING`, `AI_MODEL_FAST`, `AI_WORKSPACE`, `AI_DATA_DIR`, `AI_PORT`. Wyszukiwanie WWW wymaga `AI_WEB_SEARCH_PROVIDER` i `AI_WEB_SEARCH_API_KEY`. Domyślnie serwer nasłuchuje tylko na localhost; zdalne wiązanie jest obecnie blokowane, ponieważ uwierzytelnianie nie zostało jeszcze wdrożone. Szczegóły: `SECURITY.md`.

Klucze API przechowuj wyłącznie lokalnie w środowisku lub bezpiecznym magazynie sekretów. Nie commituj ich do Git.

## Diagnostyka
Windows: `.venv/Scripts/python.exe scripts/check_environment.py`. Linux: `.venv/bin/python scripts/check_environment.py`.
