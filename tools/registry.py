from __future__ import annotations

import copy
import math
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
        if not isinstance(self.name, str) or not re.fullmatch(r"[a-z][a-z0-9_]{1,63}", self.name):
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
        if not isinstance(self.requires_approval, bool):
            raise ValueError("requires_approval musi być wartością bool.")


class ToolRegistry:
    """Explicit allow-list of callable tools with schema and permission checks."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        if not isinstance(tool, ToolDefinition):
            raise TypeError("Można rejestrować wyłącznie ToolDefinition.")
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
    def _validate_value(value: Any, schema: dict[str, Any], path: str) -> None:
        if not isinstance(schema, dict):
            raise ValueError(f"Niepoprawny schemat pola {path}.")
        expected = schema.get("type")
        validators = {
            "string": lambda item: isinstance(item, str),
            "object": lambda item: isinstance(item, dict),
            "array": lambda item: isinstance(item, list),
            "integer": lambda item: type(item) is int,
            "number": lambda item: type(item) in {int, float},
            "boolean": lambda item: isinstance(item, bool),
        }
        if expected in validators and not validators[expected](value):
            raise ValueError(f"Pole {path} musi mieć typ {expected}.")

        if "enum" in schema and value not in schema["enum"]:
            raise ValueError(f"Pole {path} ma niedozwoloną wartość.")

        if isinstance(value, str):
            if len(value) < schema.get("minLength", 0):
                raise ValueError(f"Pole {path} jest krótsze niż dozwolone minimum.")
            if "maxLength" in schema and len(value) > schema["maxLength"]:
                raise ValueError(f"Pole {path} przekracza dozwoloną długość.")
            if "pattern" in schema and re.search(schema["pattern"], value) is None:
                raise ValueError(f"Pole {path} nie spełnia wymaganego wzorca.")

        if type(value) in {int, float} and not isinstance(value, bool):
            if not math.isfinite(value):
                raise ValueError(f"Pole {path} musi być liczbą skończoną.")
            if "minimum" in schema and value < schema["minimum"]:
                raise ValueError(f"Pole {path} jest mniejsze od minimum.")
            if "maximum" in schema and value > schema["maximum"]:
                raise ValueError(f"Pole {path} jest większe od maksimum.")

        if isinstance(value, list):
            if len(value) < schema.get("minItems", 0):
                raise ValueError(f"Lista {path} zawiera za mało elementów.")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                raise ValueError(f"Lista {path} zawiera za dużo elementów.")
            item_schema = schema.get("items")
            if item_schema is not None:
                for index, item in enumerate(value):
                    ToolRegistry._validate_value(item, item_schema, f"{path}[{index}]")

        if isinstance(value, dict):
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            if not isinstance(properties, dict) or not isinstance(required, list):
                raise ValueError(f"Niepoprawny schemat obiektu {path}.")
            missing = [name for name in required if name not in value]
            if missing:
                raise ValueError(
                    f"Obiekt {path} wymaga pól: {', '.join(missing)}."
                )
            if schema.get("additionalProperties") is False:
                extra = set(value) - set(properties)
                if extra:
                    raise ValueError(
                        f"Obiekt {path} nie przyjmuje pól: {', '.join(sorted(extra))}."
                    )
            for name, item in value.items():
                if name in properties:
                    ToolRegistry._validate_value(item, properties[name], f"{path}.{name}")

    @staticmethod
    def _validate_arguments(tool: ToolDefinition, arguments: dict[str, Any]) -> None:
        if not isinstance(arguments, dict):
            raise ValueError("Argumenty narzędzia muszą być obiektem JSON.")
        ToolRegistry._validate_value(arguments, tool.parameters, tool.name)

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

    def requires_approval(self, name: str) -> bool:
        """Return whether a registered tool requires a separate user decision."""
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Nieznane narzędzie: {name}")
        return tool.requires_approval
