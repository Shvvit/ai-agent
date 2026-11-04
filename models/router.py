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
    """Prosty, przewidywalny router profili modeli bez fikcyjnego benchmarkowania."""

    _PROFILES = {
        "coding": ("AI_MODEL_CODE", ("kod", "program", "python", "debug", "bug", "refactor", "typescript", "javascript")),
        "reasoning": ("AI_MODEL_REASONING", ("przeanaliz", "zaplanuj", "porównaj", "udowodnij", "strateg", "architektur", "reason")),
        "fast": ("AI_MODEL_FAST", ("krótko", "szybko", "streść", "stresc", "przetłumacz", "translate", "summar")),
    }

    def __init__(self, registry: ModelRegistry, default_model: str,
                 profiles: dict[str, str] | None = None) -> None:
        self.registry = registry
        self.default_model = default_model
        self.profiles = profiles if profiles is not None else {
            profile: os.getenv(env_name, "").strip()
            for profile, (env_name, _) in self._PROFILES.items()
        }

    def choose(self, task: str) -> ModelChoice:
        text = task.casefold()
        selected_profile = "default"
        for profile, (_, keywords) in self._PROFILES.items():
            if any(re.search(r"\b" + re.escape(word), text) for word in keywords):
                selected_profile = profile
                break
        preferred = self.profiles.get(selected_profile, "") if selected_profile != "default" else ""
        if preferred and self.registry.contains(preferred):
            return ModelChoice(preferred, selected_profile,
                               f"Wybrano skonfigurowany profil {selected_profile}.")
        if self.registry.contains(self.default_model):
            reason = "Użyto modelu domyślnego; brak dostępnego modelu profilu." if preferred else "Brak specjalnego profilu dla zadania."
            return ModelChoice(self.default_model, selected_profile, reason)
        fallback = self.registry.smallest()
        if fallback is not None:
            return ModelChoice(fallback.name, selected_profile,
                               "Model domyślny nie jest zainstalowany; wybrano najmniejszy dostępny model.")
        return ModelChoice(self.default_model, selected_profile,
                           "Lista modeli jest pusta; pozostawiono skonfigurowany model domyślny.")
