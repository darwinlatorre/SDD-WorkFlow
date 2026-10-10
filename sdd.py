#!/usr/bin/env python3
"""Small offline SDD consistency guard. Procedures are data, never executed."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile

KINDS = {"automated", "observable", "integration", "static"}
STATUSES = {"pending", "spec_ready", "revision_required", "in_progress", "blocked", "done"}
ROLES = ("orchestrator", "planner", "implementer", "verifier")
BUILTINS = ("build", "plan", "general", "explore", "scout")
SKILL_NAMES = ("auth0", "frontend-design", "codegraphcontext", "playwright-cli", "vercel-composition-patterns",
                  "vercel-react-best-practices", "vercel-react-native-skills")


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def decode(text):
    try:
        return json.loads(text, object_pairs_hook=pairs,
                          parse_constant=lambda x: require(False, "non-finite JSON: " + x))
    except json.JSONDecodeError as exc:
        raise Invalid("malformed JSON: " + str(exc)) from exc


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def hashable_path(root, name):
    path = safe(root, name)
    require(not any(part.startswith(".env") or re.search(r"secret|credential|token|password", part, re.I)
                    for part in Path(name).parts), "secret input forbidden: " + name)
    require(not path.is_symlink(), "unknown symlink scope: " + name)
    return path


def shape(value, fields, label, version=False):
    """Exact required field names/types; only extensions may be added."""
    require(type(value) is dict, label + ": expected object")
    expected = dict(fields)
    if version:
        expected["schema_version"] = int
    require(set(value) <= set(expected) | {"extensions"}, label + ": unknown core field")
    for key, typ in expected.items():
        require(key in value and type(value[key]) in (typ if type(typ) is tuple else (typ,)), label + ": invalid/missing " + key)
    if version:
        require(value["schema_version"] == 1, label + ": unsupported schema_version")
    require(type(value.get("extensions", {})) is dict, label + ": extensions must be object")
    return value


def strings(value, label, nonempty=False):
    require(type(value) is list and all(type(x) is str and x.strip() for x in value),
            label + ": expected string array")
    require(len(set(value)) == len(value), label + ": duplicate value")
    require(not nonempty or value, label + ": must not be empty")
    return value


def safe(root, name):
    require(type(name) is str and name and "\\" not in name and not Path(name).is_absolute()
            and ".." not in Path(name).parts and not any(c in name for c in "*?\x00"),
            "unsafe path: " + str(name))
    require(name == Path(name).as_posix(), "noncanonical path alias: " + name)
    path = root / name
    require(path.resolve().is_relative_to(root.resolve()), "path escapes root: " + name)
    require(path.resolve() == root.resolve() / name, "symlink alias path: " + name)
    return path


def bounded(root, name, write=False):
    path = safe(root, name)
    target = path.resolve().relative_to(root.resolve()).as_posix()
    protected = target == "." or target.split("/")[0] == ".sdd"
    if write:
        protected = protected or target.split("/")[0] in {"specs", ".opencode"} or target in {"sdd.py", "opencode.json", "opencode.jsonc"}
    require(not protected, "unbounded/protected " + ("write path: " if write else "scope: ") + name)
    return path


def load(root, name):
    path = safe(root, name)
    require(path.is_file(), "missing artifact: " + name)
    try:
        return decode(path.read_text(encoding="utf-8"))
    except UnicodeError as exc:
        raise Invalid("invalid UTF-8: " + name) from exc


def atomic(root, name, value):
    path = safe(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = stream.name
        stream.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False).encode() + b"\n")
    try:
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def cycle(nodes, label):
    visited, visiting = set(), set()

    def visit(node):
        require(node in nodes, label + ": dangling dependency " + str(node))
        require(node not in visiting, label + ": dependency cycle " + str(node))
        if node in visited:
            return
        visiting.add(node)
        for dependency in nodes[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)
    for node in nodes:
        visit(node)


def ids(values, prefix, label):
    strings(values, label, True)
    require(all(re.fullmatch(prefix + r"-\d{2,}", x) and int(x.split("-")[1]) > 0
                for x in values), label + ": malformed ID")
    return set(values)


def spec(root, feature, project, retired):
    docs, digest = {}, hashlib.sha256()
    for name in ("requirements.md", "design.md", "tasks.md"):
        path = safe(root, feature["spec_dir"] + "/" + name)
        require(path.is_file(), "missing spec: " + str(path.relative_to(root)))
        data = path.read_bytes()
        for item in (name.encode(), data):
            digest.update(len(item).to_bytes(8, "big"))
            digest.update(item)
        blocks = re.findall(r"^```json\s*\n(.*?)^```\s*$", data.decode("utf-8"), re.M | re.S)
        require(len(blocks) == 1, name + ": exactly one JSON fenced metadata block required")
        meta = decode(blocks[0])
        fields = {"feature": str, "version": int, "status": str}
        if name == "requirements.md":
            fields.update(requirements=list, criteria=list)
        if name == "tasks.md":
            fields["tasks"] = list
        shape(meta, fields, name, True)
        require(meta["feature"] == f'RF-{feature["id"]:03d}', name + ": wrong RF ID")
        require(meta["version"] == feature["spec_version"] > 0, name + ": version mismatch")
        require(meta["status"] == ("ready" if name == "requirements.md" else "current"),
                name + ": not current/ready")
        docs[name] = meta
    req = docs["requirements.md"]
    reqs = ids(req["requirements"], "REQ", "requirements")
    cas = {}
    for ca in req["criteria"]:
        shape(ca, {"id": str, "requirements": list}, "criterion")
        ids([ca["id"]], "CA", "criterion")
        require(ca["id"] not in cas, "duplicate CA ID: " + ca["id"])
        links = ids(ca["requirements"], "REQ", ca["id"])
        require(links <= reqs, ca["id"] + ": dangling REQ")
        cas[ca["id"]] = links
    require(cas and set().union(*cas.values()) == reqs, "uncovered REQ")
    require(not (reqs | set(cas)) & set(retired), "retired ID reused")
    tasks = {}
    for task in docs["tasks.md"]["tasks"]:
        shape(task, {"id": str, "owner": str, "depends_on": list, "requirements": list,
                     "cas": list, "procedures": list, "scope_reason": str, "write_paths": list}, "task")
        tid = task["id"]
        require(re.fullmatch(r"T[1-9]\d*", tid) and tid not in tasks, "malformed/duplicate task ID: " + tid)
        require(task["owner"] == "implementer", tid + ": invalid owner")
        for key in ("depends_on", "requirements", "cas", "procedures", "write_paths"):
            strings(task[key], tid + ": " + key, key in {"requirements", "cas", "procedures"})
        require(set(task["requirements"]) <= reqs and set(task["cas"]) <= set(cas), tid + ": dangling coverage")
        require(set().union(*(cas[x] for x in task["cas"])) <= set(task["requirements"]), tid + ": incomplete CA links")
        for pid in task["procedures"]:
            require(pid in project["procedures"], tid + ": missing procedure " + pid)
            require(task["scope_reason"] == project["procedures"][pid]["scope_reason"] and task["scope_reason"].strip(),
                    tid + ": missing approved complete scope justification")
        for name in task["write_paths"]:
            bounded(root, name, write=True)
        tasks[tid] = task
    require(tasks and set().union(*(set(t["cas"]) for t in tasks.values())) == set(cas), "uncovered CA")
    require(set().union(*(set(t["requirements"]) for t in tasks.values())) == reqs, "REQ without task")
    cycle({tid: t["depends_on"] for tid, t in tasks.items()}, "task")
    return {"digest": digest.hexdigest(), "tasks": tasks, "cas": cas,
            "sources": [feature["spec_dir"] + "/" + n for n in docs]}


def project_contract(root):
    project = shape(load(root, ".sdd/project.json"), {"name": str, "source_roots": list,
        "capabilities": list, "procedures": dict, "environment_ref": str, "risk_policy": dict,
        "one_feature_at_a_time": bool, "implementation_paths": list, "implementation_commands": list}, "project", True)
    require(project["name"].strip(), "project: empty name")
    for key in ("source_roots", "capabilities", "implementation_paths", "implementation_commands"):
        strings(project[key], "project: " + key)
    safe(root, project["environment_ref"])
    for name in project["source_roots"] + project["implementation_paths"]:
        bounded(root, name, write=True)
    policy = shape(project["risk_policy"], {"known_tags": list, "review_required_for": list}, "risk policy")
    strings(policy["known_tags"], "known_tags")
    strings(policy["review_required_for"], "review_required_for")
    require(set(policy["review_required_for"]) <= set(policy["known_tags"]), "risk policy: unknown review tag")
    for pid, procedure in project["procedures"].items():
        require(re.fullmatch(r"[a-zA-Z0-9_-]+", pid), "invalid procedure ID")
        shape(procedure, {"kind": str, "argv": list, "cwd": str, "inputs": list,
                         "environment_keys": list, "timeout": int, "expected": str,
                         "scope_reason": str, "capabilities": list}, "procedure " + pid)
        require(procedure["kind"] in KINDS and procedure["timeout"] > 0 and procedure["expected"].strip(), "invalid procedure " + pid)
        for key in ("argv", "inputs", "environment_keys", "capabilities"):
            strings(procedure[key], pid + ": " + key, key in {"argv", "inputs", "environment_keys"})
        safe(root, procedure["cwd"])
        for name in procedure["inputs"]:
            bounded(root, name)
    return project


def manifest(root, project, pid):
    """Return authoritative current local inputs, or raise unknown freshness."""
    require(pid in project["procedures"], "unknown procedure")
    procedure = project["procedures"][pid]
    env = shape(load(root, project["environment_ref"]), {"identities": dict}, "environment", True)
    identities = {}
    for key in procedure["environment_keys"]:
        value = env["identities"].get(key)
        require(type(value) is str and value.strip() and value != "unknown", "unknown environment identity: " + key)
        require(not re.search(r"secret|token|password|credential|api.?key", key, re.I), "secret identity forbidden")
        identities[key] = value
    files = {}
    for scope in sorted(procedure["inputs"]):
        base = bounded(root, scope)
        require(base.exists(), "unknown missing input scope: " + scope)
        paths = [base] + (sorted(base.rglob("*")) if base.is_dir() else [])
        for path in paths:
            name = path.relative_to(root).as_posix()
            hashable_path(root, name)
            require(path.is_file() or path.is_dir(), "unknown unsupported input: " + name)
            files[name] = "directory" if path.is_dir() else sha(path.read_bytes())
    return {"procedure": procedure, "identities": identities, "scopes": sorted(procedure["inputs"]), "files": dict(sorted(files.items()))}


def confirmation(root, name, feature, digest, purpose):
    value = shape(load(root, name), {"actor": str, "purpose": str, "feature": int,
        "version": int, "digest": str, "text": str, "date": str}, "confirmation " + name, True)
    require(value["actor"] == "human" and value["purpose"] == purpose and value["text"].strip(), "explicit human " + purpose + " required")
    require(value["feature"] == feature["id"] and value["version"] == feature["spec_version"]
            and value["digest"] == digest, "stale confirmation " + name)
    try:
        datetime.date.fromisoformat(value["date"])
    except ValueError as exc:
        raise Invalid("invalid confirmation date") from exc
    return value, sha(safe(root, name).read_bytes())


def approval_valid(root, state, feature, current):
    ref = state["approvals"].get(str(feature["id"]))
    require(type(ref) is str, "approval missing")
    record = shape(load(root, ref), {"feature": int, "version": int, "digest": str,
        "confirmation_ref": str, "confirmation_hash": str, "actor": str, "date": str}, "approval", True)
    require(record["actor"] == "human" and record["feature"] == feature["id"]
            and record["version"] == feature["spec_version"] and record["digest"] == current["digest"], "approval stale spec/version")
    confirm, checksum = confirmation(root, record["confirmation_ref"], feature, current["digest"], "approval")
    require(checksum == record["confirmation_hash"] and record["date"] == confirm["date"], "approval confirmation altered")


def retry(attempts, tid, root=None, feature=None, digest=None, reset_refs=()):
    resets = {}
    for ref in reset_refs:
        record = shape(load(root, ref), {"actor": str, "purpose": str, "feature": int,
            "task": str, "digest": str, "after_attempt": int, "attempts_digest": str,
            "source_ref": str, "text": str, "date": str}, "retry reset", True)
        position = record["after_attempt"]
        require(record["actor"] == "human" and record["purpose"] == "retry_reset" and record["text"].strip(), "explicit human retry reset required")
        require(record["feature"] == feature and record["task"] == tid and record["digest"] == digest,
                "stale/wrong retry reset")
        require(2 <= position <= len(attempts) and position not in resets and
                record["attempts_digest"] == sha(canonical(attempts[:position])), "retry reset history/prefix mismatch")
        require(safe(root, record["source_ref"]).is_file(), "retry reset source missing")
        try:
            datetime.date.fromisoformat(record["date"])
        except ValueError as exc:
            raise Invalid("invalid retry reset date") from exc
        resets[position] = record
    previous = None
    streak = 0
    for position, attempt in enumerate(attempts, 1):
        require(streak < 2, tid + ": retry budget exhausted; intervention required before more work")
        shape(attempt, {"hypothesis": str, "change_ref": str, "result": str, "progress": bool}, tid + ": attempt")
        require(all(attempt[x].strip() for x in ("hypothesis", "change_ref", "result")), tid + ": incomplete attempt")
        if previous and not previous["progress"]:
            require(previous["hypothesis"] != attempt["hypothesis"] and previous["change_ref"] != attempt["change_ref"], tid + ": unchanged retry refused")
        streak = 0 if attempt["progress"] else streak + 1
        previous = attempt
        if position in resets:
            require(streak == 2, tid + ": retry reset requires exhausted budget")
            streak, previous = 0, None
    return streak >= 2


def evidence(root, ref, feature, current, project, task):
    record = shape(load(root, ref), {"id": str, "feature": int, "digest": str, "task": str,
        "cas": list, "kind": str, "outcome": str, "procedure": str, "artifacts": list,
        "manifest": dict, "fingerprint": str}, "evidence " + ref, True)
    strings(record["cas"], "evidence CAs", True)
    strings(record["artifacts"], "evidence artifacts", True)
    require(record["id"].strip() and record["feature"] == feature["id"] and record["task"] == task["id"], "evidence wrong feature/task")
    require(set(record["cas"]) <= set(task["cas"]) and record["procedure"] in task["procedures"], "evidence dangling CA/procedure")
    require(record["kind"] in KINDS and record["kind"] == project["procedures"][record["procedure"]]["kind"], "evidence wrong kind")
    require(record["outcome"] in {"PASS", "FAIL", "BLOCKED"}, "invalid evidence outcome")
    artifacts = {name: sha(hashable_path(root, name).read_bytes()) for name in record["artifacts"] if hashable_path(root, name).is_file()}
    require(len(artifacts) == len(record["artifacts"]), "missing evidence artifact")
    payload = {"record": record, "artifacts": artifacts}
    if record["digest"] != current["digest"]:
        return record, payload, "stale spec digest"
    if record["outcome"] != "PASS":
        return record, payload, "outcome " + record["outcome"]
    try:
        now = manifest(root, project, record["procedure"])
    except Invalid as exc:
        return record, payload, "unknown freshness: " + str(exc)
    if sha(canonical(record["manifest"])) != record["fingerprint"] or now != record["manifest"]:
        return record, payload, "stale code/environment/procedure or scope membership"
    return record, payload, "fresh: complete scoped inputs unchanged; unrelated inputs excluded"


def completions(root, feature, current, project, reset_registry=None):
    ref = f'.sdd/progress/{feature["id"]}.json'
    referenced = {key.split(":")[1] for key in (reset_registry or {}) if key.startswith(str(feature["id"]) + ":")}
    if not safe(root, ref).exists():
        require(not referenced, "retry reset history missing")
        return set(), [], {}, [], []
    progress = shape(load(root, ref), {"feature": int, "tasks": dict, "handoff": str, "sources": list}, "progress", True)
    require(progress["feature"] == feature["id"] and set(progress["tasks"]) <= set(current["tasks"]), "progress dangling feature/task")
    require(referenced <= set(progress["tasks"]), "retry reset history task missing")
    strings(progress["sources"], "progress sources")
    for name in progress["sources"]:
        safe(root, name)
    done, payloads, checks, pauses, seen = set(), [], {}, [], set()
    valid_cas = set()
    for tid, entry in sorted(progress["tasks"].items()):
        shape(entry, {"status": str, "attempts": list, "evidence": list}, "progress " + tid)
        require(entry["status"] in {"pending", "in_progress", "completed"}, "invalid task status")
        strings(entry["evidence"], tid + ": evidence")
        refs = (reset_registry or {}).get(f'{feature["id"]}:{tid}', [])
        strings(refs, "retry reset references")
        if retry(entry["attempts"], tid, root, feature["id"], current["digest"], refs):
            pauses.append(tid + ": two no-progress outcomes; human intervention required")
        covered, procedures = set(), set()
        for name in entry["evidence"]:
            record, payload, reason = evidence(root, name, feature, current, project, current["tasks"][tid])
            require(record["id"] not in seen, "duplicate evidence ID: " + record["id"])
            seen.add(record["id"])
            payloads.append(payload)
            checks[name] = reason
            if reason.startswith("fresh:"):
                covered.update(record["cas"])
                valid_cas.update(record["cas"])
                procedures.add(record["procedure"])
        if (entry["status"] == "completed" and covered >= set(current["tasks"][tid]["cas"])
                and procedures >= set(current["tasks"][tid]["procedures"])):
            done.add(tid)
    # Effective completion is dependency-closed, regardless of claimed statuses.
    while any(not set(current["tasks"][tid]["depends_on"]) <= done for tid in done):
        done = {tid for tid in done if set(current["tasks"][tid]["depends_on"]) <= done}
    return done, payloads, checks, pauses, sorted(valid_cas)


def closure_gates(root, state, feature, current, evidence_digest, needs_review):
    key = str(feature["id"])
    if needs_review:
        ref = state["reviews"].get(key)
        require(type(ref) is str, "required verifier review missing")
        record = shape(load(root, ref), {"feature": int, "digest": str, "evidence_digest": str,
                                      "actor": str, "verdict": str}, "review", True)
        require(record["feature"] == feature["id"] and record["digest"] == current["digest"]
                and record["evidence_digest"] == evidence_digest and record["actor"] == "verifier"
                and record["verdict"] == "APPROVED", "required review failed/stale")
    ref = state["closures"].get(key)
    require(type(ref) is str, "explicit human closure missing")
    record = shape(load(root, ref), {"feature": int, "digest": str, "evidence_digest": str,
        "confirmation_ref": str, "confirmation_hash": str}, "closure", True)
    require(record["feature"] == feature["id"] and record["digest"] == current["digest"]
            and record["evidence_digest"] == evidence_digest, "closure stale")
    _, checksum = confirmation(root, record["confirmation_ref"], feature, current["digest"], "closure")
    require(checksum == record["confirmation_hash"], "closure confirmation altered")


def state_contract(root):
    state = shape(load(root, ".sdd/state.json"), {"project_ref": str, "features": list,
        "active_feature": (int, type(None)), "phase": str, "checkpoint": dict,
        "block": (dict, type(None)), "approvals": dict, "reviews": dict, "closures": dict,
        "history": list, "retired_ids": dict}, "state", True)
    # shape accepts tuples as explicit unions without accepting bool as int.
    require(state["project_ref"] == ".sdd/project.json", "wrong project reference")
    shape(state["checkpoint"], {"next_task": (str, type(None)), "sources": list}, "checkpoint")
    strings(state["checkpoint"]["sources"], "checkpoint sources")
    for source in state["checkpoint"]["sources"]:
        safe(root, source)
    features = {}
    for feature in state["features"]:
        shape(feature, {"id": int, "name": str, "sdd": bool, "status": str, "depends_on": list,
            "spec_dir": str, "spec_version": int, "risk_tags": list}, "feature")
        fid = feature["id"]
        require(fid > 0 and fid not in features, "duplicate/invalid feature ID")
        require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", feature["name"]), "unsafe feature name")
        require(feature["name"] not in [x["name"] for x in features.values()], "duplicate feature name")
        require(feature["status"] in STATUSES and feature["spec_version"] > 0, "invalid feature status/version")
        require(feature["spec_dir"] == "specs/" + feature["name"], "wrong spec directory")
        require(all(type(x) is int and x > 0 for x in feature["depends_on"])
                and len(set(feature["depends_on"])) == len(feature["depends_on"]), "invalid feature dependencies")
        strings(feature["risk_tags"], "risk_tags")
        features[fid] = feature
    cycle({fid: f["depends_on"] for fid, f in features.items()}, "feature")
    require(state["active_feature"] is None or state["active_feature"] in features, "dangling active feature")
    for mapping in (state["approvals"], state["reviews"], state["closures"]):
        for key, ref in mapping.items():
            require(key in {str(x) for x in features}, "dangling gate feature")
            safe(root, ref)
    for key, registry in state["retired_ids"].items():
        require(key in {str(x) for x in features}, "dangling retired registry")
        strings(registry, "retired IDs")
        require(all(re.fullmatch(r"(?:REQ|CA)-\d{2,}", x) for x in registry), "malformed retired ID")
    transitions = {"pending": {"spec_ready", "blocked"}, "spec_ready": {"in_progress", "revision_required", "blocked"},
        "revision_required": {"spec_ready", "blocked"}, "in_progress": {"done", "revision_required", "blocked"},
        "done": {"revision_required"}, "blocked": STATUSES - {"blocked", "done"}}
    last = {}
    for entry in state["history"]:
        shape(entry, {"feature": int, "from": str, "to": str, "previous_phase": str, "phase": str, "source": str}, "history")
        require(entry["feature"] in features and entry["to"] in transitions.get(entry["from"], set()), "invalid transition")
        if entry["feature"] in last:
            require(last[entry["feature"]] == entry["from"], "inconsistent transition history")
        require(safe(root, entry["source"]).is_file(), "missing transition source")
        last[entry["feature"]] = entry["to"]
    require(all(features[fid]["status"] == status for fid, status in last.items()), "history/current state mismatch")
    return state, features


def evaluate(root, assigned_tasks=None, include_profile=False, helper_access=True, runtime_grants=False):
    project = project_contract(root)
    state, features = state_contract(root)
    active = [fid for fid, f in features.items() if f["status"] in {"in_progress", "blocked"}]
    require(not project["one_feature_at_a_time"] or len(active) <= 1, "single-active-feature conflict")
    require(not active or state["active_feature"] in active, "active feature missing/conflicting")
    if state["block"] is not None:
        block = shape(state["block"], {"feature": int, "previous_status": str, "previous_phase": str,
                                      "condition": str, "resolution_ref": (str, type(None))}, "block")
        require(block["feature"] in features and state["active_feature"] == block["feature"]
                and block["previous_status"] in STATUSES - {"blocked", "done"} and block["condition"].strip(), "invalid preserved block")
        feature = features[block["feature"]]
        if feature["status"] != "blocked":
            require(feature["status"] == block["previous_status"] and state["phase"] == block["previous_phase"], "resume must restore status/phase")
            require(block["resolution_ref"] is not None, "block resolution missing")
            resolution = load(root, block["resolution_ref"])
            shape(resolution, {"actor": str, "feature": int, "condition": str, "text": str}, "resolution", True)
            require(resolution["actor"] == "human" and resolution["feature"] == feature["id"]
                    and resolution["condition"] == block["condition"] and resolution["text"].strip(), "unconfirmed block resolution")
    require(all(f["status"] != "blocked" or state["block"] is not None and state["block"]["feature"] == fid
                for fid, f in features.items()), "blocked state lost prior status/phase")
    results = {}
    for fid, feature in sorted(features.items()):
        status = feature["status"]
        result = {"feature": fid, "action": "plan", "sources": [feature["spec_dir"]], "checks": {}, "completed": []}
        if status == "blocked" and state["block"]["previous_status"] in {"pending", "spec_ready", "revision_required"}:
            result.update(action="intervention", reason=state["block"]["condition"], preserved=state["block"])
            results[fid] = result
            continue
        if status in {"pending", "revision_required"}:
            results[fid] = result
            continue
        current = spec(root, feature, project, state["retired_ids"].get(str(fid), []))
        result.update(digest=current["digest"], sources=current["sources"])
        if status == "spec_ready":
            result["action"] = "approve"
            results[fid] = result
            continue
        approval_valid(root, state, feature, current)
        require(all(features[dep]["status"] == "done" for dep in feature["depends_on"]), "feature dependencies not done")
        registry = state.get("extensions", {}).get("retry_resets", {})
        require(type(registry) is dict, "retry reset registry must be object")
        for key, refs in registry.items():
            require(re.fullmatch(r"[1-9]\d*:T[1-9]\d*", key) and int(key.split(":")[0]) in features,
                    "dangling retry reset task/feature")
            strings(refs, "retry reset references")
            if key.startswith(str(fid) + ":"):
                require(key.split(":")[1] in current["tasks"], "dangling retry reset task")
        done, payloads, checks, pauses, covered = completions(root, feature, current, project, registry)
        edigest = sha(canonical(payloads))
        result.update(completed=sorted(done), checks=checks, evidence_digest=edigest)
        result["sources"].extend(ref for key, refs in registry.items() if key.startswith(str(fid) + ":") for ref in refs)
        policy = project["risk_policy"]
        unknown_risk = not feature["risk_tags"] or not set(feature["risk_tags"]) <= set(policy["known_tags"])
        needs_review = bool(set(feature["risk_tags"]) & set(policy["review_required_for"]))
        if status == "blocked":
            result.update(action="intervention", reason=state["block"]["condition"], preserved=state["block"])
        elif pauses or unknown_risk:
            result.update(action="intervention", reason="; ".join(pauses) or "unknown risk; review/intervention required")
        elif done != set(current["tasks"]) or set(covered) != set(current["cas"]):
            eligible = [tid for tid, task in sorted(current["tasks"].items()) if tid not in done and set(task["depends_on"]) <= done]
            require(eligible, "no eligible task")
            result["eligible_tasks"] = eligible
            tid = eligible[0]
            task = current["tasks"][tid]
            missing = sorted(set().union(*(set(project["procedures"][p]["capabilities"]) for p in task["procedures"])) - set(project["capabilities"]))
            unknown = [x for x in checks.values() if x.startswith("unknown")]
            if missing or unknown:
                result.update(action="intervention", reason="missing capabilities: " + ",".join(missing) if missing else "; ".join(unknown))
            else:
                result.update(action="implement", task=tid, procedures=task["procedures"])
        else:
            try:
                closure_gates(root, state, feature, current, edigest, needs_review)
                result["action"] = "done" if status == "done" else "human close"
            except Invalid as exc:
                result.update(action="verify" if "review" in str(exc) else "human close", reason=str(exc))
        if status == "done":
            require(result["action"] == "done", "done gate failed: " + result.get("reason", "incomplete/stale evidence"))
            require(any(x["feature"] == fid and x["to"] == "done" for x in state["history"]), "done transition history missing")
        results[fid] = result
    selected = state["active_feature"]
    if selected is None:
        selected = next((fid for fid, f in sorted(features.items()) if f["status"] != "done"
                         and all(features[x]["status"] == "done" for x in f["depends_on"])), None)
    dispatch = authorization(root, project, state, features, results, assigned_tasks)
    if safe(root, "opencode.json").exists() or safe(root, ".opencode").exists():
        adapter(root, project, state, results, dispatch)
    result = {"valid": True, "next": results.get(selected, {"action": "plan", "sources": [".sdd/state.json"]}),
              "features": [results[x] for x in sorted(results)], "authorization": dispatch}
    if include_profile:
        result["permission_profile"] = permission_profile(project, dispatch, helper_access, runtime_grants)
        result["profile_note"] = "Read-only recommendation; config loads at startup, not hot reload. Runtime asks are capabilities, dispatch scope is the operational grant."
    return result


def authorization(root, project, state, features, results, assigned_tasks=None):
    """Read-only dispatch certificate; authority to persist it belongs to orchestrator."""
    record = state.get("extensions", {}).get("assignment")
    active = state["active_feature"]
    if assigned_tasks is not None:
        strings(assigned_tasks, "assigned tasks", True)
        require(active in features and results[active]["action"] == "implement", "assignment requires approved executable work")
        require(set(assigned_tasks) <= set(results[active]["eligible_tasks"]),
                "assignment includes unknown task, completed or dependency-ineligible task")
        record = {"feature": active, "digest": results[active]["digest"], "tasks": sorted(assigned_tasks),
                  "sources": [features[active]["spec_dir"] + "/tasks.md"]}
        record["id"] = sha(canonical(record))[:24]
    empty = {"assignment": record, "status": "inactive", "write_paths": [], "procedures": [], "commands": [], "context_paths": []}
    if record is None:
        # Old project-level requests are not an implicit assignment.
        if active in features:
            require(not project["implementation_paths"] and not project["implementation_commands"],
                    "assignment required; implementation permissions before approval or dispatch")
        return empty
    shape(record, {"id": str, "feature": int, "digest": str, "tasks": list, "sources": list}, "assignment")
    strings(record["tasks"], "assigned tasks", True)
    strings(record["sources"], "assignment sources", True)
    require(record["id"] == sha(canonical({k: record[k] for k in ("feature", "digest", "tasks", "sources")}))[:24], "assignment ID/content mismatch")
    fid = record["feature"]
    require(fid in features and record["digest"] == results[fid].get("digest"), "stale assignment feature/spec")
    require(record["sources"] == [features[fid]["spec_dir"] + "/tasks.md"], "assignment source mismatch")
    current = spec(root, features[fid], project, state["retired_ids"].get(str(fid), []))
    require(set(record["tasks"]) <= set(current["tasks"]), "assignment unassigned/unknown task")
    result = results[fid]
    if set(record["tasks"]) <= set(result["completed"]):
        empty["status"] = "revoked: completed"
        return empty
    # Blocks, retry pauses, reviews and closure revoke dispatch capability without a state write.
    if fid != active or result["action"] != "implement":
        empty["status"] = "revoked: no executable work"
        return empty
    require(set(record["tasks"]) <= set(result["eligible_tasks"]), "assignment includes completed or dependency-ineligible task")
    tasks = [current["tasks"][tid] for tid in record["tasks"]]
    paths = sorted(set().union(*(set(t["write_paths"]) for t in tasks)))
    procedures = sorted(set().union(*(set(t["procedures"]) for t in tasks)))
    require(set().union(*(set(project["procedures"][pid]["capabilities"]) for pid in procedures)) <= set(project["capabilities"]),
            "assignment missing procedure capability")
    commands = sorted({shlex.join(project["procedures"][pid]["argv"]) for pid in procedures})
    require(set(project["implementation_paths"]) <= set(paths), "adapter implementation paths exceed assigned tasks")
    require(set(project["implementation_commands"]) <= set(commands), "adapter commands exceed assigned procedures")
    context = [f".sdd/progress/{fid}.json"]
    for tid in record["tasks"]:
        context.extend([f".sdd/evidence/{fid}-{tid}.json", f".sdd/evidence/{fid}-{tid}-*.json", f".sdd/results/{fid}-{tid}.*"])
    return {"assignment": record, "status": "active", "write_paths": paths, "procedures": procedures,
            "commands": commands, "context_paths": context}


HELPER_COMMANDS = (
    "python3 sdd.py status --root . --json",
    "python3 sdd.py validate --root . --json",
    "python3 sdd.py status --root . --json --profile",
    "python3 sdd.py status --root . --json --profile --assigned-task *",
    "python3 sdd.py status --root . --json --profile --runtime-grants",
    "python3 sdd.py status --root . --json --profile --runtime-grants --assigned-task *",
    "python3 sdd.py approval --root . --feature * --confirmation-ref .sdd/approval-human.json --json",
)


def runtime_capabilities(root, project):
    """Startup ASK envelope, never an automatic dispatch grant."""
    paths = [name + "/*" for name in project["source_roots"] if bounded(root, name, True)]
    paths += [".sdd/progress/*.json", ".sdd/evidence/*", ".sdd/results/*"]
    commands = sorted({shlex.join(p["argv"]) for p in project["procedures"].values()})
    return paths, commands


def permission_profile(project, dispatch=None, helper_access=True, runtime_grants=False):
    read = {"*": "allow", "*.env": "deny", "*.env.*": "deny"}
    base = {"*": "deny", "read": read, "glob": "allow", "grep": "allow", "question": "allow",
            "skill": {"*": "deny", **{name: "allow" for name in SKILL_NAMES}}}
    profiles = {role: dict(base) for role in ROLES}
    profiles["orchestrator"].update(edit={"*": "deny", ".sdd/*": "allow", ".sdd/evidence/*": "deny",
        ".sdd/progress/*.json": "deny", ".sdd/progress/*-review.json": "allow", ".sdd/progress/*-closure.json": "allow"},
        task={"*": "deny", "planner": "allow", "implementer": "allow", "verifier": "allow"},
        bash={"*": "deny", **{command: "allow" for command in HELPER_COMMANDS}} if helper_access else "deny")
    profiles["orchestrator"]["edit"]["opencode.json"] = "allow"
    profiles["planner"]["edit"] = {"*": "deny", "specs/*": "allow"}
    edit = {"*": "deny"}
    dispatch = dispatch or {"write_paths": [], "context_paths": [], "commands": []}
    if runtime_grants:
        # Config is loaded once: ASK is a capability to request a runtime grant,
        # not permission to implement future tasks. The certificate stays task-exact.
        for name in project["source_roots"]:
            edit[name + "/*"] = "ask"
        for name in (".sdd/progress/*.json", ".sdd/evidence/*", ".sdd/results/*"):
            edit[name] = "ask"
        for name in (".sdd/progress/*-review.json", ".sdd/progress/*-closure.json"):
            edit[name] = "deny"
    else:
        for name in dispatch["write_paths"] + dispatch["context_paths"]:
            edit[name] = "allow"
    profiles["implementer"]["edit"] = edit
    commands = (sorted({shlex.join(p["argv"]) for p in project["procedures"].values()})
                if runtime_grants else dispatch["commands"])
    profiles["implementer"]["bash"] = {"*": "deny", **{command: "ask" for command in commands}}
    return profiles


def matches(pattern, value):
    return re.fullmatch(re.escape(pattern).replace(r"\*", ".*").replace(r"\?", "."), value) is not None


def effective(rules, value, default="deny"):
    if type(rules) is str:
        return rules
    result = default
    for pattern, action in rules.items():
        if matches(pattern, value):
            result = action
    return result


def permissions(root, role, value, project, dispatch):
    require(type(value) is dict and value.get("*") == "deny", "adapter effective permissions require default deny: " + role)
    safe_tools = {"read", "glob", "grep", "question"}
    capabilities, cap_commands = runtime_capabilities(root, project)
    runtime_grants = project.get("extensions", {}).get("runtime_grants", False)
    require(type(runtime_grants) is bool, "runtime_grants must be explicit boolean")
    profile = permission_profile(project, dispatch)[role]
    edit_allow = set(dispatch["write_paths"] + dispatch["context_paths"]) if role == "implementer" else {
        key for key, action in profile.get("edit", {}).items() if action == "allow"}
    for tool, rule in value.items():
        require(type(rule) in {str, dict}, "adapter invalid permission field: " + role)
        if type(rule) is dict:
            require(all(type(p) is str and type(a) is str and a in {"allow", "ask", "deny"} for p, a in rule.items()), "adapter invalid permission action")
            require(rule.get("*") == "deny" or tool == "read", "adapter effective permissions missing catch-all deny: " + role)
        else:
            require(rule in {"allow", "ask", "deny"}, "adapter invalid permission action")
        if tool == "*" or tool in safe_tools:
            continue
        rules = rule if type(rule) is dict else {"*": rule}
        for pattern, action in rules.items():
            if action == "deny":
                continue
            valid = False
            if tool == "edit":
                valid = pattern in edit_allow and action == "allow"
                if role == "implementer" and action == "ask":
                    valid = pattern in edit_allow or runtime_grants and pattern in capabilities
            if tool == "bash":
                valid = role == "orchestrator" and pattern in HELPER_COMMANDS
                if role == "implementer":
                    valid = action == "ask" and pattern in (cap_commands if runtime_grants else dispatch["commands"])
                    require(not any(c in pattern for c in "*?\n"), "adapter unbounded procedure command pattern")
            if tool == "task":
                valid = role == "orchestrator" and pattern in {"planner", "implementer", "verifier"}
            if tool == "skill":
                valid = pattern in SKILL_NAMES and action == "allow"
            require(valid, "adapter incompatible effective permissions: " + role + ": " + tool + " " + pattern)
    # Rule order matters: check protected targets, not equality to the starter.
    edit = value.get("edit", "deny")
    probes = [".sdd/state.json", "opencode.json", "sdd.py", "specs/notes/tasks.md", "src/future.txt",
              ".sdd/progress/1-review.json", ".sdd/progress/1-closure.json"]
    for name in probes:
        action = effective(edit, name)
        expected = effective(profile.get("edit", "deny"), name)
        if role == "implementer" and action == "ask":
            require(any(matches(p, name) for p in capabilities) and not name.endswith(("-review.json", "-closure.json")), "adapter protected runtime grant: " + name)
        else:
            require(action == "deny" or expected == "allow", "adapter wildcard permission overrides protected path: " + role)
    read = value.get("read", "deny")
    require(all(effective(read, name) == "deny" for name in (".env", "src/.env", "src/service.env.key")), "adapter secret read permission override")
    skills = value.get("skill", "deny")
    require(type(skills) is dict and skills.get("*") == "deny" and
            all(effective(skills, name) == "allow" for name in SKILL_NAMES),
            "adapter lazy named skill permissions missing/overridden: " + role)
    bash = value.get("bash", "deny")
    if role == "orchestrator" and type(bash) is dict and any(a != "deny" for a in bash.values()):
        require(project.get("extensions", {}).get("helper_access", True) is True, "adapter helper access is opted out")
        require(safe(root, "sdd.py").is_file(), "adapter helper access requires local protected sdd.py")


def adapter(root, project, state, results, dispatch):
    """Role invariants for a supported profile, not a full official schema validator."""
    config = load(root, "opencode.json")
    require(type(config) is dict and "extensions" not in config, "adapter unknown core field")
    required = {"$schema": str, "default_agent": str, "agent": dict, "permission": dict,
                "autoupdate": bool, "share": str, "formatter": bool, "lsp": bool}
    optional = {"logLevel": str, "username": str, "snapshot": bool, "watcher": dict, "model": str, "small_model": str, "provider": dict}
    shape(config, {**required, **{k: typ for k, typ in optional.items() if k in config}}, "adapter config")
    # Provider settings are opaque user data, never invoked or included in diagnostics.
    for provider in config.get("provider", {}).values():
        allowed = {"api": str, "name": str, "env": list, "id": str, "npm": str,
                   "whitelist": list, "blacklist": list, "options": dict, "models": dict}
        require(type(provider) is dict and set(provider) <= set(allowed), "adapter unsupported provider fields")
        require(all(type(value) is allowed[key] for key, value in provider.items()), "adapter invalid provider field type")
        for key in ("env", "whitelist", "blacklist"):
            require(all(type(item) is str for item in provider.get(key, [])), "adapter invalid provider string array")
        require(all(type(item) is dict for item in provider.get("models", {}).values()), "adapter invalid provider model object")
        options = provider.get("options", {})
        for key in ("apiKey", "baseURL", "enterpriseUrl"):
            require(key not in options or type(options[key]) is str, "adapter invalid provider option type")
        require("setCacheKey" not in options or type(options["setCacheKey"]) is bool, "adapter invalid provider cache option")
        for key in ("timeout", "headerTimeout", "chunkTimeout"):
            require(key not in options or options[key] is False or type(options[key]) is int and options[key] > 0,
                    "adapter invalid provider timeout")
    require(config["$schema"] == "https://opencode.ai/config.json" and config["default_agent"] == "orchestrator", "adapter schema/default role invalid")
    require(config["permission"] == {"*": "deny"} and config["autoupdate"] is False and config["share"] == "disabled"
            and config["formatter"] is False and config["lsp"] is False, "adapter unsafe global overrides")
    require(set(config["agent"]) == set(ROLES) | set(BUILTINS), "adapter must expose exactly four framework roles")
    for builtin in BUILTINS:
        require(config["agent"][builtin] == {"disable": True}, "adapter inherited built-in role enabled: " + builtin)
    if "logLevel" in config:
        require(config["logLevel"] in {"DEBUG", "INFO", "WARN", "ERROR"}, "adapter invalid logLevel")
    if "watcher" in config:
        shape(config["watcher"], {"ignore": list}, "adapter watcher")
        strings(config["watcher"]["ignore"], "adapter watcher ignore")
    files = safe(root, ".opencode/agents")
    require(files.is_dir() and {p.name for p in files.iterdir()} == {r + ".md" for r in ROLES}, "adapter missing/extra agent files")
    for role in ROLES:
        entry = config["agent"][role]
        fields = {"description": str, "mode": str, "permission": dict}
        extras = {"model": str, "color": str, "temperature": (int, float), "top_p": (int, float), "steps": int, "hidden": bool}
        shape(entry, {**fields, **{k: typ for k, typ in extras.items() if k in entry}}, "agent " + role)
        require("extensions" not in entry, "adapter invalid agent field")
        if "steps" in entry:
            require(entry["steps"] > 0, "adapter invalid agent steps")
        if "color" in entry:
            require(re.fullmatch(r"#[0-9a-fA-F]{6}", entry["color"]) or entry["color"] in
                    {"primary", "secondary", "accent", "success", "warning", "error", "info"}, "adapter invalid agent color")
        require(entry["mode"] == ("primary" if role == "orchestrator" else "subagent") and entry["description"].strip(), "adapter invalid role mode/description")
        permissions(root, role, entry["permission"], project, dispatch)
        prompt = safe(root, ".opencode/agents/" + role + ".md").read_text()
        expected = f"---\ndescription: {entry['description']}\nmode: {entry['mode']}\n---\n"
        require(prompt.startswith(expected) and "core/lifecycle.md" in prompt, "adapter frontmatter/prompt invalid: " + role)
        if role == "implementer":
            require("before approval" in prompt, "implementer approval gate missing")
        if role == "verifier":
            require("Never execute" in prompt, "verifier no-rerun contract missing")
    command = safe(root, ".opencode/commands/sdd.md")
    require(command.is_file() and command.read_text().startswith("---\ndescription: Recover durable SDD context\nagent: orchestrator\n---\n"), "adapter command discovery invalid")


def initialize(root):
    require(root.is_dir(), "root must be an existing directory")
    names = ["project.json", "state.json", "environment.json", "decisions.md"]
    context = safe(root, ".sdd")
    if context.exists():
        require(all(safe(root, ".sdd/" + n).is_file() for n in names), "partial/conflicting initialization")
        project_contract(root)
        state_contract(root)
        return {"result": "already-initialized"}
    context.mkdir()
    atomic(root, ".sdd/project.json", {"schema_version": 1, "name": root.name,
        "source_roots": [], "capabilities": [], "procedures": {}, "environment_ref": ".sdd/environment.json",
        "risk_policy": {"known_tags": ["low", "high"], "review_required_for": ["high"]},
        "one_feature_at_a_time": True, "implementation_paths": [], "implementation_commands": []})
    atomic(root, ".sdd/state.json", {"schema_version": 1, "project_ref": ".sdd/project.json", "features": [],
        "active_feature": None, "phase": "planning", "checkpoint": {"next_task": None, "sources": []},
        "block": None, "approvals": {}, "reviews": {}, "closures": {}, "history": [], "retired_ids": {}})
    atomic(root, ".sdd/environment.json", {"schema_version": 1, "identities": {}})
    safe(root, ".sdd/decisions.md").write_text("# Decisions\n\nRecord short decisions with source references.\n", encoding="utf-8")
    return {"result": "initialized"}


def record_approval(root, fid, ref):
    project = project_contract(root)
    state, features = state_contract(root)
    require(fid in features, "unknown feature")
    feature = features[fid]
    require(feature["status"] in {"spec_ready", "in_progress"}, "feature not ready for approval")
    current = spec(root, feature, project, state["retired_ids"].get(str(fid), []))
    confirm, checksum = confirmation(root, ref, feature, current["digest"], "approval")
    name = f'.sdd/approvals/{fid}-v{feature["spec_version"]}.json'
    record = {"schema_version": 1, "feature": fid, "version": feature["spec_version"], "digest": current["digest"],
              "confirmation_ref": ref, "confirmation_hash": checksum, "actor": "human", "date": confirm["date"]}
    # Existing approval versions enforce monotonic revisions across all three files.
    directory = safe(root, ".sdd/approvals")
    if directory.exists():
        for old in directory.glob(f"{fid}-v*.json"):
            match = re.fullmatch(rf"{fid}-v(\d+)\.json", old.name)
            require(match is not None and int(match[1]) <= feature["spec_version"], "approval version regression")
    if safe(root, name).exists():
        require(load(root, name) == record, "contradictory approval; increment spec version")
    else:
        atomic(root, name, record)
    if state["approvals"].get(str(fid)) != name:
        state["approvals"][str(fid)] = name
        atomic(root, ".sdd/state.json", state)
    return {"result": "approved", "feature": fid, "digest": current["digest"], "reference": name}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("init", "validate", "status", "approval"))
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--feature", type=int)
    parser.add_argument("--confirmation-ref")
    parser.add_argument("--profile", action="store_true", help="read-only role permission recommendation")
    parser.add_argument("--assigned-task", action="append", help="explicit eligible task ID (status only; repeatable)")
    parser.add_argument("--runtime-grants", action="store_true", help="profile for a one-time ASK capability envelope")
    parser.add_argument("--no-helper-access", action="store_true", help="profile without bounded helper shell access")
    raw = sys.argv[1:] if argv is None else argv
    flags = [value.split("=", 1)[0] for value in raw if value.startswith("--") and not value.startswith("--assigned-task")]
    if len(flags) != len(set(flags)):
        parser.error("duplicate option forbidden for bounded helper access")
    args = parser.parse_args(raw)
    if args.operation == "approval" and (args.feature is None or args.confirmation_ref is None):
        parser.error("approval requires --feature and --confirmation-ref")
    if args.operation != "approval" and (args.feature is not None or args.confirmation_ref is not None):
        parser.error("approval arguments are only valid for approval")
    if args.assigned_task is not None and args.operation != "status":
        parser.error("--assigned-task is only valid for status")
    if args.profile and args.operation not in {"status", "validate"}:
        parser.error("--profile is only valid for read operations")
    if (args.runtime_grants or args.no_helper_access) and not args.profile:
        parser.error("permission profile options require --profile")
    code = 0
    try:
        root = args.root.resolve()
        if args.operation == "init":
            result = initialize(root)
        elif args.operation == "approval":
            result = record_approval(root, args.feature, args.confirmation_ref)
        else:
            result = evaluate(root, args.assigned_task, args.profile, not args.no_helper_access, args.runtime_grants)
            if args.operation == "validate":
                stale = {ref: reason for f in result["features"] for ref, reason in f["checks"].items() if not reason.startswith("fresh:")}
                if stale:
                    result.update(valid=False, diagnostics=stale)
                    code = 1
    except Invalid as exc:
        result, code = {"valid": False, "action": "intervention", "error": str(exc)}, 1
    except (OSError, UnicodeError) as exc:
        result, code = {"valid": False, "error": "I/O error: " + str(exc)}, 2
    # Permission rules are ordered programs (last match wins), not sortable maps.
    print(json.dumps(result, sort_keys=not args.profile, indent=None if args.json else 2))
    return code


if __name__ == "__main__":
    sys.exit(main())
