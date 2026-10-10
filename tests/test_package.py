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
                    "decisions", "original-workflow-analysis", "opencode"}
        self.assertEqual({p.stem for p in (PACKAGE / "docs").glob("*.md")}, expected)
        self.assertIn("Copyright (c) 2026 Darwin Latorre", (PACKAGE / "LICENSE").read_text())
        self.assertIn("MIT License", (PACKAGE / "LICENSE").read_text())
        for path in PACKAGE.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            self.assertNotIn("progress/impl", path.as_posix())
            self.assertNotIn(".sdd", path.relative_to(PACKAGE).parts)
            if path.suffix not in {".md", ".json", ".py", ".svg"}:
                continue
            text = path.read_text()
            # Construct the prohibited prefixes so the scanner does not match its own source.
            for prohibited in ("/home/" + "darwinlatorre/", "/tmp/" + "opencode/", "BEGIN " + "PRIVATE KEY"):
                self.assertNotIn(prohibited, text, path)
            if path.suffix == ".md":
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
                self.assertIn("SDD-WorkFlow", " ".join(tree.itertext()))

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

    def test_CA10_REQ15_quickstart_init_validate_status_external_root(self):
        # Same published commands, excluding recursive invocation of this test suite.
        with tempfile.TemporaryDirectory(prefix="quickstart root with spaces ") as directory:
            root = Path(directory)
            for operation in ("init", "validate", "status"):
                result = subprocess.run([sys.executable, str(PACKAGE / "sdd.py"), operation, "--root", str(root), "--json"],
                                        cwd=root.parent, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["next"]["action"], "plan")


if __name__ == "__main__":
    unittest.main()
