# Własne AI

Lokalny agent AI dla Windows 10/11 i Linux, oparty obecnie na Ollama. Domyślny model to `qwen3:8b`; można wybrać dowolny model obecny w lokalnej bibliotece Ollama.

## Co działa
- polski interfejs webowy z historią rozmów, wyborem modelu i usuwaniem rozmów z poziomu panelu,
- lokalna baza SQLite,
- adapter Ollama i obsługa wywołań narzędzi,
- podstawowe delegowanie do agentów specjalistycznych (planista, analityk, programista, recenzent) z limitem zagnieżdżenia,
- odczyt i zapis plików w ograniczonym katalogu workspace,
- listowanie plików i wyszukiwanie tekstu w projekcie,
- uruchamianie skryptów Python z limitem czasu,
- bazowe planowanie i weryfikacja wybranych rezultatów,
- diagnostyka połączenia i wybór modelu,
- skrypty instalacji/uruchomienia dla Windows i Linux.

## Instalacja

Wymagany Python 3.12 lub 3.13 i zainstalowana aplikacja Ollama.

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
| `AI_PROVIDER` | `ollama` | Dostawca (obecnie Ollama) |
| `AI_MODEL` | `qwen3:8b` | Model |
| `AI_HOST` | `http://127.0.0.1:11434` | Adres serwera Ollama |
| `AI_TEMPERATURE` | `0.2` | Temperatura generowania |
| `AI_WORKSPACE` | `./workspace` | Katalog plików agenta |
| `AI_DATA_DIR` | `./data` | Lokalna baza i dane |
| `AI_PORT` | `8000` | Port interfejsu |

## Testy

```powershell
python -m pip install -e ".[dev,web]"
python -m pytest -q
```

GitHub Actions sprawdza Python 3.12/3.13 na Windows i Linux, kompilację modułów, testy, składnię JavaScript i skryptów powłoki.

## Bezpieczeństwo — ważne

Serwer domyślnie nasłuchuje tylko na localhost. Nie wystawiaj go do sieci bez uwierzytelniania i dodatkowych zabezpieczeń. Pliki są ograniczone do workspace; zapisy i odczyty mają limit rozmiaru, a ścieżki traversal i symlinki są blokowane. Uruchamianie skryptów Python nadal **nie jest pełną izolacją** — skrypt może korzystać z uprawnień konta użytkownika. Uruchamiaj tylko zaufany kod.

## Czego jeszcze nie ma

To nie jest jeszcze odpowiednik pełnego komercyjnego agenta. Pamięć semantyczna, zaawansowany multi-agent (równoległa praca, różne modele, koordynator i wspólny stan), routing/benchmark modeli, integracje API chmurowych, przeglądarka i wyszukiwanie WWW, multimodalność, streaming/anulowanie, terminal z zatwierdzaniem komend, sandbox OS i bezpieczny dostęp zdalny są wymienione jako kolejne etapy. Zobacz [docs/ROADMAP.md](docs/ROADMAP.md).


## Pamięć agenta

W ustawieniach interfejsu można dodawać, przeglądać i usuwać zapisane informacje. API pamięci:
- `GET /api/memory` — lista wpisów,
- `POST /api/memory` z JSON `{"content":"..." }` — zapamiętanie informacji,
- `DELETE /api/memory/{id}` — usunięcie wpisu,
- `DELETE /api/memory` — wyczyszczenie pamięci.

Pamięć jest lokalna (SQLite), ograniczona do 2000 ostatnich wpisów i przeszukiwana leksykalnie. To nie jest jeszcze pamięć wektorowa ani automatyczne profilowanie użytkownika. W czacie działają też komendy: `/remember treść`, `/memory` i `/clear_memory`.
