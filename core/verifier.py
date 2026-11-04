from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PureWindowsPath


@dataclass
class VerificationResult:
    success: bool
    message: str


class Verifier:
    """Weryfikuje pliki w workspace bez podążania za symlinkami."""

    def __init__(self, workspace: str | Path = "workspace", max_file_bytes: int = 2_000_000) -> None:
        self.workspace = Path(workspace).resolve()
        self.max_file_bytes = max(1, int(max_file_bytes))

    def _safe_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Ścieżka musi być niepustym tekstem.")
        windows_path = PureWindowsPath(relative_path)
        if Path(relative_path).is_absolute() or windows_path.is_absolute() or windows_path.drive:
            raise PermissionError("Weryfikacja wymaga ścieżki względnej.")
        relative = Path(relative_path.replace("\\\\", "/"))
        if ".." in relative.parts:
            raise PermissionError("Segment '..' jest zabroniony.")
        candidate = self.workspace / relative
        current = self.workspace
        for part in relative.parts:
            if part in ("", "."):
                continue
            current = current / part
            if current.is_symlink():
                raise PermissionError("Weryfikacja przez symlink jest zabroniona.")
        resolved = candidate.resolve()
        if not resolved.is_relative_to(self.workspace):
            raise PermissionError("Ścieżka wychodzi poza workspace.")
        return resolved

    def file_exists(self, relative_path: str) -> VerificationResult:
        try:
            path = self._safe_path(relative_path)
        except (ValueError, PermissionError) as exc:
            return VerificationResult(False, str(exc))
        if not path.is_file():
            return VerificationResult(False, f"Nie znaleziono pliku: {relative_path}")
        if path.stat().st_size > self.max_file_bytes:
            return VerificationResult(False, "Plik przekracza limit rozmiaru weryfikacji.")
        return VerificationResult(True, f"Potwierdzono istnienie pliku: {relative_path}")

    def file_contains(self, relative_path: str, expected_text: str) -> VerificationResult:
        if not isinstance(expected_text, str):
            return VerificationResult(False, "Oczekiwana zawartość musi być tekstem.")
        result = self.file_exists(relative_path)
        if not result.success:
            return result
        try:
            path = self._safe_path(relative_path)
            actual_text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError, ValueError, PermissionError) as exc:
            return VerificationResult(False, f"Nie można odczytać pliku: {exc}")
        if expected_text not in actual_text:
            return VerificationResult(False, "Plik nie zawiera oczekiwanego tekstu.")
        return VerificationResult(True, "Zawartość pliku została potwierdzona.")
