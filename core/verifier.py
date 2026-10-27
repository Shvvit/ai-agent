from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerificationResult:
    success: bool
    message: str


class Verifier:
    """Sprawdza rzeczywisty stan plików, a nie deklaracje modelu."""

    def __init__(self, workspace: str | Path = "workspace") -> None:
        self.workspace = Path(workspace).resolve()

    def file_exists(self, relative_path: str) -> VerificationResult:
        path = (self.workspace / relative_path).resolve()
        if not path.is_relative_to(self.workspace):
            return VerificationResult(False, "Ścieżka poza workspace jest zabroniona.")
        if not path.is_file():
            return VerificationResult(False, f"Plik nie istnieje: {relative_path}")
        return VerificationResult(True, f"Potwierdzono istnienie pliku: {relative_path}")

    def file_contains(self, relative_path: str, expected_text: str) -> VerificationResult:
        result = self.file_exists(relative_path)
        if not result.success:
            return result
        actual_text = (self.workspace / relative_path).read_text(encoding="utf-8")
        if expected_text not in actual_text:
            return VerificationResult(False, "Plik nie zawiera oczekiwanego tekstu.")
        return VerificationResult(True, "Zawartość pliku została potwierdzona.")
