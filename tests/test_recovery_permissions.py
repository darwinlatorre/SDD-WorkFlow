"""Ronda 2 regression evidence: canonical boundaries, dispatch and recovery."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from test_workflow import WorkflowTests, AdapterTests, PACKAGE, demo, sdd


class Corrections(WorkflowTests):
    def test_CA04_CA06_REQ02_REQ05_canonical_protected_aliases(self):
        path = self.root / "specs/notes/tasks.md"
        original = path.read_bytes()
        for name in ("./.sdd/state.json", "./specs/notes/tasks.md", "./opencode.json", "./", ".sdd/state.json", "specs", "opencode.json", "sdd.py"):
            with self.subTest(name=name):
                path.write_bytes(original)
                self.meta("tasks.md", lambda m: m["tasks"][0].update(write_paths=[name]))
                self.invalid("noncanonical|protected")
        path.write_bytes(original)
        (self.root / "state-alias").symlink_to(self.root / ".sdd")
        (self.root / "spec-alias").symlink_to(self.root / "specs")
        (self.root / "outside").symlink_to(self.root.parent)
        for name in ("state-alias/state.json", "spec-alias/notes/tasks.md", "outside/file"):
            with self.subTest(name=name):
                path.write_bytes(original)
                self.meta("tasks.md", lambda m: m["tasks"][0].update(write_paths=[name]))
                self.invalid("symlink alias|escapes root")

    def test_CA06_REQ08_root_alias_scopes_and_symlink_parents(self):
        original = self.read(".sdd/project.json")
        for field in ("source_roots", "implementation_paths"):
            for path in ("./", "./.sdd", "./specs", "./opencode.json"):
                self.put(".sdd/project.json", original)
                self.mutate(".sdd/project.json", lambda p: p.update({field: [path]}))
                self.invalid("noncanonical")
        for path in ("./", "./src", "./.sdd/state.json"):
            self.put(".sdd/project.json", original)
            self.mutate(".sdd/project.json", lambda p: p["procedures"]["check"].update(inputs=[path]))
            self.invalid("noncanonical")
        self.put(".sdd/project.json", original)
        (self.root / "alias").symlink_to(self.root / "src")
        self.mutate(".sdd/project.json", lambda p: p["procedures"]["check"].update(inputs=["alias/sample.txt"]))
        self.invalid("symlink alias")

    def test_CA07_CA05_REQ10_human_reset_retains_prefix_and_rearms(self):
        self.approved()
        attempts = [{"hypothesis": "h1", "change_ref": "src/sample.txt#1", "result": "FAIL", "progress": False},
                    {"hypothesis": "h2", "change_ref": "src/sample.txt#2", "result": "FAIL", "progress": False}]
        self.put(".sdd/progress/1.json", {"schema_version": 1, "feature": 1, "tasks": {"T1": {
            "status": "in_progress", "attempts": attempts, "evidence": []}}, "handoff": "Paused", "sources": ["specs/notes/tasks.md"]})
        self.assertEqual(sdd.evaluate(self.root)["next"]["action"], "intervention")
        digest = sdd.evaluate(self.root)["next"]["digest"]
        ref = ".sdd/retry-reset.json"
        reset = {"schema_version": 1, "actor": "human", "purpose": "retry_reset", "feature": 1, "task": "T1",
            "digest": digest, "after_attempt": 2, "attempts_digest": sdd.sha(sdd.canonical(attempts)),
            "source_ref": ".sdd/decisions.md", "text": "SIMULATED human: diagnostic resolved; authorize a new budget", "date": "2026-10-09"}
        self.put(ref, reset)
        self.mutate(".sdd/state.json", lambda st: st.update(extensions={"retry_resets": {"1:T1": [ref]}}))
        result = sdd.evaluate(self.root)["next"]
        self.assertEqual(result["action"], "implement")
        self.assertIn(ref, result["sources"])
        third = {"hypothesis": "h3", "change_ref": "src/sample.txt#3", "result": "PASS", "progress": True}
        self.mutate(".sdd/progress/1.json", lambda p: p["tasks"]["T1"]["attempts"].append(third))
        self.assertEqual(sdd.evaluate(self.root)["next"]["action"], "implement")
        self.assertEqual(self.read(".sdd/progress/1.json")["tasks"]["T1"]["attempts"][:2], attempts)
        for field, invalid in (("actor", "implementer"), ("digest", "old"), ("attempts_digest", "old"),
                               ("task", "T2"), ("text", ""), ("source_ref", ".sdd/missing.json")):
            with self.subTest(field=field):
                self.put(ref, {**reset, field: invalid})
                self.invalid("human|stale|history|source missing")
        self.put(ref, reset)
        self.mutate(".sdd/progress/1.json", lambda p: p["tasks"]["T1"].update(attempts=[]))
        self.invalid("history/prefix mismatch")

    def test_CA07_REQ10_generic_block_resolution_is_not_retry_reset(self):
        self.approved()
        attempts = [{"hypothesis": "h1", "change_ref": "a", "result": "FAIL", "progress": False},
                    {"hypothesis": "h2", "change_ref": "b", "result": "FAIL", "progress": False}]
        self.put(".sdd/progress/1.json", {"schema_version": 1, "feature": 1, "tasks": {"T1": {
            "status": "in_progress", "attempts": attempts, "evidence": []}}, "handoff": "Paused", "sources": []})
        self.put(".sdd/resolution.json", {"schema_version": 1, "actor": "human", "feature": 1, "condition": "access", "text": "resolved"})
        self.mutate(".sdd/state.json", lambda st: st.update(block={"feature": 1, "previous_status": "in_progress",
            "previous_phase": "implementation", "condition": "access", "resolution_ref": ".sdd/resolution.json"}))
        self.assertEqual(sdd.evaluate(self.root)["next"]["action"], "intervention")

    def test_CA09_REQ13_profile_cli_readonly_and_no_root_override(self):
        self.approved()
        before = self.snapshot()
        result = demo.cli(self.root, "status", 0, "--profile", "--assigned-task", "T1")
        self.assertEqual(result["authorization"]["assignment"]["tasks"], ["T1"])
        self.assertEqual(result["authorization"]["write_paths"], ["src/sample.txt"])
        self.assertNotIn("checks/sample.txt", result["permission_profile"]["implementer"]["edit"])
        startup = demo.cli(self.root, "status", 0, "--profile", "--runtime-grants")
        self.assertEqual(sdd.effective(startup["permission_profile"]["implementer"]["edit"], ".sdd/progress/1-review.json"), "deny")
        self.assertEqual(sdd.effective(startup["permission_profile"]["implementer"]["edit"], ".sdd/progress/1-closure.json"), "deny")
        demo.cli(self.root, "status", 1, "--profile", "--assigned-task", "T2")
        self.assertEqual(before, self.snapshot())
        result = subprocess.run([sys.executable, str(PACKAGE / "sdd.py"), "status", "--root", str(self.root),
                                 "--root=.", "--json"], capture_output=True)
        self.assertEqual(result.returncode, 2)


class DispatchAdapter(AdapterTests):
    def config(self, edit):
        config = self.read("opencode.json")
        edit(config)
        (self.root / "opencode.json").write_text(json.dumps(config, indent=2))

    def assign(self, tid="T1"):
        dispatch = sdd.evaluate(self.root, [tid])["authorization"]
        self.mutate(".sdd/state.json", lambda st: st.setdefault("extensions", {}).update(assignment=dispatch["assignment"]))
        return dispatch

    def test_CA04_REQ05_REQ14_bounded_helper_optin_and_harmless_settings(self):
        self.config(lambda c: c.update(logLevel="WARN", username="Adopter", snapshot=False, watcher={"ignore": ["build/*"]}))
        self.assertTrue(sdd.evaluate(self.root)["valid"])
        self.config(lambda c: c["agent"]["orchestrator"]["permission"].update(bash="deny"))
        self.assertTrue(sdd.evaluate(self.root)["valid"])
        profile = sdd.permission_profile(sdd.project_contract(self.root))
        self.config(lambda c: c["agent"]["orchestrator"].update(permission=profile["orchestrator"]))
        self.assertTrue(sdd.evaluate(self.root)["valid"])
        self.config(lambda c: c["agent"]["orchestrator"]["permission"]["bash"].update({"python3 *": "allow"}))
        self.invalid("effective permissions")

    def test_CA04_REQ06_assignment_future_unknown_completed_and_scope(self):
        self.approved()
        with self.assertRaisesRegex(sdd.Invalid, "dependency-ineligible"):
            sdd.evaluate(self.root, ["T2"])
        with self.assertRaisesRegex(sdd.Invalid, "unknown task"):
            sdd.evaluate(self.root, ["T99"])
        dispatch = self.assign()
        self.assertEqual(dispatch["write_paths"], ["src/sample.txt"])
        self.config(lambda c: c["agent"]["implementer"]["permission"].update(edit={"*": "deny", "checks/sample.txt": "allow"}))
        self.invalid("effective permissions")
        self.config(lambda c: c["agent"]["implementer"]["permission"].update(edit={"*": "deny"}))
        demo.complete(self.root, "T1")
        result = sdd.evaluate(self.root)
        self.assertEqual(result["authorization"]["status"], "revoked: completed")
        self.assertEqual(result["authorization"]["write_paths"], [])
        with self.assertRaisesRegex(sdd.Invalid, "completed or dependency-ineligible"):
            sdd.evaluate(self.root, ["T1"])
        self.assertEqual(self.assign("T2")["write_paths"], ["checks/sample.txt"])

    def test_CA04_REQ06_future_procedure_permission_requires_explicit_capability_optin(self):
        self.meta("tasks.md", lambda m: m["tasks"][1].update(procedures=["future"]))
        project = self.read(".sdd/project.json")
        project["procedures"]["future"] = {**project["procedures"]["check"], "argv": ["python3", "checks/future.py"]}
        self.put(".sdd/project.json", project)
        self.approved()
        self.assign()
        self.config(lambda c: c["agent"]["implementer"]["permission"].update(bash={"*": "deny", "python3 checks/future.py": "ask"}))
        self.invalid("effective permissions")
        self.config(lambda c: c["agent"]["implementer"]["permission"].update(bash={"*": "deny"}))
        self.assertNotIn("python3 checks/future.py", sdd.evaluate(self.root)["authorization"]["commands"])

    def test_CA04_CA05_CA08_operational_capability_no_config_churn_or_automatic_closure(self):
        self.mutate(".sdd/project.json", lambda p: p.update(extensions={"runtime_grants": True}))
        project = sdd.project_contract(self.root)
        profile = sdd.permission_profile(project, runtime_grants=True)
        self.config(lambda c: [c["agent"][role].update(permission=permission) for role, permission in profile.items()])
        startup_bytes = (self.root / "opencode.json").read_bytes()
        self.assertTrue(sdd.evaluate(self.root)["valid"])  # ASK capability, no authority before approval.
        self.approved()
        self.assign()
        self.assertEqual(sdd.evaluate(self.root)["authorization"]["assignment"]["tasks"], ["T1"])
        demo.complete(self.root, "T1")
        self.assertEqual(sdd.evaluate(self.root)["authorization"]["status"], "revoked: completed")
        self.assign("T2")
        demo.complete(self.root, "T2")
        self.assertEqual(sdd.evaluate(self.root)["next"]["action"], "human close")
        demo.review_and_close(self.root)
        result = sdd.evaluate(self.root)
        self.assertEqual(result["features"][0]["action"], "done")
        self.assertEqual(result["authorization"]["write_paths"], [])
        self.assertEqual(startup_bytes, (self.root / "opencode.json").read_bytes())


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(cls(name) for cls in (Corrections, DispatchAdapter)
        for name in cls.__dict__ if name.startswith("test_"))
