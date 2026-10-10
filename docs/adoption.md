# Adoption

1. Use the [installer guide](https://github.com/darwinlatorre/SDD-WorkFlow/blob/main/docs/getting-started.md) in an existing project; it initializes
   missing .sdd and preserves valid existing context, instructions and config.
2. Adapt source roots, procedures, capabilities, non-secret current identities and
   risk policy. See the repository's [Python](https://github.com/darwinlatorre/SDD-WorkFlow/blob/main/tests/fixtures/python-layout.json) and
   [Rust](https://github.com/darwinlatorre/SDD-WorkFlow/blob/main/tests/fixtures/rust-layout.json) fixtures. No toolchain is installed.
3. Inventory feature dependencies and stable IDs. Planner authors explicit
   [metadata](../core/spec-format.md); human assesses prose consistency.
4. Orchestrator consumes explicit human approval, records transitions and invokes
   bounded helper status/validate itself. Human need not run every routine command.
5. Before dispatch ask the existing status operation for explicit task authority:

```sh
python3 sdd.py status --root . --json --profile --assigned-task T1
```

Persist only `authorization.assignment` in state.extensions.assignment, then send
its ID and derived paths/procedures/commands/context paths to implementer. The
helper validates dependency eligibility/effective incompletion/current approval;
it never persists the certificate or dispatches a process. Do not copy scopes from
every task in the feature. A completed assignment returns empty revoked scopes;
orchestrator clears or replaces it before further work. If evidence changes make
an old assignment ineligible, remove/supersede it and select fresh eligible work.
Leave implementation_paths/commands empty to derive scopes from the certificate;
nonempty arrays may only request a subset of assigned work.

## One-time OpenCode startup adaptation

The installer supplies sdd.py, core/, merged opencode.json, `.opencode/agents/`,
`.opencode/commands/` and these two runtime/adoption docs. In an installed project,
use the local core and runtime links; repository learning docs remain in the checkout.
Orchestrator owns controlled adapter
coordination (opencode.json only), never application implementation. Project
config may include supported harmless settings such as username, logLevel, watcher,
snapshot or user model choice; role invariants, not starter equality, are checked.
No arbitrary plugins/MCP/global tools are validated as safe by this profile.

Planning is immediately available with no inferred paths/procedures. If the feature
inventory is empty, orchestrator records your requested pending feature and delegates
planner; source paths/procedures/capabilities/risk are obtained from the real project
before spec_ready and implementation. The installer does not guess or grant those
capabilities. Orchestrator can read/glob project sources and coordinate .sdd/config
with its existing bounded tools. Missing information requires a question, not an install.

Shipped orchestrator has only bounded local helper shell access. Implementer starts
with no writes/execution; verifier stays read-only and never runs checks. To support
ongoing work without recurrent config rewrites/restarts, orchestrator may prepare
the ASK capability profile **once before runtime startup**:

```sh
python3 sdd.py status --root . --json --profile --runtime-grants
```

Set project.extensions.runtime_grants=true explicitly and persist the returned
per-role permission recommendation in config, preserving rule order. The ASK
envelope covers bounded source roots and declared procedures, with review/closure
records denied to implementer. It is a capacity to request runtime permission,
not automatic authority to edit any future task. Validate before launching and
inspect resolved runtime config. A required explicit human spec approval/reset/
closure is different from a runtime tool permission prompt.

**OpenCode loads config at startup; it does not hot reload these permission edits.**
Reopen/restart OpenCode after the initial project-specific setup changes config.
Normal task coordination updates certificates/state and does not rewrite config
or restart the runtime task-by-task. Already granted tool permissions may remain
in a session after a certificate is operationally revoked. Prompts/dispatch checks
enforce task ownership operationally, not against a malicious agent or OS process.
If strict dynamic task isolation is required, externally restrict the execution
account/environment and revoke its grants separately; do not claim this adapter
does that. Direct @ invocation and ambient config also need deliberate control.

## Human-confirmed retry recovery

Two consecutive no-progress corrections pause the task. Keep its attempts. Human
authors the distinct retry_reset [record](../core/contracts.md), including current
digest, task, exact prefix length/hash and a diagnostic/decision source. Orchestrator
adds the reference to state.extensions.retry_resets["1:T1"]. New attempts append
after that preserved prefix. Ordinary block resolution does not reset budget;
unconfirmed, stale, wrong-task or altered-prefix records fail. Another exhaustion
requires another human intervention, never deletion of failed outcomes.

Run only project checks outside the helper with bounded timeout and concise sanitized
results. Default scopes include all relevant source/check/config inputs; narrower
complete scopes need approved justification. Never scope/hash secrets. Review
when policy requires it, then wait for distinct explicit human closure. The
[worked lifecycle](https://github.com/darwinlatorre/SDD-WorkFlow/blob/main/examples/worked-lifecycle/README.md) executes adopted helper
coordination and demonstrates unchanged startup config through task changes/closure.
