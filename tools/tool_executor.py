from __future__ import annotations

import json

from tools.file_manager import FileManager
from tools.test_runner import TestRunner
from tools.web_search import WebSearchClient
from tools.terminal import TerminalRunner


class ToolExecutor:
    """Wykonuje jawnie dozwolone narzędzia agenta."""

    def __init__(self, file_manager: FileManager | None = None, test_runner: TestRunner | None = None,
                 web_search: WebSearchClient | None = None,
                 terminal: TerminalRunner | None = None) -> None:
        self.files = file_manager or FileManager()
        self.tests = test_runner or TestRunner(workspace=self.files.workspace)
        self.web = web_search or WebSearchClient.from_env()
        self.terminal = terminal or TerminalRunner(workspace=self.files.workspace)

    @property
    def web_search_available(self) -> bool:
        return self.web.enabled

    def execute(self, name: str, arguments: dict) -> str:
        if not isinstance(arguments, dict):
            raise ValueError("Argumenty narzędzia muszą być obiektem.")
        if name == "write_file":
            path, content = arguments.get("path"), arguments.get("content")
            if not isinstance(path, str) or not isinstance(content, str):
                raise ValueError("write_file wymaga pól path i content.")
            return self.files.write_file(path, content)
        if name == "read_file":
            path = arguments.get("path")
            if not isinstance(path, str):
                raise ValueError("read_file wymaga pola path.")
            return self.files.read_file(path)
        if name == "list_files":
            path = arguments.get("path", ".")
            if not isinstance(path, str):
                raise ValueError("list_files: path musi być tekstem.")
            return "\n".join(self.files.list_files(path)) or "(brak plików)"
        if name == "search_files":
            query, path = arguments.get("query"), arguments.get("path", ".")
            if not isinstance(query, str) or not isinstance(path, str):
                raise ValueError("search_files wymaga query i opcjonalnego path.")
            return "\n".join(self.files.search_files(query, path)) or "(brak wyników)"
        if name == "run_command":
            command = arguments.get("command")
            if not isinstance(command, str):
                raise ValueError("run_command wymaga pola command.")
            result = self.terminal.run(command)
            return f"SUCCESS: {result.success}\nEXIT CODE: {result.return_code}\n{result.output}"
        if name == "web_search":
            query = arguments.get("query")
            if not isinstance(query, str):
                raise ValueError("web_search wymaga pola query.")
            results = self.web.search(query)
            if not results:
                return "(brak wyników)"
            return "\n".join(
                f"{index}. {item['title']}\nURL: {item['url']}\n{item['snippet']}"
                for index, item in enumerate(results, start=1)
            )
        if name == "run_python":
            path = arguments.get("path")
            if not isinstance(path, str):
                raise ValueError("run_python wymaga pola path.")
            result = self.tests.run_python(path)
            return f"SUKCES: {result.success}\nKOD WYJŚCIA: {result.return_code}\nWYNIK:\n{result.output}"
        raise ValueError(f"Nieznane narzędzie: {name}")

    def execute_json(self, name: str, arguments_json: str) -> str:
        arguments = json.loads(arguments_json)
        if not isinstance(arguments, dict):
            raise ValueError("Argumenty muszą być obiektem JSON.")
        return self.execute(name, arguments)
