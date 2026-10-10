# Lifecycle and authority

| From | To | Gate / actor |
| --- | --- | --- |
| pending | spec_ready | planner returns current complete spec; orchestrator records |
| spec_ready | in_progress | current full-spec human approval; dependencies done |
| spec_ready / in_progress / done | revision_required | source-linked changed context; orchestrator records retired IDs |
| revision_required | spec_ready | planner revises all three versions |
| any except blocked/done | blocked | preserve active feature, previous status/phase, condition |
| blocked | previous_status | explicit human resolution matching condition source; restore phase |
| in_progress | done | every task and CA fresh PASS, required review, explicit current human closure |

Only orchestrator writes global state, approvals, decisions, checkpoint, history
and review/closure references. Planner writes only specs. Implementer writes only
approved task paths and its feature progress/evidence. Verifier reads existing
artifacts, returns APPROVED / CHANGES_REQUESTED / BLOCKED and never executes checks
or writes global state. Human alone authorizes approval, intervention and closure.

Orchestrator reads durable context, validates before dispatch, delegates planner
before approval and implementer only after approval. Review is a phase, not status.
Single active feature defaults true; blocked retains its slot. Eligible tasks have
effectively completed dependencies. Checkpoint is a hint; fresh evidence is authority.
No handoff repeats completed tasks whose evidence remains current. Source references
point to the spec and failed/stale checks, not a redundant transcript.

One failed correction allows one focal retry with a different hypothesis AND change
reference. An unchanged retry is refused; two consecutive no-progress outcomes
pause for intervention. Missing capabilities/access or unknown scope/environment/risk
also require intervention, never automatic installations or guesses.

Recovery requires a distinct source-linked human retry_reset record bound to the
current spec/task and exact retained attempts prefix. Orchestrator records its
reference; implementer appends new attempts without deleting outcomes. Generic
access resolution alone never rearms an exhausted correction budget.

Before each dispatch orchestrator invokes bounded helper status/validate and binds
an explicit assignment ID to eligible incomplete tasks. Only that certificate's
scopes are authorized. On completion/intervention the effective scope is empty;
orchestrator clears/supersedes the persisted assignment. It never delegates a
feature-wide union of future work. Runtime ASK capabilities may be prepared once
at startup to avoid task-by-task config churn, but are not authorization to perform
unassigned work. Config edits are not hot reloaded; runtime tool grants require
their own runtime revocation if strict technical isolation is necessary.

State history is short, source-linked and transition-checked. Direct done tampering
without gates is rejected. This is not tamper-proof storage: erasing evidence/history
or supplying a fabricated human actor cannot be cryptographically prevented.
