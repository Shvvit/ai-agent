# Własne AI

Modularny agent AI rozwijany na bazie istniejącego projektu oraz wybranych, udokumentowanych wzorców z [Agent Zero](https://github.com/agent0ai/agent-zero).

## Status

Projekt jest w trakcie przebudowy. Nie wszystkie katalogi są już zaimplementowane. Gałąź integracyjna dodaje wspólny interfejs modeli, obsługę Ollama i API zgodnego z OpenAI Chat Completions (w tym OpenRouter), kontrolowany tool loop oraz testy.

## Wymagania

- Python 3.12
- Ollama (dla modeli lokalnych) albo klucz API (dla modeli chmurowych)
- Windows, Linux lub macOS

## Instalacja (Windows PowerShell)

~~~powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
~~~

Linux/macOS:

~~~bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
~~~

## Konfiguracja: Ollama

~~~bash
ollama pull qwen3:8b
~~~

Domyślnie agent używa adresu http://127.0.0.1:11434 i modelu qwen3:8b.

## Konfiguracja: OpenRouter

Ustaw zmienne środowiskowe przed uruchomieniem:

~~~powershell
$env:AI_PROVIDER="openrouter"
$env:AI_MODEL="openai/gpt-4.1-mini"
$env:OPENROUTER_API_KEY="YOUR_API_KEY"
python -m apps.cli.main
~~~

Dla dowolnego endpointu zgodnego z OpenAI Chat Completions:

- AI_PROVIDER=openai_compatible
- AI_BASE_URL=https://your-provider.example/v1
- AI_API_KEY=YOUR_API_KEY
- AI_MODEL=provider/model-name

Dodatkowe ustawienia:

- AI_TEMPERATURE — od 0 do 2, domyślnie 0.2
- AI_TIMEOUT — limit zapytania w sekundach, domyślnie 120
- AI_HOST — alternatywny adres serwera, ma pierwszeństwo przed AI_BASE_URL

Nie commituj prawdziwych kluczy API. Plik .env.example jest tylko wzorem; obecna konfiguracja czyta zmienne środowiskowe systemu. Uruchamianie wygenerowanego kodu Python jest domyślnie zablokowane, ponieważ subprocess nie jest piaskownicą. Aby jawnie włączyć uruchamianie zaufanego kodu, ustaw `$env:AI_ALLOW_UNSANDBOXED_PYTHON="1"` w PowerShell. Nie włączaj tego dla nieznanego kodu.

## Testy

~~~bash
python -m pytest -q
~~~

Testy providerów są mockowane i nie wymagają działającego Ollama ani płatnego klucza API. Testy integracyjne z rzeczywistymi modelami będą osobnym etapem.

## Automatyczny wybór modelu

Domyślnie `AI_ROUTING=off` i projekt używa jednego modelu z `AI_PROVIDER` / `AI_MODEL`.
Aby włączyć router, ustaw `AI_ROUTING=auto`. Router wybiera spośród jawnie
skonfigurowanych modeli według deklarowanych możliwości, szybkości, jakości
rozumowania i kosztu. Nie wykonuje jeszcze automatycznych benchmarków.

Przykład PowerShell (klucz API pozostaje w osobnej zmiennej środowiskowej):

~~~powershell
$env:AI_ROUTING="auto"
$env:AI_ROUTER_PRIMARY_CAPABILITIES="chat,tool_calling,code,reasoning"
$env:OPENROUTER_API_KEY="YOUR_API_KEY"
$env:AI_ROUTER_CANDIDATES='[{"name":"cloud-reasoner","provider":"openrouter","model":"provider/model-name","api_key_env":"OPENROUTER_API_KEY","capabilities":["chat","tool_calling","code","reasoning"],"speed_score":2,"reasoning_score":5,"cost_score":1,"context_window":32768}]'
python -m apps.cli.main
~~~

Każdy kandydat wymaga pól `provider`, `model` i jawnej listy `capabilities`.
Obsługiwane możliwości: `chat`, `tool_calling`, `code`, `reasoning`,
`vision`. Klucze API wskazuje się przez `api_key_env`; nie wpisuj sekretów
bezpośrednio do JSON ani repozytorium. Maksymalnie 8 dodatkowych kandydatów.

## Pamięć

Pamięć długoterminowa zapisuje wyłącznie notatki dodane jawnie przez użytkownika. W terminalu dostępne są:

- `/remember TEKST` — zapisz notatkę;
- `/memory` — pokaż notatki;
- `/search TEKST` — wyszukaj notatki;
- `/forget ID` — usuń notatkę;
- `/clear` — wyczyść historię rozmowy, bez usuwania pamięci.

Baza SQLite znajduje się domyślnie w `data/memory.sqlite3`. Wyszukiwanie jest obecnie leksykalne, nie wektorowe.

## Historia zadań

CLI zapisuje przebieg zadań w SQLite (`data/tasks.sqlite3`). Dostępne polecenia:

- `/tasks` — ostatnie zadania i ich statusy;
- `/task ID` — szczegóły wybranego zadania;
- `/retry ID` — ponawia zadanie failed, paused lub przerwane jako running od początku.

Statusy są kontrolowane przez maszynę stanów: `queued`, `running`, `paused`,
`completed`, `failed`, `cancelled`. Polecenie `/retry ID` ponawia zadanie o statusie failed, paused lub running od początku. Nie odtwarza jeszcze dokładnego checkpointu przerwanego procesu.

## Agent Zero jako upstream

Pełne źródła upstream są przypięte jako submodule w vendor/agent-zero do konkretnego commita. Aby pobrać je razem z projektem z tej gałęzi:

~~~bash
git clone --branch feature/agent-zero-integration --recurse-submodules https://github.com/Shvvit/ai-agent.git
~~~

Jeżeli repozytorium zostało już sklonowane:

~~~bash
git submodule update --init --recursive
~~~

Agent Zero ma własne zależności i runtime. Nie instalujemy ich automatycznie jako zależności Własne AI. Adaptujemy wybrane komponenty do naszej architektury i zachowujemy upstreamową licencję MIT w third_party/agent-zero/LICENSE.

## Bezpieczeństwo

- Narzędzia są ograniczone do jawnej allow-listy.
- Operacje plikowe są ograniczone do katalogu workspace.
- Uruchamianie kodu Python w subprocessie nie jest pełną piaskownicą bezpieczeństwa i wymaga dodatkowej izolacji OS przed udostępnieniem agentowi szerszego dostępu do komputera.
