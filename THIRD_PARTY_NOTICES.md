# Third-party notices

The [framework MIT license](licenses/sdd-workflow-MIT.txt) covers first-party framework code/documents and its SVGs,
**not all bundled skill content**. Each skill retains its original license/frontmatter,
attribution, references and source bytes. Supplemental terms below accompany the
installation without modifying any upstream file.

The installer distributes the framework's exact MIT terms/copyright at the distinct
managed path `licenses/sdd-workflow-MIT.txt`. It never replaces the adopting project's
root `LICENSE`, which may declare unrelated terms. The framework checkout's own
root `LICENSE` remains its official MIT license; the distributed copy is byte-identical.

This release preserves a supplied local snapshot: 279 regular source files,
2,808,106 bytes, no exclusions. Versions are those declared in that snapshot; none
were upgraded. Its fixed path/SHA-256 inventory is
[.opencode/skill-manifest.json](.opencode/skill-manifest.json). Upstream revisions
below are verified licensing/provenance references (checked 2026-10-09), not a claim
that every local byte is identical to the current upstream revision. Where no
version is declared, the inventory identifies the local snapshot exactly.

| Bundled directory | Author / retained version | Terms and verified provenance |
| --- | --- | --- |
| auth0 | Auth0 (`support@auth0.com`); 2.3.0 | Apache-2.0 declared locally and at [auth0/agent-skills v2.3.0](https://github.com/auth0/agent-skills/tree/d48ab4b1b36c9d9574f88e18dc182e9e896fa582/plugins/auth0/skills/auth0); [upstream LICENSE](https://github.com/auth0/agent-skills/blob/d48ab4b1b36c9d9574f88e18dc182e9e896fa582/LICENSE), [supplied text](third_party/licenses/Auth0-Apache-2.0.txt) |
| frontend-design | Anthropic; no version declared | Original [LICENSE.txt](.opencode/skills/frontend-design/LICENSE.txt) retained, Apache-2.0. [Anthropic source/license reference](https://github.com/anthropics/skills/tree/dbd4588f9e1033efb41dad4bef2f7947c8993d44/skills/frontend-design) |
| graphify | Safi Shamsi and Graphify contributors; .graphify_version 0.9.73 | [Graphify v0.9.73](https://github.com/Graphify-Labs/graphify/tree/ef4450d9c28acb2b8cdc22d369c1777b77148eef), formerly safishamsi/graphify (upstream redirects). Apache-2.0 with legacy MIT portions noted by upstream: [Apache text](third_party/licenses/Graphify-Apache-2.0.txt), [MIT text](third_party/licenses/Graphify-MIT.txt), [original NOTICE](third_party/licenses/Graphify-NOTICE.txt) |
| playwright-cli | Microsoft Corporation; no version declared | Apache-2.0 verified in [Microsoft source/license](https://github.com/microsoft/playwright-cli/blob/b85c7a736bb473bf55b584e54a09ffa698d6d871/LICENSE); [full supplied text with Microsoft notice](third_party/licenses/Playwright-Apache-2.0.txt) |
| vercel-composition-patterns | Vercel; 1.0.0 | MIT declared in [original SKILL.md](.opencode/skills/vercel-composition-patterns/SKILL.md) and [upstream](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/composition-patterns/SKILL.md); [supplemental MIT text](third_party/licenses/Vercel-MIT.txt) |
| vercel-react-best-practices | Vercel Engineering; 1.0.0 | MIT declared in [original SKILL.md](.opencode/skills/vercel-react-best-practices/SKILL.md) and [upstream](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/react-best-practices/SKILL.md); same supplemental MIT text |
| vercel-react-native-skills | Vercel; 1.0.0 | MIT declared in [original SKILL.md](.opencode/skills/vercel-react-native-skills/SKILL.md) and [upstream](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/react-native-skills/SKILL.md); same supplemental MIT text |

The three Vercel SKILL.md blob identities match the pinned revision above, whose
[README](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/README.md)
also declares MIT. No standalone license text was provided in those local trees;
the supplemental standard MIT terms retain their declared author attribution,
without inventing a copyright year. Other existing notices were not removed.

Source guidance may discuss design/branding, CLI installs, browser operations or
graph generation. It is reproduced unchanged, not adopted as framework authority
or executed during packaging/installation. Loading guidance does not override the
four roles or human scope. Trademarks remain with their respective owners; upstream
external URLs are attribution references, not claims of network/integration verification.
