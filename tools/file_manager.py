from __future__ import annotations

from pathlib import Path, PureWindowsPath


class FileManager:
    """Obsługuje pliki wyłącznie wewnątrz katalogu workspace."""

    def __init__(self, workspace: str | Path = "workspace", max_file_bytes: int = 2_000_000) -> None:
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.max_file_bytes = max_file_bytes

    def _safe_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Ścieżka musi być niepustym tekstem.")
        windows_path = PureWindowsPath(relative_path)
        if Path(relative_path).is_absolute() or windows_path.is_absolute() or windows_path.drive:
            raise PermissionError("Wymagana jest ścieżka względna.")
        candidate = Path(relative_path.replace("\\", "/"))
        if ".." in candidate.parts:
            raise PermissionError("Segment '..' jest zabroniony.")
        path = (self.workspace / candidate).resolve()
        if not path.is_relative_to(self.workspace):
            raise PermissionError("Dostęp poza workspace jest zabroniony.")
        current = self.workspace
        for part in candidate.parts:
            if part in ("", "."):
                continue
            current = current / part
            if current.is_symlink():
                raise PermissionError("Dostęp przez dowiązania symboliczne jest zabroniony.")
        return path

    def write_file(self, relative_path: str, content: str) -> str:
        if not isinstance(content, str):
            raise TypeError("Treść pliku musi być tekstem.")
        if len(content.encode("utf-8")) > self.max_file_bytes:
            raise ValueError(f"Plik przekracza limit {self.max_file_bytes} bajtów.")
        path = self._safe_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Zapisano plik: {relative_path}"

    def read_file(self, relative_path: str) -> str:
        path = self._safe_path(relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"Nie znaleziono pliku: {relative_path}")
        if path.stat().st_size > self.max_file_bytes:
            raise ValueError(f"Plik przekracza limit odczytu {self.max_file_bytes} bajtów.")
        return path.read_text(encoding="utf-8")

    def list_files(self, relative_path: str = ".", limit: int = 200) -> list[str]:
        directory = self._safe_path(relative_path)
        if not directory.is_dir():
            raise NotADirectoryError(f"To nie jest katalog: {relative_path}")
        results: list[str] = []
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                continue
            if path.is_file():
                resolved = path.resolve()
                if resolved.is_relative_to(self.workspace):
                    results.append(resolved.relative_to(self.workspace).as_posix())
                    if len(results) >= max(1, min(limit, 1000)):
                        break
        return results

    def search_files(self, query: str, relative_path: str = ".", limit: int = 50) -> list[str]:
        if not isinstance(query, str) or not query:
            raise ValueError("Fraza wyszukiwania nie może być pusta.")
        matches: list[str] = []
        for name in self.list_files(relative_path, limit=1000):
            path = self._safe_path(name)
            if path.stat().st_size > self.max_file_bytes:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            for number, line in enumerate(content.splitlines(), start=1):
                if query.casefold() in line.casefold():
                    matches.append(f"{name}:{number}: {line.strip()[:300]}")
                    if len(matches) >= max(1, min(limit, 200)):
                        return matches
        return matches
