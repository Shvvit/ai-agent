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
