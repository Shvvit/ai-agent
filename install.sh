#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="${PYTHON:-python3.12}"
command -v "$PYTHON" >/dev/null 2>&1 || { echo "Wymagany Python 3.12 (ustaw PYTHON=python3.13, jeśli dostępny)."; exit 1; }
"$PYTHON" -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev,web]"
.venv/bin/python scripts/check_environment.py
echo "Instalacja zakończona. Uruchom: ./start.sh"
