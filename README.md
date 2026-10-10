<p align="center"><img src="assets/wordmark.svg" alt="SDD-WorkFlow — linked specifications and human gates" width="560"></p>

# SDD-WorkFlow

**Small contracts. Durable context. Human authority.**

A stack-independent **software development framework** built around Spec-Driven
Development and Harness Engineering: four focused roles, immutable full-spec
approval, scoped verification evidence and a deterministic offline Python helper.
Adopt it into an existing project with the stack and agent runtime you choose.

## Why use it?

- **Explicit authority:** one coordinator, one implementer and human decision gates.
- **Recoverable work:** persistent checkpoints and source-linked context across sessions.
- **Incremental quality:** reuse valid evidence; repeat only checks invalidated by changes.
- **Efficient context:** short handoffs, selective reads and shared contracts.
- **Educational by design:** learn how Harness Engineering turns agent instructions
  into bounded, observable and repeatable development work.

```text
Request → Spec → Human approval → Implementation + evidence
                                      ↓
                        Conditional review → Human closure
```

## Quickstart

Python 3.10+ is sufficient. From the downloaded repository, on a POSIX shell:

```sh
FRAMEWORK="$PWD"
PROJECT="$(mktemp -d)"
python3 "$FRAMEWORK/sdd.py" init --root "$PROJECT"
python3 "$FRAMEWORK/sdd.py" validate --root "$PROJECT" --json
python3 "$FRAMEWORK/sdd.py" status --root "$PROJECT" --json
python3 -m unittest discover -s "$FRAMEWORK/tests" -v
DEMO="$(mktemp -d)"
python3 "$FRAMEWORK/examples/worked-lifecycle/demo.py" --root "$DEMO"
```

Init writes only `.sdd/` context, never application code. Status recommends plan;
it does not transition state or execute tests. The demo executes actual helper
gates and a small local assertion; its human/agent records are explicitly simulated.
Keep the temporary directories for inspection or remove only those you created.
Commands also work outside the repository when FRAMEWORK is its absolute path.

## Learn and adopt

- [Getting started](docs/getting-started.md) — commands, approval and exit codes.
- [Agent entry map](AGENTS.md) — roles and context loaded on demand.
- [Core contracts](core/contracts.md), [spec format](core/spec-format.md),
  [lifecycle](core/lifecycle.md), [verification](core/verification.md).
- [Architecture](docs/architecture.md), [adoption](docs/adoption.md),
  [alternate runtimes](docs/alternate-runtimes.md).
- [Worked lifecycle](examples/worked-lifecycle/README.md) — failure, repair and closure.
- [Harness Engineering](docs/harness-engineering.md), [decisions](docs/decisions.md),
  [original workflow analysis](docs/original-workflow-analysis.md).
- [OpenCode compatibility](docs/opencode.md) and [brand](assets/README.md).

## Four roles, one state writer

Orchestrator coordinates and records global state; planner authors the spec;
implementer changes approved task paths and records evidence; conditional verifier
reviews existing artifacts **without reruns**. Human approves and explicitly closes.
No successful test or helper command automatically marks a feature done.

OpenCode is optional. Its orchestrator can run bounded helper status/validate/approval
without recurring human command chores. Implementation starts denied; a one-time
bounded ASK capability adaptation avoids task-by-task runtime restarts. Each dispatch
still requires an explicit eligible-task assignment ID and exact scopes; future or
completed tasks are not authorized. Disable inherited work agents and inspect
effective configuration before use. Config loads at startup, not hot reload.
Permissions and dispatch certificates are operational guardrails,
not an OS sandbox or proof of human identity. See the isolation limits above.

MIT — Copyright (c) 2026 Darwin Latorre. [License](LICENSE).
