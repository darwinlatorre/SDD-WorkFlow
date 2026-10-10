"""CA-10 / REQ-15 publication checks; no external libraries or agent providers."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

PACKAGE = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_CA10_REQ15_documentation_links_license_and_public_safety(self):
        expected = {"architecture", "getting-started", "adoption", "alternate-runtimes", "harness-engineering",
                    "decisions", "original-workflow-analysis", "opencode", "skills"}
        self.assertEqual({p.stem for p in (PACKAGE / "docs").glob("*.md")}, expected)
        self.assertIn("Copyright (c) 2026 Darwin Latorre", (PACKAGE / "LICENSE").read_text())
        self.assertIn("MIT License", (PACKAGE / "LICENSE").read_text())
        self.assertEqual((PACKAGE / "licenses/sdd-workflow-MIT.txt").read_bytes(), (PACKAGE / "LICENSE").read_bytes())
        for path in PACKAGE.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts or ".git" in path.relative_to(PACKAGE).parts:
                continue
            self.assertNotIn("progress/impl", path.as_posix())
            self.assertNotIn(".sdd", path.relative_to(PACKAGE).parts)
            data = path.read_bytes()
            # Check actual bytes, including binary assets; don't exempt skill trees.
            for marker in (b"BEGIN " + b"PRIVATE KEY", b"BEGIN " + b"RSA PRIVATE KEY"):
                self.assertNotIn(marker, data, path)
            for credential in (rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b", rb"\bAKIA[0-9A-Z]{16}\b", rb"\bsk_live_[A-Za-z0-9]{24,}\b"):
                self.assertIsNone(re.search(credential, data), path)
            try:
                text = data.decode("utf-8")
            except UnicodeError:
                continue  # Already scanned binary bytes, not silently excluded.
            # Construct the prohibited prefixes so the scanner does not match its own source.
            for prohibited in ("/home/" + "darwinlatorre/", "/tmp/" + "opencode/", "BEGIN " + "PRIVATE KEY"):
                self.assertNotIn(prohibited, text, path)
            if path.suffix == ".md" and ".opencode/skills/" not in path.relative_to(PACKAGE).as_posix():
                for link in re.findall(r"\]\(([^)]+)\)", text):
                    if link.startswith(("https://", "#")):
                        continue
                    self.assertTrue((path.parent / link.split("#")[0]).exists(), (path, link))
                for image in re.findall(r'src="([^"]+)"', text):
                    self.assertTrue((path.parent / image).is_file(), (path, image))

    def test_CA10_REQ15_SVG_safe_geometry_and_wordmarks(self):
        files = sorted((PACKAGE / "assets").glob("*.svg"))
        self.assertEqual(len(files), 4)
        for path in files:
            tree = ET.fromstring(path.read_text())
            self.assertEqual(tree.tag, "{http://www.w3.org/2000/svg}svg")
            self.assertTrue(tree.get("viewBox"))
            tags = {node.tag.rsplit("}", 1)[-1] for node in tree.iter()}
            self.assertEqual(tags - {"svg", "title", "desc", "path", "text"}, set())
            self.assertEqual(len(tree.findall("{http://www.w3.org/2000/svg}path")), 2)
            for node in tree.iter():
                self.assertFalse(any("href" in k or k.startswith("on") for k in node.attrib))
            self.assertIn("#292D32", path.read_text())
            if "mono" not in path.stem:
                self.assertIn("#B8734B", path.read_text())
            else:
                self.assertNotIn("#B8734B", path.read_text())
            if "wordmark" in path.stem:
                self.assertIn("sdd-workflow", " ".join(tree.itertext()))
                self.assertNotIn("SDD-WorkFlow", " ".join(tree.itertext()))

    def test_CA10_REQ15_worked_lifecycle_actual_commands_external_space_root(self):
        with tempfile.TemporaryDirectory(prefix="lifecycle project with spaces ") as directory:
            root = Path(directory)
            result = subprocess.run([sys.executable, str(PACKAGE / "examples/worked-lifecycle/demo.py"), "--root", str(root)],
                                    cwd=root.parent, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("PASS: real CLI gates/checks", result.stdout)
            state = json.loads((root / ".sdd/state.json").read_text())
            self.assertEqual(state["features"][0]["status"], "done")
            self.assertIsNone(state["block"])
            self.assertEqual(state["history"][1]["previous_phase"], "implementation")
            self.assertEqual(len(state["history"]), 4)
            self.assertTrue(state["closures"]["1"])
            progress = json.loads((root / ".sdd/progress/1.json").read_text())
            self.assertEqual(len(progress["tasks"]["T1"]["attempts"]), 3)
            self.assertFalse(progress["tasks"]["T1"]["attempts"][0]["progress"])
            self.assertFalse(progress["tasks"]["T1"]["attempts"][1]["progress"])
            self.assertTrue(progress["tasks"]["T1"]["attempts"][2]["progress"])
            self.assertIn("1:T1", state["extensions"]["retry_resets"])

    def test_CA16_REQ22_installed_quickstart_planning_external_root(self):
        # Offline equivalent of the primary install route; no inference is claimed.
        with tempfile.TemporaryDirectory(prefix="quickstart root with spaces ") as directory:
            root = Path(directory)
            result = subprocess.run(["sh", str(PACKAGE / "install.sh"), "--source", str(PACKAGE), "--project", str(root)],
                                    cwd=root.parent, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            for operation in ("validate", "status"):
                result = subprocess.run([sys.executable, str(PACKAGE / "sdd.py"), operation, "--root", str(root), "--json"],
                                        cwd=root.parent, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["next"]["action"], "plan")
            self.assertEqual(json.loads(result.stdout)["authorization"]["write_paths"], [])
            context = json.loads((root / ".sdd/project.json").read_text())
            self.assertEqual(context["procedures"], {})
            paths = [root / "AGENTS.md", *(root / "core").glob("*.md"), *(root / "docs").glob("*.md")]
            for path in paths:
                for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                    if not link.startswith(("https://", "#")):
                        self.assertTrue((path.parent / link.split("#")[0]).exists(), (path, link))

    def test_CA16_REQ22_REQ23_REQ24_openCode_first_learning_identity_and_setup(self):
        readme = (PACKAGE / "README.md").read_text()
        self.assertIn("# sdd-workflow\n", readme)
        folded = re.sub(r"\s+", " ", readme)
        self.assertIn("I built this framework as a **learning project to understand and apply", folded)
        self.assertIn("Harness Engineering", folded)
        quickstart = readme.split("## Quickstart", 1)[1].split("## Learn and adopt", 1)[0]
        self.assertIn("curl -fsSL https://raw.githubusercontent.com/darwinlatorre/SDD-WorkFlow/main/install.sh | sh", quickstart)
        self.assertIn("opencode", quickstart)
        self.assertNotIn("unittest", quickstart)
        self.assertNotIn("demo.py", quickstart)
        for term in ("Python 3.10+", "curl", "OpenCode", "specs/<feature>/requirements.md", "design.md", "tasks.md", "approve", "resume", "reopen"):
            self.assertIn(term, quickstart)
        prompt = (PACKAGE / ".opencode/agents/orchestrator.md").read_text()
        for term in ("empty feature inventory", "pending", "read/glob/grep", "Empty source roots/procedures", "Before spec_ready", "one-time ASK", "reopen OpenCode", "not hot reloaded"):
            self.assertIn(term, prompt)
        self.assertIn("not a claim that an inference session", (PACKAGE / "docs/getting-started.md").read_text())

    def test_CA18_REQ26_functional_presentation_catalog_and_terms(self):
        self.assertFalse((PACKAGE / "assets/README.md").exists())
        readme = (PACKAGE / "README.md").read_text()
        self.assertNotIn("assets/README.md", readme)
        self.assertNotIn("Small contracts. Durable context. Human authority.", readme)
        self.assertIn("seven independent [skills](docs/skills.md)", readme)
        catalog = (PACKAGE / "docs/skills.md").read_text()
        from test_install import installer
        for name in installer.SKILLS:
            self.assertIn(f"../.opencode/skills/{name}/SKILL.md", catalog)
        self.assertEqual(sum(line.startswith("| [") for line in catalog.splitlines()), 7)
        self.assertIn("take precedence", catalog)
        self.assertIn("not all bundled skill content", (PACKAGE / "THIRD_PARTY_NOTICES.md").read_text())
        self.assertIn("Copyright 2026 Safi Shamsi", (PACKAGE / "third_party/licenses/Graphify-NOTICE.txt").read_text())
        self.assertIn("Microsoft Corporation", (PACKAGE / "third_party/licenses/Playwright-Apache-2.0.txt").read_text())
        self.assertIn("Apache License", (PACKAGE / ".opencode/skills/frontend-design/LICENSE.txt").read_text())
        inventory = json.loads((PACKAGE / ".opencode/skill-manifest.json").read_text())
        for name in installer.SKILLS:
            text = (PACKAGE / ".opencode/skills" / name / "SKILL.md").read_text()
            self.assertIn("name: " + name, text)
        # Original Auth0/design advice is data, not first-party presentation to rewrite.
        self.assertIn("Universal Login branding", (PACKAGE / ".opencode/skills/auth0/SKILL.md").read_text())
        self.assertIn("brand", (PACKAGE / ".opencode/skills/frontend-design/SKILL.md").read_text().lower())
        self.assertEqual(len(inventory["files"]), 279)

    def test_CA17_CA18_upstream_relative_reference_context(self):
        # Literal source links, not code fences/example application paths. Compiled
        # Vercel AGENTS links keep the originating rules/ relative context upstream.
        checked, illustrative = 0, []
        for path in (PACKAGE / ".opencode/skills").rglob("*.md"):
            text = re.sub(r"^```[^\n]*\n.*?^```\s*$", "", path.read_text(), flags=re.M | re.S)
            # Inline Go generics, [label](url) templates and generated screenshot
            # examples are code, not source-file hyperlinks. Scan their bytes for
            # secrets above; exclude only Markdown code syntax from link parsing.
            text = re.sub(r"`[^`\n]+`", "", text)
            for link in re.findall(r"\]\(([^)]+)\)", text):
                link = link.split("#")[0]
                if not link or re.match(r"^[a-z]+:", link):
                    continue
                candidate = path.parent / link
                if candidate.exists():
                    checked += 1
                    continue
                if path.name == "AGENTS.md" and path.parent.name.startswith("vercel-") and (path.parent / "rules" / link).exists():
                    checked += 1
                    continue
                illustrative.append((path.relative_to(PACKAGE).as_posix(), link))
        self.assertGreater(checked, 20)
        self.assertEqual(illustrative, [], "review any new upstream-relative exceptions; do not rewrite sources")


if __name__ == "__main__":
    unittest.main()
