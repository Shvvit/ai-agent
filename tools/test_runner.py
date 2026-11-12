from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath


@dataclass
class TestResult:
    success: bool
    return_code: int
    output: str


class TestRunner:
    """Runs Python files from the workspace (not an OS-level sandbox)."""

    __test__ = False  # Prevent pytest from trying to collect this helper class.

    def __init__(self, workspace: str | Path = "workspace", timeout: int = 30) -> None:
        if timeout <= 0:
            raise ValueError("Timeout musi być większy od zera.")
        self.workspace = Path(workspace).resolve()
        self.timeout = timeout
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run_python(self, relative_path: str) -> TestResult:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Podaj względną ścieżkę do pliku .py.")
        raw_path = relative_path.strip()
        windows_path = PureWindowsPath(raw_path)
        if Path(raw_path).is_absolute() or windows_path.is_absolute() or windows_path.drive:
            raise PermissionError("Nie wolno uruchamiać plików spoza workspace.")

        candidate = Path(raw_path.replace("\\", "/"))
        if ".." in candidate.parts:
            raise PermissionError("Nie wolno uruchamiać plików spoza workspace.")
        script = (self.workspace / candidate).resolve()
        if not script.is_relative_to(self.workspace):
            raise PermissionError("Nie wolno uruchamiać plików spoza workspace.")
        if not script.is_file() or script.suffix != ".py":
            raise ValueError("Podaj istniejący plik .py w workspace.")

        try:
            result = subprocess.run(
                [sys.executable, "-I", str(script)],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                check=False,
            )
            output = (result.stdout + "\n" + result.stderr).strip()
            return TestResult(result.returncode == 0, result.returncode, output)
        except subprocess.TimeoutExpired:
            return TestResult(False, -1, f"Test przekroczył limit {self.timeout} s.")
