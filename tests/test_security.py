from __future__ import annotations

import importlib


def test_server_refuses_remote_binding(monkeypatch):
    runner = importlib.import_module("scripts.run")
    monkeypatch.setenv("AI_BIND_HOST", "0.0.0.0")
    monkeypatch.setenv("AI_ALLOW_REMOTE", "1")
    assert runner.main() == 3
