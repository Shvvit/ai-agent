# Własne AI — szkic projektu

> Status: dokument bazowy / szkic. To opis kierunku projektu, nie deklaracja, że wszystkie funkcje już istnieją.
> Repozytorium: `Shvvit/ai-agent`
> Gałąź robocza: `work/full-agent-rebuild`

## 1. Cel

Własne AI ma być uniwersalnym, modułowym agentem AI, którego można uruchomić na różnych komputerach, z różnymi modelami i przez różnych użytkowników. Nie może być na stałe związany z jednym dostawcą modeli, jedną kartą graficzną, systemem operacyjnym ani interfejsem.

Agent ma nie tylko odpowiadać na pytania. Ma rozumieć cel użytkownika, przygotowywać plan, korzystać z dozwolonych narzędzi, wykonywać zadania, sprawdzać rezultaty i informować o błędach.

## 2. Główne zasady architektury

1. **Niezależność od modelu** — modele lokalne i chmurowe są podłączane przez wspólny interfejs dostawcy (adapter). Ollama jest jednym z adapterów, a nie fundamentem całego systemu.
2. **Modułowość** — funkcje są rozdzielone na moduły, które można rozwijać, wymieniać, wyłączać i testować osobno.
3. **Przenośność** — projekt ma działać na różnych konfiguracjach sprzętowych i systemach operacyjnych; funkcje zależne od systemu muszą mieć jawne adaptery.
4. **Wielu użytkowników** — ustawienia, historia, pamięć, klucze i uprawnienia muszą być odseparowane per użytkownik.
5. **Wiele interfejsów** — wspólny rdzeń ma być dostępny przez CLI, GUI oraz kontrolowany dostęp zdalny.
6. **Bezpieczeństwo** — narzędzia mają działać z minimalnymi uprawnieniami; operacje ryzykowne wymagają polityk i zgody użytkownika.
7. **Weryfikowalność** — agent nie może przedstawiać planu jako wykonanego zadania; wynik musi być sprawdzony, a ograniczenia jawnie raportowane.
8. **Skalowalność** — system ma działać na słabszym komputerze z małym modelem i wykorzystywać mocniejsze modele/serwery, gdy są dostępne.

## 3. Docelowe obszary funkcjonalne

### A. Rdzeń agenta
- zarządzanie cyklem rozmowy i kontekstem;
- rozpoznawanie intencji i rozbijanie celu na zadania;
- planowanie, wykonywanie, kontrola postępu i weryfikacja;
- obsługa błędów, ponawianie i bezpieczne zatrzymywanie;
- rejestrowanie działań i wyników.

### B. Dostawcy i modele AI
- wspólny interfejs dla dostawców lokalnych i chmurowych;
- wykrywanie dostępnych modeli i ich możliwości;
- konfiguracja modeli, limitów i kluczy;
- wybór modelu do zadania na podstawie możliwości, jakości, szybkości, kosztu i dostępnych zasobów;
- testy/benchmarki modeli oraz możliwość ręcznego nadpisania wyboru.

### C. Narzędzia i środowisko
- praca z plikami i katalogami w wyznaczonym obszarze;
- uruchamianie kodu i testów w izolowanym środowisku;
- terminal z politykami dostępu;
- wyszukiwanie informacji i praca z przeglądarką;
- integracje z aplikacjami i usługami przez rozszerzalne konektory;
- narzędzia systemowe dobierane do OS i uprawnień.

### D. Pamięć i użytkownicy
- osobna konfiguracja, historia i pamięć dla każdego użytkownika;
- pamięć krótkoterminowa i długoterminowa;
- wyszukiwanie informacji w pamięci, z możliwością jej przeglądania, poprawiania i usuwania;
- kontrola tego, co jest zapisywane;
- import/eksport danych użytkownika.

### E. Wielu agentów
- role specjalistyczne (np. planista, analityk, programista, recenzent);
- przekazywanie zadań między agentami;
- wspólny stan zadania i kontrola konfliktów;
- limity czasu, tokenów, pamięci i kosztów;
- praca równoległa tam, gdzie jest bezpieczna i uzasadniona.

### F. Interfejsy i dostęp
- CLI;
- GUI/web;
- dostęp zdalny przez uwierzytelnione API;
- zarządzanie sesjami, zadaniami, modelami, pamięcią i uprawnieniami;
- możliwość późniejszego dodawania kolejnych klientów bez przepisywania rdzenia.

### G. Multimodalność
- tekst jako podstawa;
- możliwość podłączania modeli i narzędzi do obrazów, audio i wideo;
- obsługa wejść/wyjść multimodalnych zależnie od możliwości wybranego modelu;
- jawne informowanie, gdy dany model nie obsługuje danego typu danych.

### H. Rozszerzenia
- moduły instalowane jako dodatki;
- manifest możliwości, zależności i uprawnień;
- włączanie/wyłączanie i wersjonowanie rozszerzeń;
- stabilne API modułów.

## 4. Docelowy przepływ zadania

1. Użytkownik przekazuje cel.
2. Agent ustala wymagania, ograniczenia i poziom ryzyka.
3. Planista tworzy plan i kryteria ukończenia.
4. Router wybiera modele i narzędzia odpowiednie do poszczególnych kroków.
5. Wykonawcy realizują kroki z kontrolą uprawnień.
6. Weryfikator sprawdza rezultat względem kryteriów.
7. W razie błędu agent może bezpiecznie poprawić wynik w ustalonych limitach.
8. Użytkownik otrzymuje rezultat, raport działań i informację o tym, czego nie udało się potwierdzić.

