# OpenCode UI integration plan

Status (2026-11-14): implementation in progress. The pinned OpenCode desktop is built in Windows CI and now bundles the WlasneAI Python sidecar. Direct sidecar startup and readiness are tested. Electron startup has not passed yet; see `OPENCODE_UPSTREAM_AUDIT.md` for the current failure and remaining acceptance work. PySide6 remains the rollback app.

## Goal

Replace the current PySide6 desktop window with the **original OpenCode desktop experience**, adapted to WlasneAI. This is an upstream-code integration, not a visual imitation.

Upstream:
- Repository: https://github.com/anomalyco/opencode
- License: MIT. Preserve upstream LICENSE, copyright notices, and attribution for every imported/modified upstream file.
- Pin used for initial evaluation: `f6e0c2d0833ffe772035f221fed923e1cd5fb408` (2026-11-13).

## Architecture decision

The existing desktop is a Python/PySide6 application. OpenCode's actual desktop UI is a SolidJS application in `packages/app`, hosted by an Electron shell in `packages/desktop`. The app depends on other workspace packages and the OpenCode client/schema contracts; copying a single folder or screenshot-level recreation will not work.

Target architecture:
1. Keep WlasneAI's Python agent, memory, task manager, tools, and model adapters as the project-specific runtime.
2. Adopt the upstream OpenCode desktop shell and renderer, with upstream shared UI packages and their workspace dependencies.
3. Add a compatibility/bridge layer between the OpenCode UI client contract and WlasneAI's Python runtime. The bridge must cover session lifecycle, streaming events, messages, tool status/results, cancellation, model/provider selection, and permissions/questions before the UI can be considered integrated.
4. Configure the desktop shell to start/stop the WlasneAI Python service as a managed sidecar and connect only to its loopback API.
5. Package the Electron app and Python runtime together for Windows. Do not keep the old PyInstaller/PySide6 EXE as the final shell.
6. Keep Ollama and OpenRouter support, and expose WlasneAI-specific agents/tools/settings in the adapted UI.

## Integration phases

### Phase 1 — upstream compatibility audit
- Pin and inspect upstream desktop/app/ui/session-ui/client/schema packages and their workspace scripts.
- Record required licenses and third-party notices.
- Identify the exact API contract used by the renderer at the pinned revision.
- Decide which upstream screens/settings can be used unchanged and which need WlasneAI-specific adapters.

### Phase 2 — desktop foundation
- Bring in the upstream desktop workspace without importing the OpenCode agent engine as a second competing agent.
- Add WlasneAI branding, app identity, icons, update channel, and startup/shutdown of the Python sidecar.
- Keep the existing Python CLI/headless runtime usable.

### Phase 3 — Python bridge
- Replace the currently empty `api/app.py`, `api/routes.py`, and `api/schemas.py` with a tested compatibility API.
- Implement streaming and lifecycle semantics expected by the pinned UI.
- Map UI actions to existing WlasneAI sessions, task manager, memory, models, and tools.
- Add contract tests against the upstream OpenAPI/schema types.

### Phase 4 — build and acceptance
- Build on Windows CI using pinned Bun/Node dependencies and Python 3.12.
- Package the Electron renderer and Python sidecar into one Windows installer/EXE distribution.
- Test first launch, restart, Ollama unavailable/available, OpenRouter, session persistence, streaming, tool execution, permission prompts, and clean shutdown on Windows.
- Publish only after the packaged app passes smoke tests.

## Non-goals / safeguards

- Do not replace WlasneAI's agent logic with OpenCode's engine by accident.
- Do not claim full UI integration merely because the upstream frontend compiles.
- Do not remove the current working Windows build until the replacement passes acceptance tests.
- Do not silently send prompts, files, or telemetry to external services.
- Keep upstream MIT attribution and notices intact.
