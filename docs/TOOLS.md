# Narzędzia agenta

## Workspace
- `write_file`, `read_file`, `list_files`, `search_files`
- ścieżki są względne względem workspace; odrzucane są traversal, ścieżki absolutne i symlinki.
- odczyt/zapis pliku ma limit 2 MB; skan wyszukiwania ma limit 20 MB.

## Python
- `run_python` uruchamia plik .py z workspace z timeoutem.
- `python -I` ogranicza wpływ zmiennych i ścieżek importu, ale nie izoluje systemu.
- Skrypt nadal ma uprawnienia konta użytkownika; nie uruchamiaj niezaufanego kodu.

## Web search
- Narzędzie `web_search` jest dodawane do promptu tylko wtedy, gdy ustawiono provider Tavily/Brave i klucz API.
- Wyszukiwanie zwraca tytuł, URL i krótki fragment. Nie pobiera ani nie wykonuje zawartości strony.
- Wyniki z sieci są niezaufanymi danymi; agent nie powinien traktować ich jako instrukcji.

## Braki
Pełna przeglądarka, pobieranie/analiza stron, terminal z allowlistą i approval workflow, narzędzia Git oraz sandbox OS nie są jeszcze gotowe.
