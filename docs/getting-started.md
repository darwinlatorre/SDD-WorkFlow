# Getting started

Use the [README quickstart](../README.md); no dependencies beyond Python 3.10+.
`--root` always refers to an existing adopting directory, even from another cwd.
All four commands print deterministic JSON (pretty by default, compact with --json).
Exit 0 is success; 1 invalid contract/gate; 2 usage or I/O failure. Status can report
intervention as a valid next action; validate returns 1 for recorded stale evidence.

| Operation | Behavior |
| --- | --- |
| init --root PATH | minimal context only; idempotent and non-overwriting |
| validate --root PATH | read-only structure, gates, freshness, optional adapter profile |
| status --root PATH | read-only eligible next action with sources/reasons |
| approval --root PATH --feature ID --confirmation-ref PATH | record existing human confirmation; sole orchestrator operation |

Optional read-operation `--profile` emits a permission recommendation without
changing state/config. `status --assigned-task T1` (repeatable) binds explicit
eligible incomplete task IDs to current approval; `--profile --runtime-grants`
requests a startup ASK capability recommendation, not an implementation grant.
`--profile --no-helper-access` is an opt-out profile. Duplicate options are refused
(except repeatable assigned-task) so bounded helper patterns cannot replace --root.
Only the existing four operations exist; no runner/advance/dispatch command is added.

## Approval, without inventing consent

Planner prepares the three [spec documents](../core/spec-format.md). Orchestrator
sets spec_ready. `status` exposes the full digest. Human authors a confirmation
JSON from the [contract](../core/contracts.md) with that digest, current feature
and version, purpose approval, explicit text and ISO date. Store it at a root-relative
path such as `.sdd/approval-human.json`. Then, from the adopting root:

```sh
python3 "$FRAMEWORK/sdd.py" approval --root "$PWD" --feature 1 --confirmation-ref .sdd/approval-human.json
```

This command consumes an existing artifact; without it the command deliberately
fails. An actor string does not authenticate a human: retain external authority.
The [demo](../examples/worked-lifecycle/README.md) supplies an explicitly simulated
confirmation for educational reproduction, not production consent.

Orchestrator then records in_progress, active feature, checkpoint and source-linked
history. Helper never advances automatically. Implementer records separate progress
and scoped evidence; approved specs stay byte-identical. After review when required,
human supplies closure; orchestrator records closure references and done only when
validation accepts current gates. All read operations leave files unchanged.

The shipped orchestrator can invoke `python3 sdd.py status --root . --json`,
`python3 sdd.py validate --root . --json` and the documented bounded approval pattern
from the adopting root. Routine helper output does not need a human intermediary.
Approval still consumes an existing explicit human record. It cannot synthesize
approval, close a feature or execute procedures.
