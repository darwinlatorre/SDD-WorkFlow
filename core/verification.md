# Incremental verification

Record distinct automated, observable, integration and static evidence. Run only
the declared procedure outside the helper, with its approved timeout and expected
outcome. Keep concise sanitized result references, never shell/environment dumps.
For each CA, at least one passing evidence record must be bound to the correct
task, procedure, current spec and complete scoped manifest.

Any scoped code/test/config input edit, addition/deletion, procedure definition
or allowlisted current environment revision change invalidates affected checks.
Unknown/absent identity, unbounded scope or unsupported freshness fails closed.
Unrelated out-of-scope edits retain validity with an explicit reason. Directory
membership prevents timestamp-only and existing-files-only false freshness.

A claimed completed task is effective only with fresh evidence for all its CAs
and all selected procedures. Resume recomputes these gates; it never executes tests.
Review binds to current spec and complete evidence/artifact set. Verifier inspects
these results only; missing evidence returns BLOCKED/CHANGES_REQUESTED, not reruns.
Human closure binds to the same current set. No successful check closes a feature.

Revalidate the explicit dispatch certificate at handoff. A revoked/completed
assignment gives no operational write/command scope even if a runtime retains
broader ASK or remembered grants. Retry resets preserve the exact failed attempt
prefix and require source-linked human intervention; tests cover rejection of
erased outcomes and unconfirmed/incorrect/spec-stale resets.
