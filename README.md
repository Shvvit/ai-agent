# Własne AI

Lokalny, rozszerzalny agent AI dla Windows/Linux. Projekt jest rozwijany z myślą o pracy z Ollama, ograniczonym VRAM i możliwości dołączania dostawców modeli oraz narzędzi.

## Aktualny zakres
- adapter modelu Ollama (domyślnie `qwen3:8b`),
- interfejs webowy w języku polskim,
- historia rozmów przechowywana lokalnie w SQLite,
- narzędzia workspace: odczyt/zapis plików i uruchamianie skryptów Python,
- bazowa warstwa planowania i weryfikacji,
- testy automatyczne i CI dla Python 3.12/3.13.

## Wymagania
- Python 3.12 lub 3.13,
- Ollama dla lokalnego modelu,
- model pobrany w Ollama, np. `ollama pull qwen3:8b`.

## Instalacja (Windows PowerShell)
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,web]"
ollama pull qwen3:8b
$env:AI_MODEL = "qwen3:8b"
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

Otwórz http://127.0.0.1:8000.

## Konfiguracja
| Zmienna | Domyślna wartość | Znaczenie |
|---|---|---|
| `AI_PROVIDER` | `ollama` | Dostawca modelu |
| `AI_MODEL` | `qwen3:8b` | Nazwa modelu Ollama |
| `AI_HOST` | `http://127.0.0.1:11434` | Adres Ollama |
| `AI_TEMPERATURE` | `0.2` | Temperatura generowania |
| `AI_WORKSPACE` | `./workspace` | Katalog roboczy agenta |
| `AI_DATA_DIR` | `./data` | Lokalna baza i dane |

## Testy
```powershell
python -m pip install -e ".[dev,web]"
python -m pytest -q
```

## Bezpieczeństwo
Aplikacja domyślnie nasłuchuje tylko na localhost. Nie wystawiaj jej do sieci bez dodania uwierzytelniania, ochrony CSRF, limitów żądań i kontroli dostępu. Narzędzia plikowe ograniczają ścieżki do workspace, ale uruchamianie kodu Pythona nie jest pełną izolacją systemową — traktuj workspace jako zaufany katalog i nie uruchamiaj nieznanego kodu.

## Status projektu
To aktywnie rozwijany projekt. Funkcje oznaczone jako planowane nie są deklarowane jako gotowe. Integracje z chmurą, multimodalność, trwała pamięć semantyczna, delegowanie do wielu agentów i bezpieczna izolacja procesów wymagają dalszej implementacji oraz testów.
