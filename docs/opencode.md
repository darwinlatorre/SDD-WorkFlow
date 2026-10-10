# OpenCode adapter and isolation limits

Official guidance inspected on 2026-10-09:

- [Schema](https://opencode.ai/config.json): Config.default_agent/agent/permission,
  AgentConfig.description/mode/disable/permission and harmless runtime settings.
- [Agents](https://opencode.ai/docs/agents/): plural project agent discovery and
  description/mode frontmatter; disabled inherited work agents.
- [Commands](https://opencode.ai/docs/commands/): plural commands directory, agent field.
- [Permissions](https://opencode.ai/docs/permissions/): edit gates write/edit/patch,
  global-agent merge and last matching wildcard rule wins.
- [CLI](https://opencode.ai/docs/cli/): no-provider agent/config listing and documented
  disable-fetch/update/plugin/download flags.

Official schema/docs are the compatibility reference; no configuration skill is
bundled or required. No provider/model selection is mandatory. Only
orchestrator is primary/default; planner, implementer and verifier are subagents.
Build/plan/general/explore/scout are disabled. Hidden runtime compaction/title/
summary utilities are not framework roles and inherit global deny work permissions.

Helper startup checks role **invariants**, not exact starter dictionary equality:
default deny, allowed bounded tools, canonical protected paths, explicit assigned
eligible-task automatic allowances, verifier no execution/write/delegation,
orchestrator-only global/config coordination and correct wildcard precedence.
Supported harmless config fields (logLevel/username/snapshot/watcher/model choices,
role color/temperature/steps) are allowed. This is a narrow supported profile
checker, not a general official JSON Schema validator. Inspect the installed
runtime's effective config/discovery independently, without provider calls.

Orchestrator may invoke only the documented local `python3 sdd.py` status, validate
and approval patterns, with root fixed to `.`. Approval's human confirmation path
is fixed to .sdd/approval-human.json. Duplicate CLI options are rejected, so wildcard
task/feature arguments cannot replace root/confirmation flags. Other shell commands
remain denied. The helper never executes agents/procedures, transitions state or
manufactures consent. Keep sdd.py protected and run only in the trusted adopting root.

Exact automatic implementer edits come only from the current assignment certificate.
An optional explicit runtime_grants=true profile instead prepares project-bounded
ASK capabilities once, before startup. This avoids task-by-task config churn: each
dispatch still checks a fresh ID, incomplete eligible tasks and their exact scopes.
Completed/blocked/paused grants are operationally revoked by status (empty scopes).
The startup capability is not an assignment and authorizes no future task by itself.

**Configuration is loaded at startup, not hot reloaded.** Editing opencode.json
does not instantly activate/revoke permissions in an existing session. Runtime ASK
grants (including remembered permissions) may outlive a certificate. Direct @
invocations, ambient global/remote/environment config and plugins are outside local
inspection. Use clean config, no untrusted plugins/MCP, inspect resolved permissions
and retain external isolation when strict enforcement is needed. `--pure` is helpful,
not a sandbox. Shell checks can mutate anything their OS process can access.

Thus task certificates/single-writer rules are operational authority boundaries,
not OS isolation against malicious checks/agents. A verifier remains technically
denied shell/write tools even with runtime_grants enabled. Secret-name guards are
conservative but cannot recognize arbitrary credentials embedded in code: keep
secrets out of project context/scopes. Actor strings do not authenticate humans.
No inference-session or model compatibility claim is made from config listings.
