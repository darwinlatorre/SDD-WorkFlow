"""CA-11–15 / REQ-17–21: bounded installer/entrypoint preservation and failures."""
import importlib.util
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import stat
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
        self.tmp = tempfile.TemporaryDirectory(prefix="sdd install roots with spaces ")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.source = self.base / "source checkout"
        self.project = self.base / "existing project"
        self.source.mkdir()
        self.project.mkdir()
        for name in (*installer.MANAGED, "opencode.json", "install.py", "install.sh"):
            self.put(self.source, name, (PACKAGE / name).read_bytes())
        shutil.copytree(PACKAGE / ".opencode/skills", self.source / ".opencode/skills", copy_function=shutil.copy2)
        inventory = json.loads((self.source / ".opencode/skill-manifest.json").read_text())
        # T9 can verify its composition before T10 publishes real catalog/notices.
        for name in installer.SUPPLEMENTS:
            path = PACKAGE / name
            self.put(self.source, name, path.read_bytes() if path.is_file() else b"Synthetic T9 supplement fixture; not public documentation.\n")
        inventory["supplements"] = {name: hashlib.sha256((self.source / name).read_bytes()).hexdigest() for name in installer.SUPPLEMENTS}
        self.put(self.source, ".opencode/skill-manifest.json", json.dumps(inventory, sort_keys=True, indent=2) + "\n")

    def put(self, root, name, data):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode() if isinstance(data, str) else data)

    def snapshot(self):
        return {p.relative_to(self.project).as_posix(): ("link", os.readlink(p)) if p.is_symlink()
                else ("file", p.read_bytes(), stat.S_IMODE(p.stat().st_mode)) if p.is_file()
                else ("dir", stat.S_IMODE(p.stat().st_mode)) for p in self.project.rglob("*")}

    def local(self, default=False):
        return subprocess.run([sys.executable, str(self.source / "install.py"), *([] if default else ["--project", str(self.project)])],
                              cwd=self.project if default else self.base, capture_output=True, text=True, timeout=20)

    def install(self, **kwargs):
        return installer.install(self.project, self.source, **kwargs)

    def refused(self, reason):
        before = self.snapshot()
        with self.assertRaisesRegex((ValueError, OSError), reason):
            self.install()
        self.assertEqual(before, self.snapshot())

    def seed_user(self):
        config = {"default_agent": "plan", "model": "openai/user-model", "small_model": "openai/user-small",
                  "provider": {"openai": {"options": {"baseURL": "https://example.invalid/v1", "apiKey": "synthetic-only"}}},
                  "username": "Project owner", "snapshot": False, "watcher": {"ignore": ["build/*"]},
                  "agent": {"planner": {"model": "openai/planner", "temperature": 0.1, "color": "info"}}}
        original = json.dumps(config, indent=4).encode()
        self.put(self.project, "opencode.json", original)
        self.put(self.project, "AGENTS.md", "# Product instructions\nKeep my domain rules unchanged.\n")
        self.put(self.project, "src/user.txt", "unrelated user content")
        return original

    def test_CA11_REQ17_clean_default_explicit_spaces_outside_cwd(self):
        result = self.local()
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in (*installer.MANAGED, *installer.skill_files(self.source, installer.helper_from(self.source))):
            self.assertEqual((self.project / name).read_bytes(), (self.source / name).read_bytes())
        context = json.loads((self.project / ".sdd/project.json").read_text())
        self.assertEqual(context["name"], self.project.name)
        self.assertEqual(context["source_roots"], [])
        self.assertEqual(context["procedures"], {})
        helper = subprocess.run([sys.executable, str(self.project / "sdd.py"), "status", "--root", str(self.project), "--json"], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(helper.returncode, 0, helper.stderr + helper.stdout)
        self.assertEqual(json.loads(helper.stdout)["next"]["action"], "plan")
        self.assertFalse((self.project / "install.py").exists())
        self.assertFalse((self.project / "tests").exists())
        before = self.snapshot()
        result = self.local(default=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "already-installed")
        self.assertEqual(before, self.snapshot())

    def test_CA12_REQ18_preserve_provider_model_instructions_backups_repeat(self):
        original = self.seed_user()
        agents = (self.project / "AGENTS.md").read_bytes()
        result = self.local()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("synthetic-only", result.stdout + result.stderr)
        merged = json.loads((self.project / "opencode.json").read_text())
        for name, value in json.loads(original).items():
            if name not in {"agent", "default_agent"}:
                self.assertEqual(merged[name], value)
        self.assertEqual(merged["agent"]["planner"]["model"], "openai/planner")
        self.assertEqual(merged["default_agent"], "orchestrator")
        self.assertEqual((self.project / "opencode.json.sdd-backup").read_bytes(), original)
        self.assertEqual((self.project / "AGENTS.md.sdd-backup").read_bytes(), agents)
        self.assertTrue((self.project / "AGENTS.md").read_bytes().startswith(agents))
        self.assertEqual((self.project / "AGENTS.md").read_text().count(installer.START), 1)
        before = self.snapshot()
        self.assertEqual(self.install()["result"], "already-installed")
        self.assertEqual(before, self.snapshot())

    def test_CA12_CA18_framework_mit_copy_preserves_project_license_and_conflicts(self):
        name = "licenses/sdd-workflow-MIT.txt"
        project_license = b"Existing product license: unrelated proprietary terms.\n"
        self.put(self.project, "LICENSE", project_license)
        (self.project / "LICENSE").chmod(0o444)
        expected = (PACKAGE / "LICENSE").read_bytes()
        self.assertEqual((PACKAGE / name).read_bytes(), expected)
        result = self.local()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.project / "LICENSE").read_bytes(), project_license)
        self.assertEqual(stat.S_IMODE((self.project / "LICENSE").stat().st_mode), 0o444)
        self.assertEqual((self.project / name).read_bytes(), expected)
        self.assertIn("[framework MIT license](licenses/sdd-workflow-MIT.txt)", (self.project / "THIRD_PARTY_NOTICES.md").read_text())
        self.assertTrue((self.project / name).is_file())  # Installed notices link resolves.
        inventory = json.loads((self.project / ".opencode/skill-manifest.json").read_text())
        self.assertEqual(inventory["supplements"][name], hashlib.sha256(expected).hexdigest())
        before = self.snapshot()
        self.assertEqual(self.install()["result"], "already-installed")
        self.assertEqual(before, self.snapshot())
        self.put(self.project, name, "Different pre-existing managed license text")
        self.refused("managed conflict: licenses/sdd-workflow-MIT.txt")
        self.assertEqual((self.project / "LICENSE").read_bytes(), project_license)

    def test_CA12_REQ18_populated_valid_context_spec_evidence_preserved(self):
        from test_workflow import demo, sdd
        demo.prepare(self.project)
        sdd.record_approval(self.project, 1, demo.human(self.project, "approval"))
        demo.activate(self.project)
        demo.complete(self.project, "T1")
        before = {p.relative_to(self.project).as_posix(): p.read_bytes() for scope in (".sdd", "specs", "src", "checks")
                  for p in (self.project / scope).rglob("*") if p.is_file()}
        self.install()
        self.assertEqual(before, {name: (self.project / name).read_bytes() for name in before})
        self.assertEqual(sdd.evaluate(self.project)["next"]["task"], "T2")

    def test_CA13_REQ19_late_managed_conflict_no_writes(self):
        self.seed_user()
        self.put(self.project, installer.MANAGED[-1], "different user command")
        self.refused("managed conflict")

    def test_CA13_REQ19_strict_json_duplicate_jsonc_competing_config(self):
        for data in ("[]", "{broken", '{"model":"a","model":"b"}'):
            self.put(self.project, "opencode.json", data)
            self.refused("object|malformed|duplicate")
        (self.project / "opencode.json").unlink()
        for name in ("opencode.jsonc", ".opencode/opencode.json", ".opencode/opencode.jsonc"):
            self.put(self.project, name, "{}")
            self.refused("unsupported/competing config")
            (self.project / name).unlink()

    def test_CA13_REQ19_role_permission_setting_conflicts(self):
        for config in ({"agent": {"extra": {}}}, {"agent": {"build": {"disable": False}}},
                       {"permission": {"*": "allow"}}, {"formatter": True}, {"instructions": ["unknown.md"]},
                       {"agent": {"verifier": {"permission": {"*": "deny", "bash": "allow"}}}},
                       {"provider": {"custom": {"unsupported": "do-not-print"}}},
                       {"provider": {"openai": {"options": {"apiKey": 123}}}},
                       {"provider": {"openai": {"env": [123]}}},
                       {"provider": {"openai": {"options": {"timeout": True}}}}):
            self.put(self.project, "opencode.json", json.dumps(config))
            self.refused("agent|adapter|unknown core")

    def test_CA13_REQ19_backup_and_marked_block_conflicts(self):
        self.seed_user()
        self.put(self.project, "opencode.json.sdd-backup", "different backup")
        self.refused("backup conflict")
        (self.project / "opencode.json.sdd-backup").unlink()
        self.put(self.project, "AGENTS.md", installer.START + "\nunknown\n" + installer.END)
        self.refused("differing source-map")
        self.put(self.project, "AGENTS.md", installer.MAP + installer.MAP)
        self.refused("ambiguous source-map")

    def test_CA13_REQ19_partial_invalid_context_is_not_repaired(self):
        self.put(self.project, ".sdd/project.json", "{}")
        self.refused("partial .sdd")
        shutil.rmtree(self.project / ".sdd")
        helper = installer.helper_from(self.source)
        helper.initialize(self.project)
        self.put(self.project, ".sdd/state.json", "{}")
        self.refused("state: invalid/missing")

    def test_CA13_REQ19_destination_parent_source_symlinks_and_overlap(self):
        for name, target in (("sdd.py", self.source / "sdd.py"), ("core", self.source / "core"),
                             (".sdd", self.source / "core"), ("opencode.json", self.base / "missing")):
            (self.project / name).symlink_to(target)
            self.refused("symlink|alias|escapes")
            (self.project / name).unlink()
        with self.assertRaisesRegex(ValueError, "overlap"):
            installer.install(self.source, self.source)
        path = self.source / "sdd.py"
        path.unlink()
        path.symlink_to(PACKAGE / "sdd.py")
        with patch.object(installer, "helper_from", side_effect=AssertionError("must not import unsafe source")):
            self.refused("escapes|alias")

    def test_CA13_REQ19_readonly_directory_file_extra_role_types(self):
        self.project.chmod(0o555)
        self.addCleanup(self.project.chmod, 0o755)
        self.refused("unwritable")
        self.project.chmod(0o755)
        self.seed_user()
        (self.project / "opencode.json").chmod(0o444)
        self.refused("unwritable")
        (self.project / "opencode.json").chmod(0o644)
        self.put(self.project, ".opencode/agents/unassigned.md", "extra role")
        self.refused("extra/conflicting agent")

    def test_CA14_REQ20_rollback_after_managed_config_agents_context_backup(self):
        for selected in ("sdd.py", "opencode.json", "AGENTS.md", ".sdd/project.json", ".sdd/state.json", "AGENTS.md.sdd-backup"):
            with self.subTest(after=selected):
                self.seed_user()
                before = self.snapshot()
                def fail(name):
                    if name == selected:
                        raise OSError("injected write failure at " + name)
                with self.assertRaisesRegex(ValueError, "rolled back"):
                    self.install(after_write=fail)
                self.assertEqual(before, self.snapshot())

    def test_CA14_REQ20_rollback_preserves_existing_context_and_reports_residual(self):
        helper = installer.helper_from(self.source)
        helper.initialize(self.project)
        self.seed_user()
        before = self.snapshot()
        def fail(name):
            if name == "AGENTS.md":
                raise ValueError("injected validation failure")
        with self.assertRaisesRegex(ValueError, "rolled back"):
            self.install(after_write=fail)
        self.assertEqual(before, self.snapshot())
        real = installer.atomic
        # Simulate loss of the ability to restore an original, without relying on uid.
        original = (self.project / "opencode.json").read_bytes()
        def broken_restore(path, data, mode):
            if path.name == "opencode.json" and data == original:
                raise OSError("rollback blocked")
            return real(path, data, mode)
        with patch.object(installer, "atomic", side_effect=broken_restore), self.assertRaisesRegex(ValueError, "rollback incomplete; recover paths: opencode.json"):
            self.install(after_write=fail)

    def test_CA11_CA15_REQ17_REQ21_offline_shell_no_network_provider_install(self):
        bin_dir = self.base / "fake tools"
        bin_dir.mkdir()
        for tool in ("curl", "opencode", "pip", "npm"):
            path = bin_dir / tool
            path.write_text("#!/bin/sh\nexit 97\n")
            path.chmod(0o755)
        result = subprocess.run(["sh", str(self.source / "install.sh"), "--source", str(self.source), "--project", str(self.project)],
                                cwd=self.base, env={**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"]},
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "installed")

    def archive(self, entries=None):
        archive = self.base / "fixture.tar.gz"
        with tarfile.open(archive, "w:gz") as stream:
            if entries is None:
                for name in (*installer.MANAGED, *installer.skill_files(self.source, installer.helper_from(self.source)), "install.py", "opencode.json"):
                    stream.add(self.source / name, arcname="SDD-WorkFlow-main/" + name, recursive=False)
            else:
                for name, kind in entries:
                    info = tarfile.TarInfo(name)
                    if kind == "file":
                        info.size = 1
                        stream.addfile(info, io.BytesIO(b"x"))
                    else:
                        info.type = {"symlink": tarfile.SYMTYPE, "hardlink": tarfile.LNKTYPE, "device": tarfile.CHRTYPE}[kind]
                        info.linkname = "../../outside"
                        stream.addfile(info)
        return archive

    def remote_fixture(self, archive, fail=False):
        tools = self.base / "curl fixture"
        tools.mkdir(exist_ok=True)
        curl = tools / "curl"
        curl.write_text("#!/bin/sh\n" + ("exit 22\n" if fail else
            "case \"$*\" in *https://codeload.github.com/darwinlatorre/SDD-WorkFlow/tar.gz/refs/heads/main*) ;; *) exit 96;; esac\n"
            "while [ \"$#\" -gt 0 ]; do if [ \"$1\" = -o ]; then cp \"$FIXTURE_ARCHIVE\" \"$2\"; exit; fi; shift; done\nexit 95\n"))
        curl.chmod(0o755)
        stages = self.base / "owned staging"
        stages.mkdir(exist_ok=True)
        result = subprocess.run(["sh", str(self.source / "install.sh"), "--project", str(self.project)], cwd=self.base,
            env={**os.environ, "PATH": str(tools) + os.pathsep + os.environ["PATH"], "FIXTURE_ARCHIVE": str(archive), "TMPDIR": str(stages), "UNRELATED_SECRET": "do-not-capture"},
            capture_output=True, text=True, timeout=20)
        self.assertEqual(list(stages.iterdir()), [])
        self.assertNotIn("do-not-capture", result.stdout + result.stderr)
        return result

    def test_CA15_REQ21_download_archive_failures_before_project_writes(self):
        for entries in ([('/absolute', 'file')], [('SDD-WorkFlow-main/../../escape', 'file')],
                        [('SDD-WorkFlow-main/link', 'symlink')], [('SDD-WorkFlow-main/link', 'hardlink')],
                        [('SDD-WorkFlow-main/device', 'device')], [('SDD-WorkFlow-main/a', 'file')] * 2,
                        [('SDD-WorkFlow-main/a', 'file'), ('SDD-WorkFlow-main/a/b', 'file')], [('other/file', 'file')]):
            with self.subTest(entries=entries):
                before = self.snapshot()
                result = self.remote_fixture(self.archive(entries))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("archive refused", result.stderr)
                self.assertEqual(before, self.snapshot())
        before = self.snapshot()
        archive = self.archive()
        result = self.remote_fixture(archive, fail=True)
        self.assertNotEqual(result.returncode, 0)
        archive.write_bytes(b"not gzip")
        result = self.remote_fixture(archive)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_CA15_REQ21_local_archive_handoff_success_not_published_smoke(self):
        result = self.remote_fixture(self.archive())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["result"], "installed")

    def test_CA15_REQ21_decompression_and_member_limits(self):
        archive = self.base / "oversized.tar.gz"
        with gzip.open(archive, "wb") as stream:
            for _ in range(513):
                stream.write(b"x" * 65536)
        before = self.snapshot()
        result = self.remote_fixture(archive)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())
        entries = [(f"SDD-WorkFlow-main/f{n}", "file") for n in range(2001)]
        result = self.remote_fixture(self.archive(entries))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.snapshot())

    def test_CA13_REQ19_concurrent_change_is_not_overwritten(self):
        real = installer.helper_from
        def guarded(source):
            helper = real(source)
            original = helper.adapter
            def concurrent(*args):
                self.put(self.project, "sdd.py", "concurrent user content")
                return original(*args)
            helper.adapter = concurrent
            return helper
        with patch.object(installer, "helper_from", side_effect=guarded), self.assertRaisesRegex(ValueError, "concurrent destination change"):
            self.install()
        self.assertEqual(set(self.snapshot()), {"sdd.py"})
        self.assertEqual((self.project / "sdd.py").read_text(), "concurrent user content")


if __name__ == "__main__":
    unittest.main()
