"""Focused upstream acquisition/preservation tests. No production skill payloads."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
module = importlib.util.spec_from_file_location("installer", PACKAGE / "install.py")
installer = importlib.util.module_from_spec(module)
module.loader.exec_module(installer)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="upstream project with spaces ")
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.requests = []
        self.raw_requests = []

    def put(self, name, text):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def existing_skills(self):
        for name in installer.SKILLS:
            self.put(f".opencode/skills/{name}/SKILL.md", "User custom content; no frontmatter/version audit.\n")

    def snapshot(self):
        return {p.relative_to(self.project).as_posix(): (p.read_bytes(), p.stat().st_mode) if p.is_file()
                else ("directory", p.stat().st_mode) for p in self.project.rglob("*")}

    def download(self, repo, ref, destination):
        self.requests.append((repo, ref))
        with tarfile.open(destination, "w:gz") as archive:
            for row_repo, row_ref, subtree, name, _ in installer.SKILL_SOURCES:
                if (repo, ref) != (row_repo, row_ref):
                    continue
                for suffix, data in (("SKILL.md", f"---\nname: {name}\ndescription: Fixture\n---\nOriginal bytes\r\n".encode()),
                                     ("references/guide.md", b"Upstream reference\n")):
                    info = tarfile.TarInfo("archive/" + subtree + "/" + suffix)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
            for path, data in (("LICENSE", b"Original upstream terms\r\n"), ("irrelevant.py", b"must not install or execute")):
                info = tarfile.TarInfo("archive/" + path)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))

    def raw_download(self, url, destination, limit, label):
        self.raw_requests.append(url)
        destination.write_bytes(b"---\nname: codegraphcontext\ndescription: Fixture\n---\nOriginal bytes\r\n"
                                if url.endswith("/SKILL.md") else b"Original upstream terms\r\n")

    def test_CA17_missing_sources_and_shared_vercel_fetch(self):
        with patch.object(installer, "download_archive", side_effect=self.download), patch.object(installer, "download_bytes", side_effect=self.raw_download):
            installer.install(self.project, PACKAGE)
        self.assertEqual(self.requests, list(dict.fromkeys((row[0], row[1]) for row in installer.SKILL_SOURCES if row[3] != "codegraphcontext")))
        self.assertEqual(len(self.requests), 4)
        self.assertEqual({repo for repo, _ in self.requests}, {"auth0/agent-skills", "anthropics/skills", "microsoft/playwright-cli", "vercel-labs/agent-skills"})
        prefix = "https://raw.githubusercontent.com/CodeGraphContext/CodeGraphContext/1eedea3527a31443b75d29a632c4c477b7b30508/"
        self.assertEqual(self.raw_requests, [prefix + ".cursor/skills/codegraphcontext/SKILL.md", prefix + "LICENSE"])
        codegraph = next(row for row in installer.SKILL_SOURCES if row[3] == "codegraphcontext")
        self.assertEqual(codegraph[:4], ("CodeGraphContext/CodeGraphContext", "1eedea3527a31443b75d29a632c4c477b7b30508", ".cursor/skills/codegraphcontext", "codegraphcontext"))
        self.assertFalse(any("graphify" in repo.lower() for repo, _ in self.requests))
        for _, _, _, name, notices in installer.SKILL_SOURCES:
            root = self.project / ".opencode/skills" / name
            self.assertIn(f"name: {name}".encode(), (root / "SKILL.md").read_bytes())
            self.assertTrue((root / "SKILL.md").read_bytes().endswith(b"Original bytes\r\n"))
            if name != "codegraphcontext":
                self.assertTrue((root / "references/guide.md").is_file())
            if "LICENSE" in notices:
                self.assertEqual((root / "upstream-notices/LICENSE").read_bytes(), b"Original upstream terms\r\n")
            self.assertFalse((root / "irrelevant.py").exists())

    def test_CA12_CA17_existing_custom_skills_no_download_and_repeat(self):
        self.existing_skills()
        self.put(".opencode/skills/graphify/SKILL.md", "Old unrelated guidance retained")
        self.put(".opencode/skill-manifest.json", "Old user manifest retained")
        self.put("third_party/licenses/user.txt", "Old user terms retained")
        self.put("LICENSE", "User license")
        self.put("AGENTS.md", "Product instructions\n" + installer.MAP.replace(b"## SDD-WorkFlow sources", b"## sdd-workflow sources").decode())
        before = self.snapshot()
        with patch.object(installer, "download_archive", side_effect=AssertionError("no network")):
            installer.install(self.project, PACKAGE)
            for name, record in before.items():
                self.assertEqual(self.snapshot()[name], record)
            installed = self.snapshot()
            self.assertEqual(installer.install(self.project, PACKAGE)["result"], "already-installed")
            self.assertEqual(installed, self.snapshot())
        self.assertEqual((self.project / "licenses/sdd-workflow-MIT.txt").read_bytes(), (PACKAGE / "LICENSE").read_bytes())

    def test_CA13_CA17_collisions_no_network_or_writes(self):
        for malformed in ("file", "directory"):
            with self.subTest(malformed=malformed):
                path = self.project / ".opencode/skills/auth0"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("collision") if malformed == "file" else path.mkdir()
                before = self.snapshot()
                with patch.object(installer, "download_archive", side_effect=AssertionError("no fetch before collision check")), self.assertRaises(ValueError):
                    installer.install(self.project, PACKAGE)
                self.assertEqual(before, self.snapshot())
                path.unlink() if path.is_file() else path.rmdir()

    def test_CA17_download_failure_after_staging_leaves_project_unchanged(self):
        self.put("AGENTS.md", "Unchanged instructions")
        before = self.snapshot()
        def failed(repo, ref, destination):
            if self.requests:
                raise installer.Conflict("fixture upstream download failed")
            self.download(repo, ref, destination)
        with patch.object(installer, "download_archive", side_effect=failed), self.assertRaisesRegex(ValueError, "download failed"):
            installer.install(self.project, PACKAGE)
        self.assertEqual(before, self.snapshot())

    def test_CA17_raw_codegraph_failure_staged_and_present_skip(self):
        self.existing_skills()
        missing = self.project / ".opencode/skills/codegraphcontext/SKILL.md"
        missing.unlink()
        missing.parent.rmdir()
        before = self.snapshot()
        def fail_license(url, destination, limit, label):
            if url.endswith("/LICENSE"):
                raise installer.Conflict("fixture raw license download failed")
            self.raw_download(url, destination, limit, label)
        with patch.object(installer, "download_archive", side_effect=AssertionError("no repository archive")), patch.object(installer, "download_bytes", side_effect=fail_license), self.assertRaisesRegex(ValueError, "download failed"):
            installer.install(self.project, PACKAGE)
        self.assertEqual(before, self.snapshot())
        self.put(".opencode/skills/codegraphcontext/SKILL.md", "Custom existing guidance")
        with patch.object(installer, "download_archive", side_effect=AssertionError("no archive")), patch.object(installer, "download_bytes", side_effect=AssertionError("no raw request")):
            installer.install(self.project, PACKAGE)
        self.assertEqual((self.project / ".opencode/skills/codegraphcontext/SKILL.md").read_text(), "Custom existing guidance")

    def test_CA17_unsafe_selected_archive_path_or_link_no_writes(self):
        for kind in ("path", "link"):
            with self.subTest(kind=kind):
                def unsafe(repo, ref, destination):
                    with tarfile.open(destination, "w:gz") as archive:
                        info = tarfile.TarInfo("archive/plugins/auth0/skills/auth0/../../escape" if kind == "path" else "archive/plugins/auth0/skills/auth0/SKILL.md")
                        info.type = tarfile.SYMTYPE if kind == "link" else tarfile.REGTYPE
                        info.linkname = "/outside"
                        archive.addfile(info)
                before = self.snapshot()
                with patch.object(installer, "download_archive", side_effect=unsafe), self.assertRaisesRegex(ValueError, "unsafe"):
                    installer.install(self.project, PACKAGE)
                self.assertEqual(before, self.snapshot())

    def test_CA12_CA14_framework_state_config_preservation_and_rollback(self):
        from test_workflow import demo, sdd
        demo.prepare(self.project)
        self.existing_skills()
        self.put("opencode.json", json.dumps({"model": "openai/user-model", "provider": {"openai": {"options": {"baseURL": "https://example.invalid"}}}}))
        self.put("AGENTS.md", "Product instructions\n")
        before = self.snapshot()
        def fail(name):
            if name == "AGENTS.md":
                raise OSError("fixture handled failure")
        with patch.object(installer, "download_archive", side_effect=AssertionError("no network")), self.assertRaisesRegex(ValueError, "rolled back"):
            installer.install(self.project, PACKAGE, after_write=fail)
        self.assertEqual(before, self.snapshot())
        with patch.object(installer, "download_archive", side_effect=AssertionError("no network")):
            installer.install(self.project, PACKAGE)
        for name, record in before.items():
            if name.startswith((".sdd/", "specs/")):
                self.assertEqual(record, self.snapshot()[name])
        self.assertEqual(json.loads((self.project / "opencode.json").read_text())["model"], "openai/user-model")
        self.assertEqual((self.project / "AGENTS.md.sdd-backup").read_text(), "Product instructions\n")
        self.assertTrue(sdd.evaluate(self.project)["valid"])

    def test_CA04_CA17_native_name_permissions_without_work_authority(self):
        self.existing_skills()
        with patch.object(installer, "download_archive", side_effect=AssertionError("no network")):
            installer.install(self.project, PACKAGE)
        guard = installer.helper_from(PACKAGE)
        cfg = json.loads((self.project / "opencode.json").read_text())
        for role in guard.ROLES:
            permissions = cfg["agent"][role]["permission"]
            for name in installer.SKILLS:
                self.assertEqual(guard.effective(permissions["skill"], name), "allow")
            self.assertEqual(guard.effective(permissions["skill"], "graphify"), "deny")
            self.assertEqual(guard.effective(permissions["skill"], "codegraph"), "deny")
            if role != "orchestrator":
                self.assertEqual(guard.effective(permissions.get("edit", "deny"), ".sdd/state.json"), "deny")
            if role == "verifier":
                self.assertEqual(guard.effective(permissions.get("bash", "deny"), "cgc index ."), "deny")
        self.assertIn("codegraphcontext", installer.SKILLS)


if __name__ == "__main__":
    unittest.main()
