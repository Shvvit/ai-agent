from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath


@dataclass
class TestResult:
    success: bool
    return_code: int
    output: str


class TestRunner:
    __test__ = False  # Prevent pytest from treating this helper as a test class.

    """Uruchamia skrypty Python w workspace z timeoutem i limitem przechwyconego wyjścia."""

    def __init__(self, workspace: str | Path = "workspace", timeout: int = 30,
                 max_output_bytes: int = 1_000_000) -> None:
        self.workspace = Path(workspace).resolve()
        self.timeout = max(1, min(int(timeout), 300))
        self.max_output_bytes = max(1024, min(int(max_output_bytes), 5_000_000))
        self.workspace.mkdir(parents=True, exist_ok=True)

    def run_python(self, relative_path: str) -> TestResult:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("Ścieżka do skryptu nie może być pusta.")
        windows_path = PureWindowsPath(relative_path)
        if Path(relative_path).is_absolute() or windows_path.is_absolute() or windows_path.drive:
            raise PermissionError("Nie wolno uruchamiać plików spoza workspace.")
        relative = Path(relative_path.replace("\\", "/"))
        if ".." in relative.parts:
            raise PermissionError("Nie wolno uruchamiać plików spoza workspace.")
        script = (self.workspace / relative).resolve()
        if not script.is_relative_to(self.workspace):
            raise PermissionError("Nie wolno uruchamiać plików spoza workspace.")
        current = self.workspace
        for part in relative.parts:
            current = current / part
            if current.is_symlink():
                raise PermissionError("Nie wolno uruchamiać plików przez dowiązania symboliczne.")
        if not script.is_file() or script.suffix.lower() != ".py":
            raise ValueError("Podaj istniejący plik .py w workspace.")
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            process = subprocess.Popen(
                [sys.executable, "-I", str(script)],
                cwd=self.workspace, stdout=stdout_file, stderr=stderr_file,
                stdin=subprocess.DEVNULL, shell=False,
            )
            timed_out = False
            try:
                return_code = process.wait(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                return_code = process.wait()
            stdout_file.seek(0)
            stderr_file.seek(0)
            stdout = stdout_file.read(self.max_output_bytes + 1)
            stdout_truncated = len(stdout) > self.max_output_bytes
            stdout = stdout[:self.max_output_bytes]
            remaining = self.max_output_bytes - len(stdout)
            stderr = stderr_file.read(remaining + 1)
            stderr_truncated = len(stderr) > remaining
            stderr = stderr[:remaining]
        truncated = stdout_truncated or stderr_truncated
        output = (stdout.decode("utf-8", errors="replace")
                  + "\n" + stderr.decode("utf-8", errors="replace")).strip()
        if truncated:
            output += "\n[Wynik skrócony do limitu.]"
        if timed_out:
            return TestResult(False, -1, f"Test przekroczył limit {self.timeout} s.\n{output}".strip())
        return TestResult(return_code == 0, return_code, output)
