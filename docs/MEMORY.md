# Pamięć

Pamięć jest lokalna i przechowywana w tabeli SQLite `memories`.

## Komendy czatu
- `/remember treść` — zapisuje wpis.
- `/memory` — wyświetla zapisane wpisy.
- `/clear_memory` — usuwa wszystkie wpisy.

## API
- `GET /api/memory`
- `POST /api/memory` z `{"content":"..." }`
- `DELETE /api/memory/{id}`
- `DELETE /api/memory`

Wpis ma limit 4000 znaków; baza przechowuje do 2000 wpisów. Wyszukiwanie jest leksykalne, z prostym dopasowaniem prefiksów przydatnym dla odmiany wyrazów w języku polskim. Do promptu trafia maksymalnie 8 wyników i 4000 znaków kontekstu.

To nie jest pamięć wektorowa, automatyczne wydobywanie faktów ani trwały profil preferencji. Treść wpisów jest kontekstem, nie instrukcją systemową. Użytkownik powinien kontrolować, co zapisuje.
