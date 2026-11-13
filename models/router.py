from __future__ import annotations

import os
import re
from dataclasses import dataclass

from models.registry import ModelRegistry


@dataclass(frozen=True)
class ModelChoice:
    model: str
    profile: str
    reason: str


class ModelRouter:
    """Przewidywalny router profili; nie udaje pomiarów wydajności modeli."""

    _PROFILES = {
        "coding": ("AI_MODEL_CODE", ("kod", "program", "python", "debug", "bug", "refactor", "typescript", "javascript")),
        "reasoning": ("AI_MODEL_REASONING", ("przeanaliz", "zaplanuj", "porównaj", "udowodnij", "strateg", "architektur", "reason")),
        "fast": ("AI_MODEL_FAST", ("krótko", "szybko", "streść", "stresc", "przetłumacz", "translate", "summar")),
    }

    def __init__(
        self,
        registry: ModelRegistry,
        default_model: str,
        profiles: dict[str, str] | None = None,
    ) -> None:
        self.registry = registry
        self.default_model = default_model
        configured = profiles if profiles is not None else {
            profile: os.getenv(env_name, "").strip()
            for profile, (env_name, _) in self._PROFILES.items()
        }
        # Nie pozwól, aby błędne wartości konfiguracji powodowały awarię routingu.
        self.profiles = {
            name: model.strip()
            for name, model in configured.items()
            if name in self._PROFILES and isinstance(model, str) and model.strip()
        }

    @classmethod
    def _detect_profile(cls, task: str) -> str:
        """Wybiera pierwszy pasujący profil; kolejność jest celowo deterministyczna."""
        text = task.casefold()
        for profile, (_, keywords) in cls._PROFILES.items():
            if any(re.search(r"\b" + re.escape(word), text) for word in keywords):
                return profile
        return "default"

    def choose(self, task: str) -> ModelChoice:
        if not isinstance(task, str):
            raise TypeError("Opis zadania musi być tekstem.")

        selected_profile = self._detect_profile(task.strip())
        preferred = self.profiles.get(selected_profile, "") if selected_profile != "default" else ""

        if preferred and self.registry.contains(preferred):
            return ModelChoice(
                preferred,
                selected_profile,
                f"Wybrano skonfigurowany profil {selected_profile}.",
            )

        if self.registry.contains(self.default_model):
            reason = (
                "Model profilu nie jest zainstalowany; użyto modelu domyślnego."
                if preferred
                else "Brak specjalnego profilu dla zadania; użyto modelu domyślnego."
            )
            return ModelChoice(self.default_model, selected_profile, reason)

        fallback = self.registry.smallest()
        if fallback is not None:
            return ModelChoice(
                fallback.name,
                selected_profile,
                "Model domyślny nie jest zainstalowany; wybrano najmniejszy dostępny model.",
            )

        return ModelChoice(
            self.default_model,
            selected_profile,
            "Lista modeli jest pusta; pozostawiono skonfigurowany model domyślny.",
        )
