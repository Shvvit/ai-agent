# Konfiguracja

Ustawienia są przekazywane przez zmienne środowiskowe. Domyślnie agent używa lokalnej Ollama. Dostawcę można zmienić bez modyfikowania kodu rdzenia.

## Dostawca modelu

| Zmienna | Domyślnie | Znaczenie |
|---|---|---|
| `AI_PROVIDER` | `ollama` | `ollama` albo `openai_compatible` |
| `AI_MODEL` | `qwen3:8b` | Identyfikator modelu u wybranego dostawcy |
| `AI_HOST` | `http://127.0.0.1:11434` | Adres serwera Ollama |
| `AI_BASE_URL` | `https://api.openai.com/v1` | Bazowy adres API zgodnego z OpenAI Chat Completions |
| `AI_API_KEY` | puste | Klucz API wymagany dla `openai_compatible`; nie zapisuj go w repozytorium |
| `AI_TEMPERATURE` | `0.2` | Temperatura 0–2 |
| `AI_REQUEST_TIMEOUT` | `90` | Limit czasu żądania modelu w sekundach, 1–600 |

Adapter `openai_compatible` obsługuje endpointy zgodne z formatem Chat Completions, w tym OpenAI i serwery implementujące ten sam format. Nie oznacza to automatycznej kompatybilności ze wszystkimi API ani obsługi wszystkich funkcji danego dostawcy. Routing profili i wykrywanie listy modeli pozostają obecnie funkcjami specyficznymi dla Ollama.

## Pozostałe ustawienia

| Zmienna | Domyślnie | Znaczenie |
|---|---|---|
| `AI_AUTO_ROUTING` | `1` | Regułowy dobór profilu modelu w Ollama |
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

## Przykład PowerShell — Ollama

```powershell
$env:AI_PROVIDER = "ollama"
$env:AI_MODEL = "qwen3:8b"
$env:AI_MODEL_CODE = "qwen2.5-coder:7b"
$env:AI_AUTO_ROUTING = "1"
.\start.ps1
```

## Przykład PowerShell — API zgodne z OpenAI

```powershell
$env:AI_PROVIDER = "openai_compatible"
$env:AI_MODEL = "nazwa-modelu"
$env:AI_BASE_URL = "https://api.openai.com/v1"
$env:AI_API_KEY = "wstaw-klucz-w-lokalnym-terminalu"
.\start.ps1
```

## Przykład Linux

```bash
export AI_PROVIDER=ollama
export AI_MODEL=qwen3:8b
export AI_MODEL_CODE=qwen2.5-coder:7b
export AI_AUTO_ROUTING=1
./start.sh
```

Model profilu musi być zainstalowany w Ollama, aby router mógł go wybrać. Gdy go brakuje, router używa modelu domyślnego. Jeśli model domyślny nie jest zainstalowany, wybiera najmniejszy dostępny model. Wybór nie jest benchmarkiem.

Klucze API należy przechowywać w zmiennych środowiskowych lub bezpiecznym magazynie sekretów. Nie umieszczaj ich w plikach śledzonych przez Git, logach, zgłoszeniach ani zrzutach diagnostycznych.
