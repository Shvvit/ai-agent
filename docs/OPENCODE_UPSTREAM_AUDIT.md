# OpenCode upstream audit for WlasneAI

Audit date: 2026-11-13
Upstream repository: https://github.com/anomalyco/opencode
Upstream branch evaluated: `dev`
Upstream commit evaluated: `f6e0c2d0833ffe772035f221fed923e1cd5fb408`
Upstream package version observed: `2.3.0`
License: MIT (see `vendor/opencode/LICENSE`).

## Findings

The current WlasneAI desktop is a PySide6 application in `apps/desktop/main.py`. The API package files (`api/app.py`, `api/routes.py`, `api/schemas.py`, `api/events.py`, and `api/sessions.py`) are currently empty. The project is Python-first and has no existing JavaScript workspace or frontend build.

The upstream OpenCode desktop is not a standalone UI folder:
- `packages/desktop`: Electron main/preload/renderer shell and Windows packaging.
- `packages/app`: SolidJS application containing the actual session/chat/workspace UI.
- `packages/ui`: shared UI primitives and styles.
- `packages/client`, `packages/schema`, `packages/session-ui`, `packages/util`, `packages/plugin`, `packages/gui-plugins`: required workspace packages and contracts.
- Root workspace uses Bun workspaces and a centralized dependency catalog/lockfile.

The desktop package depends on multiple `workspace:*` packages. Copying only `packages/desktop` or only `packages/app` will not build. The upstream root manifest currently declares Bun 1.4.4, and the desktop package uses Electron 44.9.1 plus electron-vite/electron-builder.

## Integration decision

Use the actual upstream Electron + SolidJS desktop application and retain WlasneAI's Python runtime as the project-specific agent backend.

Do not attempt to embed the current PySide6 window inside Electron. Do not build a lookalike. Do not run a second OpenCode agent engine in parallel with WlasneAI.

The upstream UI expects OpenCode's server/client contracts and capabilities. WlasneAI's API modules are empty today, so the backend compatibility layer must be implemented before the imported UI can function. The UI and server must be pinned to the same upstream commit to avoid contract drift.

## Planned execution

1. Import/pin the upstream workspace with its full required package graph and MIT notice.
2. Establish a reproducible Bun workspace build on CI before changing upstream behavior.
3. Inspect the exact client/server contract at the pinned commit and generate a compatibility checklist.
4. Implement a Python sidecar HTTP/SSE/WebSocket compatibility service for WlasneAI sessions, messages, streaming, cancellation, models/providers, tool calls/results, permissions, and project/workspace operations as required by the renderer.
5. Adapt the upstream desktop startup lifecycle to launch and supervise the WlasneAI sidecar, use loopback-only communication, and shut it down cleanly.
6. Replace OpenCode-specific provider/agent actions with WlasneAI's model router, Ollama/OpenRouter adapters, task manager, memory, and tool registry.
7. Build the Electron app and Python sidecar into one Windows distribution; keep the current PySide6 executable as rollback until acceptance.
8. Run Windows smoke/e2e tests for first launch, restart, offline Ollama, Ollama model, OpenRouter credentials, session persistence, streaming, tools, cancellation, and clean shutdown.

## Current state

This commit records the source audit and upstream license only. It does not claim that the upstream UI has already been imported or that an integrated installer exists. The next code milestone is importing the upstream workspace in a buildable, pinned form.
