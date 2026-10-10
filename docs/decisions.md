# Decisions

| Decision | Reason / rejected alternative / consequence |
| --- | --- |
| Single stdlib helper | Portable offline validation; no generic workflow engine or package installs |
| Four roles | One implementer rather than stack-specific agents; explicit ownership |
| Full byte-framed approval | Requirements/design/tasks all matter; reject tasks-only hashes and mutable checkboxes |
| JSON fenced metadata | Deterministic IDs/links, not prose parsing; human checks semantic consistency |
| External progress and evidence | Preserve immutable spec; reject completion-only checkboxes |
| Scoped manifests | Include additions/deletions and identities; reject timestamp-only freshness |
| Conditional read-only verifier | Review existing evidence, not redundant test execution |
| Manual transitions | Orchestrator single writer; no automatic advance/done or publication |
| Role-invariant adapter profile | Allow bounded helper opt-in and harmless runtime settings; reject unsafe wildcard overrides |
| Explicit dispatch certificates | Derive scopes only from assigned eligible incomplete tasks, not feature-wide unions |
| One-time ASK capability envelope | Avoid task-by-task config churn; config is startup-loaded and task authority remains operational |
| Human-confirmed retry reset | Bind to retained attempt prefix/diagnostic source; never erase outcomes to regain budget |
| No cross-version evidence mapping in minimal profile | Digest mismatch requires fresh evidence; safe rather than guessed semantic equivalence |

See [architecture](architecture.md) and [original analysis](original-workflow-analysis.md).
