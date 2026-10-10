# Minimal immutable spec

Each document has exactly one fenced `json` metadata block. English prose outside
it is authoritative behavior; planner and human keep it consistent with metadata.
All content is hashed; completion never changes approved spec checkboxes.

requirements.md uses headings Context, Requirements (EARS), Acceptance criteria
(Given/When/Then), Traceability and Sources. Metadata example:

```json
{"schema_version":1,"feature":"RF-001","version":1,"status":"ready","requirements":["REQ-01"],"criteria":[{"id":"CA-01","requirements":["REQ-01"]}]}
```

design.md uses Architecture, Changes, Decisions, Impact and Alternatives:

```json
{"schema_version":1,"feature":"RF-001","version":1,"status":"current"}
```

tasks.md uses Tasks and Verification. Each task has one owner, dependencies,
REQ/CA coverage, procedure IDs, scope justification and explicit write paths:

```json
{"schema_version":1,"feature":"RF-001","version":1,"status":"current","tasks":[{"id":"T1","owner":"implementer","depends_on":[],"requirements":["REQ-01"],"cas":["CA-01"],"procedures":["check"],"scope_reason":"All source and check inputs","write_paths":["src/change.py"]}]}
```

REQ/CA IDs are stable positive decimal suffixes (at least two digits), never
renumbered or reused after retirement. Feature RF derives from the numeric ID.
Every REQ has a CA and task; every CA has linked REQs and a task with procedures.
Task coverage includes its CA's requirements. Dependencies exist and are acyclic.
Prose correctness is not inferred by NLP. Structural validation is not semantic review.
