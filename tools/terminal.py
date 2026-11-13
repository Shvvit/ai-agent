from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from security.command_guard import CommandGuard


@dataclass(frozen=True)
class CommandResult:
    success: bool
    return_code: int
    output: str


class TerminalRunner:
    """Uruchamia ograniczony zestaw komend diagnostycznych bez powłoki."""

    def __init__(self, workspace: str | Path | None = None, timeout: int = 15,
                 max_output_chars: int = 12000) -> None:
        workspace = workspace if workspace is not None else os.getenv("AI_WORKSPACE", ".")
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.timeout = max(1, min(int(timeout), 30))
        self.max_output_chars = max(1000, min(int(max_output_chars), 50000))

    @staticmethod
    def _environment() -> dict[str, str]:
        allowed = {"PATH", "SYSTEMROOT", "WINDIR", "HOME", "USERPROFILE",
                   "TMP", "TEMP", "LANG", "LC_ALL", "OLLAMA_HOST"}
        return {key: value for key, value in os.environ.items() if key in allowed}

    def run(self, command: str) -> CommandResult:
        args = CommandGuard.parse(command)
        try:
            result = subprocess.run(
                args, cwd=self.workspace, shell=False, capture_output=True,
                text=True, encoding="utf-8", errors="replace",
                timeout=self.timeout, check=False, env=self._environment(),
            )
            output = (result.stdout + "\n" + result.stderr).strip()
            if len(output) > self.max_output_chars:
                output = output[:self.max_output_chars] + "\n[Wynik skrócony.]"
            return CommandResult(result.returncode == 0, result.returncode, output)
        except subprocess.TimeoutExpired:
            return CommandResult(False, -1, f"Komenda przekroczyła limit {self.timeout} s.")
        except FileNotFoundError as exc:
            return CommandResult(False, 127, f"Nie znaleziono programu: {args[0]}")
