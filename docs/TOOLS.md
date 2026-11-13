# Tool system

Tools are registered through `ToolRegistry`. Each `ToolDefinition` contains:

- a unique name and description;
- a JSON object schema for model-visible parameters;
- a Python handler;
- required capabilities;
- an optional explicit user-approval requirement.

The registry is an allow-list: unregistered names cannot execute. It validates
required fields, nested JSON types, enum values, array/string limits, numeric
bounds and disallowed extra fields before calling a handler. It also checks granted capabilities and approval requirements.

The default `ToolExecutor` registers workspace file read/write, Python test
execution and specialist delegation. The Python tool additionally requires
`AI_ALLOW_UNSANDBOXED_PYTHON=1` because subprocess execution is not a security
sandbox. Delegated specialists receive no computer tools and cannot delegate
recursively. Approval-gated tools requested by the model are routed through a separate callback.
The CLI uses a prompt that shows the tool name and arguments and defaults to
rejecting the action; non-interactive callers without an approval callback fail
closed. Destructive computer-control tools have not yet been added.
