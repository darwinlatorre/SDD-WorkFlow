# Alternate runtimes

The four role [contracts](../core/lifecycle.md) work with humans, another agent
runtime, or a mixture. Translate read/write/execute/delegate permissions explicitly.
Do not add parallel global state writers. Keep planner away from application code,
implementer away from state/spec/closure, verifier away from execution and writes.

If your runtime cannot enforce required boundaries, use external permissions or
human-mediated operations and state the limitation. A prompt alone is not access
control. The helper stays offline and deterministic regardless of model choice.
No provider, graph, skill bundle or model is mandatory. Optional graph retrieval
must be source-confirmed and never replace approval inputs or evidence freshness.
