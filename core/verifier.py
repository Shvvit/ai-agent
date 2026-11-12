from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath


@dataclass
class VerificationResult:
    success: bool
    message: str


class Verifier:
    """Checks real filesystem state rather than trusting model claims."""

    def __init__(self, workspace: str | Path = "workspace") -> None:
        self.workspace = Path(workspace).resolve()

    def _resolve_path(self, relative_path: str) -> Path | None:
        if not isinstance(relative_path, str) or not relative_path.strip():
            return None
        raw_path = relative_path.strip()
        windows_path = PureWindowsPath(raw_path)
        if Path(raw_path).is_absolute() or windows_path.is_absolute() or windows_path.drive:
            return None
        candidate = Path(raw_path.replace("\\", "/"))
        if ".." in candidate.parts:
            return None
        path = (self.workspace / candidate).resolve()
        if not path.is_relative_to(self.workspace):
            return None
        return path

    def file_exists(self, relative_path: str) -> VerificationResult:
        path = self._resolve_path(relative_path)
        if path is None:
            return VerificationResult(False, "Ścieżka poza workspace jest zabroniona.")
        if not path.is_file():
            return VerificationResult(False, f"Plik nie istnieje: {relative_path}")
        return VerificationResult(True, f"Potwierdzono istnienie pliku: {relative_path}")

    def file_contains(self, relative_path: str, expected_text: str) -> VerificationResult:
        path = self._resolve_path(relative_path)
        if path is None:
            return VerificationResult(False, "Ścieżka poza workspace jest zabroniona.")
        if not path.is_file():
            return VerificationResult(False, f"Plik nie istnieje: {relative_path}")
        actual_text = path.read_text(encoding="utf-8")
        if expected_text not in actual_text:
            return VerificationResult(False, "Plik nie zawiera oczekiwanego tekstu.")
        return VerificationResult(True, "Zawartość pliku została potwierdzona.")
