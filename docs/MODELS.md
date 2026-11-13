# Modele

Obecnie działa adapter lokalnego Ollama.

## Wybór
- `AI_MODEL` ustala model domyślny.
- `AI_MODEL_CODE`, `AI_MODEL_REASONING` i `AI_MODEL_FAST` definiują opcjonalne modele profili.
- Router rozpoznaje typ zadania na podstawie słów kluczowych i wybiera model profilu tylko wtedy, gdy jest zainstalowany.
- Jeśli profil nie jest dostępny, używany jest model domyślny. Jeśli domyślnego nie ma na liście, używany jest najmniejszy dostępny model.
- Jawny wybór z UI ma pierwszeństwo przed automatycznym routingiem.

## Ograniczenia
Router nie mierzy tokenów/s, VRAM ani jakości. Nie uruchamia benchmarków i nie przełącza dostawców. Wszystkie subagenty korzystają z tego samego skonfigurowanego modelu. Inne provider-y API są przyszłym etapem.

## Lokalny benchmark Ollama

Skrypt `scripts/benchmark_models.py` mierzy lokalne modele sekwencyjnie. Domyślnie testuje tylko model z `AI_MODEL` (lub `qwen3:8b`), używa kontekstu 2048 tokenów, limitu 128 generowanych tokenów i po każdym pomiarze zwalnia model z pamięci (`keep_alive=0`). Nie ładuje kilku modeli równocześnie.

Przykłady PowerShell:

```powershell
# Domyślny model
python scripts/benchmark_models.py

# Porównanie modeli, które są już zainstalowane w Ollama
python scripts/benchmark_models.py --models qwen3:8b,qwen3:4b --repeat 2

# Krótszy test, mniejszy kontekst i własny plik raportu
python scripts/benchmark_models.py --models qwen3:8b --num-ctx 1024 --num-predict 64 --output data/benchmark.json
```

Skrypt sprawdza, czy wskazane modele są zainstalowane. Nie pobiera ich automatycznie. Raport JSON zawiera czas ładowania, szybkość przetwarzania promptu i generowania, liczbę tokenów oraz szczytowe użycie pamięci. VRAM jest próbkowany przez `nvidia-smi`; RAM i VRAM obejmują cały system, a więc mogą być zaburzone przez inne uruchomione programy. Jeśli `nvidia-smi` nie jest dostępne, pola VRAM będą puste.

Każdy pomiar jest zimnym startem, dlatego `--repeat 2` oznacza dwa osobne ładowania modelu, a nie test stałej szybkości przy modelu utrzymywanym w pamięci. Porównuj modele przy tych samych ustawieniach, tym samym promptcie i możliwie bez innych obciążających programów. Wynik tokenów/s pochodzi bezpośrednio z metryk Ollama (`eval_count / eval_duration`), a nie z czasu całego żądania.

Benchmark nie ocenia jakości odpowiedzi ani nie wyznacza automatycznie najlepszego modelu. Na razie jest narzędziem pomiarowym; dopiero po zebraniu wyników z Twojego PC ustawimy profile routingu pod RTX 5060 8 GB i 16 GB RAM.
