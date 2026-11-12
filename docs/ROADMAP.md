# Roadmap

## Implemented on the integration branch

- Ollama adapter and OpenAI-compatible provider adapter (including OpenRouter).
- Provider-neutral tool-call protocol with a bounded execution loop.
- Explicit allow-list for file read/write and Python test tools.
- Workspace path checks, Windows path normalization and symlink rejection.
- Specialist delegation (researcher, programmer, reviewer) with no recursive tools.
- Bounded conversation history.
- Capability-aware model router with explicit candidate profiles and offline tests.
- SQLite long-term memory with explicit writes, lexical retrieval, tags, importance, pinning and deletion.
- CLI commands for saving, searching, listing and deleting memories.
- Task planning, result verification, limited repair attempts and a persistent task ledger with validated lifecycle transitions.
- CI on Python 3.12.

## Next milestones

1. Add checkpoint-level resume (current `/retry` restarts an interrupted task from its original request).
2. Add a model health-check and real benchmark harness (latency, tokens/s, memory use, tool-call success).
3. Add local/cloud candidate discovery and validated per-model configuration.
4. Add semantic memory retrieval and user-approved memory summarization.
5. Add browser research with source citations and strict domain/action policies.
6. Add a genuine OS-level execution sandbox before enabling broad computer control.
7. Add multimodal input and a desktop/web UI.
8. Add real integration tests against local Ollama and optional cloud credentials.

## Hardware design constraints

The default configuration must remain usable on the existing RTX 5060 8 GB and
16 GB system RAM. Specialist parallelism defaults to one to avoid VRAM spikes.
Cloud models are optional; local Ollama remains the no-key default.

## Acceptance rules

- Never silently claim a model capability that has not been declared.
- Never persist chat content automatically.
- Never execute arbitrary code under the assumption that a Python subprocess is a sandbox.
- Keep the default branch unchanged until the integration branch is reviewed.
