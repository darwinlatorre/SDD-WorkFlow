<p align="center"><img src="assets/wordmark.svg" alt="sdd-workflow" width="560"></p>

# sdd-workflow

I built this framework as a **learning project to understand and apply Spec-Driven
Development (SDD) and Harness Engineering**. It also offers a practical, stack-independent
way to coordinate development in existing projects using OpenCode or another runtime.

The same installer preinstalls seven independent [skills](docs/skills.md) for task-relevant guidance; it does not install or run their tools.

Four focused roles share durable context: orchestrator coordinates, planner prepares
the spec, one implementer changes approved assigned work, and a conditional verifier
reviews existing evidence without rerunning checks. Human approval and closure stay
explicit. Scoped evidence and compact handoffs make work recoverable across sessions.

```text
Request → Spec → Human approval → Implementation + evidence
                                      ↓
                        Conditional review → Human closure
```

## Quickstart

Already have **Python 3.10+, curl and OpenCode** installed, with your own working
model/provider configuration. This installer does not install those tools.

1. In your existing project's terminal, install the project-local framework:

   ```sh
   curl -fsSL https://raw.githubusercontent.com/darwinlatorre/SDD-WorkFlow/main/install.sh | sh
   ```

2. Start OpenCode in that same directory:

   ```sh
   opencode
   ```

3. Ask the default orchestrator:

   > Plan a feature to export the project's existing items to a CSV file.
   > Prepare requirements, design and tasks; do not implement yet.

4. Read `specs/<feature>/requirements.md`, `design.md` and `tasks.md`. When satisfied,
   explicitly approve that spec version in the conversation before implementation.
   Orchestrator prepares the real project's paths/check procedures and one-time
   bounded permissions. **If config changes, reopen OpenCode to load it**, then continue.

5. To resume later, reopen `opencode` in the same project and ask:

   > Resume the active feature from its checkpoint; reuse evidence that is still valid.

Installation preserves compatible model/provider settings and product instructions,
backs up changed config/instructions, and never overwrites existing workflow state
or specs. Conflicts fail without a force overwrite. The remote command trusts this
repository's public GitHub `main`, not a pinned release. Use the
[local/offline route](docs/getting-started.md) if you prefer a reviewed checkout.

## Learn and adopt

- [Getting started](docs/getting-started.md): installation options and first session.
- [Agent entry map](AGENTS.md), [contracts](core/contracts.md),
  [spec format](core/spec-format.md), [lifecycle](core/lifecycle.md),
  [verification](core/verification.md).
- [Adoption](docs/adoption.md), [OpenCode permissions/limits](docs/opencode.md),
  [architecture](docs/architecture.md), [alternate runtimes](docs/alternate-runtimes.md).
- [Harness Engineering](docs/harness-engineering.md), [decisions](docs/decisions.md),
  [original analysis](docs/original-workflow-analysis.md).
- Secondary: [helper CLI, demo and maintainer tests](docs/getting-started.md#secondary-helper-demo-and-tests),
  [worked lifecycle](examples/worked-lifecycle/README.md).

The stdlib helper is offline and deterministic; installation is a separate bounded
operation, not an updater or autonomous engine. No graph, skill bundle or model is
mandatory. Runtime ASK capabilities are not task authority or an OS sandbox;
assignments remain explicit and config is loaded at startup, not hot reloaded.
See the runtime limits before using untrusted checks. No passing test automatically
closes a feature. Offline inspection is not a claimed model-driven planning session.

First-party code: MIT — Copyright (c) 2026 Darwin Latorre. [License](LICENSE).
Bundled skills retain their [upstream terms and attribution](THIRD_PARTY_NOTICES.md).
