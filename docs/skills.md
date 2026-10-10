# Bundled skills

The installer copies exactly these seven independent source trees to
`.opencode/skills/`, including original references, assets, scripts, frontmatter and
version/notices. No original checkout is needed by an installed project.

| Name | Guidance | Prerequisites for approved work (not installed here) |
| --- | --- | --- |
| [auth0](../.opencode/skills/auth0/SKILL.md) | Authentication and Auth0 configuration | Relevant SDK/CLI, authorized tenant access and external credentials |
| [frontend-design](../.opencode/skills/frontend-design/SKILL.md) | Frontend design decisions | The adopting project's frontend stack; visual inspection tools when required |
| [graphify](../.opencode/skills/graphify/SKILL.md) | Source-linked graph retrieval/analysis | Graphify tooling and its task-specific dependencies/access |
| [playwright-cli](../.opencode/skills/playwright-cli/SKILL.md) | Browser checks and artifacts | Existing Playwright CLI/browser and approved target access |
| [vercel-composition-patterns](../.opencode/skills/vercel-composition-patterns/SKILL.md) | React component composition | Applicable React version/project tooling |
| [vercel-react-best-practices](../.opencode/skills/vercel-react-best-practices/SKILL.md) | React/Next.js performance review | Applicable project stack/check procedures |
| [vercel-react-native-skills](../.opencode/skills/vercel-react-native-skills/SKILL.md) | React Native/Expo practices | Relevant project tooling/device capability when explicitly required |

All four framework roles may load **only task-relevant** guidance through OpenCode's
native `skill` tool. Never load everything into context at startup. The seven names
are explicitly allowed; unknown names default to deny, including unrelated user
skills and runtime/global skills not in this bundle. User skills are not deleted.

Human scope, approval/assignment gates and role/tool permissions **take precedence**
over upstream instructions. Reading guidance grants no application edit, shell,
delegation, browser/cloud/graph execution, prerequisite installation or test rerun.
Planner stays spec-only; verifier stays read-only and never executes checks;
orchestrator alone coordinates global state. Upstream setup suggestions/metadata
are preserved as source, not executed as installer hooks. Ask for required access
instead of treating bundled instructions as permission escalation.

The stdlib helper has no dependency on loading any skill. Global `find-skills` and
built-in `customize-opencode` are not physical sources in this bundle. Native runtime
discovery may list its own built-in skill; the framework does not authorize loading it.
For deliberate adaptations see [runtime limits](opencode.md).

Sources/versions, full redistribution terms and the immutable path/hash inventory
are in [third-party notices](../THIRD_PARTY_NOTICES.md) and
[skill manifest](../.opencode/skill-manifest.json). Upstream links/examples are retained
in their original context; external links are not claimed as tested integrations.
