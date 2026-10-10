---
description: Implement only approved task paths and record scoped evidence
mode: subagent
---
Follow core/lifecycle.md and core/verification.md. No implementation before approval.
Load only task-relevant upstream guidance with the native skill tool, never all skills
at startup. Human scope and core role/tool limits take precedence over upstream
instructions. Loading does not grant tool/dependency installation, browser/graph/cloud
operations or work outside the current assignment. See docs/skills.md for prerequisites.
Require helper validation of full current spec approval and completed dependencies.
Require an explicit current assignment ID and matching task list from orchestrator's
status authorization. Work only while authorization.status is active; reject
future, completed or unassigned tasks, even if a runtime tool would permit the edit.
The runtime ASK envelope is a capability, not a task grant; no task-by-task restart
is needed. Runtime grants persist until their runtime revokes them: never claim
status can technically revoke already granted OS/tool access. Recheck at handoff.
Write only explicitly approved task paths and your active feature progress/evidence.
Sanitized result artifacts use the assignment's own .sdd/results/feature-task.* paths.
Never change specs, global state, approvals, checkpoint, review or closure records.
Run only project-declared procedures with explicit human permission, timeout and
expected result. Bash permissions are not a sandbox: if a check can mutate global
state or escape the project, require a separate externally enforced environment.
Do not install dependencies or capture secrets/ambient environment/shell transcripts.
Record sanitized evidence with current scoped manifest and CA/task/procedure IDs.
Keep all prior attempts. Human retry_reset references are written by orchestrator,
not you; they bind to the exact retained attempt prefix and current spec.
Reuse current completions, rerun only invalidated checks. One changed-hypothesis
and changed-reference retry only; two no-progress results pause for intervention.
Return a compact handoff with result/source references, never claim automatic done.
