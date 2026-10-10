"""Affected display/link/onboarding checks; no inventories or upstream audits."""
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
    def test_CA10_CA16_CA18_display_links_learning_and_no_vendor_package(self):
        readme = (PACKAGE / "README.md").read_text()
        self.assertIn("# SDD-WorkFlow\n", readme)
        self.assertIn("learning project to understand and apply", re.sub(r"\s+", " ", readme))
        quickstart = readme.split("## Quickstart", 1)[1].split("## Learn and adopt", 1)[0]
        self.assertIn("curl -fsSL https://raw.githubusercontent.com/darwinlatorre/ssd-workflow/main/install.sh | sh", quickstart)
        for term in ("opencode", "specs/<feature>/requirements.md", "design.md", "tasks.md", "approve", "resume", "reopen"):
            self.assertIn(term, quickstart)
        self.assertNotIn("unittest", quickstart)
        self.assertNotIn("assets/README.md", readme)
        self.assertFalse((PACKAGE / ".opencode/skill-manifest.json").exists())
        self.assertFalse(any((PACKAGE / ".opencode/skills").rglob("SKILL.md")))
        self.assertFalse(any((PACKAGE / "third_party").rglob("*.txt")))
        self.assertEqual((PACKAGE / "licenses/sdd-workflow-MIT.txt").read_bytes(), (PACKAGE / "LICENSE").read_bytes())
        for path in [PACKAGE / "README.md", PACKAGE / "AGENTS.md", PACKAGE / "THIRD_PARTY_NOTICES.md", *(PACKAGE / "docs").glob("*.md")]:
            text = path.read_text()
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if link.startswith(("https://", "#")):
                    if "darwinlatorre/" in link:
                        self.assertIn("darwinlatorre/ssd-workflow", link)
                    continue
                self.assertTrue((path.parent / link.split("#")[0]).exists(), (path, link))
        guide = (PACKAGE / "docs/skills.md").read_text()
        self.assertIn("CodeGraphContext/CodeGraphContext", guide)
        self.assertIn("codegraphcontext", guide)
        self.assertIn("network for missing skills", guide)
        self.assertIn("no cgc execution", guide)
        bootstrap = (PACKAGE / "install.sh").read_text()
        self.assertIn("https://codeload.github.com/darwinlatorre/ssd-workflow/tar.gz/refs/heads/main", bootstrap)
        self.assertIn("ssd-workflow-main/install.py", bootstrap)

    def test_CA10_REQ15_SVG_safe_geometry_and_wordmarks(self):
        files = sorted((PACKAGE / "assets").glob("*.svg"))
        self.assertEqual(len(files), 4)
        for path in files:
            root = ET.fromstring(path.read_text())
            self.assertTrue(root.get("viewBox"))
            self.assertEqual({node.tag.rsplit("}", 1)[-1] for node in root.iter()} - {"svg", "path", "text", "title", "desc"}, set())
            self.assertFalse(any("href" in key or key.startswith("on") for node in root.iter() for key in node.attrib))
            if "wordmark" in path.stem:
                self.assertIn("SDD-WorkFlow", " ".join(root.itertext()))

    def test_CA11_CA16_local_framework_bootstrap_with_present_skills(self):
        from test_install import installer
        with tempfile.TemporaryDirectory(prefix="onboarding root with spaces ") as directory:
            project = Path(directory)
            for name in installer.SKILLS:
                path = project / ".opencode/skills" / name / "SKILL.md"
                path.parent.mkdir(parents=True)
                path.write_text("Existing customized user guidance\n")
            result = subprocess.run(["sh", str(PACKAGE / "install.sh"), "--source", str(PACKAGE), "--project", str(project)], cwd=project.parent,
                capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            status = subprocess.run([sys.executable, str(project / "sdd.py"), "status", "--root", str(project), "--json"], cwd=project.parent,
                capture_output=True, text=True, timeout=10)
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertEqual(json.loads(status.stdout)["next"]["action"], "plan")
            self.assertIn("## SDD-WorkFlow sources", (project / "AGENTS.md").read_text())
            for path in [project / "AGENTS.md", project / "THIRD_PARTY_NOTICES.md", *(project / "docs").glob("*.md")]:
                for link in re.findall(r"\]\(([^)]+)\)", path.read_text()):
                    if not link.startswith(("https://", "#")):
                        self.assertTrue((path.parent / link.split("#")[0]).exists(), (path, link))

    def test_CA10_REQ15_worked_lifecycle_actual_commands_external_space_root(self):
        # Existing educational example retained; not part of the v5 refresh run.
        with tempfile.TemporaryDirectory(prefix="lifecycle project with spaces ") as directory:
            result = subprocess.run([sys.executable, str(PACKAGE / "examples/worked-lifecycle/demo.py"), "--root", directory],
                cwd=Path(directory).parent, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
