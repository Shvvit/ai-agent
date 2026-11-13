from __future__ import annotations

import pytest

from tools.registry import ToolDefinition, ToolRegistry


def make_registry(schema, handler=lambda args: "ok"):
    registry = ToolRegistry()
    registry.register(ToolDefinition(
        name="validate_input",
        description="Validates supplied input",
        parameters=schema,
        handler=handler,
    ))
    return registry


def test_registry_only_exposes_registered_tools():
    registry = make_registry({
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    }, handler=lambda args: args["text"])
    assert registry.names() == ("validate_input",)
    assert registry.definitions()[0]["function"]["name"] == "validate_input"
    assert registry.definitions(exclude_names={"validate_input"}) == []


def test_registry_validates_required_fields_types_and_extra_fields():
    registry = make_registry({
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
        "additionalProperties": False,
    })
    with pytest.raises(ValueError, match="wymaga pól"):
        registry.execute("validate_input", {})
    with pytest.raises(ValueError, match="musi mieć typ string"):
        registry.execute("validate_input", {"text": 123})
    with pytest.raises(ValueError, match="nie przyjmuje pól"):
        registry.execute("validate_input", {"text": "ok", "extra": True})


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
        name="validate_input",
        description="Returns text",
        parameters={"type": "object", "properties": {}},
        handler=lambda args: "ok",
    )
    registry.register(tool)
    with pytest.raises(ValueError, match="już zarejestrowane"):
        registry.register(tool)
    with pytest.raises(ValueError, match="Nieznane narzędzie"):
        registry.execute("unknown", {})


def test_registry_enforces_enum_values():
    registry = make_registry({
        "type": "object",
        "properties": {"role": {"type": "string", "enum": ["researcher", "reviewer"]}},
        "required": ["role"],
        "additionalProperties": False,
    })
    assert registry.execute("validate_input", {"role": "reviewer"}) == "ok"
    with pytest.raises(ValueError, match="niedozwoloną wartość"):
        registry.execute("validate_input", {"role": "administrator"})


def test_registry_validates_nested_array_items_and_limits():
    registry = make_registry({
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "enum": ["researcher", "reviewer"]},
                        "task": {"type": "string", "minLength": 1, "maxLength": 20},
                    },
                    "required": ["role", "task"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["tasks"],
        "additionalProperties": False,
    })
    valid = {"tasks": [{"role": "researcher", "task": "Sprawdź kod"}]}
    assert registry.execute("validate_input", valid) == "ok"
    with pytest.raises(ValueError, match="za dużo elementów"):
        registry.execute("validate_input", {"tasks": valid["tasks"] * 3})
    with pytest.raises(ValueError, match="niedozwoloną wartość"):
        registry.execute("validate_input", {"tasks": [{"role": "root", "task": "test"}]})
    with pytest.raises(ValueError, match="nie przyjmuje pól"):
        registry.execute("validate_input", {"tasks": [{"role": "reviewer", "task": "test", "shell": True}]})


def test_registry_validates_numeric_bounds_and_rejects_non_finite_numbers():
    registry = make_registry({
        "type": "object",
        "properties": {"temperature": {"type": "number", "minimum": 0, "maximum": 2}},
        "required": ["temperature"],
        "additionalProperties": False,
    })
    assert registry.execute("validate_input", {"temperature": 1.0}) == "ok"
    with pytest.raises(ValueError, match="większe od maksimum"):
        registry.execute("validate_input", {"temperature": 3})
    with pytest.raises(ValueError, match="skończoną"):
        registry.execute("validate_input", {"temperature": float("inf")})


def test_registry_does_not_allow_boolean_as_number():
    registry = make_registry({
        "type": "object",
        "properties": {"count": {"type": "number"}},
        "required": ["count"],
    })
    with pytest.raises(ValueError, match="musi mieć typ number"):
        registry.execute("validate_input", {"count": True})
