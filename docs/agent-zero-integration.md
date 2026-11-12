# Agent Zero integration plan

## Decision

Use a **selective integration with our own architecture**, not a wholesale fork and not a replacement of this repository.

The existing `Shvvit/ai-agent` project remains the main product. Agent Zero is an upstream reference and a source of proven ideas/components. We will inspect its implementation and license before copying or adapting any code.

Upstream: https://github.com/agent0ai/agent-zero

## Why this approach

- Preserve our existing project structure, model configuration, engine, verifier, tools, and tests.
- Avoid inheriting unrelated UI, deployment, dependencies, and design decisions.
- Adapt only components that demonstrably improve our target system.
- Keep the integration reversible and reviewable through small commits.
- Respect the upstream license and retain required notices for any reused code.

## Target capabilities

1. Local and cloud model providers, including Ollama and OpenRouter-compatible APIs.
2. Model router that selects models by task, capability, latency, context, and available VRAM.
3. Planner -> executor -> verifier loop with bounded retries and clear failure reporting.
4. Specialist agents and controlled delegation.
5. Persistent, searchable memory with explicit user control.
6. Tool system for terminal, files, browser, and computer interaction with permission boundaries.
7. CLI first, then desktop and remote web interfaces.
8. Evaluation suite for task success, latency, token use, reliability, and hardware load.

## Integration rules

- Do not replace the existing engine until a measurable comparison shows the replacement is better.
- Do not import the entire Agent Zero repository as a dependency.
- Keep risky computer/terminal actions behind explicit permissions and sandboxing.
- Keep secrets out of source control; use environment variables and local secret storage.
- Add tests for each adapted component.
- Maintain compatibility with the current target machine: RTX 5060 8 GB VRAM and 16 GB system RAM.

## Initial repository observations

The current repository already has the beginnings of separate `agents/`, `core/`, `models/`, `memory/`, `tools/`, `security/`, and `tests/` areas. Several tracked modules are currently empty placeholders, while `agents/base.py`, `agents/planner.py`, `core/engine.py`, `apps/cli/main.py`, and `config/model_config.py` contain implementation. This makes a selective integration safer than replacing the project wholesale.

## Work sequence

### Phase 0 — baseline and upstream audit
- Record current branch, tests, dependencies, and working behavior.
- Inspect Agent Zero architecture, supported providers, tool execution, memory, agent delegation, security, and license.
- Map upstream concepts to our modules; classify each as reuse, adapt, replace, or reject.

### Phase 1 — model and runtime foundation
- Stabilize provider interfaces and Ollama connectivity.
- Add provider health checks, timeouts, retries, and normalized errors.
- Establish baseline performance tests on the target PC.

### Phase 2 — orchestration and tools
- Improve planning/execution/verification.
- Add specialist-agent delegation only where it improves measured results.
- Harden tool permissions and sandbox boundaries.

### Phase 3 — memory and interfaces
- Implement durable memory and retrieval.
- Expand CLI, then add desktop and remote interfaces.

### Phase 4 — evaluation and optimization
- Compare models and agent strategies using repeatable tasks.
- Optimize VRAM/RAM use, latency, and reliability.

## Acceptance criteria

A change is accepted only when:
- tests pass;
- the behavior is demonstrated with a reproducible task;
- resource use is measured on the target hardware where relevant;
- security and failure behavior are documented;
- the change is smaller or more maintainable than the alternative.
