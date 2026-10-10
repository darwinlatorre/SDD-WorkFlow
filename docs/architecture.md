# Architecture

The portable core describes contracts and authority. `sdd.py` has small explicit
functions for parsing, path containment, spec framing, dependency cycles, freshness,
effective completion, closure and adapter checks. It uses only Python's standard
library. JSON fenced blocks avoid guessing metadata from prose.

Adopting context lives in `.sdd/`; approved behavior lives in `specs/`. Global state
has one writer. Progress/evidence remain external to immutable approval inputs.
The CLI performs no application scaffolding, command execution or network access.
OpenCode is an optional four-role adapter, not the core's execution engine.

Dispatch certificates and retry resets use the existing reserved extensions,
not another engine/store. Optional status profile output stays read-only. A current
explicit assignment yields exact eligible-task scopes; an optional one-time runtime
ASK envelope keeps startup config stable while orchestrator updates operational
authority. Bounded helper access replaces mandatory human command relay. No
hot-reload, dynamic OS revocation or automatic lifecycle transition is claimed.

Project procedures and non-secret identity descriptors provide stack-specific data.
Local bounded files/directories and explicit current identities are supported
freshness methods. Mutable external services without authoritative revisions are
unknown. Prose correctness, scope completeness and human identity need review.

Atomic replacement is per-file only, not transactional multi-file storage. An
interrupted approval can leave a durable record before its state reference; repeating
the same confirmation repairs the reference without overwriting contradictory data.
Validation fails closed on inconsistent cross-file state. Storage is not tamper-proof.
