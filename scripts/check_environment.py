from __future__ import annotations

import importlib.util
import platform
import shutil
import sys


def main() -> int:
    print("Własne AI — diagnostyka środowiska")
    print(f"System: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {sys.version.split()[0]}")
    supported = (3, 12) <= sys.version_info[:2] < (3, 14)
    print(f"Python 3.12–3.13: {'OK' if supported else 'NIEOBSŁUGIWANY'}")
    for name in ("ollama", "fastapi", "uvicorn", "pydantic", "httpx"):
        print(f"Moduł {name}: {'OK' if importlib.util.find_spec(name) else 'BRAK'}")
    print(f"Ollama CLI: {shutil.which('ollama') or 'nie znaleziono (sprawdź PATH)'}")
    return 0 if supported else 1


if __name__ == "__main__":
    raise SystemExit(main())
