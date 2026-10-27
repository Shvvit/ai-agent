
from __future__ import annotations

from pathlib import Path


class FileManager:
    """Obsługuje pliki wyłącznie wewnątrz katalogu workspace."""

    def __init__(self, workspace: str | Path = "workspace") -> None:
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Ścieżka musi być niepustym tekstem.")

        candidate = Path(relative_path)

        if candidate.is_absolute():
            raise PermissionError("Wymagana jest ścieżka względna.")

        path = (self.workspace / candidate).resolve()

        if not path.is_relative_to(self.workspace):
            raise PermissionError("Dostęp poza workspace jest zabroniony.")

        # Nie pozwalamy przechodzić przez dowiązania symboliczne.
        current = self.workspace
        for part in candidate.parts:
            if part in ("", "."):
                continue
            if part == "..":
                raise PermissionError("Segment '..' jest zabroniony.")

            current = current / part
            if current.is_symlink():
                raise PermissionError(
                    "Dostęp przez dowiązania symboliczne jest zabroniony."
                )

        return path

    def write_file(self, relative_path: str, content: str) -> str:
        if not isinstance(content, str):
            raise TypeError("Treść pliku musi być tekstem.")

        path = self._safe_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Zapisano plik: {relative_path}"

    def read_file(self, relative_path: str) -> str:
        path = self._safe_path(relative_path)

        if not path.is_file():
            raise FileNotFoundError(f"Nie znaleziono pliku: {relative_path}")

        return path.read_text(encoding="utf-8")
