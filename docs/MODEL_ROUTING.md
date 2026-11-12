# Model routing

Własne AI exposes a capability-aware `ModelRouter`. A route declares its actual
capabilities (`chat`, `tool_calling`, `code`, `reasoning`, optionally
`vision`), speed, reasoning quality, cost score and context window.

The router applies hard capability filters first. It never selects a route
that does not explicitly declare the capabilities required by the current
request. It then scores eligible routes using task heuristics and declared
trade-offs. If no route is eligible, it raises an explicit error rather than
silently selecting an unsuitable model.

Current task classification:
- tool schemas require `tool_calling`;
- common programming/debugging terms request `code`;
- architecture, analysis, planning, and long prompts request `reasoning`;
- other prompts require only `chat`.

Routes are injectable in Python and covered by offline tests. The next step is
to expose candidate profiles through validated environment configuration and
connect live local/cloud model candidates. Scores are explicit configuration,
not automatically measured benchmarks.
