# Własne AI

Modułowy agent AI dla Windows 10/11 i Linux. Domyślnie używa lokalnej Ollama (`qwen3:8b`), ale rdzeń obsługuje też adapter API zgodnego z OpenAI Chat Completions.

## Co działa
- polski interfejs webowy z historią rozmów, wyborem modelu i usuwaniem rozmów z poziomu panelu,
- lokalna baza SQLite,
- trwała kolejka zadań: zapisywanie, podgląd statusu, wykonywanie i anulowanie zadań oczekujących,
- wspólny kontrakt dostawców modeli, adapter Ollama i adapter API zgodnego z OpenAI Chat Completions (z wywołaniami narzędzi),
- rejestr modeli Ollama i prosty router profili (kodowanie/analityka/szybkie zadania) z kontrolowanym fallbackiem,
- ograniczone narzędzie terminala tylko do komend diagnostycznych read-only (bez dowolnego shell),
- opcjonalne wyszukiwanie WWW przez API Tavily lub Brave, dostępne jako narzędzie agenta po skonfigurowaniu klucza,
- podstawowe delegowanie do agentów specjalistycznych (planista, analityk, programista, recenzent) z limitem zagnieżdżenia,
- odczyt i zapis plików w ograniczonym katalogu workspace,
- listowanie plików i wyszukiwanie tekstu w projekcie,
- uruchamianie skryptów Python z limitem czasu,
- bazowe planowanie i weryfikacja wybranych rezultatów,
- diagnostyka połączenia i wybór modelu,
- skrypty instalacji/uruchomienia dla Windows i Linux.

## Instalacja

Wymagany Python 3.12 lub 3.13. Ollama jest potrzebna dla domyślnego dostawcy lokalnego; można też skonfigurować endpoint zgodny z OpenAI Chat Completions.

**Windows 10/11 (PowerShell):**
```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\install.ps1
ollama pull qwen3:8b
.\start.ps1
```

**Linux:**
```bash
chmod +x install.sh start.sh
./install.sh
ollama pull qwen3:8b
./start.sh
```

Otwórz http://127.0.0.1:8000. Szczegóły: [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Konfiguracja

| Zmienna | Domyślnie | Opis |
|---|---|---|
| `AI_PROVIDER` | `ollama` | `ollama` lub `openai_compatible` |
| `AI_MODEL` | `qwen3:8b` | Model |
| `AI_HOST` | `http://127.0.0.1:11434` | Adres serwera Ollama |\n| `AI_BASE_URL` | `https://api.openai.com/v1` | Bazowy adres API zgodnego z OpenAI |\n| `AI_API_KEY` | — | Klucz API dla `openai_compatible` (nie zapisuj go w repozytorium) |\n| `AI_REQUEST_TIMEOUT` | `90` | Timeout żądania modelu w sekundach |
| `AI_TEMPERATURE` | `0.2` | Temperatura generowania |
| `AI_MODEL_CODE` | — | Opcjonalny model do zadań programistycznych |
| `AI_MODEL_REASONING` | — | Opcjonalny model do analizy i planowania |
| `AI_MODEL_FAST` | — | Opcjonalny model do krótkich i szybkich zadań |
| `AI_AUTO_ROUTING` | `1` | Automatyczny wybór profilu modelu w czacie (`0` wyłącza) |
| `AI_WEB_SEARCH_PROVIDER` | — | `tavily` lub `brave`; bez ustawienia wyszukiwanie jest wyłączone |
| `AI_WEB_SEARCH_API_KEY` | — | Klucz API dostawcy wyszukiwania |
| `AI_WEB_SEARCH_MAX_RESULTS` | `5` | Maksymalna liczba wyników (1–10) |
| `AI_WORKSPACE` | `./workspace` | Katalog plików agenta |
| `AI_DATA_DIR` | `./data` | Lokalna baza i dane |
| `AI_PORT` | `8000` | Port interfejsu |

## Diagnostyka możliwości