## 5. Bezpieczeństwo — wymagania docelowe

- domyślnie brak nieograniczonego dostępu do systemu;
- jawne uprawnienia dla narzędzi i rozszerzeń;
- izolacja wykonywania kodu i operacji na plikach;
- potwierdzanie działań destrukcyjnych, finansowych, publikujących lub zmieniających system;
- bezpieczne przechowywanie sekretów;
- uwierzytelnianie i autoryzacja dostępu zdalnego;
- limity zasobów, czasu i rozmiaru danych;
- audyt działań i możliwość przerwania zadania.

## 6. Co już istnieje, a co jest dopiero celem

Poniższa lista jest punktem startowym do weryfikacji kodu. Nie oznacza, że element jest kompletny lub produkcyjnie bezpieczny.

### Istniejące elementy w aktualnej gałęzi
- aplikacja webowa/GUI w podstawowej postaci i CLI;
- API oraz historia rozmów w SQLite;
- adapter Ollama;
- podstawowe narzędzia plikowe;
- pamięć SQLite z wyszukiwaniem leksykalnym;
- podstawowy silnik planowania, wykonywania i weryfikacji;
- kolejka zadań;
- podstawowa delegacja ról agentów;
- routing profili modeli oparty na regułach;
- opcjonalne wyszukiwanie przez zewnętrzne API;
- ograniczony, diagnostyczny terminal i runner Pythona.

### Wymaga dalszej pracy
- adaptery innych lokalnych i chmurowych dostawców;
- wiarygodny benchmark i automatyczny dobór modeli;
- pełna izolacja kodu i narzędzi;
- bezpieczny dostęp zdalny i system wielu użytkowników;
- równoległa orkiestracja agentów ze wspólnym stanem i budżetami;
- pamięć semantyczna/wektorowa i kontrolowane pozyskiwanie faktów;
- pełna przeglądarka i interakcja ze stronami;
- wykonywanie zadań w tle, streaming, wznawianie i przerywanie;
- multimodalność;
- system rozszerzeń z uprawnieniami i stabilnym API;
- kompletne testy integracyjne, bezpieczeństwa i testy ręczne.

## 7. Kolejność rozwijania

Pracujemy małymi, sprawdzalnymi zmianami — jeden plik na raz. Każda zmiana powinna mieć:
1. jasno określony cel;
2. odczyt aktualnej wersji pliku i jego zależności;
3. minimalną, spójną implementację;
4. testy lub kontrolę adekwatną do zmiany;
5. zapis informacji o tym, co działa, a co nadal jest ograniczeniem.

Proponowane etapy:

- **Etap 0 — szkic i inwentaryzacja:** zatwierdzenie kierunku, sprawdzenie istniejących modułów i rozdzielenie funkcji działających od planowanych.
- **Etap 1 — fundament architektury:** kontrakty modułów, konfiguracja, użytkownicy, uprawnienia i stabilne interfejsy.
- **Etap 2 — modele:** wspólny interfejs dostawców, kolejne adaptery, rejestr możliwości i testowanie modeli.
- **Etap 3 — agent:** planowanie, narzędzia, wykonanie, weryfikacja, przerwanie i odzyskiwanie po błędach.
- **Etap 4 — bezpieczeństwo:** izolacja, zgody, sekrety, audyt i zdalne uwierzytelnianie.
- **Etap 5 — pamięć i wielu użytkowników:** separacja danych, pamięć semantyczna i zarządzanie danymi.
- **Etap 6 — interfejsy i rozszerzenia:** dopracowanie CLI/GUI/API i system dodatków.
- **Etap 7 — multimodalność i skalowanie:** obrazy, audio, wideo, wiele modeli i większe środowiska.
- **Etap 8 — walidacja:** testy na różnych OS, sprzęcie, modelach i scenariuszach użycia.

## 8. Reguły pracy nad repozytorium

- Zmiany wykonujemy na `work/full-agent-rebuild`; nie scalaj do `master` bez osobnej zgody.
- W pojedynczym kroku zmieniamy jeden plik.
- Przed edycją zawsze pobieramy aktualną treść i SHA pliku.
- Po zapisie sprawdzamy wynik, a następnie testujemy najbliższy moduł.
- Nie deklarujemy funkcji jako gotowej, jeśli istnieje tylko interfejs, opis lub atrapowy moduł.
- Nie usuwamy działających funkcji bez uzasadnienia i testu regresji.
- Nie wpisujemy sekretów ani danych prywatnych do repozytorium.
- Każda funkcja ma mieć określone wymagania, ograniczenia i sposób sprawdzenia.

## 9. Otwarte decyzje

Te kwestie należy rozstrzygać podczas rozwijania projektu, zamiast zgadywać:
- docelowy sposób wdrażania i zarządzania wieloma użytkownikami;
- zakres zdalnego dostępu i model hostowania;
- lista pierwszych dostawców modeli poza Ollamą;
- docelowe granice uprawnień dla sterowania komputerem;
- wybór technologii izolacji zależny od systemu operacyjnego;
- priorytet i zakres pierwszych funkcji multimodalnych;
- format i kompatybilność rozszerzeń.

---
Ten dokument będzie rozwijany razem z projektem. Po każdym większym etapie powinien odzwierciedlać rzeczywisty stan kodu, a nie tylko ambicje projektu.
