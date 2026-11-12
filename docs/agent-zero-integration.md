# Agent Zero integration plan

## Decision

Use selective integration with our own architecture. Agent Zero is an upstream reference and a source of proven design patterns; this repository remains the main product.

Upstream: https://github.com/agent0ai/agent-zero

## License and provenance

The upstream repository currently uses the MIT License. The original license text is retained at `third_party/agent-zero/LICENSE`. Any upstream source files copied or substantial portions reused must retain the copyright and license notice.

The upstream source tree contains more than 4,000 entries and is tightly coupled to its runtime, extensions, helpers, and UI. Copying the whole application into this project would create a second application and introduce a very large dependency stack. This branch adapts bounded patterns instead of blindly vendoring the full runtime.

## Baseline findings

- Most modules in this repository are empty placeholders.
- Only Ollama was configured, despite a provider field in model settings.
- The non-Ollama path in BaseAgent bypassed tool calling entirely.
- AgentEngine marked ordinary conversational tasks as unsuccessful because it only verified tasks mentioning a file.
- File tools are allow-listed and workspace paths are constrained; preserve this.
- Python subprocess execution is not an OS security sandbox.

## Implemented in this branch

- Added provider-neutral `ChatResult` and `ToolCall` types.
- Added an OpenAI Chat Completions adapter for OpenRouter and compatible endpoints.
- Unified the tool loop for Ollama and OpenAI-compatible providers.
- Added environment validation for provider, URL, API key, temperature, and timeout.
- Added mocked tests for provider parsing, invalid tool-call payloads, and configuration.
- Fixed task status semantics: a completed conversational answer is no longer incorrectly labelled as a failed task; independent verification is exposed separately.
- Added upstream MIT license notice.
- Added GitHub Actions CI to install the project and run pytest on this integration branch.
- Added tool-call budget handling that returns a result for every requested call and prevents unbounded tool loops.

## Remaining roadmap

1. Add specialist-agent delegation with bounded depth, timeouts, and explicit role profiles.
2. Add persistent task memory with provenance and user controls.
3. Add a capability-aware model router and benchmark suite.
4. Add live integration tests against Ollama and optional OpenRouter credentials.
5. Harden process execution using OS-level sandboxing before enabling broad computer-control tools.

## Acceptance criteria

- CI tests pass.
- Provider errors and malformed tool calls are surfaced clearly.
- The agent never executes tool names outside its allow-list.
- Secrets are not committed to source control.
- The original master branch remains unchanged until reviewed.
