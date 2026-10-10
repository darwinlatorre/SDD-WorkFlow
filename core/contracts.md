# Local contracts, version 1

All paths are relative to the adopting root. JSON is UTF-8, duplicate keys and
unknown core fields are errors; `extensions` is the only free-form object.
The helper is a consistency guard, not authentication or a sandbox. Never put
secrets in context, procedures, identity descriptors, scopes or evidence.

`sdd.py` is the executable structural reference. `examples/worked-lifecycle/demo.py`
provides complete synthetic records. No application structure is imposed.

| Artifact | Required fields (in addition to schema_version: 1) | Writer |
| --- | --- | --- |
| .sdd/project.json | name, source_roots, capabilities, procedures, environment_ref, risk_policy, one_feature_at_a_time, implementation_paths, implementation_commands | orchestrator/human adaptation |
| .sdd/state.json | project_ref, features, active_feature, phase, checkpoint, block, approvals, reviews, closures, history, retired_ids | orchestrator |
| .sdd/progress/ID.json | feature, tasks, handoff, sources | implementer |
| .sdd/evidence/ID.json | id, feature, digest, task, cas, kind, outcome, procedure, artifacts, manifest, fingerprint | implementer |
| .sdd/approvals/ID-vVERSION.json | feature, version, digest, confirmation_ref, confirmation_hash, actor, date | orchestrator |
| review/closure records referenced from state | feature, digest, evidence_digest; review adds verdict/actor, closure adds confirmation_ref/confirmation_hash | verifier returns review; orchestrator persists both |

Feature fields: id (positive integer), name (safe slug), sdd (boolean), status,
depends_on (feature IDs), spec_dir (`specs/name`), spec_version, risk_tags.
Progress tasks map task ID to status (`pending`, `in_progress`, `completed`),
attempts, evidence (paths). An attempt has hypothesis, change_ref, result,
progress (boolean). Sources and handoffs are compact references, not transcripts.
Checkpoint: next_task (string or null), sources (paths). Block: feature,
previous_status, previous_phase, condition, resolution_ref (path or null).
History entries: feature, from, to, previous_phase, phase, source.
`retired_ids` maps feature ID strings to REQ/CA IDs; orchestrator preserves deleted
IDs before revision. The helper rejects reuse but cannot detect erased history.

Paths must use their canonical spelling (no `./`, redundant separators, traversal
or symlink aliases, even when contained). Root scopes and canonical .sdd targets
are forbidden; task writes also exclude specs, adapter config/directories and helper.
Fingerprint input scopes may include relevant config/spec inputs but never .sdd
or the unbounded root. All checks use resolved targets, not lexical prefixes alone.

Optional state.extensions.assignment is an orchestrator-owned dispatch certificate:
id (deterministic 24-character SHA prefix), feature, digest, tasks and sources.
`status --profile --assigned-task T1` emits it read-only. Every explicit task must
be effectively incomplete and dependency eligible under current approval/risk/access
gates. Paths/procedures/commands derive only from those tasks, never the feature union.
Persist the certificate yourself; the helper never writes it or dispatches an agent.
Completion, block, retry pause or closure yields empty revoked operational scopes;
supersede a mixed/completed/ineligible or stale certificate before more work.
Optional project implementation_paths/commands narrow a current assignment; they
are not authority on their own. Leave them empty for normal certificate-derived work.

Optional project.extensions.runtime_grants=true explicitly enables a one-time
startup ASK envelope over bounded source roots, progress/evidence/result artifacts
and declared procedures. ASK capability is NOT a task grant; dispatch remains exact.
Optional extensions.helper_access=false opts out of bounded helper shell commands.
These options do not override approval, single writer, dependency or closure gates.

Procedure fields: kind (automated/observable/integration/static), argv (string
array), cwd, inputs (file/directory paths), environment_keys, timeout (positive
seconds), expected, scope_reason, capabilities (names). Directory membership is
hashed including empty directories. A complete bounded scope must be justified
in approved tasks by the same `scope_reason`; defaults cover all source roots.
No globs, root-wide/secret scopes, ambient environment capture or procedure execution.
Environment descriptor: schema_version and identities (allowlisted non-secret
name -> current revision/version string). Missing or unsupported identities yield
unknown freshness. Project risk_policy has known_tags and review_required_for.
Unknown risk cannot bypass review. Extensions do not override gates.

Confirmation: schema_version, actor: human, purpose: approval/closure/resolution,
feature, version, digest, text (explicit nonempty instruction), date (ISO date).
These are externally authored attestations, not cryptographic identity proofs.

Retry recovery has a distinct human record: schema_version, actor: human,
purpose: retry_reset, feature, task, current digest, after_attempt (prefix length),
attempts_digest (SHA of canonical retained prefix), source_ref (diagnosis/decision),
explicit text and ISO date. Orchestrator adds its path to
state.extensions.retry_resets["feature:task"] (ordered references). At an exhausted
two-no-progress boundary, a valid record starts a new budget without erasing any
attempt. Prefix/spec/task changes, missing diagnosis, non-human or empty confirmation
are rejected. Ordinary block resolution does not reset retry budget. Keep resets and
prior outcomes; later exhaustion requires another explicit intervention.
Approval hashes the names and exact bytes of requirements.md, design.md, tasks.md
in that order, each preceded by an unsigned 8-byte big-endian length. No normalization.
Contradictory approvals are never overwritten. Revision requires all three versions
to increment and a new human confirmation. Old records stay inspectable.

Evidence manifest is canonical JSON of procedure, identities, scopes and files
(sorted relative path -> SHA-256; directories marked `directory`). Fingerprint is
SHA-256 of that canonical JSON. Evidence-set digest hashes complete evidence payloads
and referenced artifact hashes, so edits invalidate review/closure. Failed evidence
is retained but never satisfies a CA. Digest mismatches fail closed: this minimal
profile does not support cross-version reuse mappings; record new evidence instead.

Initialization creates only .sdd/project.json, state.json, environment.json and
decisions.md. Complete repeated initialization is a no-op; partial initialization
is an error. Mutable JSON writes use atomic replacement. No implicit transition,
shell runner, provider invocation, network, installation or automatic closure.
