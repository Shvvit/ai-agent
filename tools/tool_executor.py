from __future__ import annotations

import json
import os
from typing import Any, Callable

from tools.file_manager import FileManager
from tools.registry import ToolDefinition, ToolRegistry
from tools.test_runner import TestRunner


class ToolExecutor:
    """Runs only tools registered in the capability-aware registry."""

    def __init__(
        self,
        file_manager: FileManager | None = None,
        test_runner: TestRunner | None = None,
        agent_team=None,
        registry: ToolRegistry | None = None,
        granted_capabilities: set[str] | None = None,
        approval_callback: Callable[[str, dict[str, Any]], bool] | None = None,
    ) -> None:
        self.files = file_manager or FileManager()
        self.tests = test_runner or TestRunner(workspace=self.files.workspace)
        self.agent_team = agent_team
        self.approval_callback = approval_callback
        if approval_callback is not None and not callable(approval_callback):
            raise TypeError("approval_callback musi być funkcją.")
        self.registry = registry or ToolRegistry()
        default_capabilities = {"workspace_read", "workspace_write", "agent_delegation"}
        if os.getenv("AI_ALLOW_UNSANDBOXED_PYTHON", "").strip() == "1":
            default_capabilities.add("code_execution")
        self.granted_capabilities = (
            set(granted_capabilities)
            if granted_capabilities is not None
            else default_capabilities
        )
        if registry is None:
            self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        self.registry.register(ToolDefinition(
            name="write_file",
            description="Zapisuje plik wewnątrz workspace.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            handler=lambda args: self.files.write_file(args["path"], args["content"]),
            required_capabilities=frozenset({"workspace_write"}),
        ))
        self.registry.register(ToolDefinition(
            name="read_file",
            description="Odczytuje plik z workspace.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
            handler=lambda args: self.files.read_file(args["path"]),
            required_capabilities=frozenset({"workspace_read"}),
        ))
        self.registry.register(ToolDefinition(
            name="run_python",
            description="Uruchamia plik Python z workspace; wymaga jawnego opt-in użytkownika.",
            parameters={
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
                "additionalProperties": False,
            },
            handler=self._run_python,
            required_capabilities=frozenset({"code_execution"}),
        ))
        self.registry.register(ToolDefinition(
            name="delegate_task",
            description="Przekazuje analizę jednemu wyspecjalizowanemu agentowi bez narzędzi komputera.",
            parameters={
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["researcher", "programmer", "reviewer"]},
                    "task": {"type": "string"},
                },
                "required": ["role", "task"],
                "additionalProperties": False,
            },
            handler=self._delegate_task,
            required_capabilities=frozenset({"agent_delegation"}),
        ))
        self.registry.register(ToolDefinition(
            name="delegate_tasks",
            description="Deleguje do trzech niezależnych analiz do wyspecjalizowanych agentów.",
            parameters={
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 3,
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string", "enum": ["researcher", "programmer", "reviewer"]},
                                "task": {"type": "string"},
                            },
                            "required": ["role", "task"],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["tasks"],
                "additionalProperties": False,
            },
            handler=self._delegate_tasks,
            required_capabilities=frozenset({"agent_delegation"}),
        ))

    def definitions(self, *, exclude_names: set[str] | None = None) -> list[dict[str, Any]]:
        return self.registry.definitions(exclude_names=exclude_names)

    def _run_python(self, arguments: dict[str, Any]) -> str:
        result = self.tests.run_python(arguments["path"])
        return (
            f"SUKCES: {result.success}\n"
            f"KOD WYJŚCIA: {result.return_code}\n"
            f"WYNIK:\n{result.output}"
        )

    def _team(self):
        if self.agent_team is not None:
            return self.agent_team
        from agents.team import AgentTeam
        return AgentTeam()

    def _delegate_task(self, arguments: dict[str, Any]) -> str:
        return self._team().run(arguments["role"], arguments["task"])

    def _delegate_tasks(self, arguments: dict[str, Any]) -> str:
        results = self._team().run_many(arguments["tasks"])
        return "\n\n".join(
            f"AGENT {index + 1}:\n{result}"
            for index, result in enumerate(results)
        )

    def execute(self, name: str, arguments: dict, *, approved: bool = False) -> str:
        return self.registry.execute(
            name,
            arguments,
            granted_capabilities=self.granted_capabilities,
            approved=approved,
        )

    def execute_for_agent(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a model-requested tool, requiring a separate user decision when configured."""
        approved = False
        if self.registry.requires_approval(name):
            if self.approval_callback is None:
                raise PermissionError(
                    f"Narzędzie {name} wymaga zgody użytkownika, ale nie ma aktywnego kanału zatwierdzania."
                )
            decision = self.approval_callback(name, dict(arguments))
            if not isinstance(decision, bool):
                raise TypeError("Kanał zatwierdzania musi zwracać bool.")
            if not decision:
                raise PermissionError(f"Użytkownik odmówił wykonania narzędzia {name}.")
            approved = True
        return self.execute(name, arguments, approved=approved)

    def execute_json(self, name: str, arguments_json: str) -> str:
        arguments = json.loads(arguments_json)
        if not isinstance(arguments, dict):
            raise ValueError("Argumenty muszą być obiektem JSON.")
        return self.execute(name, arguments)
