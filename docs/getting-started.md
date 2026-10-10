# Getting started

Follow the [README OpenCode-first quickstart](../README.md). Python 3.10+, OpenCode
and a working user-chosen model/provider must already be available; remote use also
needs curl. No runtime, toolchain, provider or dependency is installed.

## Installation options

From the existing project, the primary remote command is:

```sh
curl -fsSL https://raw.githubusercontent.com/darwinlatorre/SDD-WorkFlow/main/install.sh | sh
```

To select a different existing project (including spaces):

```sh
curl -fsSL https://raw.githubusercontent.com/darwinlatorre/SDD-WorkFlow/main/install.sh | sh -s -- --project "/path/to/project"
```

A downloaded/reviewed checkout works completely offline, from any cwd:

```sh
python3 "/path/to/SDD-WorkFlow/install.py" --project "/path/to/project"
sh "/path/to/SDD-WorkFlow/install.sh" --source "/path/to/SDD-WorkFlow" --project "/path/to/project"
```

Default project is cwd. The installer copies only helper/core/roles/command and two
adoption/runtime docs, merges compatible root opencode.json, adds one marked AGENTS
source map and initializes missing .sdd context. It preserves product instructions,
supported model/provider settings and every existing state/spec/evidence file.
The same package also installs the [seven skills](skills.md), references/assets and
[upstream terms](../THIRD_PARTY_NOTICES.md). It does not run their scripts or setup hooks.
Reinstalling the same compatible package is a no-op, not an update mechanism.

Changed original config/instructions have exact `opencode.json.sdd-backup` and
`AGENTS.md.sdd-backup` files. They may contain private user settings: do not publish
them or include their contents in evidence. Review/ignore them in your own project.
JSONC, differing managed files, conflicting permissions/roles, partial context or
unwritable destinations fail before writes. Review named conflicts separately; no
force flag or automatic JSONC conversion exists. Handled write failures roll back
installer changes; unresolved rollback paths require manual recovery. This is not
an OS-crash transaction. Remote source trusts public GitHub main; staging/extraction
is bounded and cleaned, but is not a pinned/authenticated release guarantee.

## First session, approval and resume

Run `opencode` in the installed project. Give the orchestrator a concrete feature
request, for example the CSV export prompt in README. Empty paths/procedures do not
prevent initial planning. Orchestrator inspects the project on demand with read/glob,
records a pending feature and delegates planner. Specs appear under `specs/<feature>/`.
Before spec_ready/implementation it obtains actual bounded paths, check procedures,
capabilities, non-secret identities and risk policy; it does not invent or auto-install
them. Ask for missing data when necessary.

Review all three documents and explicitly approve the current version. Orchestrator
records your source-linked human confirmation, consumes it with the bounded helper,
and coordinates one-time runtime ASK setup. **Reopen OpenCode after config changes**;
it is not hot reloaded. Current task assignment IDs—not broad capabilities—authorize
work. No task-by-task config rewrite or repeated spec approval is needed for unchanged
approved work. When interrupted, reopen the same project and request checkpoint
resumption with valid evidence reuse. Distinct explicit human closure is still required.

These are usage instructions, not a claim that an inference session was run during
offline package verification. See [adoption](adoption.md) and [runtime limits](opencode.md).

## Secondary helper, demo and tests

The installed helper remains four operations: init, validate, status and approval.
Read commands are deterministic JSON, read-only, with optional `--profile` and
status `--assigned-task`; exit 0 success, 1 invalid/gate failure, 2 usage/I/O failure.
Approval consumes an existing explicit human confirmation, never invents consent.
Its fixed orchestrator route uses `.sdd/approval-human.json`; see [contracts](../core/contracts.md).

From a framework checkout (not required for your first OpenCode session):

```sh
FRAMEWORK="$PWD"
python3 -m unittest discover -s "$FRAMEWORK/tests" -v
DEMO="$(mktemp -d)"
python3 "$FRAMEWORK/examples/worked-lifecycle/demo.py" --root "$DEMO"
```

The [worked example](../examples/worked-lifecycle/README.md) executes real helper
gates/local assertions with honestly simulated human/agent records. It is secondary
learning material, not setup work newcomers must complete before planning.
