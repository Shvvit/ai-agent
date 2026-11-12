# Architecture

## Request path

1. `AgentEngine` creates a durable task record, validates the request and retrieves a small number of relevant, explicitly saved memories.
2. `Planner` asks the main `BaseAgent` to produce an actionable plan.
3. `BaseAgent` calls the selected model adapter through the shared chat protocol.
4. The provider-neutral tool loop dispatches only allow-listed tools.
5. Specialist tasks may be delegated to bounded agents with no tools and no recursive delegation.
6. `AgentEngine` checks requested file artifacts and can make a limited repair attempt for Python files.
7. The task ledger records status, plan, answer, errors and attempts; `/retry ID` restarts failed or interrupted tasks from the original request.

## Model providers and routing

- `OllamaModel` provides local inference.
- `OpenAICompatibleModel` supports OpenRouter and compatible Chat Completions endpoints.
- `ModelRouter` filters candidates by declared capabilities before scoring speed, reasoning quality, cost and context window.
- Candidate scores are configuration hints, not benchmark results.

## Memory

- Short conversation history is bounded in RAM.
- Long-term notes are stored in SQLite only after an explicit save request.
- Retrieved notes are passed as untrusted context data, never as higher-priority instructions.
- Users can list, search and delete notes from the CLI.

## Safety boundaries

- File tools are confined to the configured workspace and reject traversal/symlink paths.
- The tool executor uses a strict name allow-list.
- Delegated agents do not receive computer tools.
- Python subprocess execution is not a security sandbox; broad computer access remains disabled until OS-level isolation is implemented.
