# Konfiguracja

Wszystkie ustawienia są przekazywane przez zmienne środowiskowe. Domyślne uruchomienie jest lokalne.

| Zmienna | Domyślnie | Znaczenie |
|---|---|---|
| `AI_PROVIDER` | `ollama` | Jedyny obecnie obsługiwany provider |
| `AI_MODEL` | `qwen3:8b` | Model domyślny |
| `AI_HOST` | `http://127.0.0.1:11434` | Adres Ollama |
| `AI_TEMPERATURE` | `0.2` | Temperatura 0–2 |
| `AI_AUTO_ROUTING` | `1` | Regułowy dobór profilu modelu |
| `AI_MODEL_CODE` | puste | Model dla kodowania |
| `AI_MODEL_REASONING` | puste | Model dla analizy/planowania |
| `AI_MODEL_FAST` | puste | Model dla krótkich zadań |
| `AI_WORKSPACE` | `./workspace` | Katalog operacji plikowych |
| `AI_DATA_DIR` | `./data` | Baza SQLite i dane |
| `AI_PORT` | `8000` | Port interfejsu |
| `AI_WEB_SEARCH_PROVIDER` | puste | `tavily` lub `brave` |
| `AI_WEB_SEARCH_API_KEY` | puste | Klucz wyszukiwarki |
| `AI_WEB_SEARCH_MAX_RESULTS` | `5` | 1–10 wyników |
| `AI_WEB_SEARCH_TIMEOUT` | `12` | Timeout API w sekundach |

Przykład PowerShell:
```powershell
$env:AI_MODEL = "qwen3:8b"
$env:AI_MODEL_CODE = "qwen2.5-coder:7b"
$env:AI_AUTO_ROUTING = "1"
.\start.ps1
```

Przykład Linux:
```bash
export AI_MODEL=qwen3:8b
export AI_MODEL_CODE=qwen2.5-coder:7b
export AI_AUTO_ROUTING=1
./start.sh
```

Model profilu musi być zainstalowany w Ollama, aby router mógł go wybrać. Gdy go brakuje, router używa modelu domyślnego. Jeśli model domyślny nie jest zainstalowany, wybiera najmniejszy dostępny model. Wybór nie jest benchmarkiem.
