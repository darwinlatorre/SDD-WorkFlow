# Worked lifecycle: synthetic local notes

Run the actual helper lifecycle from any cwd, with a clean existing root:

```sh
DEMO="$(mktemp -d)"
python3 "$FRAMEWORK/examples/worked-lifecycle/demo.py" --root "$DEMO"
python3 "$FRAMEWORK/sdd.py" status --root "$DEMO" --json
```

FRAMEWORK is the absolute framework directory set in the [quickstart](../../README.md).
The source text/check fixtures are educational artifacts, not an application template.
Python assertions and subprocess CLI operations really execute; human/planner/
implementer/orchestrator/verifier records are explicitly **simulated** by demo.py.
Nothing invokes OpenCode, an agent provider, a cloud service or network command.

The demo copies the helper/core/four-role adapter into the disposable adopting root.
It configures bounded helper + explicitly opted-in ASK capabilities once, then
calls the same local helper commands an orchestrator may invoke. Real status
profiles produce task-specific assignment IDs; simulated orchestrator actions
persist them. No human relays each status or rewrites permissions between tasks.
The config remains byte-identical through completion and explicit human closure.
This is an operational coordination demonstration, not provider execution or proof
that an existing OpenCode session hot reloads config/technically revokes grants.

| Stage | Actual observation / simulated action |
| --- | --- |
| Initialize/adapt | Real init/validate; simulated project/planner metadata |
| Approve | Simulated explicit human confirmation; real approval consumes current digest |
| Assign/retry/recover | Real eligible T1 certificate; two retained failures pause; simulated source-linked human reset rearms budget |
| Implement T1 | Real local declared assertion and scoped evidence; simulated task completion |
| Interrupted recovery | Real status recommends T2, never completed T1 again |
| Block | Simulated access condition/prior phase; real status returns intervention |
| Resolve | Simulated explicit human resolution; real status resumes T2 |
| Stale source | Edit source; real validate exits 1 and status selects affected T1 |
| Repair | Restore exact source bytes; reuse now-fresh T1 evidence, only incomplete T2 needs its check |
| Finish T2 | Real assertion/evidence; low risk status requests human close, not done |
| Spec alteration | Append checkbox; real status refuses stale approval; restore exact bytes |
| High risk | Simulated policy tag change; real status requests verifier |
| Review/close | Simulated APPROVED review + distinct explicit human closure; real gates accept done |
| Revoke | Real status returns empty completed assignment scopes; startup config is unchanged |

The automatic test suite additionally exercises actual low-risk closure without a
review record, stale review/artifact binding, failed CAs, unknown identities,
dependency cycles, missing approvals/closure, permissions and retry intervention.
Spec alterations in a real project require version increments across all three
documents and renewed approval, not byte restoration used for this negative demo.
Inspect .sdd/progress, evidence, approvals and history after the run. Live consumer
state stays ignored and is never published as a real project's approval evidence.