`GET /api/capabilities` zwraca listę dostępnych narzędzi i jawne ograniczenia systemu (m.in. brak sandboxa OS, brak przerywania aktywnych zadań i wyłączony zdalny dostęp). Panel diagnostyczny pokazuje te informacje bez ujawniania kluczy API.

## Testy

```powershell
python -m pip install -e ".[dev,web]"
python -m pytest -q
```

GitHub Actions sprawdza Python 3.12/3.13 na Windows i Linux, kompilację modułów, testy, składnię JavaScript i skryptów powłoki.

## Bezpieczeństwo — ważne

Serwer domyślnie nasłuchuje tylko na localhost. Nie wystawiaj go do sieci bez uwierzytelniania i dodatkowych zabezpieczeń. Pliki są ograniczone do workspace; zapisy i odczyty mają limit rozmiaru, a ścieżki traversal i symlinki są blokowane. Uruchamianie skryptów Python nadal **nie jest pełną izolacją** — skrypt może korzystać z uprawnień konta użytkownika. Uruchamiaj tylko zaufany kod.

## Czego jeszcze nie ma

To nie jest jeszcze odpowiednik pełnego komercyjnego agenta. Pamięć semantyczna, zaawansowany multi-agent (równoległa praca, różne modele, koordynator i wspólny stan), benchmark i automatyczny routing między dostawcami, adaptery do API niezgodnych z OpenAI, pełna przeglądarka i ekstrakcja treści stron (wyszukiwanie WWW ma już opcjonalną integrację Tavily/Brave), multimodalność, streaming/anulowanie, terminal z zatwierdzaniem komend, sandbox OS i bezpieczny dostęp zdalny są wymienione jako kolejne etapy. Zobacz [docs/ROADMAP.md](docs/ROADMAP.md).


## Zadania agenta

Panel zadań jest dostępny w ustawieniach interfejsu. Zadania są trwale zapisywane w SQLite. API modeli: `GET /api/models/recommend?task=...` dobiera skonfigurowany model profilu, jeśli jest zainstalowany; w przeciwnym razie używa modelu domyślnego lub najmniejszego dostępnego. To routing regułowy, nie benchmark wydajności.

### Benchmark lokalnych modeli

Aby porównać szybkość i pamięć modeli zainstalowanych w Ollama, uruchom:

```powershell
python scripts/benchmark_models.py --models qwen3:8b,qwen3:4b
```

Skrypt działa sekwencyjnie, mierzy czas ładowania, tokeny/s oraz pamięć RAM/VRAM i zapisuje raport JSON. Szczegóły i opcje: [docs/MODELS.md](docs/MODELS.md#lokalny-benchmark-ollama).

API: `POST /api/tasks` (utworzenie), `GET /api/tasks` (lista), `GET /api/tasks/{id}` (szczegóły), `POST /api/tasks/{id}/execute` (synchroniczne wykonanie przez skonfigurowanego dostawcę modelu), `POST /api/tasks/{id}/cancel` (anulowanie zadania oczekującego). Aktywnego wywołania modelu nie można jeszcze przerwać; anulowanie działa wyłącznie przed rozpoczęciem. Wykonywanie zadania blokuje żądanie do zakończenia modelu.

## Pamięć agenta

W ustawieniach interfejsu można dodawać, przeglądać i usuwać zapisane informacje. API pamięci:
- `GET /api/memory` — lista wpisów,
- `POST /api/memory` z JSON `{"content":"..." }` — zapamiętanie informacji,
- `DELETE /api/memory/{id}` — usunięcie wpisu,
- `DELETE /api/memory` — wyczyszczenie pamięci.

Pamięć jest lokalna (SQLite), ograniczona do 2000 ostatnich wpisów i przeszukiwana leksykalnie. To nie jest jeszcze pamięć wektorowa ani automatyczne profilowanie użytkownika. W czacie działają też komendy: `/remember treść`, `/memory` i `/clear_memory`.
