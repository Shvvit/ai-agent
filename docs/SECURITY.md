

## Uruchamianie kodu Python

Python w subprocessie nie jest piaskownicą: kod może próbować odczytywać pliki,
korzystać z sieci i uruchamiać inne procesy. Dlatego `TestRunner` domyślnie
blokuje wykonanie. Użytkownik może jawnie włączyć je przez
`AI_ALLOW_UNSANDBOXED_PYTHON=1`, wyłącznie dla kodu, któremu ufa. Nie należy
włączać tej opcji dla nieznanych projektów ani modeli bez dodatkowej izolacji OS.
