"""CA-17/REQ-25 packaging and lazy permissions; no upstream script execution."""
import hashlib
import json
from pathlib import Path
import shutil
import unittest
from test_install import InstallTests, installer, PACKAGE
from test_workflow import AdapterTests, sdd


class SkillInstall(InstallTests):
    def inventory(self, update):
        path = self.source / ".opencode/skill-manifest.json"
        value = json.loads(path.read_text())
        update(value)
        path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")

    def test_CA17_REQ25_complete_fixed_source_inventory(self):
        files = installer.skill_files(self.source, installer.helper_from(self.source))
        skills = [name for name in files if name.startswith(".opencode/skills/")]
        self.assertEqual(len(skills), 279)
        self.assertEqual(sum((self.source / name).stat().st_size for name in skills), 2808106)
        self.assertEqual((self.source / ".opencode/skills/graphify/.graphify_version").read_text().strip(), "0.9.73")
        self.assertEqual({p.name for p in (self.source / ".opencode/skills").iterdir()}, set(installer.SKILLS))

    def test_CA17_REQ25_exact_install_repeat_unrelated_and_additional_user_files(self):
        self.put(self.project, ".opencode/skills/user-notes/SKILL.md", "---\nname: user-notes\ndescription: Local notes\n---\nUnrelated user skill.\n")
        self.put(self.project, ".opencode/skills/auth0/user-note.txt", "User note outside managed manifest")
        self.seed_user()
        original = self.snapshot()
        self.install()
        for name in installer.skill_files(self.source, installer.helper_from(self.source)):
            self.assertEqual((self.project / name).read_bytes(), (self.source / name).read_bytes())
        for name, record in original.items():
            if name not in {"opencode.json", "AGENTS.md"}:
                self.assertEqual(record, self.snapshot()[name])
        before = self.snapshot()
        self.assertEqual(self.install()["result"], "already-installed")
        self.assertEqual(before, self.snapshot())

    def test_CA17_REQ25_late_differing_skill_file_is_preflight_conflict(self):
        name = sorted(json.loads((self.source / ".opencode/skill-manifest.json").read_text())["files"])[-1]
        self.put(self.project, name, "differing named user content")
        self.refused("managed conflict")

    def test_CA17_REQ25_missing_unknown_links_types_source_no_writes(self):
        root = self.source / ".opencode/skills"
        path = root / "graphify/SKILL.md"
        original = path.read_bytes()
        path.unlink()
        self.refused("unknown/missing skill source members")
        path.write_bytes(original)
        extra = root / "graphify/untracked.md"
        extra.write_text("unknown release member")
        self.refused("unknown/missing skill source members")
        extra.unlink()
        extra.symlink_to(self.source / "sdd.py")
        self.refused("unsafe skill source type/link")
        extra.unlink()
        path.unlink()
        path.mkdir()
        self.refused("unknown/missing skill source members")
        path.rmdir()
        path.write_bytes(original)
        shutil.copytree(root / "graphify", root / "find-skills")
        self.refused("unknown/missing skill source name")

    def test_CA17_REQ25_manifest_hash_name_and_path_guard(self):
        path = self.source / ".opencode/skills/graphify/SKILL.md"
        path.write_bytes(path.read_bytes().replace(b"name: graphify", b"name: wrong-name"))
        self.refused("hash conflict|name/frontmatter mismatch")
        self.inventory(lambda m: m["files"].update({".opencode/skills/graphify/SKILL.md": hashlib.sha256(path.read_bytes()).hexdigest()}))
        self.refused("name/frontmatter mismatch")
        path.write_bytes(path.read_bytes().replace(b"name: wrong-name", b"name: graphify"))
        self.inventory(lambda m: m["files"].update({"../outside": "0" * 64}))
        self.refused("unknown/missing skill source members")

    def test_CA17_REQ25_skill_rollback_and_destination_aliases(self):
        self.put(self.project, ".opencode/skills/user-notes/readme.txt", "untouched")
        before = self.snapshot()
        def fail(name):
            if name == ".opencode/skills/graphify/SKILL.md":
                raise OSError("injected skill write failure")
        with self.assertRaisesRegex(ValueError, "rolled back"):
            self.install(after_write=fail)
        self.assertEqual(before, self.snapshot())
        (self.project / ".opencode/skills/graphify").symlink_to(self.source / ".opencode/skills/graphify")
        self.refused("escapes|alias")

    def test_CA17_REQ25_prior_compatible_permission_map_gets_only_skill_access(self):
        config = json.loads((self.source / "opencode.json").read_text())
        for role in sdd.ROLES:
            config["agent"][role]["permission"].pop("skill")
        self.put(self.project, "opencode.json", json.dumps(config))
        self.install()
        loaded = json.loads((self.project / "opencode.json").read_text())
        for role in sdd.ROLES:
            permission = loaded["agent"][role]["permission"]
            self.assertEqual({key: value for key, value in permission.items() if key != "skill"}, config["agent"][role]["permission"])
            self.assertEqual(permission["skill"], {"*": "deny", **{name: "allow" for name in installer.SKILLS}})


class SkillPermissions(AdapterTests):
    def test_CA17_REQ25_each_role_lazy_names_unknown_default_deny(self):
        self.assertTrue(sdd.evaluate(self.root)["valid"])
        profile = sdd.permission_profile(sdd.project_contract(self.root))
        for role in sdd.ROLES:
            for name in installer.SKILLS:
                self.assertEqual(sdd.effective(profile[role]["skill"], name), "allow")
            for name in ("find-skills", "customize-opencode", "auth0-future", "vercel-future", "unrelated-user"):
                self.assertEqual(sdd.effective(profile[role]["skill"], name), "deny")
            if role != "orchestrator":
                self.assertEqual(sdd.effective(profile[role].get("task", "deny"), "implementer"), "deny")
            if role == "verifier":
                self.assertEqual(sdd.effective(profile[role].get("edit", "deny"), "src/file.py"), "deny")
                self.assertEqual(sdd.effective(profile[role].get("bash", "deny"), "python3 checks/run.py"), "deny")

    def test_CA17_REQ25_skill_patterns_order_missing_and_unknown_allow_rejected(self):
        path = self.root / "opencode.json"
        original = path.read_bytes()
        variants = [{"*": "allow"}, {"*": "deny", "auth0*": "allow"}, {"*": "deny", "vercel-*": "allow"},
                    {"*": "deny", **{name: "allow" for name in installer.SKILLS}, "unrelated-user": "allow"},
                    {**{name: "allow" for name in installer.SKILLS}, "*": "deny"}, "deny"]
        for role in sdd.ROLES:
            for rules in variants:
                with self.subTest(role=role, rules=rules):
                    path.write_bytes(original)
                    config = self.read("opencode.json")
                    config["agent"][role]["permission"]["skill"] = rules
                    path.write_text(json.dumps(config))
                    self.invalid("permissions|catch-all")


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(cls(name) for cls in (SkillInstall, SkillPermissions)
        for name in cls.__dict__ if name.startswith("test_"))
