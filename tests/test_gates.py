"""Additional CA-02/04/06/08 fail-closed boundary tests."""
from pathlib import Path
import json
from test_workflow import WorkflowTests, sdd, demo
import unittest


class GateTests(WorkflowTests):
    def test_CA06_REQ08_secret_artifact_never_hashed(self):
        self.approved()
        demo.complete(self.root, "T1")
        demo.text(self.root, ".env", "synthetic-only")
        self.mutate(".sdd/evidence/1-T1.json", lambda e: e.update(artifacts=[".env"]))
        self.invalid("secret input forbidden")

    def test_CA06_REQ08_unknown_method_and_unbounded_scope_rejected(self):
        self.mutate(".sdd/project.json", lambda p: p["procedures"]["check"].update(freshness_method="timestamp"))
        self.invalid("unknown core")

    def test_CA06_REQ08_scope_change_and_directory_add_delete(self):
        self.approved()
        demo.complete(self.root, "T1")
        (self.root / "src/empty").mkdir()
        self.assertEqual(sdd.evaluate(self.root)["next"]["completed"], [])
        (self.root / "src/empty").rmdir()
        self.assertEqual(sdd.evaluate(self.root)["next"]["completed"], ["T1"])
        self.mutate(".sdd/project.json", lambda p: p["procedures"]["check"].update(inputs=["src"]))
        self.assertEqual(sdd.evaluate(self.root)["next"]["completed"], [])

    def test_CA08_REQ11_failed_review_cannot_close(self):
        self.finished()
        self.mutate(".sdd/state.json", lambda st: st["features"][0].update(risk_tags=["high"]))
        demo.review_and_close(self.root, True)
        self.mutate(".sdd/progress/1-review.json", lambda r: r.update(verdict="CHANGES_REQUESTED"))
        self.invalid("review failed/stale")

    def test_CA08_REQ12_missing_CA_evidence_cannot_close(self):
        self.finished()
        demo.review_and_close(self.root)
        self.mutate(".sdd/progress/1.json", lambda p: p["tasks"]["T2"].update(evidence=[]))
        self.invalid("done gate failed")

    def test_CA02_REQ06_missing_capability_is_intervention(self):
        self.approved()
        self.mutate(".sdd/project.json", lambda p: p.update(capabilities=[]))
        result = sdd.evaluate(self.root)["next"]
        self.assertEqual(result["action"], "intervention")
        self.assertIn("python", result["reason"])

    def test_CA08_REQ12_altered_closure_confirmation(self):
        self.finished()
        demo.review_and_close(self.root)
        self.mutate(".sdd/closure-human.json", lambda c: c.update(text="changed confirmation"))
        self.invalid("closure confirmation altered")


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(GateTests(name) for name in GateTests.__dict__ if name.startswith("test_"))
