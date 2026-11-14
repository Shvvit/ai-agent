"""Deterministic local OpenAI-compatible provider for the packaged desktop smoke test."""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self) -> None:
        if self.path != "/health":
            self.send_error(404)
            return
        self._json(200, {"healthy": True})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        if self.headers.get("Authorization") != "Bearer wlasneai-e2e-key":
            self.send_error(401)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            payload: dict[str, Any] = json.loads(self.rfile.read(size))
            user_message = next(
                message for message in reversed(payload["messages"])
                if message.get("role") == "user"
            )
            prompt = user_message.get("content", "")
            if not isinstance(prompt, str):
                raise ValueError("Expected text-only smoke-test prompt")
        except (KeyError, StopIteration, TypeError, ValueError, json.JSONDecodeError):
            self.send_error(400, "Invalid chat completion request")
            return

        self._json(200, {
            "id": "chatcmpl-wlasneai-e2e",
            "object": "chat.completion",
            "created": 1,
            "model": payload.get("model", "wlasneai-e2e"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"WlasneAI E2E response: {prompt}",
                },
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        })

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(format % args, flush=True)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", int(os.getenv("WLASNEAI_E2E_PROVIDER_PORT", "43177"))), Handler)
    print("WlasneAI smoke provider ready", flush=True)
    server.serve_forever()
