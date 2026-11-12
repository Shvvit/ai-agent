from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict[str, Any]], str]
    required_capabilities: frozenset[str] = frozenset()
    requires_approval: bool = False

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", self.name):
            raise ValueError("Nazwa narzędzia ma niepoprawny format.")
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("Opis narzędzia nie może być pusty.")
        if not isinstance(self.parameters, dict) or self.parameters.get("type") != "object":
            raise ValueError("Schemat parametrów narzędzia musi być obiektem JSON.")
        if not callable(self.handler):
            raise ValueError("Narzędzie musi mieć funkcję handler.")
        if not isinstance(self.required_capabilities, (set, frozenset)) or any(
            not isinstance(item, str) or not item for item in self.required_capabilities
        ):
            raise ValueError("required_capabilities musi być zbiorem nazw uprawnień.")


class ToolRegistry:
    """Explicit allow-list of callable tools with schema and permission checks."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Narzędzie {tool.name} jest już zarejestrowane.")
        self._tools[tool.name] = tool

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))

    def definitions(self, *, exclude_names: set[str] | None = None) -> list[dict[str, Any]]:
        excluded = exclude_names or set()
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": copy.deepcopy(tool.parameters),
                },
            }
            for name, tool in sorted(self._tools.items())
            if name not in excluded
        ]

    @staticmethod
    def _validate_arguments(tool: ToolDefinition, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ValueError("Argumenty narzędzia muszą być obiektem JSON.")
        schema = tool.parameters
        required = schema.get("required", [])
        missing = [name for name in required if name not in arguments]
        if missing:
            raise ValueError(
                f"Narzędzie {tool.name} wymaga pól: {', '.join(missing)}."
            )
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}))
            extra = set(arguments) - allowed
            if extra:
                raise ValueError(
                    f"Narzędzie {tool.name} nie przyjmuje pól: {', '.join(sorted(extra))}."
                )
        for name, value in arguments.items():
            prop = schema.get("properties", {}).get(name, {})
            expected = prop.get("type")
            valid = {
                "string": lambda item: isinstance(item, str),
                "object": lambda item: isinstance(item, dict),
                "array": lambda item: isinstance(item, list),
                "integer": lambda item: type(item) is int,
                "number": lambda item: type(item) in {int, float},
                "boolean": lambda item: isinstance(item, bool),
            }.get(expected)
            if valid is not None and not valid(value):
                raise ValueError(
                    f"Pole {name} narzędzia {tool.name} musi mieć typ {expected}."
                )

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        granted_capabilities: set[str] | None = None,
        approved: bool = False,
    ) -> str:
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Nieznane narzędzie: {name}")
        self._validate_arguments(tool, arguments)
        if granted_capabilities is None:
            granted = set()
        elif not isinstance(granted_capabilities, (set, frozenset)) or any(
            not isinstance(item, str) for item in granted_capabilities
        ):
            raise TypeError("granted_capabilities musi być zbiorem tekstowych uprawnień.")
        else:
            granted = set(granted_capabilities)
        if not isinstance(approved, bool):
            raise TypeError("approved musi być wartością bool.")
        missing = tool.required_capabilities - granted
        if missing:
            raise PermissionError(
                f"Brak uprawnień do narzędzia {name}: {', '.join(sorted(missing))}."
            )
        if tool.requires_approval and approved is not True:
            raise PermissionError(f"Narzędzie {name} wymaga jawnej zgody użytkownika.")
        result = tool.handler(arguments)
        if not isinstance(result, str):
            raise TypeError(f"Narzędzie {name} musi zwracać tekst.")
        return result
