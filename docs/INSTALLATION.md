# Instalacja i uruchamianie

## Windows 10/11
1. Zainstaluj Python 3.12 (z dodaniem do PATH) i Ollama.
2. Otwórz PowerShell w katalogu repozytorium.
3. Jeśli skrypty są blokowane, wykonaj: `Set-ExecutionPolicy -Scope Process Bypass`.
4. Uruchom `./install.ps1`.
5. Pobierz model: `ollama pull qwen3:8b`.
6. Uruchom `./start.ps1` i otwórz http://127.0.0.1:8000.

## Linux
Wymagany Python 3.12 lub 3.13 oraz Ollama. Wykonaj `chmod +x install.sh start.sh`, potem `./install.sh`, `ollama pull qwen3:8b` i `./start.sh`.

## Konfiguracja
Zmienne środowiskowe: `AI_MODEL`, `AI_HOST`, `AI_TEMPERATURE`, `AI_WORKSPACE`, `AI_DATA_DIR`, `AI_PORT`. Domyślnie serwer nasłuchuje tylko na localhost. Nie ustawiaj hosta na 0.0.0.0 bez własnego uwierzytelniania i ochrony sieciowej.

## Diagnostyka
Windows: `.venv/Scripts/python.exe scripts/check_environment.py`. Linux: `.venv/bin/python scripts/check_environment.py`.
