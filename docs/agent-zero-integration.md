# Agent Zero integration plan

## Decision

Use selective integration with our own architecture. Agent Zero is an upstream reference and a source of proven design patterns; this repository remains the main product.

Upstream: https://github.com/agent0ai/agent-zero

## License and copying

The upstream repository currently contains an MIT license. Any source files copied or substantial portions reused must retain the copyright and license notice. The first implementation in this branch adapts the provider-neutral tool-call loop and specialist-agent/provider patterns to our own modules; it does not vendor the entire upstream application or its large dependency stack.

The upstream source tree has more than 4,000 entries and is tightly coupled to its runtime, extensions, helpers, and UI. Copying it wholesale into this project would add a second application, not improve our existing agent. We therefore import and adapt bounded components, with provenance documented here.

## Current baseline findings

- The project has a useful module layout, but most modules are empty placeholders.
- Only Ollama is configured, even though the model configuration already has a provider field.
- The non-Ollama path in BaseAgent bypasses tool calling entirely.
- AgentEngine reports every ordinary conversational task as unsuccessful because it only verifies tasks that mention a file.
- Tool execution is allow-listed and workspace paths are constrained, which should be preserved.
- Python execution in a subprocess is not a security sandbox; do not describe it as one.

## Changes in this integration

- Added a normalized provider-independent chat result and tool-call representation.
- Added an OpenAI Chat Completions adapter for OpenRouter and compatible endpoints.
- Updated the agent to use one tool loop for Ollama and OpenAI-compatible providers.
- Expanded validated environment configuration, including API-key and timeout handling.
- Added mocked provider/configuration tests that do not require a live API key or Ollama server.

## Next work

1. Add specialist-agent delegation with bounded depth, timeouts, and explicit role profiles.
2. Add persistent task memory with provenance and user controls.
3. Add a capability-aware model router and benchmark suite.
4. Add real integration tests against a local Ollama instance and an optional OpenRouter key.
5. Harden process execution using OS-level sandboxing before enabling broader computer-control tools.

## Acceptance criteria

- Tests pass.
- Provider errors and malformed tool calls are surfaced clearly.
- The agent never executes tool names outside its allow-list.
- Secrets are not committed to source control.
- The original master branch remains unchanged until changes are reviewed.
