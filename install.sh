#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ -n "${PYTHON:-}" ]]; then
  command -v "$PYTHON" >/dev/null 2>&1 || { echo "Nie znaleziono interpretera: $PYTHON"; exit 1; }
else
  PYTHON=""
  for candidate in python3.12 python3.13; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYTHON="$candidate"
      break
    fi
  done
fi
[[ -n "$PYTHON" ]] || { echo "Wymagany Python 3.12 lub 3.13 (możesz ustawić PYTHON=python3.13)."; exit 1; }
echo "Używam: $("$PYTHON" --version)"
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,web]"
.venv/bin/python scripts/check_environment.py
echo "Instalacja zakończona. Uruchom: ./start.sh"
