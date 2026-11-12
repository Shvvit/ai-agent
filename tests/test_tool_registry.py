from __future__ import annotations

import pytest

from tools.registry import ToolDefinition, ToolRegistry


def test_registry_only_exposes_registered_tools():
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="echo",
        description="Returns supplied text",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        handler=lambda args: args["text"],
    ))
    assert registry.names() == ("echo",)
    assert registry.definitions()[0]["function"]["name"] == "echo"
    assert registry.definitions(exclude_names={"echo"}) == []


def test_registry_validates_required_fields_types_and_extra_fields():
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="echo",
        description="Returns supplied text",
        parameters={
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
            "additionalProperties": False,
        },
        handler=lambda args: args["text"],
    ))
    with pytest.raises(ValueError, match="wymaga pól"):
        registry.execute("echo", {})
    with pytest.raises(ValueError, match="musi mieć typ string"):
        registry.execute("echo", {"text": 123})
    with pytest.raises(ValueError, match="nie przyjmuje pól"):
        registry.execute("echo", {"text": "ok", "extra": True})


def test_registry_enforces_capabilities_and_explicit_approval():
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="delete_file",
        description="Deletes a workspace file",
        parameters={"type": "object", "properties": {}, "additionalProperties": False},
        handler=lambda args: "deleted",
        required_capabilities=frozenset({"workspace_write"}),
        requires_approval=True,
    ))
    with pytest.raises(PermissionError, match="Brak uprawnień"):
        registry.execute("delete_file", {}, granted_capabilities=set())
    with pytest.raises(PermissionError, match="zgody użytkownika"):
        registry.execute("delete_file", {}, granted_capabilities={"workspace_write"})
    assert registry.execute(
        "delete_file", {}, granted_capabilities={"workspace_write"}, approved=True
    ) == "deleted"


def test_registry_rejects_duplicate_and_unknown_tools():
    registry = ToolRegistry()
    tool = ToolDefinition(
        name="echo",
        description="Returns supplied text",
        parameters={"type": "object", "properties": {}},
        handler=lambda args: "ok",
    )
    registry.register(tool)
    with pytest.raises(ValueError, match="już zarejestrowane"):
        registry.register(tool)
    with pytest.raises(ValueError, match="Nieznane narzędzie"):
        registry.execute("unknown", {})
