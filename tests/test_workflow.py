"""REQ/CA mappings are in test names. All project roots are synthetic/disposable."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
module = importlib.util.spec_from_file_location("demo", PACKAGE / "examples/worked-lifecycle/demo.py")
demo = importlib.util.module_from_spec(module)
module.loader.exec_module(demo)
sdd = demo.sdd


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="sdd root with spaces ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        demo.prepare(self.root)

    def read(self, name):
        return sdd.load(self.root, name)

    def put(self, name, data):
        demo.put(self.root, name, data)

    def mutate(self, name, function):
        value = self.read(name)
        function(value)
        self.put(name, value)

    def meta(self, name, function):
        feature = self.read(".sdd/state.json")["features"][0]
        path = self.root / feature["spec_dir"] / name
        block = sdd.re.findall(r"^```json\s*\n(.*?)^```\s*$", path.read_text(), sdd.re.M | sdd.re.S)[0]
        value = json.loads(block)
        function(value)
        demo.metadata(self.root, name, value)

    def invalid(self, reason):
        with self.assertRaisesRegex(sdd.Invalid, reason):
            sdd.evaluate(self.root)

    def approved(self):
        sdd.record_approval(self.root, 1, demo.human(self.root, "approval"))
        demo.activate(self.root)

    def finished(self):
        self.approved()
        demo.complete(self.root, "T1")
        demo.complete(self.root, "T2")

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_CA01_REQ01_REQ16_two_layouts_offline(self):
        for fixture in ("python-layout.json", "rust-layout.json"):
            with self.subTest(fixture=fixture), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                demo.prepare(root, fixture)
                with patch("subprocess.run", side_effect=AssertionError("must not execute")):
                    self.assertTrue(sdd.evaluate(root)["valid"])
                self.assertFalse((root / "opencode.json").exists())
                self.assertEqual(set(root.iterdir()), {root / ".sdd", root / "specs", *(root / x.split('/')[0] for x in sdd.project_contract(root)["source_roots"])})

    def test_CA02_REQ02_wrong_types_unknown_fields_duplicate_keys(self):
        original = (self.root / ".sdd/project.json").read_bytes()
        for bad in (b'{"schema_version":1,"schema_version":1}', b'{broken', b'[]'):
            (self.root / ".sdd/project.json").write_bytes(bad)
            self.invalid("duplicate|malformed|expected object")
        (self.root / ".sdd/project.json").write_bytes(original)
        self.mutate(".sdd/project.json", lambda p: p.update(one_feature_at_a_time=1))
        self.invalid("one_feature_at_a_time")
        (self.root / ".sdd/project.json").write_bytes(original)
        self.mutate(".sdd/project.json", lambda p: p.update(surprise=True))
        self.invalid("unknown core")

    def test_CA02_REQ02_invalid_ID_variants(self):
        path = self.root / "specs/notes/requirements.md"
        original = path.read_bytes()
        variants = [(lambda m: m["requirements"].append("REQ-01"), "duplicate"),
                    (lambda m: m["requirements"].append("garbage"), "malformed ID"),
                    (lambda m: m["criteria"][0]["requirements"].append("REQ-99"), "dangling"),
                    (lambda m: m["requirements"].append("REQ-03"), "uncovered REQ"),
                    (lambda m: m["criteria"].append(copy.deepcopy(m["criteria"][0])), "duplicate CA")]
        for change, reason in variants:
            with self.subTest(reason=reason):
                path.write_bytes(original)
                self.meta("requirements.md", change)
                self.invalid(reason)

    def test_CA02_REQ02_retired_ID_reuse(self):
        self.mutate(".sdd/state.json", lambda st: st["retired_ids"].update({"1": ["REQ-01"]}))
        self.invalid("retired ID reused")

    def test_CA02_REQ02_uncovered_CA(self):
        self.meta("tasks.md", lambda m: m["tasks"].pop())
        self.invalid("uncovered CA")

    def test_CA02_REQ02_task_duplicate_dangling_cycle(self):
        path = self.root / "specs/notes/tasks.md"
        original = path.read_bytes()
        changes = [(lambda m: m["tasks"].append(copy.deepcopy(m["tasks"][0])), "duplicate task"),
                   (lambda m: m["tasks"][0]["depends_on"].append("T9"), "dangling dependency"),
                   (lambda m: m["tasks"][0]["depends_on"].append("T2"), "dependency cycle")]
        for change, reason in changes:
            with self.subTest(reason=reason):
                path.write_bytes(original)
                self.meta("tasks.md", change)
                self.invalid(reason)

    def test_CA02_REQ06_feature_duplicate_dangling_cycle(self):
        original = self.read(".sdd/state.json")
        for variant in ("duplicate", "dangling", "cycle"):
            st = copy.deepcopy(original)
            first = st["features"][0]
            if variant == "duplicate":
                st["features"].append(copy.deepcopy(first))
            elif variant == "dangling":
                first["depends_on"] = [9]
            else:
                first["depends_on"] = [1]
            self.put(".sdd/state.json", st)
            self.invalid("duplicate|dangling|cycle")

    def test_CA02_REQ06_single_active_conflict(self):
        self.approved()
        st = self.read(".sdd/state.json")
        second = {**st["features"][0], "id": 2, "name": "other", "spec_dir": "specs/other"}
        st["features"].append(second)
        self.put(".sdd/state.json", st)
        self.invalid("single-active")

    def test_CA02_REQ06_only_eligible_task(self):
        self.approved()
        demo.complete(self.root, "T2")
        result = sdd.evaluate(self.root)["next"]
        self.assertEqual(result["task"], "T1")
        self.assertEqual(result["completed"], [])

    def test_CA02_REQ06_feature_dependency_gate(self):
        self.approved()
        st = self.read(".sdd/state.json")
        st["features"].append({**st["features"][0], "id": 2, "name": "other", "spec_dir": "specs/other", "status": "pending"})
        st["features"][0]["depends_on"] = [2]
        self.put(".sdd/state.json", st)
        self.invalid("dependencies not done")

    def test_CA03_REQ03_every_approved_file_is_immutable(self):
        self.approved()
        for name in ("requirements.md", "design.md", "tasks.md"):
            path = self.root / "specs/notes" / name
            original = path.read_bytes()
            with self.subTest(file=name):
                path.write_bytes(original + b"\n- [x] changed whitespace and checkbox\n")
                self.invalid("approval stale")
                path.write_bytes(original)
        self.assertEqual(sdd.evaluate(self.root)["next"]["task"], "T1")

    def test_CA03_REQ03_version_and_confirmation_gate(self):
        with self.assertRaisesRegex(sdd.Invalid, "missing artifact"):
            sdd.record_approval(self.root, 1, ".sdd/missing.json")
        ref = demo.human(self.root, "approval")
        for field, bad in (("actor", "agent"), ("text", ""), ("version", 2), ("purpose", "closure")):
            original = self.read(ref)
            self.mutate(ref, lambda p: p.update({field: bad}))
            with self.subTest(field=field), self.assertRaises(sdd.Invalid):
                sdd.record_approval(self.root, 1, ref)
            self.put(ref, original)
        self.approved()
        self.meta("design.md", lambda p: p.update(version=2))
        self.invalid("version mismatch")

    def test_CA03_REQ04_progress_does_not_change_approval(self):
        self.approved()
        digest = sdd.evaluate(self.root)["next"]["digest"]
        demo.complete(self.root, "T1")
        self.assertEqual(digest, sdd.evaluate(self.root)["next"]["digest"])

    def test_CA03_REQ03_approval_idempotent_no_contradictory_overwrite(self):
        ref = demo.human(self.root, "approval")
        sdd.record_approval(self.root, 1, ref)
        before = self.snapshot()
        sdd.record_approval(self.root, 1, ref)
        self.assertEqual(before, self.snapshot())
        self.mutate(ref, lambda p: p.update(text="Different human instruction"))
        with self.assertRaisesRegex(sdd.Invalid, "contradictory"):
            sdd.record_approval(self.root, 1, ref)

    def test_CA05_REQ09_resume_never_recommends_completed_work(self):
        self.approved()
        demo.complete(self.root, "T1")
        before = self.snapshot()
        one = sdd.evaluate(self.root)
        two = sdd.evaluate(self.root)
        self.assertEqual(one, two)
        self.assertEqual(one["next"]["task"], "T2")
        self.assertEqual(one["next"]["completed"], ["T1"])
        self.assertEqual(before, self.snapshot())

    def test_CA05_REQ07_block_preserve_and_confirmed_resume(self):
        self.approved()
        demo.complete(self.root, "T1")
        st = self.read(".sdd/state.json")
        st["history"] = []
        st["features"][0]["status"] = "blocked"
        st["block"] = {"feature": 1, "previous_status": "in_progress", "previous_phase": "implementation", "condition": "access", "resolution_ref": None}
        self.put(".sdd/state.json", st)
        result = sdd.evaluate(self.root)["next"]
        self.assertEqual(result["action"], "intervention")
        self.assertEqual(result["preserved"]["previous_phase"], "implementation")
        st["features"][0]["status"] = "in_progress"
        self.put(".sdd/state.json", st)
        self.invalid("resolution missing")
        st["block"]["resolution_ref"] = ".sdd/resolution.json"
        self.put(".sdd/resolution.json", {"schema_version": 1, "actor": "human", "feature": 1, "condition": "access", "text": "resolved"})
        self.put(".sdd/state.json", st)
        self.assertEqual(sdd.evaluate(self.root)["next"]["task"], "T2")
        st["phase"] = "planning"
        self.put(".sdd/state.json", st)
        self.invalid("restore status/phase")

    def test_CA05_REQ07_missing_block_details(self):
        self.mutate(".sdd/state.json", lambda st: (st["features"][0].update(status="blocked"), st.update(active_feature=1)))
        self.invalid("lost prior")

    def test_CA06_REQ08_source_test_environment_procedure_staleness(self):
        self.approved()
        demo.complete(self.root, "T1")
        initial = self.snapshot()
        changes = [lambda: demo.text(self.root, "src/sample.txt", "Changed"),
                   lambda: demo.text(self.root, "checks/sample.txt", "Changed"),
                   lambda: self.mutate(".sdd/environment.json", lambda e: e["identities"].update(python="v2")),
                   lambda: self.mutate(".sdd/project.json", lambda p: p["procedures"]["check"].update(timeout=61)),
                   lambda: demo.text(self.root, "src/added.txt", "Added"),
                   lambda: (self.root / "src/sample.txt").unlink()]
        for index, change in enumerate(changes):
            for name, data in initial.items():
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            if (self.root / "src/added.txt").exists():
                (self.root / "src/added.txt").unlink()
            with self.subTest(change=index):
                change()
                result = sdd.evaluate(self.root)["next"]
                self.assertEqual(result["completed"], [])
                self.assertIn("stale", next(iter(result["checks"].values())))

    def test_CA06_REQ08_unknown_environment_requires_intervention(self):
        self.approved()
        demo.complete(self.root, "T1")
        self.mutate(".sdd/environment.json", lambda e: e.update(identities={}))
        self.assertEqual(sdd.evaluate(self.root)["next"]["action"], "intervention")
        self.assertIn("unknown freshness", next(iter(sdd.evaluate(self.root)["next"]["checks"].values())))

    def test_CA06_REQ08_out_of_scope_reuses_evidence(self):
        self.approved()
        demo.complete(self.root, "T1")
        demo.text(self.root, "unrelated/readme.txt", "Unrelated")
        result = sdd.evaluate(self.root)["next"]
        self.assertEqual(result["completed"], ["T1"])
        self.assertIn("unrelated inputs excluded", next(iter(result["checks"].values())))

    def test_CA06_REQ08_failed_evidence_claim_is_not_completion(self):
        self.approved()
        demo.complete(self.root, "T1")
        self.mutate(".sdd/evidence/1-T1.json", lambda e: e.update(outcome="FAIL"))
        self.assertEqual(sdd.evaluate(self.root)["next"]["completed"], [])

    def test_CA06_REQ08_scope_secret_and_symlink_fail_closed(self):
        for bad in ("../escape", "/absolute", ".", "src/*"):
            original = self.read(".sdd/project.json")
            self.mutate(".sdd/project.json", lambda p: p["procedures"]["check"].update(inputs=[bad]))
            self.invalid("unsafe|unbounded")
            self.put(".sdd/project.json", original)
        demo.text(self.root, "src/.env", "not-a-real-secret")
        with self.assertRaisesRegex(sdd.Invalid, "secret input"):
            sdd.manifest(self.root, sdd.project_contract(self.root), "check")
        (self.root / "src/.env").unlink()
        (self.root / "src/link").symlink_to(self.root.parent)
        with self.assertRaisesRegex(sdd.Invalid, "escapes|symlink"):
            sdd.manifest(self.root, sdd.project_contract(self.root), "check")

    def test_CA07_REQ10_changed_retry_and_pause(self):
        self.approved()
        demo.complete(self.root, "T1")
        ref = ".sdd/progress/1.json"
        first = {"hypothesis": "h1", "change_ref": "src/sample.txt#1", "result": "FAIL", "progress": False}
        self.mutate(ref, lambda p: p["tasks"]["T1"].update(attempts=[first, first]))
        self.invalid("unchanged retry refused")
        second = {**first, "hypothesis": "h2", "change_ref": "src/sample.txt#2"}
        self.mutate(ref, lambda p: p["tasks"]["T1"].update(attempts=[first, second]))
        result = sdd.evaluate(self.root)["next"]
        self.assertEqual(result["action"], "intervention")
        self.assertIn("two no-progress", result["reason"])
        third = {**second, "hypothesis": "h3", "change_ref": "src/sample.txt#3", "progress": True}
        self.mutate(ref, lambda p: p["tasks"]["T1"].update(attempts=[first, second, third]))
        self.invalid("retry budget exhausted")

    def test_CA08_REQ11_low_and_high_risk_paths(self):
        self.finished()
        self.assertEqual(sdd.evaluate(self.root)["next"]["action"], "human close")
        self.mutate(".sdd/state.json", lambda st: st["features"][0].update(risk_tags=["high"]))
        self.assertEqual(sdd.evaluate(self.root)["next"]["action"], "verify")
        self.mutate(".sdd/state.json", lambda st: st["features"][0].update(risk_tags=["unknown"]))
        self.assertEqual(sdd.evaluate(self.root)["next"]["action"], "intervention")

    def test_CA08_REQ12_done_requires_human_closure_and_all_gates(self):
        self.finished()
        st = self.read(".sdd/state.json")
        st["features"][0]["status"] = "done"
        st["history"] = []
        st["active_feature"] = None
        self.put(".sdd/state.json", st)
        self.invalid("done gate failed.*closure")

    def test_CA08_REQ12_complete_low_risk_closure(self):
        self.finished()
        demo.review_and_close(self.root)
        self.assertEqual(sdd.evaluate(self.root)["features"][0]["action"], "done")
        self.assertEqual(self.read(".sdd/state.json")["reviews"], {})

    def test_CA08_REQ11_REQ12_review_and_closure_bind_payloads(self):
        self.finished()
        self.mutate(".sdd/state.json", lambda st: st["features"][0].update(risk_tags=["high"]))
        demo.review_and_close(self.root, True)
        self.assertTrue(sdd.evaluate(self.root)["valid"])
        self.mutate(".sdd/evidence/1-T1.json", lambda e: e.update(extensions={"note": "payload changed"}))
        self.invalid("review failed/stale")

    def test_CA08_REQ12_stale_artifact_closure(self):
        self.finished()
        demo.review_and_close(self.root)
        demo.text(self.root, ".sdd/results/1-T1.txt", "changed result")
        self.invalid("closure stale")

    def test_CA08_REQ12_stale_code_rejects_done(self):
        self.finished()
        demo.review_and_close(self.root)
        demo.text(self.root, "src/sample.txt", "changed")
        self.invalid("done gate failed")

    def test_CA09_REQ13_readonly_cli_deterministic_external_cwd(self):
        self.approved()
        before = self.snapshot()
        for operation in ("validate", "status"):
            args = [sys.executable, str(PACKAGE / "sdd.py"), operation, "--root", str(self.root), "--json"]
            a = subprocess.run(args, cwd=self.root.parent, capture_output=True, timeout=10)
            b = subprocess.run(args, cwd=self.root.parent, capture_output=True, timeout=10)
            self.assertEqual(a.returncode, 0)
            self.assertEqual(a.stdout, b.stdout)
        self.assertEqual(before, self.snapshot())

    def test_CA09_REQ13_real_init_approval_cli_and_exit_codes(self):
        self.assertEqual(demo.cli(self.root, "init")["result"], "already-initialized")
        ref = demo.human(self.root, "approval")
        self.assertEqual(demo.cli(self.root, "approval", 0, "--feature", "1", "--confirmation-ref", ref)["result"], "approved")
        demo.cli(self.root, "approval", 1, "--feature", "1", "--confirmation-ref", ".sdd/missing.json")
        result = subprocess.run([sys.executable, str(PACKAGE / "sdd.py"), "approval", "--root", str(self.root)], capture_output=True)
        self.assertEqual(result.returncode, 2)

    def test_CA09_REQ13_init_partial_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".sdd").mkdir()
            demo.text(root, ".sdd/project.json", "do not overwrite")
            with self.assertRaisesRegex(sdd.Invalid, "partial"):
                sdd.initialize(root)
            self.assertEqual((root / ".sdd/project.json").read_text(), "do not overwrite")

    def test_CA09_REQ13_read_operations_do_not_execute_procedures(self):
        self.approved()
        self.mutate(".sdd/project.json", lambda p: p["procedures"]["check"].update(argv=["not-an-executable", "network-or-secret-capture"]))
        with patch("subprocess.run", side_effect=AssertionError("no execution")), patch.dict("os.environ", {"SECRET_TOKEN": "never-capture"}):
            result = sdd.evaluate(self.root)
        self.assertNotIn("never-capture", json.dumps(result))

    def test_CA09_REQ13_invalid_transition_history(self):
        self.mutate(".sdd/state.json", lambda st: st["history"].append({"feature": 1, "from": "pending", "to": "done", "previous_phase": "planning", "phase": "closed", "source": "specs/notes/tasks.md"}))
        self.invalid("invalid transition")


class AdapterTests(WorkflowTests):
    # Inherit fixture helpers, not test methods: overridden test discovery below.
    def setUp(self):
        super().setUp()
        shutil.copy(PACKAGE / "opencode.json", self.root)
        shutil.copy(PACKAGE / "sdd.py", self.root)
        shutil.copytree(PACKAGE / ".opencode", self.root / ".opencode")

    def test_CA04_REQ05_REQ14_valid_four_role_startup(self):
        self.assertTrue(sdd.evaluate(self.root)["valid"])
        self.approved()
        project = sdd.project_contract(self.root)
        project["implementation_paths"] = ["src/sample.txt"]
        self.put(".sdd/project.json", project)
        dispatch = sdd.evaluate(self.root, ["T1"])["authorization"]
        self.mutate(".sdd/state.json", lambda st: st.update(extensions={"assignment": dispatch["assignment"]}))
        config = self.read("opencode.json")
        for role, permission in sdd.permission_profile(project, dispatch).items():
            config["agent"][role]["permission"] = permission
        # atomic sorts keys; adapter permissions have significant ordering.
        (self.root / "opencode.json").write_text(json.dumps(config, indent=2))
        self.assertTrue(sdd.evaluate(self.root)["valid"])

    def test_CA04_REQ14_missing_roles_commands_schema(self):
        original = (self.root / "opencode.json").read_bytes()
        for mutate in (lambda c: c.update({"$schema": "wrong"}),
                       lambda c: c["agent"].pop("planner"),
                       lambda c: c["agent"]["build"].update(disable=False),
                       lambda c: c.update(permissions={"*": "allow"})):
            (self.root / "opencode.json").write_bytes(original)
            config = self.read("opencode.json")
            mutate(config)
            (self.root / "opencode.json").write_text(json.dumps(config))
            self.invalid("adapter|unknown core")
        (self.root / "opencode.json").write_bytes(original)
        (self.root / ".opencode/commands/sdd.md").unlink()
        self.invalid("command discovery")

    def test_CA04_REQ05_permission_wildcards_global_writes_verifier_execution(self):
        original = (self.root / "opencode.json").read_bytes()
        changes = [("planner", "edit", {"*": "deny", "specs/*": "allow", ".sdd/state.json": "allow"}),
                   ("planner", "edit", {"specs/*": "allow", "*": "allow"}),
                   ("verifier", "bash", "allow"), ("implementer", "edit", {"*": "allow"}),
                   ("verifier", "task", {"*": "allow"}), ("orchestrator", "edit", {"*": "allow"})]
        for role, key, value in changes:
            with self.subTest(role=role, key=key):
                (self.root / "opencode.json").write_bytes(original)
                config = self.read("opencode.json")
                config["agent"][role]["permission"][key] = value
                (self.root / "opencode.json").write_text(json.dumps(config))
                self.invalid("effective permissions")

    def test_CA04_REQ14_missing_agent_file_and_frontmatter_override(self):
        path = self.root / ".opencode/agents/verifier.md"
        original = path.read_bytes()
        path.unlink()
        self.invalid("missing/extra agent")
        path.write_bytes(original.replace(b"mode: subagent", b"mode: primary"))
        self.invalid("frontmatter")

    def test_CA04_REQ05_preapproval_block_cannot_enable_implementation(self):
        self.mutate(".sdd/state.json", lambda st: (st.update(active_feature=1,
            block={"feature": 1, "previous_status": "spec_ready", "previous_phase": "planning",
                   "condition": "Await human", "resolution_ref": None}), st["features"][0].update(status="blocked")))
        self.mutate(".sdd/project.json", lambda p: p.update(implementation_paths=["src/sample.txt"]))
        self.invalid("implementation permissions before approval")

    def test_CA04_REQ14_commands_must_be_assigned_procedures(self):
        self.approved()
        dispatch = sdd.evaluate(self.root, ["T1"])["authorization"]
        self.mutate(".sdd/state.json", lambda st: st.update(extensions={"assignment": dispatch["assignment"]}))
        self.mutate(".sdd/project.json", lambda p: p.update(implementation_commands=["python3 unassigned.py"]))
        self.invalid("commands exceed assigned procedures")


# Only run AdapterTests' own cases, avoiding duplicated inherited suites.
def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite(loader.loadTestsFromTestCase(WorkflowTests))
    suite.addTests(AdapterTests(name) for name in AdapterTests.__dict__ if name.startswith("test_"))
    return suite


if __name__ == "__main__":
    unittest.main()
