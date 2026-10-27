
from __future__ import annotations

import json

from tools.file_manager import FileManager
from tools.test_runner import TestRunner


class ToolExecutor:
    """Wykonuje dozwolone narzędzia agenta."""

    def __init__(
        self,
        file_manager: FileManager | None = None,
        test_runner: TestRunner | None = None,
    ) -> None:
        self.files = file_manager or FileManager()
        self.tests = test_runner or TestRunner(
            workspace=self.files.workspace
        )

    def execute(self, name: str, arguments: dict) -> str:
        if name == "write_file":
            path = arguments.get("path")
            content = arguments.get("content")

            if not isinstance(path, str) or not isinstance(content, str):
                raise ValueError("write_file wymaga pól path i content.")

            return self.files.write_file(path, content)

        if name == "read_file":
            path = arguments.get("path")

            if not isinstance(path, str):
                raise ValueError("read_file wymaga pola path.")

            return self.files.read_file(path)

        if name == "run_python":
            path = arguments.get("path")

            if not isinstance(path, str):
                raise ValueError("run_python wymaga pola path.")

            result = self.tests.run_python(path)
            return (
                f"SUKCES: {result.success}\n"
                f"KOD WYJŚCIA: {result.return_code}\n"
                f"WYNIK:\n{result.output}"
            )

        raise ValueError(f"Nieznane narzędzie: {name}")

    def execute_json(self, name: str, arguments_json: str) -> str:
        arguments = json.loads(arguments_json)

        if not isinstance(arguments, dict):
            raise ValueError("Argumenty muszą być obiektem JSON.")

        return self.execute(name, arguments)
