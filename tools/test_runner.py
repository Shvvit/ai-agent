
from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TestResult:
    success: bool
    return_code: int
    output: str


class TestRunner:
    """Uruchamia testy Pythona wyłącznie w katalogu workspace."""

    def __init__(
        self,
        workspace: str | Path = "workspace",
        timeout: int = 30,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.timeout = timeout
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run_python(self, relative_path: str) -> TestResult:
        script = (self.workspace / relative_path).resolve()

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
            return TestResult(
                success=result.returncode == 0,
                return_code=result.returncode,
                output=output,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                success=False,
                return_code=-1,
                output=f"Test przekroczył limit {self.timeout} s.",
            )
