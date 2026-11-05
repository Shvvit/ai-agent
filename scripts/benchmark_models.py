from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import psutil


DEFAULT_PROMPT = (
    "Napisz krótki, poprawny program w Pythonie, który sprawdza, "
    "czy podana liczba jest pierwsza. Dodaj obsługę liczb mniejszych niż 2."
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sekwencyjny benchmark lokalnych modeli Ollama (bez równoległego ładowania)."
    )
    parser.add_argument(
        "--models",
        default=os.getenv("AI_MODEL", "qwen3:8b"),
        help="Modele rozdzielone przecinkami; domyślnie AI_MODEL lub qwen3:8b.",
    )
    parser.add_argument("--host", default=os.getenv("AI_HOST", "http://127.0.0.1:11434"))
    parser.add_argument("--num-predict", type=int, default=128, help="Limit generowanych tokenów.")
    parser.add_argument("--num-ctx", type=int, default=2048, help="Limit kontekstu dla bezpieczniejszego pomiaru.")
    parser.add_argument("--repeat", type=int, default=1, help="Liczba powtórzeń; każde zaczyna od zimnego ładowania.")
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--output", default="benchmark-results.json")
    return parser.parse_args()


def read_vram_used_mb() -> int | None:
    """Zwraca łączne użycie VRAM raportowane przez nvidia-smi lub None."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=True,
        )
        values = [int(line.strip()) for line in result.stdout.splitlines() if line.strip().isdigit()]
        return sum(values) if values else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


class ResourceSampler:
    """Próbkuje pamięć hosta i VRAM w trakcie pojedynczego wywołania."""

    def __init__(self, interval: float = 0.2) -> None:
        self.interval = interval
        self.ram_baseline = psutil.virtual_memory().used
        self.ram_peak = self.ram_baseline
        self.vram_baseline = read_vram_used_mb()
        self.vram_peak = self.vram_baseline
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._sample, daemon=True)

    def _sample(self) -> None:
        while not self._stop.is_set():
            self.ram_peak = max(self.ram_peak, psutil.virtual_memory().used)
            current_vram = read_vram_used_mb()
            if current_vram is not None:
                self.vram_peak = current_vram if self.vram_peak is None else max(self.vram_peak, current_vram)
            self._stop.wait(self.interval)

    def __enter__(self) -> "ResourceSampler":
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        self._thread.join(timeout=3.0)
        self.ram_peak = max(self.ram_peak, psutil.virtual_memory().used)
        current_vram = read_vram_used_mb()
        if current_vram is not None:
            self.vram_peak = current_vram if self.vram_peak is None else max(self.vram_peak, current_vram)

    def result(self) -> dict[str, int | None]:
        return {
            "ram_used_delta_mb": round((self.ram_peak - self.ram_baseline) / (1024 * 1024)),
            "ram_peak_used_mb": round(self.ram_peak / (1024 * 1024)),
            "vram_used_delta_mb": (
                self.vram_peak - self.vram_baseline
                if self.vram_peak is not None and self.vram_baseline is not None
                else None
            ),
            "vram_peak_used_mb": self.vram_peak,
        }


def seconds_from_ns(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or value < 0:
        return None
    return round(value / 1_000_000_000, 3)


def tokens_per_second(token_count: Any, duration_ns: Any) -> float | None:
    if not isinstance(token_count, (int, float)) or not isinstance(duration_ns, (int, float)):
        return None
    if token_count < 0 or duration_ns <= 0:
        return None
    return round(token_count / (duration_ns / 1_000_000_000), 2)


def list_installed_models(client: httpx.Client, host: str) -> list[str]:
    response = client.get(f"{host.rstrip('/')}/api/tags")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or not isinstance(payload.get("models", []), list):
        raise ValueError("Ollama zwróciła nieprawidłową listę modeli.")
    return sorted({
        item["name"]
        for item in payload.get("models", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    })


def benchmark_one(
    client: httpx.Client,
    host: str,
    model: str,
    prompt: str,
    num_predict: int,
    num_ctx: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "keep_alive": 0,
        "options": {
            "temperature": 0,
            "num_predict": num_predict,
            "num_ctx": num_ctx,
        },
    }
    with ResourceSampler() as sampler:
        started = time.perf_counter()
        response = client.post(f"{host.rstrip('/')}/api/chat", json=payload)
        elapsed = time.perf_counter() - started
        response.raise_for_status()
        data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Ollama zwróciła nieprawidłowy wynik benchmarku.")

    eval_count = data.get("eval_count", 0)
    prompt_eval_count = data.get("prompt_eval_count", 0)
    eval_duration = data.get("eval_duration")
    prompt_eval_duration = data.get("prompt_eval_duration")
    return {
        "model": model,
        "wall_time_seconds": round(elapsed, 3),
        "load_seconds": seconds_from_ns(data.get("load_duration")),
        "prompt_tokens": prompt_eval_count,
        "prompt_processing_seconds": seconds_from_ns(prompt_eval_duration),
        "prompt_tokens_per_second": tokens_per_second(prompt_eval_count, prompt_eval_duration),
        "generated_tokens": eval_count,
        "generation_seconds": seconds_from_ns(eval_duration),
        "generation_tokens_per_second": tokens_per_second(eval_count, eval_duration),
        "total_server_seconds": seconds_from_ns(data.get("total_duration")),
        "done_reason": data.get("done_reason"),
        "resources": sampler.result(),
    }


def main() -> int:
    args = parse_args()
    if not 1 <= args.num_predict <= 4096:
        print("Błąd: --num-predict musi być w zakresie 1–4096.", file=sys.stderr)
        return 2
    if not 256 <= args.num_ctx <= 32768:
        print("Błąd: --num-ctx musi być w zakresie 256–32768.", file=sys.stderr)
        return 2
    if not 1 <= args.repeat <= 5:
        print("Błąd: --repeat musi być w zakresie 1–5.", file=sys.stderr)
        return 2
    if args.timeout <= 0 or not args.prompt.strip():
        print("Błąd: timeout i prompt muszą być dodatnie/niepuste.", file=sys.stderr)
        return 2

    host = args.host.strip().rstrip("/")
    models = list(dict.fromkeys(item.strip() for item in args.models.split(",") if item.strip()))
    if not models:
        print("Błąd: podaj przynajmniej jeden model przez --models.", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    try:
        with httpx.Client(timeout=args.timeout) as client:
            installed = list_installed_models(client, host)
            missing = [model for model in models if model not in installed]
            if missing:
                print("Nie znaleziono modeli: " + ", ".join(missing), file=sys.stderr)
                print("Zainstalowane modele: " + (", ".join(installed) or "brak"), file=sys.stderr)
                return 2

            print(f"Ollama: {host}")
            print(f"Modele: {', '.join(models)}")
            print(f"Ustawienia: num_ctx={args.num_ctx}, num_predict={args.num_predict}, powtórzenia={args.repeat}")
            print("Tryb: sekwencyjny, każde wywołanie ładuje model od nowa (keep_alive=0).")
            print("Uwaga: pomiar pamięci RAM/VRAM obejmuje cały system, nie tylko proces Ollama.\n")

            for model in models:
                for repetition in range(1, args.repeat + 1):
                    print(f"[{model}] próba {repetition}/{args.repeat}...", flush=True)
                    try:
                        result = benchmark_one(
                            client, host, model, args.prompt, args.num_predict, args.num_ctx
                        )
                        result["repetition"] = repetition
                        results.append(result)
                        rate = result["generation_tokens_per_second"]
                        load = result["load_seconds"]
                        vram = result["resources"]["vram_peak_used_mb"]
                        print(
                            f"  {rate if rate is not None else 'n/a'} tok/s | "
                            f"ładowanie: {load if load is not None else 'n/a'} s | "
                            f"szczyt VRAM: {vram if vram is not None else 'n/a'} MB"
                        )
                    except (httpx.HTTPError, ValueError, KeyError) as exc:
                        results.append({
                            "model": model,
                            "repetition": repetition,
                            "error": f"{type(exc).__name__}: {exc}",
                        })
                        print(f"  BŁĄD: {type(exc).__name__}: {exc}", file=sys.stderr)

    except (httpx.HTTPError, ValueError) as exc:
        print(f"Nie można połączyć się z Ollama: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "host": host,
        "system": platform.platform(),
        "python": platform.python_version(),
        "settings": {
            "num_ctx": args.num_ctx,
            "num_predict": args.num_predict,
            "repeat": args.repeat,
            "keep_alive": 0,
            "prompt": args.prompt,
        },
        "notes": [
            "Każdy pomiar rozpoczyna od zimnego ładowania modelu.",
            "VRAM jest próbkowany przez nvidia-smi; brak nvidia-smi oznacza null.",
            "RAM i VRAM to pomiary całego systemu, więc inne aplikacje wpływają na wynik.",
            "Szybkość generowania pochodzi z eval_count/eval_duration zwróconych przez Ollama.",
        ],
        "results": results,
    }
    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nZapisano raport: {output.resolve()}")
    successful = [item for item in results if "error" not in item]
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
