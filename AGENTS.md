# Agent entry map

Use this map to find the relevant contracts; do not load every document at startup.

## Roles

- **orchestrator**: default coordinator and sole global-state writer.
- **planner**: authors the versioned spec.
- **implementer**: implements assigned approved work and produces evidence.
- **verifier**: conditionally reviews existing artifacts without rerunning checks.

Executable OpenCode definitions live in `.opencode/agents/`. Portable authority and
handoff contracts live in `core/`; avoid duplicating them in project instructions.

## Context on demand

| Need | Source |
| --- | --- |
| Framework overview and runnable demo | `README.md` |
| Current project and checkpoint | `.sdd/project.json`, `.sdd/state.json`, when initialized |
| Roles, persistent records and ownership | `core/contracts.md` |
| Spec authoring and traceability | `core/spec-format.md` |
| Approval, recovery, review and closure | `core/lifecycle.md` |
| Incremental evidence and reuse | `core/verification.md` |
| Adopt into an existing project | `docs/adoption.md` |
| Runtime permissions and startup adaptation | `docs/opencode.md` |
| Task-relevant bundled guidance and upstream terms | `docs/skills.md`, `THIRD_PARTY_NOTICES.md` |

Recover the active checkpoint first. Read the assigned spec and current evidence,
then follow source references only as needed. Keep approved specs immutable and
store completion separately. Human approval and closure are explicit lifecycle
gates; passing checks alone does not advance global state.
