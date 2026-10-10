#!/usr/bin/env python3
"""Install the bounded project-local package. No force, updater or runtime install."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile

MANAGED = ("sdd.py", "core/contracts.md", "core/spec-format.md", "core/lifecycle.md",
           "core/verification.md", "docs/adoption.md", "docs/opencode.md",
           ".opencode/agents/orchestrator.md", ".opencode/agents/planner.md",
           ".opencode/agents/implementer.md", ".opencode/agents/verifier.md",
           ".opencode/commands/sdd.md", ".opencode/skill-manifest.json")
SKILLS = ("auth0", "frontend-design", "graphify", "playwright-cli", "vercel-composition-patterns",
          "vercel-react-best-practices", "vercel-react-native-skills")
SUPPLEMENTS = ("docs/skills.md", "THIRD_PARTY_NOTICES.md", "licenses/sdd-workflow-MIT.txt", "third_party/licenses/Auth0-Apache-2.0.txt",
               "third_party/licenses/Graphify-Apache-2.0.txt", "third_party/licenses/Graphify-MIT.txt",
               "third_party/licenses/Graphify-NOTICE.txt", "third_party/licenses/Playwright-Apache-2.0.txt",
               "third_party/licenses/Vercel-MIT.txt")
CONTEXT = ("project.json", "state.json", "environment.json", "decisions.md")
START = "<!-- sdd-workflow:source-map:start -->"
END = "<!-- sdd-workflow:source-map:end -->"
MAP = (START + "\n## sdd-workflow sources\n\n"
       "Use `.opencode/agents/` for the four role definitions. Orchestrator alone\n"
       "coordinates global state; implementer works only on assigned approved tasks.\n"
       "Read sources on demand, not all at startup:\n\n"
       "- [Records and ownership](core/contracts.md)\n"
       "- [Spec format](core/spec-format.md)\n"
       "- [Approval, recovery and closure](core/lifecycle.md)\n"
       "- [Evidence](core/verification.md)\n"
       "- [Adoption](docs/adoption.md) and [runtime limits](docs/opencode.md)\n"
       "- `.sdd/project.json` and `.sdd/state.json`: current context and checkpoint\n\n"
       "Keep specs immutable; human approval and closure remain explicit gates.\n" + END + "\n").encode()


class Conflict(ValueError):
    pass


def check(condition, message):
    if not condition:
        raise Conflict(message)


def target(root, name):
    path = root / name
    check(path.resolve().is_relative_to(root), "path escapes project: " + name)
    check(path.resolve() == path, "symlink/alias conflict: " + name)
    for parent in path.parents:
        if parent == root:
            break
        check(not parent.exists() or parent.is_dir(), "parent is not a directory: " + str(parent.relative_to(root)))
    check(not path.exists() or path.is_file(), "managed path is not a file: " + name)
    return path


def read(root, name):
    path = target(root, name)
    return path.read_bytes() if path.exists() else None


def writable(path, directory=False):
    needed = os.W_OK | (os.X_OK if directory else 0)
    check(bool(path.stat().st_mode & 0o222) and os.access(path, needed), "unwritable destination: " + str(path.name))


def preflight_path(root, name):
    path = target(root, name)
    if path.exists():
        writable(path)
    parent = path.parent
    while not parent.exists():
        parent = parent.parent
    writable(parent, True)


def merge(base, current):
    """Fill absent keys only. Given permission programs must pass helper invariants."""
    check(type(current) is dict, "opencode.json must be an object")
    result = dict(current)
    for key, value in base.items():
        if key == "default_agent":
            result[key] = "orchestrator"  # The explicit onboarding default change.
        elif key == "agent":
            supplied = result.get(key, {})
            check(type(supplied) is dict, "opencode.json agent must be an object")
            check(set(supplied) <= set(value), "opencode.json has extra/conflicting agents")
            agents = dict(supplied)
            for name, defaults in value.items():
                previous = agents.get(name, {})
                check(type(previous) is dict, "opencode.json invalid agent: " + name)
                if defaults.get("disable"):
                    check(name not in supplied or previous == defaults, "enabled/unsupported built-in agent: " + name)
                agents[name] = {**defaults, **previous}
                # New guidance access can fill an absent tool key; never overwrite
                # an explicit user skill rule or change other permission programs.
                if "permission" in defaults and type(agents[name].get("permission")) is dict:
                    permission = dict(agents[name]["permission"])
                    if "skill" not in permission:
                        permission["skill"] = defaults["permission"]["skill"]
                    agents[name]["permission"] = permission
            result[key] = agents
        elif key not in result:
            result[key] = value
    return result


def instructions(original):
    if original is None:
        return MAP
    original.decode("utf-8")  # Unsupported instruction encoding is a no-write failure.
    begin, end = START.encode(), END.encode()
    if begin in original or end in original:
        check(original.count(begin) == original.count(end) == 1, "AGENTS.md ambiguous source-map markers")
        start = original.index(begin)
        stop = original.index(end) + len(end)
        check(original[start:stop] == MAP.rstrip(b"\n"), "AGENTS.md differing source-map block")
        return original
    return original + (b"\n" if original.endswith(b"\n") else b"\n\n") + MAP


def helper_from(source):
    spec = importlib.util.spec_from_file_location("sdd_install_guard", source / "sdd.py")
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def skill_files(source, helper):
    """Fixed release data only. No original host lookup, imports or install hooks."""
    inventory = helper.decode(read(source, ".opencode/skill-manifest.json").decode("utf-8"))
    helper.shape(inventory, {"skills": list, "files": dict, "supplements": dict}, "skill manifest", True)
    check(inventory["skills"] == list(SKILLS), "skill manifest must contain exactly seven names")
    files = inventory["files"]
    check(files and len(files) <= 1000 and set(inventory["supplements"]) == set(SUPPLEMENTS), "skill manifest membership invalid")
    roots = source / ".opencode/skills"
    check(roots.is_dir() and not roots.is_symlink(), "missing/unsafe skill source directory")
    check({p.name for p in roots.iterdir()} == set(SKILLS), "unknown/missing skill source name")
    actual = set()
    for path in roots.rglob("*"):
        check(not path.is_symlink() and (path.is_file() or path.is_dir()), "unsafe skill source type/link")
        if path.is_file():
            actual.add(path.relative_to(source).as_posix())
    check(actual == set(files), "unknown/missing skill source members; use the complete release")
    for name in SKILLS:
        key = f".opencode/skills/{name}/SKILL.md"
        check(key in files, "missing SKILL.md: " + name)
        text = read(source, key).decode("utf-8")
        check(text.startswith("---\n") and "\n---\n" in text[4:], "malformed skill frontmatter: " + name)
        header = text[4:].split("\n---\n", 1)[0]
        check(re.search(r"^name: " + re.escape(name) + r"\s*$", header, re.M), "skill name/frontmatter mismatch: " + name)
        check(re.search(r"^description: *(?:\S[^\n]*|\n[ \t]+\S)", header, re.M), "missing skill description: " + name)
    for name, digest in {**files, **inventory["supplements"]}.items():
        check(type(name) is str and name == Path(name).as_posix() and ".." not in Path(name).parts
              and not Path(name).is_absolute() and "\\" not in name, "unsafe skill manifest path")
        check(type(digest) is str and re.fullmatch(r"[a-f0-9]{64}", digest), "invalid skill manifest hash")
        data = read(source, name)
        check(data is not None and hashlib.sha256(data).hexdigest() == digest, "skill/supplement hash conflict: " + name)
    return tuple(files) + SUPPLEMENTS


def existing_context(helper, project):
    context = project / ".sdd"
    check(not context.is_symlink(), "symlink conflict: .sdd")
    if not context.exists():
        return None
    check(context.is_dir(), ".sdd is not a directory")
    for name in CONTEXT:
        check(read(project, ".sdd/" + name) is not None, "partial .sdd initialization: " + name)
    helper.shape(helper.load(project, ".sdd/environment.json"), {"identities": dict}, "environment", True)
    read(project, ".sdd/decisions.md").decode("utf-8")
    # Validate retained context at its real root: do not copy app code, secrets or
    # user evidence into staging. Validate the merged adapter separately below.
    adapter = helper.adapter
    try:
        helper.adapter = lambda *args: None
        return helper.evaluate(project)
    finally:
        helper.adapter = adapter


def atomic(path, data, mode):
    temp = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temp = Path(stream.name)
            stream.write(data)
        temp.chmod(mode)
        os.replace(temp, path)
    finally:
        if temp is not None and temp.exists():
            temp.unlink()


def commit(project, plan, helper, after_write=None):
    ledger, directories = [], []
    try:
        for name, (data, original, mode) in plan.items():
            path = target(project, name)
            check(read(project, name) == original, "concurrent destination change: " + name)
            missing = []
            parent = path.parent
            while not parent.exists():
                missing.append(parent)
                parent = parent.parent
            for parent in reversed(missing):
                parent.mkdir()
                directories.append(parent)
            ledger.append((name, original, mode))
            atomic(path, data, mode)
            if after_write:
                after_write(name)
        helper.evaluate(project)  # Full final installed profile/context guard.
    except (OSError, ValueError) as exc:
        residual = []
        for name, original, mode in reversed(ledger):
            try:
                path = target(project, name)
                if original is None:
                    if path.exists():
                        path.unlink()
                else:
                    atomic(path, original, mode)
            except (OSError, ValueError):
                residual.append(name)
        for directory in reversed(directories):
            try:
                directory.rmdir()  # Only empty directories this install created.
            except OSError:
                residual.append(directory.relative_to(project).as_posix())
        if residual:
            raise Conflict("rollback incomplete; recover paths: " + ", ".join(sorted(set(residual)))) from exc
        raise Conflict("installation rolled back: " + str(exc)) from exc


def install(project, source=None, after_write=None):
    source = (source or Path(__file__).resolve().parent).resolve()
    project = project.resolve()
    check(source.is_dir() and project.is_dir(), "source/project must be existing directories")
    check(not source.is_relative_to(project) and not project.is_relative_to(source), "source/project overlap refused; use a separate project")
    for name in ("opencode.jsonc", ".opencode/opencode.json", ".opencode/opencode.jsonc"):
        check(not (project / name).exists() and not (project / name).is_symlink(),
              "unsupported/competing config: " + name + "; review/convert it to root strict JSON separately")
    agents = project / ".opencode/agents"
    if agents.exists():
        check(agents.is_dir() and not agents.is_symlink(), "unsafe agents directory")
        check({p.name for p in agents.iterdir()} <= {Path(n).name for n in MANAGED if n.startswith(".opencode/agents/")}, "extra/conflicting agent files")
    desired, observed = {}, {}
    for name in MANAGED:
        data = read(source, name)
        check(data is not None, "source missing managed file: " + name)
        original = read(project, name)
        observed[name] = original
        check(original is None or original == data, "managed conflict: " + name + "; review/move the conflicting file before reinstalling")
        desired[name] = data
    helper = helper_from(source)
    for name in skill_files(source, helper):
        data = read(source, name)
        original = read(project, name)
        observed[name] = original
        check(original is None or original == data, "managed conflict: " + name + "; preserve/review it before reinstalling")
        desired[name] = data
    config_original = read(project, "opencode.json")
    observed["opencode.json"] = config_original
    starter_bytes = read(source, "opencode.json")
    check(starter_bytes is not None, "source missing opencode.json")
    starter = helper.decode(starter_bytes.decode("utf-8"))
    check(type(starter) is dict, "source opencode.json must be an object")
    current = helper.decode(config_original.decode("utf-8")) if config_original is not None else {}
    configured = merge(starter, current)
    config_bytes = (json.dumps(configured, indent=2, ensure_ascii=False) + "\n").encode()
    # Semantic no-op retains exact whitespace/bytes on repeat.
    desired["opencode.json"] = config_original if current == configured else config_bytes
    agents_original = read(project, "AGENTS.md")
    observed["AGENTS.md"] = agents_original
    desired["AGENTS.md"] = instructions(agents_original)
    retained = existing_context(helper, project)
    with tempfile.TemporaryDirectory(prefix="sdd-install-stage-") as directory:
        stage = Path(directory)
        for name, data in desired.items():
            path = stage / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if retained is None:
            helper.initialize(stage)
            context = helper.load(stage, ".sdd/project.json")
            context["name"] = project.name
            helper.atomic(stage, ".sdd/project.json", context)
            for name in CONTEXT:
                desired[".sdd/" + name] = (stage / ".sdd" / name).read_bytes()
                observed[".sdd/" + name] = None
            helper.evaluate(stage)
        else:
            contract = helper.project_contract(project)
            state, _ = helper.state_contract(project)
            helper.adapter(stage, contract, state, {f["feature"]: f for f in retained["features"]}, retained["authorization"])
        for name, original in (("opencode.json", config_original), ("AGENTS.md", agents_original)):
            if original is not None and desired[name] != original:
                backup = name + ".sdd-backup"
                previous = read(project, backup)
                observed[backup] = previous
                check(previous is None or previous == original, "backup conflict: " + backup + "; preserve/review it before reinstalling")
                desired[backup] = original
        plan = {}
        for name, data in desired.items():
            original = read(project, name)
            check(original == observed[name], "concurrent destination change: " + name)
            if original == data:
                continue
            preflight_path(project, name)
            mode = stat.S_IMODE((project / name).stat().st_mode) if original is not None else (0o600 if name.startswith(".sdd/") or name.endswith(".sdd-backup") else
                    stat.S_IMODE((source / name).stat().st_mode) & 0o777 if name.startswith(".opencode/skills/") else 0o644)
            plan[name] = (data, original, mode)
        # Recheck all relevant managed destinations, including no-ops, before commit.
        if retained is None:
            check(not (project / ".sdd").exists(), "concurrent .sdd initialization; retry after reviewing it")
        for name, original in observed.items():
            check(read(project, name) == original, "concurrent destination change: " + name)
        commit(project, plan, helper, after_write)
    return {"result": "installed" if plan else "already-installed", "paths": list(plan)}


def main(argv=None):
    if sys.version_info < (3, 10):
        print("Python 3.10+ must already be installed.", file=sys.stderr)
        return 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        result = install(args.project)
    except (OSError, ValueError, UnicodeError) as exc:
        print("Install refused: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result))  # Paths only; never config/provider/backup contents.
    return 0


if __name__ == "__main__":
    sys.exit(main())
