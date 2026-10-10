#!/usr/bin/env python3
"""Reproducible educational lifecycle; human/agent actions here are simulations."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import shutil
import sys

PACKAGE = Path(__file__).resolve().parents[2]
module = importlib.util.spec_from_file_location("sdd", PACKAGE / "sdd.py")
sdd = importlib.util.module_from_spec(module)
module.loader.exec_module(sdd)


def put(root, name, data):
    sdd.atomic(root, name, data)


def text(root, name, data):
    path = sdd.safe(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")


def metadata(root, name, data):
    text(root, "specs/notes/" + name, "# Notes - " + name + "\n\n```json\n" + json.dumps(data, indent=2) + "\n```\n\n"
         + {"requirements.md": "## Requirements\nREQ-01: The note SHALL remain readable.\nREQ-02: The check SHALL recognize the note.\n\n## Acceptance criteria\nCA-01: Given the note, when read, then it contains Sample.\nCA-02: Given the check, when executed, then it succeeds.\n\n## Traceability\nREQ-01 -> CA-01; REQ-02 -> CA-02.\n",
            "design.md": "## Architecture\nA synthetic text artifact and a local assertion.\n\n## Changes\nNo application framework.\n\n## Decisions\nBounded source/check scopes.\n",
            "tasks.md": "## Tasks\nT1: inspect the note. T2: validate the assertion. Owner: implementer.\n\n## Verification\nRun the declared check; record evidence separately.\n"}[name])


def prepare(root, layout="python-layout.json"):
    sdd.initialize(root)
    project = json.loads((PACKAGE / "tests/fixtures" / layout).read_text())
    put(root, ".sdd/project.json", project)
    for scope in project["source_roots"]:
        text(root, scope + "/sample.txt", "Sample\n")
    tool = project["procedures"]["check"]["environment_keys"][0]
    put(root, ".sdd/environment.json", {"schema_version": 1, "identities": {tool: "synthetic-current-v1"}})
    feature = {"id": 1, "name": "notes", "sdd": True, "status": "spec_ready", "depends_on": [],
               "spec_dir": "specs/notes", "spec_version": 1, "risk_tags": ["low"]}
    state = sdd.load(root, ".sdd/state.json")
    state["features"] = [feature]
    put(root, ".sdd/state.json", state)
    common = {"schema_version": 1, "feature": "RF-001", "version": 1}
    metadata(root, "requirements.md", {**common, "status": "ready", "requirements": ["REQ-01", "REQ-02"],
        "criteria": [{"id": "CA-01", "requirements": ["REQ-01"]}, {"id": "CA-02", "requirements": ["REQ-02"]}]})
    metadata(root, "design.md", {**common, "status": "current"})
    tasks = [{"id": "T" + str(n), "owner": "implementer", "depends_on": [] if n == 1 else ["T1"],
        "requirements": [f"REQ-0{n}"], "cas": [f"CA-0{n}"], "procedures": ["check"],
        "scope_reason": project["procedures"]["check"]["scope_reason"],
        "write_paths": [project["source_roots"][n - 1] + "/sample.txt"]} for n in (1, 2)]
    metadata(root, "tasks.md", {**common, "status": "current", "tasks": tasks})
    return feature


def human(root, purpose):
    state, features = sdd.state_contract(root)
    feature = features[1]
    current = sdd.spec(root, feature, sdd.project_contract(root), [])
    name = ".sdd/" + purpose + "-human.json"
    put(root, name, {"schema_version": 1, "actor": "human", "purpose": purpose, "feature": 1,
        "version": feature["spec_version"], "digest": current["digest"],
        "text": "SIMULATED human: explicitly " + purpose + " this synthetic feature", "date": "2026-10-09"})
    return name


def activate(root):
    state = sdd.load(root, ".sdd/state.json")
    state["features"][0]["status"] = "in_progress"
    state["active_feature"] = 1
    state["phase"] = "implementation"
    state["checkpoint"] = {"next_task": "T1", "sources": ["specs/notes/tasks.md"]}
    state["history"].append({"feature": 1, "from": "spec_ready", "to": "in_progress",
        "previous_phase": "planning", "phase": "implementation", "source": state["approvals"]["1"]})
    put(root, ".sdd/state.json", state)


def complete(root, tid, run_check=False):
    project = sdd.project_contract(root)
    state, features = sdd.state_contract(root)
    current = sdd.spec(root, features[1], project, [])
    if run_check:
        procedure = project["procedures"]["check"]
        outcome = subprocess.run(procedure["argv"], cwd=sdd.safe(root, procedure["cwd"]),
                                 timeout=procedure["timeout"], capture_output=True)
        assert outcome.returncode == 0
    else:
        # Tests use synthetic procedure outcomes, not claims of executing Rust/Python app suites.
        assert all(sdd.safe(root, scope + "/sample.txt").read_text() == "Sample\n"
                   for scope in project["source_roots"])
    artifact = ".sdd/results/1-" + tid + ".txt"
    text(root, artifact, "PASS: synthetic note assertion; no output/environment capture\n")
    manifest = sdd.manifest(root, project, "check")
    name = ".sdd/evidence/1-" + tid + ".json"
    put(root, name, {"schema_version": 1, "id": "1-" + tid, "feature": 1, "digest": current["digest"],
        "task": tid, "cas": current["tasks"][tid]["cas"], "kind": "automated", "outcome": "PASS",
        "procedure": "check", "artifacts": [artifact], "manifest": manifest, "fingerprint": sdd.sha(sdd.canonical(manifest))})
    path = ".sdd/progress/1.json"
    progress = sdd.load(root, path) if sdd.safe(root, path).exists() else {
        "schema_version": 1, "feature": 1, "tasks": {}, "handoff": "Synthetic completion", "sources": ["specs/notes/tasks.md"]}
    attempts = progress["tasks"].get(tid, {}).get("attempts", [])
    progress["tasks"][tid] = {"status": "completed", "attempts": attempts, "evidence": [name]}
    put(root, path, progress)


def review_and_close(root, review=False):
    result = sdd.evaluate(root)["next"]
    state = sdd.load(root, ".sdd/state.json")
    common = {"schema_version": 1, "feature": 1, "digest": result["digest"], "evidence_digest": result["evidence_digest"]}
    if review:
        name = ".sdd/progress/1-review.json"
        put(root, name, {**common, "actor": "verifier", "verdict": "APPROVED"})
        state["reviews"]["1"] = name
    ref = human(root, "closure")
    name = ".sdd/progress/1-closure.json"
    put(root, name, {**common, "confirmation_ref": ref, "confirmation_hash": sdd.sha(sdd.safe(root, ref).read_bytes())})
    state["closures"]["1"] = name
    state["block"] = None  # Resolved condition remains source-linked in history/resolution artifact.
    state["features"][0]["status"] = "done"
    state["active_feature"] = None
    state["phase"] = "closed"
    state["history"].append({"feature": 1, "from": "in_progress", "to": "done", "previous_phase": "implementation",
                             "phase": "closed", "source": name})
    put(root, ".sdd/state.json", state)


def cli(root, operation, expected=0, *extra):
    if (root / "sdd.py").exists():
        args = ["python3", "sdd.py", operation, "--root", "."]
        args += [*extra, "--json"] if operation == "approval" else ["--json", *extra]
        cwd = root
    else:
        args = [sys.executable, str(PACKAGE / "sdd.py"), operation, "--root", str(root), "--json", *extra]
        cwd = root.parent
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=10)
    assert result.returncode == expected, result.stdout + result.stderr
    return json.loads(result.stdout)


def run(root):
    assert not (root / ".sdd").exists(), "demo requires a clean existing root"
    cli(root, "init")
    prepare(root)
    # One-time startup adaptation: bounded helper + ASK capabilities, no future task grant.
    shutil.copy(PACKAGE / "sdd.py", root)
    shutil.copytree(PACKAGE / ".opencode", root / ".opencode")
    shutil.copytree(PACKAGE / "core", root / "core")
    # Simulated planner adapts a real bounded procedure, then human approves its exact bytes.
    project = sdd.project_contract(root)
    text(root, "checks/assert_note.py", "from pathlib import Path\nassert Path('src/sample.txt').read_text() == 'Sample\\n'\nassert Path('checks/sample.txt').read_text() == 'Sample\\n'\n")
    project["procedures"]["check"]["argv"] = ["python3", "checks/assert_note.py"]
    project["extensions"]["runtime_grants"] = True
    put(root, ".sdd/project.json", project)
    config = json.loads((PACKAGE / "opencode.json").read_text())
    for role, permissions in sdd.permission_profile(project, runtime_grants=True).items():
        config["agent"][role]["permission"] = permissions
    text(root, "opencode.json", json.dumps(config, indent=2))
    startup_config = (root / "opencode.json").read_bytes()
    put(root, ".sdd/environment.json", {"schema_version": 1, "identities": {"python": sys.version.split()[0]}})
    cli(root, "validate")
    ref = human(root, "approval")
    cli(root, "approval", 0, "--feature", "1", "--confirmation-ref", ref)
    activate(root)  # Simulated orchestrator action, NOT an automatic helper transition.
    assert cli(root, "status")["next"]["task"] == "T1"
    assign(root, "T1")
    # Retry intervention and explicit source-linked recovery, without deleting failures.
    attempts = [{"hypothesis": "h1", "change_ref": "src/sample.txt#1", "result": "FAIL", "progress": False},
                {"hypothesis": "h2", "change_ref": "src/sample.txt#2", "result": "FAIL", "progress": False}]
    put(root, ".sdd/progress/1.json", {"schema_version": 1, "feature": 1, "tasks": {"T1": {
        "status": "in_progress", "attempts": attempts, "evidence": []}}, "handoff": "Paused retry", "sources": ["specs/notes/tasks.md"]})
    paused = cli(root, "status")
    assert paused["next"]["action"] == "intervention" and paused["authorization"]["write_paths"] == []
    ref = ".sdd/retry-reset.json"
    put(root, ref, {"schema_version": 1, "actor": "human", "purpose": "retry_reset", "feature": 1, "task": "T1",
        "digest": paused["next"]["digest"], "after_attempt": 2, "attempts_digest": sdd.sha(sdd.canonical(attempts)),
        "source_ref": ".sdd/decisions.md", "text": "SIMULATED human: diagnosis resolved; retry budget rearmed", "date": "2026-10-09"})
    state = sdd.load(root, ".sdd/state.json")
    state["extensions"]["retry_resets"] = {"1:T1": [ref]}
    put(root, ".sdd/state.json", state)
    assert cli(root, "status")["next"]["task"] == "T1"
    complete(root, "T1", True)
    progress = sdd.load(root, ".sdd/progress/1.json")
    progress["tasks"]["T1"]["attempts"].append({"hypothesis": "h3", "change_ref": "checks/assert_note.py#3", "result": "PASS", "progress": True})
    put(root, ".sdd/progress/1.json", progress)
    assert progress["tasks"]["T1"]["attempts"][:2] == attempts
    assert cli(root, "status")["next"]["task"] == "T2"
    assert cli(root, "status")["authorization"]["status"] == "revoked: completed"
    assign(root, "T2")
    # Interruption: same bytes and same recommendation on a new helper invocation.
    state = sdd.load(root, ".sdd/state.json")
    state["features"][0]["status"] = "blocked"
    state["block"] = {"feature": 1, "previous_status": "in_progress", "previous_phase": "implementation",
                      "condition": "Human confirms local access restored", "resolution_ref": None}
    state["history"].append({"feature": 1, "from": "in_progress", "to": "blocked", "previous_phase": "implementation",
                             "phase": "implementation", "source": "specs/notes/tasks.md"})
    put(root, ".sdd/state.json", state)
    assert cli(root, "status")["next"]["action"] == "intervention"
    put(root, ".sdd/resolution.json", {"schema_version": 1, "actor": "human", "feature": 1,
        "condition": state["block"]["condition"], "text": "SIMULATED: access restored"})
    state["block"]["resolution_ref"] = ".sdd/resolution.json"
    state["features"][0]["status"] = "in_progress"
    state["history"].append({"feature": 1, "from": "blocked", "to": "in_progress", "previous_phase": "implementation",
                             "phase": "implementation", "source": ".sdd/resolution.json"})
    put(root, ".sdd/state.json", state)
    assert cli(root, "status")["next"]["task"] == "T2"
    text(root, "src/sample.txt", "Changed\n")
    # Old T2 is now dependency-ineligible: orchestrator clears its stale dispatch.
    state = sdd.load(root, ".sdd/state.json")
    state["extensions"].pop("assignment")
    put(root, ".sdd/state.json", state)
    assert cli(root, "validate", 1)["valid"] is False
    assert cli(root, "status")["next"]["task"] == "T1"
    text(root, "src/sample.txt", "Sample\n")
    # Exact-byte repair restores freshness; reuse the existing T1 result, do not rerun it.
    assert cli(root, "status")["next"]["task"] == "T2"
    assign(root, "T2")
    complete(root, "T2", True)
    assert cli(root, "status")["next"]["action"] == "human close"
    # Prove exact spec immutability, then restore bytes (no revision invented).
    path = root / "specs/notes/tasks.md"
    original = path.read_bytes()
    path.write_bytes(original + b"\n- [x] unauthorized edit\n")
    cli(root, "status", 1)
    path.write_bytes(original)
    # Risk tags are operational policy input: demonstrate conditional verifier path.
    state = sdd.load(root, ".sdd/state.json")
    state["features"][0]["risk_tags"] = ["high"]
    put(root, ".sdd/state.json", state)
    assert cli(root, "status")["next"]["action"] == "verify"
    review_and_close(root, True)  # Simulated verifier + explicit simulated human closure.
    cli(root, "validate")
    assert cli(root, "status")["features"][0]["action"] == "done"
    assert cli(root, "status")["authorization"]["write_paths"] == []
    assert (root / "opencode.json").read_bytes() == startup_config
    print("PASS: real CLI gates/checks; simulated planner, implementer, human, orchestrator and verifier records")


def assign(root, tid):
    """Simulated orchestrator persists a real read-only helper assignment certificate."""
    result = cli(root, "status", 0, "--profile", "--assigned-task", tid)
    assert result["authorization"]["status"] == "active"
    state = sdd.load(root, ".sdd/state.json")
    state.setdefault("extensions", {})["assignment"] = result["authorization"]["assignment"]
    put(root, ".sdd/state.json", state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    run(parser.parse_args().root.resolve())
