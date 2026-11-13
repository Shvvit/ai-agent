"""OpenCode-compatible process entry point for the WlasneAI Python sidecar."""
from __future__ import annotations

import json
import os
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


# Keep in sync with upstream/opencode/packages/cli/package.json at the pinned
# submodule revision. DesktopCli reads the adjacent opencode-cli.version file.
SIDECAR_VERSION = "2.3.0"


def registration_path(env: dict[str, str] | None = None, home: Path | None = None) -> Path:
    values = os.environ if env is None else env
    state_home = values.get("XDG_STATE_HOME")
    root = Path(state_home) if state_home else (home or Path.home()) / ".local" / "state"
    return root / "opencode" / "service.json"


def write_registration(path: Path, *, pid: int, url: str, version: str = SIDECAR_VERSION) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": version, "url": url, "pid": pid}
    fd, temp_name = tempfile.mkstemp(prefix="service-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def remove_owned_registration(path: Path, *, pid: int, url: str) -> None:
    try:
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("pid") == pid and payload.get("url") == url:
            path.unlink(missing_ok=True)
    except (OSError, ValueError):
        pass


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args in (["--version"], ["-v"], ["version"]):
        print(f"opencode v{SIDECAR_VERSION}")
        return 0
    if args[:2] != ["serve", "--service"]:
        print("Usage: opencode-cli.exe serve --service | --version", file=sys.stderr)
        return 2

    os.environ["WLASNEAI_OPENCODE_VERSION"] = SIDECAR_VERSION
    from api.server import start_bridge

    bridge = start_bridge(host="127.0.0.1", port=0)
    registration = registration_path()
    write_registration(registration, pid=os.getpid(), url=bridge.base_url)
    stopping = False

    def stop(_signum: int, _frame: Any) -> None:
        nonlocal stopping
        stopping = True
        bridge.server.should_exit = True

    for signum in (signal.SIGINT, signal.SIGTERM):
        signal.signal(signum, stop)
    try:
        while bridge.thread.is_alive() and not stopping:
            time.sleep(0.2)
    finally:
        bridge.stop()
        remove_owned_registration(registration, pid=os.getpid(), url=bridge.base_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
