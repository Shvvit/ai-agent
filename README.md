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

Nie commituj prawdziwych kluczy API. Plik .env.example jest tylko wzorem; obecna konfiguracja czyta zmienne środowiskowe systemu.

## Testy

~~~bash
python -m pytest -q
~~~

Testy providerów są mockowane i nie wymagają działającego Ollama ani płatnego klucza API. Testy integracyjne z rzeczywistymi modelami będą osobnym etapem.

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
