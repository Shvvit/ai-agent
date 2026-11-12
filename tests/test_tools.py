from __future__ import annotations

import pytest

from core.verifier import Verifier
from tools.file_manager import FileManager
from tools.test_runner import TestRunner
from tools.tool_executor import ToolExecutor


def test_write_and_read_file(tmp_path):
    files = FileManager(tmp_path / "workspace")
    files.write_file("example.txt", "Własne AI działa")
    assert files.read_file("example.txt") == "Własne AI działa"


def test_write_file_creates_subdirectories(tmp_path):
    files = FileManager(tmp_path / "workspace")
    files.write_file("folder/subfolder/example.txt", "test")
    assert files.read_file("folder/subfolder/example.txt") == "test"


def test_read_missing_file_raises_error(tmp_path):
    files = FileManager(tmp_path / "workspace")
    with pytest.raises(FileNotFoundError):
        files.read_file("missing.txt")


@pytest.mark.parametrize(
    "path",
    [
        "../outside.txt",
        "..\\outside.txt",
        "folder/../../outside.txt",
        "C:\\Windows\\system.ini",
        "\\\\server\\share\\file.txt",
    ],
)
def test_path_traversal_and_windows_absolute_paths_are_blocked(tmp_path, path):
    files = FileManager(tmp_path / "workspace")
    with pytest.raises(PermissionError):
        files.write_file(path, "nie powinno się zapisać")


def test_absolute_path_is_blocked(tmp_path):
    files = FileManager(tmp_path / "workspace")
    with pytest.raises(PermissionError):
        files.read_file(str(tmp_path / "outside.txt"))


def test_verifier_rejects_windows_style_traversal(tmp_path):
    verifier = Verifier(tmp_path / "workspace")
    result = verifier.file_exists("..\\outside.txt")
    assert result.success is False


def test_test_runner_rejects_windows_style_traversal(tmp_path):
    runner = TestRunner(workspace=tmp_path / "workspace")
    with pytest.raises(PermissionError):
        runner.run_python("..\\outside.py")


def test_tool_executor_rejects_unknown_tool(tmp_path):
    files = FileManager(tmp_path / "workspace")
    runner = TestRunner(workspace=files.workspace)
    executor = ToolExecutor(file_manager=files, test_runner=runner)
    with pytest.raises(ValueError, match="Nieznane narzędzie"):
        executor.execute("unknown_tool", {})


def test_tool_executor_writes_file(tmp_path):
    files = FileManager(tmp_path / "workspace")
    runner = TestRunner(workspace=files.workspace)
    executor = ToolExecutor(file_manager=files, test_runner=runner)
    result = executor.execute("write_file", {"path": "created.txt", "content": "OK"})
    assert "Zapisano plik" in result
    assert files.read_file("created.txt") == "OK"


def test_python_execution_requires_explicit_opt_in(tmp_path):
    files = FileManager(tmp_path / "workspace")
    files.write_file("hello.py", "print('hello')\n")
    runner = TestRunner(workspace=files.workspace)
    with pytest.raises(PermissionError, match="domyślnie wyłączone"):
        runner.run_python("hello.py")


def test_python_execution_runs_only_after_explicit_opt_in(tmp_path):
    files = FileManager(tmp_path / "workspace")
    files.write_file("hello.py", "print('hello')\n")
    runner = TestRunner(workspace=files.workspace, allow_unsafe_execution=True)
    result = runner.run_python("hello.py")
    assert result.success is True
    assert result.output == "hello"


def test_tool_executor_formats_multiple_agent_results_with_newlines():
    class Team:
        def run_many(self, tasks):
            return ["wynik pierwszy", "wynik drugi"]

    executor = ToolExecutor(agent_team=Team())
    output = executor.execute(
        "delegate_tasks",
        {"tasks": [
            {"role": "researcher", "task": "A"},
            {"role": "reviewer", "task": "B"},
        ]},
    )
    assert output == "AGENT 1:\nwynik pierwszy\n\nAGENT 2:\nwynik drugi"



def test_tool_executor_uses_capability_allow_list(tmp_path):
    files = FileManager(tmp_path / "workspace")
    executor = ToolExecutor(
        file_manager=files,
        granted_capabilities={"workspace_read"},
    )
    with pytest.raises(PermissionError, match="Brak uprawnień"):
        executor.execute(
            "write_file",
            {"path": "denied.txt", "content": "no"},
        )


def test_tool_executor_rejects_missing_schema_fields(tmp_path):
    executor = ToolExecutor(file_manager=FileManager(tmp_path / "workspace"))
    with pytest.raises(ValueError, match="wymaga pól"):
        executor.execute("write_file", {"path": "missing-content.txt"})
