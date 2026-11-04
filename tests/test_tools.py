from __future__ import annotations

import pytest

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


@pytest.mark.parametrize("path", ["../outside.txt", "..\\outside.txt", "folder/../../outside.txt"])
def test_path_traversal_is_blocked(tmp_path, path):
    files = FileManager(tmp_path / "workspace")
    with pytest.raises(PermissionError):
        files.write_file(path, "nie powinno się zapisać")


@pytest.mark.parametrize("path", [r"C:\\Windows\\win.ini", r"\\server\\share\\file.txt"])
def test_windows_absolute_path_is_blocked_on_every_platform(tmp_path, path):
    files = FileManager(tmp_path / "workspace")
    with pytest.raises(PermissionError):
        files.read_file(path)


def test_absolute_path_is_blocked(tmp_path):
    files = FileManager(tmp_path / "workspace")
    with pytest.raises(PermissionError):
        files.read_file(str(tmp_path / "outside.txt"))


def test_test_runner_blocks_windows_path_traversal(tmp_path):
    runner = TestRunner(workspace=tmp_path / "workspace")
    with pytest.raises(PermissionError):
        runner.run_python(r"..\\outside.py")


def test_test_runner_runs_python_file(tmp_path):
    runner = TestRunner(workspace=tmp_path / "workspace")
    (runner.workspace / "hello.py").write_text("print('hello')", encoding="utf-8")
    result = runner.run_python("hello.py")
    assert result.success
    assert result.output == "hello"


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


def test_list_and_search_workspace_files(tmp_path):
    files = FileManager(tmp_path / "workspace")
    files.write_file("src/main.py", "print('agent')\n# TODO improve")
    files.write_file("README.md", "Własne AI")
    assert files.list_files() == ["README.md", "src/main.py"]
    assert files.search_files("todo") == ["src/main.py:2: # TODO improve"]


def test_file_size_limit_is_enforced(tmp_path):
    files = FileManager(tmp_path / "workspace", max_file_bytes=8)
    with pytest.raises(ValueError, match="przekracza limit"):
        files.write_file("large.txt", "123456789")


def test_symlink_escape_is_blocked(tmp_path):
    files = FileManager(tmp_path / "workspace")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    link = files.workspace / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks unavailable for current user/system")
    with pytest.raises(PermissionError):
        files.read_file("escape/secret.txt")


def test_search_rejects_unbounded_query(tmp_path):
    files = FileManager(tmp_path / "workspace")
    with pytest.raises(ValueError, match="maksymalnie 1000"):
        files.search_files("x" * 1001)


from tools.web_search import WebSearchClient, WebSearchError


def test_web_search_requires_explicit_provider_and_key():
    client = WebSearchClient()
    assert client.enabled is False
    with pytest.raises(WebSearchError):
        client.search("local AI agent")


def test_web_search_validates_query():
    client = WebSearchClient(provider="tavily", api_key="test")
    with pytest.raises(ValueError):
        client.search(" ")


def test_tavily_search_normalizes_results(monkeypatch):
    import tools.web_search as module

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"results": [
                {"title": "Docs", "url": "https://example.com/docs", "content": "Useful docs"},
                {"title": "Bad", "url": "javascript:alert(1)", "content": "not a link"},
            ]}

    monkeypatch.setattr(module.httpx, "post", lambda *args, **kwargs: FakeResponse())
    results = WebSearchClient(provider="tavily", api_key="secret").search("agent framework")
    assert results == [{
        "title": "Docs", "url": "https://example.com/docs", "snippet": "Useful docs"
    }]


def test_tool_executor_routes_web_search():
    class FakeSearch:
        enabled = True

        def search(self, query):
            assert query == "Ollama documentation"
            return [{"title": "Ollama", "url": "https://ollama.com", "snippet": "Official docs"}]

    executor = ToolExecutor(web_search=FakeSearch())
    assert executor.web_search_available
    output = executor.execute("web_search", {"query": "Ollama documentation"})
    assert "https://ollama.com" in output
    assert "Official docs" in output


def test_web_search_environment_limits_are_bounded(monkeypatch):
    monkeypatch.setenv("AI_WEB_SEARCH_PROVIDER", "brave")
    monkeypatch.setenv("AI_WEB_SEARCH_API_KEY", "test")
    monkeypatch.setenv("AI_WEB_SEARCH_TIMEOUT", "999")
    monkeypatch.setenv("AI_WEB_SEARCH_MAX_RESULTS", "999")
    client = WebSearchClient.from_env()
    assert client.timeout == 60.0
    assert client.max_results == 10


def test_brave_search_uses_token_header(monkeypatch):
    import tools.web_search as module

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"web": {"results": [
                {"title": "Search", "url": "https://example.org", "description": "Snippet"}
            ]}}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(module.httpx, "get", fake_get)
    result = WebSearchClient(provider="brave", api_key="brave-secret").search("query")
    assert captured["headers"]["X-Subscription-Token"] == "brave-secret"
    assert result[0]["snippet"] == "Snippet"


def test_tool_executor_routes_allowlisted_terminal_command():
    class FakeResult:
        success = True
        return_code = 0
        output = "NAME ID SIZE"

    class FakeTerminal:
        def run(self, command):
            assert command == "ollama list"
            return FakeResult()

    executor = ToolExecutor(terminal=FakeTerminal())
    result = executor.execute("run_command", {"command": "ollama list"})
    assert "NAME ID SIZE" in result
    assert "SUCCESS: True" in result


def test_test_runner_bounds_captured_output(tmp_path):
    runner = TestRunner(workspace=tmp_path / "workspace", max_output_bytes=1024)
    (runner.workspace / "large.py").write_text("print('x' * 5000)", encoding="utf-8")
    result = runner.run_python("large.py")
    assert result.success
    assert "Wynik skrócony do limitu" in result.output
    assert len(result.output) < 1100


def test_test_runner_kills_timed_out_process(tmp_path):
    runner = TestRunner(workspace=tmp_path / "workspace", timeout=1)
    (runner.workspace / "slow.py").write_text("import time; time.sleep(3)", encoding="utf-8")
    result = runner.run_python("slow.py")
    assert result.success is False
    assert result.return_code == -1
    assert "przekroczył limit" in result.output
