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

The full upstream repository is now attached as a Git submodule at `upstream/opencode`, pinned to `f6e0c2d0833ffe772035f221fed923e1cd5fb408`. The root `.gitmodules` file preserves the existing Agent Zero submodule and adds the OpenCode source. The upstream MIT license is also copied to `vendor/opencode/LICENSE` with attribution notes.

This makes the complete original OpenCode UI and desktop source available in the WlasneAI repository without flattening or losing upstream history. It is a source import, not yet a working WlasneAI desktop integration: the Python compatibility service, Electron sidecar lifecycle, WlasneAI-specific UI adaptations, and combined Windows packaging remain to be implemented and tested.

The next code milestone is to make the pinned upstream desktop workspace build reproducibly on Windows CI, then implement the Python compatibility bridge against the exact pinned API contracts.


## Follow-up audit: desktop sidecar and API contract (2026-11-13)

The pinned upstream desktop already has a first-class sidecar connection path. Relevant upstream files at the pinned commit:

- `packages/desktop/src/main/service/sidecar-probe.ts`: discovers an already-running compatible service in packaged mode.
- `packages/desktop/src/main/service/sidecar-credentials.ts`: stores the sidecar endpoint and password in the Electron main process, and derives Basic authorization only for requests to that endpoint.
- `packages/app/src/runtime/server/registry.tsx`: models the built-in desktop server as a `sidecar` connection and marks it as local.
- `packages/app/src/runtime/server/client.tsx`: creates the API transport for the sidecar and supports endpoint changes/reconnects.
- `packages/app/src/runtime/server/api.ts`: constructs the generated OpenCode API client against the selected base URL.
- `packages/app/src/runtime/server/health.ts`: probes the server using the generated `server.info` endpoint, not the custom `/global/health` endpoint.

This confirms the intended integration direction: package WlasneAI's Python process as the desktop sidecar, then feed its endpoint to the existing sidecar connection lifecycle. Merely setting `OPENCODE_SERVER_URL` in the Python process is not sufficient to register it with Electron's sidecar lifecycle.

### Compatibility gaps found in the first bridge implementation

The current `api/app.py` is a useful smoke-test bridge, not yet an OpenCode-compatible server. The original desktop uses the generated client from `packages/client` and calls a much broader typed API. In particular:

- Health checks use the generated `server.info` operation at `GET /api/info` in pinned commit `f6e0c2d0833ffe772035f221fed923e1cd5fb408`; `GET /global/health` alone cannot make the desktop consider the bridge healthy.
- The UI's message submission path is based on the generated session prompt/message operations and typed response/event contracts; the current synchronous `POST /session/{id}/message` implementation is not yet proven compatible.
- The renderer consumes a live event stream and session lifecycle events. The current SSE endpoint emits only `server.connected` once and does not publish message/session updates.
- Provider/model and agent responses must match the exact generated schemas, not just be plausible JSON with similar field names.
- The desktop uses additional project/location/config, file, permission, command, and session endpoints during normal navigation and interaction. These must be inventoried from the pinned client contract before declaring compatibility.

### Updated implementation sequence

1. Add a contract inventory from the pinned `packages/client/src/contract.ts` and generated API schema. For every operation used during initial desktop boot and chat, record method, path, query/body schema, response schema, and whether it is required or optional.
2. Implement the minimum boot contract first: server info, location, project, path, config, provider/model, agent, command, session list/create/get, and event subscription.
3. Implement streaming prompt execution and event emission with stable OpenCode message/part IDs. Preserve WlasneAI's own model routing and agent execution.
4. Add a sidecar launcher in the Electron main process that starts the packaged Python runtime, waits for a readiness handshake, supplies endpoint credentials through the existing sidecar mechanism, monitors process exit, and shuts down cleanly.
5. Expand API coverage for tools, files, permissions, cancellation, and other UI features only after the boot + chat flow passes end-to-end tests.

Do not treat the existing Windows build as proof of UI compatibility: it currently proves only that the upstream desktop workspace can be built in CI.

### Verified API implementation progress

The pinned protocol source was rechecked at `f6e0c2d0833ffe772035f221fed923e1cd5fb408`. The bridge now implements these exact initial desktop contracts:

- `GET /api/info` (`server.info`): version, process id, URL list, and temporary path.
- `GET /api/project` (`project.list`): project id, canonical path, timestamps, and sandbox list.
- `GET /api/location` (`location.get`): resolved directory and project identity.
- `GET/POST /api/session`, `GET/DELETE /api/session/:sessionID`: session listing, creation, retrieval, and removal with the pinned `Session.Info` response envelope.
- `GET /api/session/active` and `GET /api/session/:sessionID/message`: active-session snapshot and typed transcript history.
- `GET /api/event` and `POST /api/session/:sessionID/prompt`: SSE connection, prompt admission, WlasneAI execution, and session/message events.
- `GET /api/config`, `/api/agent`, `/api/command`, `/api/provider`, `/api/model`, and `/api/model/default`: location-scoped boot catalog responses.

The corresponding API tests assert the required response fields and values. This covers server readiness, project/location discovery, initial catalogs, and a text-only session/prompt flow. File attachments, tool event mapping, provider-driven model streaming, and real Electron sidecar startup remain unimplemented, so the UI integration is still incomplete.

## Sidecar packaging and runtime progress (2026-11-14)

- The Windows workflow builds the original pinned OpenCode desktop and packages `apps/sidecar_cli.py` as its `opencode-cli.exe`, while preserving the existing PySide6 executable as a separate rollback artifact.
- The packaged Python process starts only on loopback, registers `id`, `version`, `url`, `pid`, and a random password in the service file expected by the pinned client, and serves the API with HTTP Basic Auth.
- Windows CI has passed Python tests, both executable builds, direct sidecar registration/readiness, and Electron package verification.
- A later CI launch confirmed that Electron staged `opencode-cli.exe`, started the WlasneAI service, and logged `v2 CLI background service ready`. Its test initially looked in the wrong registry location. Upstream `preferApplicationEnvironment` clears `XDG_STATE_HOME` on Windows, so the pinned-source patch now re-establishes the WlasneAI-only registry both before the early probe and in `BackgroundService.prepare` after environment setup.
- The Windows CI run on `58b0885a50e177a8cafbd1b71d3ae50a4508aa67` confirmed the corrected registry path and authenticated connection log. A UI-driven chat round trip remains an acceptance gate; integration is not complete yet.

## UI-driven sidecar test added (2026-11-14)

- The Windows Electron smoke step now starts a local OpenAI-compatible test server, configures the WlasneAI sidecar to use it, and enables Chromium DevTools Protocol on the packaged development-channel app.
- A Playwright script attaches to the running original renderer, submits a prompt through the real composer, and waits for the matching WlasneAI response in the transcript. The mock provider returns the submitted text, so the test is deterministic and does not use Ollama or external credentials.
- The first run on `21155c1892764d88dbe24124b1c1e86be4a585c8` confirmed the original renderer loaded but it displayed an initialization error before the composer appeared. The Python suite, both executable builds, sidecar protocol check, and Electron-to-sidecar authentication passed on that commit; the UI chat round trip did not.
- The smoke script now captures renderer errors, failed requests, `/api` response status and bodies, and the error detail text field. Use those logs to identify the missing or invalid startup contract, then fix and rerun the test before treating the renderer as integrated.
