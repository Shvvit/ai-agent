from __future__ import annotations

import base64
import hmac

from starlette.responses import JSONResponse


class SidecarBasicAuthMiddleware:
    """Protect the desktop sidecar API with the credential OpenCode requires."""

    def __init__(self, app, password: str):
        self.app = app
        self.authorization = b"Basic " + base64.b64encode(f"opencode:{password}".encode("utf-8"))

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", ()))
        authorization = headers.get(b"authorization", b"")
        if not hmac.compare_digest(authorization, self.authorization):
            response = JSONResponse(
                {"detail": "Unauthorized"},
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="WlasneAI"'},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)
