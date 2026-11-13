from __future__ import annotations

from security.approval import ConsoleApproval


def test_console_approval_accepts_explicit_yes():
    shown = []
    approval = ConsoleApproval(
        input_fn=lambda prompt: "tak",
        output_fn=shown.append,
    )
    assert approval.approve("delete_file", {"path": "notes.txt"}) is True
    assert any("delete_file" in line for line in shown)
    assert any("notes.txt" in line for line in shown)


def test_console_approval_defaults_to_deny():
    approval = ConsoleApproval(
        input_fn=lambda prompt: "",
        output_fn=lambda line: None,
    )
    assert approval.approve("delete_file", {"path": "notes.txt"}) is False


def test_console_approval_rejects_ambiguous_input():
    approval = ConsoleApproval(
        input_fn=lambda prompt: "yes, do it",
        output_fn=lambda line: None,
    )
    assert approval.approve("delete_file", {}) is False
