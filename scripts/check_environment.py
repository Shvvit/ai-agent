from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import sys

import httpx


def main() -> int:
    print("Własne AI — diagnostyka środowiska")
    print(f"System: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {sys.version.split()[0]}")
    supported = (3, 12) <= sys.version_info[:2] < (3, 14)
    print(f"Python 3.12–3.13: {'OK' if supported else 'NIEOBSŁUGIWANY'}")
    for name in ("ollama", "fastapi", "uvicorn", "pydantic", "httpx"):
        print(f"Moduł {name}: {'OK' if importlib.util.find_spec(name) else 'BRAK'}")
    ollama_cli = shutil.which("ollama")
    print(f"Ollama CLI: {ollama_cli or 'nie znaleziono (sprawdź PATH)'}")
    host = os.getenv("AI_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("AI_MODEL", "qwen3:8b")
    try:
        response = httpx.get(f"{host}/api/tags", timeout=2.0)
        response.raise_for_status()
        installed = {
            item.get("name", "") for item in response.json().get("models", [])
            if isinstance(item, dict)
        }
        print(f"Serwer Ollama: online ({host})")
        print(f"Model domyślny {model}: {'zainstalowany' if model in installed else 'BRAK — wykonaj ollama pull ' + model}")
        print(f"Modele dostępne: {', '.join(sorted(installed)) or 'brak'}")
    except (httpx.HTTPError, ValueError):
        print(f"Serwer Ollama: offline lub niedostępny ({host})")
        print("Uruchom Ollama i pobierz model przed rozpoczęciem rozmowy.")
    return 0 if supported else 1


if __name__ == "__main__":
    raise SystemExit(main())
