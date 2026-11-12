# Tool system

Tools are registered through `ToolRegistry`. Each `ToolDefinition` contains:

- a unique name and description;
- a JSON object schema for model-visible parameters;
- a Python handler;
- required capabilities;
- an optional explicit user-approval requirement.

The registry is an allow-list: unregistered names cannot execute. It validates
required fields, basic JSON types and disallowed extra fields before calling a
handler. It also checks granted capabilities and approval requirements.

The default `ToolExecutor` registers workspace file read/write, Python test
execution and specialist delegation. The Python tool additionally requires
`AI_ALLOW_UNSANDBOXED_PYTHON=1` because subprocess execution is not a security
sandbox. Delegated specialists receive no computer tools and cannot delegate
recursively. The registry supports approval-gated tools, but destructive
computer-control tools have not yet been added.
