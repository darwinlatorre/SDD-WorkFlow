# Original workflow analysis

Read-only source review: original AGENTS.md, docs/specs.md, docs/architecture.md,
docs/conventions.md, docs/verification.md and CHECKPOINTS.md. No application code,
private fixtures, execution reports, paths or credentials are copied here.

The original workflow separates requirements, design, tasks, human approval,
implementation and conditional review. It preserves blocked phase/state and uses
stable REQ/CA IDs, explicit task owners/dependencies and source-linked reports.
Verification requires real commands, bounded retries, incremental reuse, and a
reviewer who evaluates evidence rather than rerunning checks. These are retained.

Its original application architecture is stack/domain-specific. This framework
extracts project-supplied paths/procedures/capabilities/risk data instead of copying
that application or its frontend/backend split. A single public implementer owns
work across stacks. Graph/skills and model choice are optional adaptations.

The original approval stores versions and a tasks snapshot while allowing execution
checkboxes in tasks and documentary status changes at closure. Here all three spec
files are framed and hashed exactly; approval and completion are separate records.
Current scoped evidence replaces reliance on claimed completion or old logs.
Single writer, human gates and compact recovery remain central. No claim is made
that these structural changes prove semantic correctness or improve benchmark results.
