from __future__ import annotations

import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def _validate_url_port(parsed, setting: str) -> None:
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{setting} zawiera nieprawidłowy port.") from exc
    if port is not None and not 1 <= port <= 65535:
        raise ValueError(f"{setting} musi używać portu z zakresu 1–65535.")


@dataclass(frozen=True)
class ModelConfig:
    """Ustawienia modelu pobierane ze zmiennych środowiskowych."""

    provider: str = "ollama"
    model: str = "qwen3:8b"
    host: str = "http://127.0.0.1:11434"
    temperature: float = 0.2
    base_url: str = "https://api.openai.com/v1"
    api_key: str = field(default="", repr=False)
    request_timeout: float = 90.0

    @classmethod
    def from_env(cls) -> ModelConfig:
        provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()
        model = os.getenv("AI_MODEL", "qwen3:8b").strip()
        host = os.getenv("AI_HOST", "http://127.0.0.1:11434").strip()
        base_url = os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip()
        api_key = os.getenv("AI_API_KEY", "").strip()
        raw_temperature = os.getenv("AI_TEMPERATURE", "0.2")
        raw_timeout = os.getenv("AI_REQUEST_TIMEOUT", "90")

        if provider not in {"ollama", "openai_compatible"}:
            raise ValueError(
                f"Nieobsługiwany provider: {provider}. "
                "Dostępne: ollama, openai_compatible."
            )
        if not model or len(model) > 256 or any(ch in model for ch in "\r\n"):
            raise ValueError("AI_MODEL musi mieć od 1 do 256 znaków i nie może zawierać nowych linii.")

        parsed_host = urlsplit(host)
        _validate_url_port(parsed_host, "AI_HOST")
        if parsed_host.scheme not in {"http", "https"} or not parsed_host.hostname:
            raise ValueError("AI_HOST musi być poprawnym adresem HTTP lub HTTPS.")
        if (parsed_host.username or parsed_host.password or parsed_host.query
                or parsed_host.fragment or parsed_host.path not in {"", "/"}
                or any(ch.isspace() for ch in host)):
            raise ValueError("AI_HOST nie może zawierać ścieżki, danych logowania, query ani białych znaków.")

        parsed_base = urlsplit(base_url)
        _validate_url_port(parsed_base, "AI_BASE_URL")
        if parsed_base.scheme not in {"http", "https"} or not parsed_base.hostname:
            raise ValueError("AI_BASE_URL musi być poprawnym adresem HTTP lub HTTPS.")
        if (parsed_base.username or parsed_base.password or parsed_base.query
                or parsed_base.fragment or any(ch.isspace() for ch in base_url)):
            raise ValueError("AI_BASE_URL nie może zawierać danych logowania, query ani białych znaków.")
        if provider == "openai_compatible" and not api_key:
            raise ValueError("AI_API_KEY jest wymagany dla openai_compatible.")

        try:
            temperature = float(raw_temperature)
            request_timeout = float(raw_timeout)
        except ValueError as exc:
            raise ValueError("AI_TEMPERATURE i AI_REQUEST_TIMEOUT muszą być liczbami.") from exc
        if not 0.0 <= temperature <= 2.0:
            raise ValueError("AI_TEMPERATURE musi mieścić się w zakresie 0–2.")
        if not 1.0 <= request_timeout <= 600.0:
            raise ValueError("AI_REQUEST_TIMEOUT musi mieścić się w zakresie 1–600 sekund.")

        return cls(
            provider=provider,
            model=model,
            host=host,
            temperature=temperature,
            base_url=base_url,
            api_key=api_key,
            request_timeout=request_timeout,
        )
