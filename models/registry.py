from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ModelInfo:
    name: str
    size_bytes: int = 0
    modified_at: str | None = None
    digest: str | None = None

    @classmethod
    def from_ollama(cls, payload: dict[str, Any]) -> "ModelInfo":
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Model Ollama musi mieć nazwę.")
        size = payload.get("size", 0)
        if not isinstance(size, int) or size < 0:
            size = 0
        modified = payload.get("modified_at")
        digest = payload.get("digest")
        return cls(name=name, size_bytes=size,
                   modified_at=modified if isinstance(modified, str) else None,
                   digest=digest if isinstance(digest, str) else None)


class ModelRegistry:
    """Normalizuje listę modeli zwróconą przez lokalne API Ollama."""

    def __init__(self, models: list[ModelInfo] | None = None) -> None:
        self._models = {model.name: model for model in (models or [])}

    @classmethod
    def from_ollama_payload(cls, payload: dict[str, Any]) -> "ModelRegistry":
        raw = payload.get("models", [])
        if not isinstance(raw, list):
            raise ValueError("Ollama zwróciła nieprawidłową listę modeli.")
        models = []
        for item in raw:
            if isinstance(item, dict):
                try:
                    models.append(ModelInfo.from_ollama(item))
                except ValueError:
                    continue
        return cls(models)

    def list(self) -> list[ModelInfo]:
        return sorted(self._models.values(), key=lambda item: (item.size_bytes, item.name))

    def contains(self, name: str) -> bool:
        return name in self._models

    def smallest(self) -> ModelInfo | None:
        items = self.list()
        return items[0] if items else None
