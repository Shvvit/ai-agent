from __future__ import annotations

import os
import socket
import threading
import time
from dataclasses import dataclass

import uvicorn

from api.app import create_app


@dataclass
class BridgeServer:
    server: uvicorn.Server
    thread: threading.Thread
    host: str
    port: int

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def stop(self, timeout: float = 5.0) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=timeout)


def _free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def start_bridge(host: str = "127.0.0.1", port: int | None = None, timeout: float = 10.0) -> BridgeServer:
    """Start the API on loopback only and wait until it accepts connections."""
    selected_port = port or _free_port(host)
    config = uvicorn.Config(create_app(), host=host, port=selected_port, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, name="wlasneai-api", daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not thread.is_alive():
            raise RuntimeError("Serwer API WlasneAI zakończył działanie podczas uruchamiania.")
        try:
            with socket.create_connection((host, selected_port), timeout=0.2):
                os.environ["OPENCODE_SERVER_URL"] = f"http://{host}:{selected_port}"
                return BridgeServer(server, thread, host, selected_port)
        except OSError:
            time.sleep(0.05)
    server.should_exit = True
    thread.join(timeout=1)
    raise TimeoutError("Nie udało się uruchomić lokalnego API WlasneAI.")


def main() -> None:
    bridge = start_bridge(port=int(os.getenv("WLASNEAI_API_PORT", "0")))
    print(f"WlasneAI API: {bridge.base_url}")
    try:
        while bridge.thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        bridge.stop()


if __name__ == "__main__":
    main()
