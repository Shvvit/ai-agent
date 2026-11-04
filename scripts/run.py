from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        import uvicorn
    except ImportError:
        print('Brak zależności web. Uruchom: python -m pip install -e ".[web]"')
        return 2
    host = os.getenv("AI_BIND_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("AI_PORT", "8000"))
    except ValueError:
        print("Nieprawidłowy AI_PORT: podaj liczbę od 1 do 65535.")
        return 2
    if not 1 <= port <= 65535:
        print("Nieprawidłowy AI_PORT: podaj liczbę od 1 do 65535.")
        return 2
    if host not in {"127.0.0.1", "localhost", "::1"}:
        print("Odmowa: zdalny dostęp nie jest jeszcze zabezpieczony uwierzytelnianiem. Użyj localhost.")
        return 3
    uvicorn.run("api.app:app", host=host, port=port, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
