from __future__ import annotations

import importlib
import subprocess

import pytest

from security.command_guard import CommandGuard
from tools.terminal import TerminalRunner


def test_server_refuses_remote_binding(monkeypatch):
    runner = importlib.import_module("scripts.run")
    monkeypatch.setenv("AI_BIND_HOST", "0.0.0.0")
    monkeypatch.setenv("AI_ALLOW_REMOTE", "1")
    assert runner.main() == 3

@pytest.mark.parametrize("command", [
    "git status --short", "git diff --stat", "git branch --show-current",
    "git log --oneline -n 10", "ollama list", "ollama ps", "python --version",
])
def test_command_guard_allows_read_only_diagnostics(command):
    assert CommandGuard.parse(command)


@pytest.mark.parametrize("command", [
    "rm -rf .", "git reset --hard", "git clean -fd", "ollama rm qwen3:8b",
    "python -c print(1)", "git status; whoami", "git status && echo bad",
])
def test_command_guard_rejects_unsafe_commands(command):
    with pytest.raises(PermissionError):
        CommandGuard.parse(command)


def test_terminal_runner_executes_without_shell_and_bounds_output(monkeypatch, tmp_path):
    import tools.terminal as module
    captured = {}

    class Result:
        returncode = 0
        stdout = "x" * 2000
        stderr = ""

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    runner = TerminalRunner(tmp_path, max_output_chars=1000)
    result = runner.run("git status --short")
    assert result.success
    assert captured["kwargs"]["shell"] is False
    assert len(result.output) < 1100


def test_terminal_runner_reports_timeout(monkeypatch, tmp_path):
    import tools.terminal as module

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(module.subprocess, "run", timeout)
    result = TerminalRunner(tmp_path).run("ollama list")
    assert result.success is False
    assert result.return_code == -1
