from __future__ import annotations

import pytest

from tools.file_manager import FileManager
from tools.test_runner import TestRunner
from tools.tool_executor import ToolExecutor


def test_write_and_read_file(tmp_path):
    files = FileManager(tmp_path / "workspace")

    files.write_file("example.txt", "Własne AI działa")
    result = files.read_file("example.txt")

    assert result == "Własne AI działa"


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
    ],
)
def test_path_traversal_is_blocked(tmp_path, path):
    files = FileManager(tmp_path / "workspace")

    with pytest.raises(PermissionError):
        files.write_file(path, "nie powinno się zapisać")


def test_absolute_path_is_blocked(tmp_path):
    files = FileManager(tmp_path / "workspace")

    with pytest.raises(PermissionError):
        files.read_file(str(tmp_path / "outside.txt"))


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

    result = executor.execute(
        "write_file",
        {"path": "created.txt", "content": "OK"},
    )

    assert "Zapisano plik" in result
    assert files.read_file("created.txt") == "OK"
