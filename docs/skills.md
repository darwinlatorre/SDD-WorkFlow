# Upstream skills

Missing guidance comes directly from the official repositories below, not from
copies shipped in this framework. `install.py` contains the same compact source
table. Refs are fixed commits; three Vercel selections share one archive download.

| Native name | Repository / ref | Selected subtree |
| --- | --- | --- |
| auth0 | [auth0/agent-skills](https://github.com/auth0/agent-skills/tree/d48ab4b1b36c9d9574f88e18dc182e9e896fa582) | plugins/auth0/skills/auth0 |
| frontend-design | [anthropics/skills](https://github.com/anthropics/skills/tree/dbd4588f9e1033efb41dad4bef2f7947c8993d44) | skills/frontend-design |
| codegraphcontext | [CodeGraphContext/CodeGraphContext](https://github.com/CodeGraphContext/CodeGraphContext/tree/1eedea3527a31443b75d29a632c4c477b7b30508) | .cursor/skills/codegraphcontext |
| playwright-cli | [microsoft/playwright-cli](https://github.com/microsoft/playwright-cli/tree/b85c7a736bb473bf55b584e54a09ffa698d6d871) | skills/playwright-cli |
| vercel-composition-patterns | [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills/tree/063bee94c3f4df8453406c830b0a7df0f2860278) | skills/composition-patterns |
| vercel-react-best-practices | same Vercel repo/ref | skills/react-best-practices |
| vercel-react-native-skills | same Vercel repo/ref | skills/react-native-skills |

If `.opencode/skills/<name>/SKILL.md` already exists as a regular file in a safe
directory, installation skips that skill without network or content/version audits.
Customizations, unrelated skills, old Graphify directories and previous consumer
manifests/terms are not deleted. A malformed destination is a named conflict, not
an update/overwrite request. All missing downloads finish in temporary staging
before project writes; network/path/SKILL.md failures leave the project unchanged.
Original bytes/frontmatter and available upstream notices are kept. No file hashes,
reference crawls or license/load audits are installation gates.

All four roles may load only task-relevant guidance through `skill`, never all at
startup. Named permissions use these actual native names; unknown names (including
Graphify) default to deny. Guidance does not grant shell/edit/delegation or override
human scope/approval/assignment limits. Verifier stays read-only and never reruns checks.

No skill executables or prerequisites are installed/run here. Auth0 work requires
authorized tooling/access; frontend/React/mobile work needs the project's existing
stack; browser work needs approved Playwright/browser capability. Codegraphcontext
is guidance only: no cgc execution, MCP registration or database setup is performed.
Missing access should be requested, not inferred from skill setup suggestions.

The helper stays offline/stdlib; **local framework installation can still require
network for missing skills**. Reinstall with all expected SKILL.md directories
present requires no skill downloads. See [runtime limits](opencode.md) and
[upstream notices](../THIRD_PARTY_NOTICES.md).
