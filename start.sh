#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
  echo "Brak .venv. Najpierw uruchom ./install.sh"
  exit 2
fi
exec .venv/bin/python scripts/run.py
