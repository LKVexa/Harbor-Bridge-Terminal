"""UC-2.8.0 edge-component atoms: inventory, integrity, bindings and isolated per-atom qualification.

The 99 supplied edge-component archives are carried byte-for-byte under ``edge/source/`` (byte-identical
duplicates stored once and recorded as aliases). One canonical build per element is extracted under
``edge/atoms/<key>/``; distinct alternative builds of the same element are extracted under ``edge/variants/``.
``edge/EDGE_MANIFEST.json`` is the authority for all of it.

Every atom keeps its own package, tests and claims. The ship never imports an atom into its own process:
an atom suite runs in a child interpreter whose import path holds only that atom and the ship's ``pk/pk_core``,
so two atoms can never shadow each other and a failing atom cannot disturb the ship. A green atom suite is
evidence about that atom on this host; it never promotes a PK checklist item or a master-series task to PASS.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from . import engines as E
from . import Refusal

SCHEMA_STATUS = "UC/EDGE_STATUS/1"
SCHEMA_CHECK = "UC/EDGE_CHECK/1"
SCHEMA_RUN = "UC/EDGE_TEST_RUN/1"
MAX_JOBS = 16
DEFAULT_DEADLINE_S = 600
# Optional extra import roots for atom children only (e.g. a site-packages holding pytest); never the ship's own path.
EXTRA_ENV = "UC_EDGE_EXTRA_PATH"
# Fallback driver when pytest is absent: load every test*.py by file path (the atom test folders are not packages)
# and run its unittest cases; prints the standard unittest summary.
_UNITTEST_DRIVER = r"""
import importlib.util, os, sys, unittest
root = sys.argv[1]; suite = unittest.TestSuite(); loader = unittest.TestLoader(); broken = 0
for dp, dns, fns in os.walk(root):
    dns[:] = sorted(d for d in dns if d != '__pycache__')
    for fn in sorted(fns):
        if fn.startswith('test') and fn.endswith('.py'):
            path = os.path.join(dp, fn)
            name = '_edge_' + os.path.relpath(path, root).replace(os.sep, '_')[:-3]
            try:
                spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
                sys.modules[name] = mod; sys.path.insert(0, dp); spec.loader.exec_module(mod)
                suite.addTests(loader.loadTestsFromModule(mod))
            except Exception as exc:
                broken += 1; print('ERROR collecting', path, type(exc).__name__, exc, file=sys.stderr)
r = unittest.TextTestRunner(verbosity=0).run(suite)
sys.exit(0 if r.wasSuccessful() and not broken else 1)
"""
_ID = re.compile(r"^(GAP|INV|PLN|SCH)-\d\d$|^EXT-[A-Z0-9-]{1,40}$")


def edge_dir(root: Optional[str] = None) -> str:
    return os.path.join(root or E.ship_root(), "edge")


def manifest(root: Optional[str] = None) -> Dict[str, Any]:
    p = os.path.join(edge_dir(root), "EDGE_MANIFEST.json")
    if not os.path.isfile(p):
        raise Refusal("edge/EDGE_MANIFEST.json is missing: this ship carries no edge atoms")
    with open(p, "r", encoding="utf-8") as f:
        m = json.load(f)
    if m.get("schema") != "UC/EDGE_ATOMS/1":
        raise Refusal("unexpected edge manifest schema", {"schema": m.get("schema")})
    return m


def bindings(root: Optional[str] = None) -> Dict[str, Any]:
    p = os.path.join(root or E.ship_root(), "pk", "PK_ATOM_BINDINGS.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def atom(element: str, root: Optional[str] = None) -> Dict[str, Any]:
    element = element.strip().upper()
    if not _ID.match(element):
        raise Refusal("element id must look like GAP-01, INV-24, PLN-07, SCH-01 or EXT-IOS735-LCTL", {"element": element})
    for a in manifest(root)["atoms"]:
        if a["element"] == element:
            return a
    raise Refusal("no edge atom is installed for that element", {"element": element})


def latest_evidence(root: Optional[str] = None) -> Optional[Dict[str, Any]]:
    p = os.path.join(edge_dir(root), "evidence", "EDGE_TEST_RESULTS.json")
    if not os.path.isfile(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def status(root: Optional[str] = None) -> Dict[str, Any]:
    root = root or E.ship_root()
    m = manifest(root)
    b = bindings(root)
    ev = latest_evidence(root)
    per = {r["element"]: r for r in (ev or {}).get("results", [])}
    rows = []
    for a in m["atoms"]:
        r = per.get(a["element"], {})
        rows.append({"element": a["element"], "key": a["key"], "version": a.get("package_version"),
                     "pk_component": b["bindings"].get(a["element"], {}).get("pk_component"),
                     "recorded": r.get("verdict"), "passed": r.get("passed"), "failed": r.get("failed"),
                     "errors": r.get("errors")})
    verdicts: Dict[str, int] = {}
    for r in rows:
        verdicts[str(r["recorded"])] = verdicts.get(str(r["recorded"]), 0) + 1
    return {"schema": SCHEMA_STATUS, "candidate": m["candidate"], "requested_archives": m["requested_archives"],
            "stored_unique_archives": m["stored_unique_archives"], "byte_identical_duplicates": m["byte_identical_duplicates"],
            "elements": m["elements"], "variants": m["variants"],
            "bound_to_pk_components": sum(1 for r in rows if r["pk_component"]),
            "recorded_evidence": {"file": "edge/evidence/EDGE_TEST_RESULTS.json" if ev else None,
                                  "host": (ev or {}).get("host"), "totals": (ev or {}).get("totals"), "verdicts": verdicts},
            "atoms": rows,
            "boundaries": ["atom suites are evidence about an atom on one host, not PK checklist or master-series PASS",
                           "atoms run as isolated child interpreters; the ship never imports atom code in-process",
                           "no atom is wired into berth execution, the hull, VWS control or the 1-bit fabric",
                           "not Production GO"]}


def check(root: Optional[str] = None, deep: bool = False) -> Dict[str, Any]:
    """Fail-closed integrity check: every stored archive matches its recorded SHA-256, every canonical and
    variant tree exists, and (deep) every extracted file is byte-identical to its archive member with no extras."""
    root = root or E.ship_root()
    ed = edge_dir(root)
    m = manifest(root)
    problems: List[str] = []
    stored = set()
    for r in m["archives"]:
        p = os.path.join(ed, r["stored_as"])
        if not os.path.isfile(p):
            problems.append(f"missing archive {r['stored_as']}")
            continue
        if r["stored_as"] not in stored:
            stored.add(r["stored_as"])
            if _sha(p) != (r["sha256"] if "byte_identical_to" not in r else next(
                    x["sha256"] for x in m["archives"] if x["archive"] == r["byte_identical_to"])):
                problems.append(f"sha256 mismatch {r['stored_as']}")
    on_disk = set(f"source/{n}" for n in os.listdir(os.path.join(ed, "source")))
    for extra in sorted(on_disk - stored):
        problems.append(f"unrecorded archive {extra}")
    compared = 0
    for r in m["archives"]:
        if r.get("role") not in ("canonical", "variant", "release-evidence"):
            continue
        dest = os.path.join(ed, r["installed_at"])
        if not os.path.isdir(dest):
            problems.append(f"missing tree {r['installed_at']}")
            continue
        if not deep:
            continue
        with zipfile.ZipFile(os.path.join(ed, r["stored_as"])) as z:
            for info in z.infolist():
                n = info.filename.replace("\\", "/")
                if info.is_dir() or "__pycache__" in n.split("/") or n.endswith((".pyc", ".pyo")):
                    continue
                fp = os.path.join(dest, *n.split("/"))
                if not os.path.isfile(fp):
                    problems.append(f"missing {r['installed_at']}/{n}")
                    continue
                h = hashlib.sha256(z.read(info)).hexdigest()
                if _sha(fp) != h:
                    problems.append(f"modified {r['installed_at']}/{n}")
                compared += 1
    if deep:
        members: Dict[str, set] = {}
        for r in m["archives"]:
            if r.get("role") in ("canonical", "variant", "release-evidence"):
                with zipfile.ZipFile(os.path.join(ed, r["stored_as"])) as z:
                    members[r["installed_at"]] = {i.filename.replace("\\", "/") for i in z.infolist() if not i.is_dir()}
        for inst, names in members.items():
            base = os.path.join(ed, inst)
            nested = [k for k in members if k != inst and k.startswith(inst + "/")]
            for dp, dns, fns in os.walk(base):
                dns[:] = [d for d in dns if d != "__pycache__"]
                for fn in fns:
                    rel = os.path.relpath(os.path.join(dp, fn), base).replace(os.sep, "/")
                    if any((inst + "/" + rel).startswith(k + "/") for k in nested):
                        continue
                    if rel not in names and not fn.endswith((".pyc", ".pyo")):
                        problems.append(f"unrecorded file {inst}/{rel}")
    return {"schema": SCHEMA_CHECK, "pass": not problems, "deep": deep, "archives": len(m["archives"]),
            "stored_unique": len(stored), "files_compared": compared, "problems": problems[:200],
            "problem_count": len(problems)}


def _pytest_available(python: str, extra: Optional[List[str]] = None) -> bool:
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(extra or [x for x in os.environ.get(EXTRA_ENV, "").split(os.pathsep) if x]))
    try:
        return subprocess.run([python, "-c", "import pytest"], capture_output=True, timeout=60, env=env).returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _count(pat: str, text: str) -> int:
    m = re.search(r"(\d+) " + pat, text)
    return int(m.group(1)) if m else 0


def run_atom(a: Dict[str, Any], root: Optional[str] = None, python: Optional[str] = None,
             deadline_s: int = DEFAULT_DEADLINE_S, use_pytest: Optional[bool] = None) -> Dict[str, Any]:
    """Run one atom's own suite in a child interpreter with an isolated import path."""
    root = root or E.ship_root()
    python = python or sys.executable
    ed = edge_dir(root)
    if not a.get("tests"):
        return {"element": a["element"], "verdict": "NO_SUITE", "passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    # Atom suites write into their own trees (benchmarks, evidence files). They run in a disposable copy under
    # _runs/edge/work/ so the sealed atom stays byte-identical to its archive.
    import shutil, tempfile
    work_parent = os.path.join(root, "_runs", "edge", "work")
    os.makedirs(work_parent, exist_ok=True)
    work = tempfile.mkdtemp(prefix=a["element"] + "-", dir=work_parent)  # short: Windows MAX_PATH
    try:
        shutil.copytree(os.path.join(ed, a["path"]), os.path.join(work, a["path"]),
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        return _run_in(a, root, work, python, deadline_s, use_pytest)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _run_in(a: Dict[str, Any], root: str, ed: str, python: str, deadline_s: int, use_pytest: Optional[bool]) -> Dict[str, Any]:
    tests = os.path.join(ed, a["tests"])
    parent = os.path.dirname(tests)
    top = os.path.dirname(parent) if os.path.isfile(os.path.join(parent, "__init__.py")) else parent
    helpers = [dp for dp, _d, fs in os.walk(tests) if any(f.startswith(("fixtures", "_boot", "helpers")) for f in fs)]
    extra = [x for x in os.environ.get(EXTRA_ENV, "").split(os.pathsep) if x]
    path = [top, parent, os.path.join(parent, "src"), os.path.join(ed, a["path"]), os.path.join(root, "pk")] + extra
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    if use_pytest is None:
        use_pytest = _pytest_available(python, extra)
    attempts = ([("prepend", path), ("importlib", [parent] + path + helpers), ("prepend", path + helpers)]
                if use_pytest else [("unittest", path + helpers)])
    best: Optional[Dict[str, Any]] = None
    started = time.time()
    for mode, pp in attempts:
        e = dict(env, PYTHONPATH=os.pathsep.join(pp))
        if mode == "unittest":
            cmd = [python, "-B", "-c", _UNITTEST_DRIVER, tests]
        else:
            cmd = [python, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-header", "-o", "addopts=",
                   f"--import-mode={mode}", "--rootdir", top, tests]
        try:
            p = subprocess.run(cmd, cwd=top, env=e, capture_output=True, text=True, timeout=deadline_s,
                               encoding="utf-8", errors="replace")
            text, rc = (p.stdout or "") + (p.stderr or ""), p.returncode
        except subprocess.TimeoutExpired:
            text, rc = "TIMEOUT", -9
        tail = text.strip().splitlines()[-1] if text.strip() else ""
        if mode == "unittest":
            ran_m = re.search(r"Ran (\d+) tests?", text)
            ran = int(ran_m.group(1)) if ran_m else 0
            fl = re.search(r"FAILED \(([^)]*)\)", text)
            fm = re.search(r"failures=(\d+)", fl.group(1)) if fl else None
            em = re.search(r"errors=(\d+)", fl.group(1)) if fl else None
            sm = re.search(r"skipped=(\d+)", text)
            failed = int(fm.group(1)) if fm else 0
            errors = (int(em.group(1)) if em else 0) + text.count("ERROR collecting")
            skipped = int(sm.group(1)) if sm else 0
            passed = max(0, ran - failed - errors - skipped)
        else:
            passed, failed, errors, skipped = (_count("passed", tail), _count("failed", tail),
                                               _count("errors?", tail), _count("skipped", tail))
        if mode == "unittest":
            failing = re.findall(r"^(?:FAIL|ERROR): (\S+ \([^)]*\))", text, re.M)[:50]
        else:
            failing = re.findall(r"^(?:FAILED|ERROR) (\S+)", text, re.M)[:50]
        r = {"element": a["element"], "key": a["key"], "runner": "pytest" if use_pytest else "unittest",
             "import_mode": mode, "rc": rc, "passed": passed, "failed": failed, "errors": errors, "skipped": skipped,
             "summary": tail[:300], "failing": failing}
        if best is None or (passed - 10 * errors, -failed) > (best["passed"] - 10 * best["errors"], -best["failed"]):
            best = r
        if rc == 0:
            break
    assert best is not None
    best["seconds"] = round(time.time() - started, 2)
    if best["rc"] == -9:
        best["verdict"] = "TIMEOUT"
    elif best["rc"] == 0 and best["passed"] > 0:
        best["verdict"] = "SUITE_GREEN"
    elif best["passed"] == 0 and best["failed"] == 0:
        best["verdict"] = "SUITE_NOT_RUNNABLE"
    else:
        best["verdict"] = "SUITE_RED"
    return best


def run_all(root: Optional[str] = None, jobs: int = 4, only: Optional[List[str]] = None,
            deadline_s: int = DEFAULT_DEADLINE_S) -> Dict[str, Any]:
    import platform
    root = root or E.ship_root()
    jobs = max(1, min(int(jobs), MAX_JOBS))
    atoms = [a for a in manifest(root)["atoms"] if not only or a["element"] in only]
    use_pytest = _pytest_available(sys.executable)
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        results = list(ex.map(lambda a: run_atom(a, root, deadline_s=deadline_s, use_pytest=use_pytest), atoms))
    totals = {k: sum(r[k] for r in results) for k in ("passed", "failed", "errors", "skipped")}
    verdicts: Dict[str, int] = {}
    for r in results:
        verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1
    return {"schema": SCHEMA_RUN, "candidate": "UC-2.8.0",
            "executed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "host": {"python": platform.python_version(), "system": platform.system(), "machine": platform.machine(),
                     "runner": "pytest" if use_pytest else "unittest", "jobs": jobs},
            "atoms_run": len(results), "totals": totals, "verdicts": verdicts, "results": results,
            "note": "Evidence about each atom's own suite on this host. It does not promote PK checklist items or master-series tasks."}


# ---------------------------------------------------------------------------------------------- CLI surface

def configure(sp) -> None:
    p = sp.add_parser("edge", help="inspect, verify and qualify the installed edge-component atoms")
    p.add_argument("edge_verb", choices=("status", "list", "check", "show", "test"))
    p.add_argument("target", nargs="?", help="element id (GAP-01, INV-24, PLN-07, SCH-01, EXT-IOS735-LCTL) or 'all' for test")
    p.add_argument("--deep", action="store_true", help="check: compare every extracted file with its archive member")
    p.add_argument("--jobs", type=int, default=4, help="test all: parallel atom suites (1-16)")
    p.add_argument("--deadline", type=int, default=DEFAULT_DEADLINE_S, help="per-atom deadline in seconds")
    p.add_argument("--out", help="also write the JSON result to this path")
    p.set_defaults(fn=cli)


def cli(a) -> int:
    from .cli import _emit, EXIT_OK, EXIT_FAIL
    if a.edge_verb == "status":
        return _emit(status(), out=a.out)
    if a.edge_verb == "list":
        return _emit([{"element": x["element"], "key": x["key"], "version": x.get("package_version"), "path": x["path"]}
                      for x in manifest()["atoms"]], out=a.out)
    if a.edge_verb == "check":
        r = check(deep=a.deep)
        return _emit(r, EXIT_OK if r["pass"] else EXIT_FAIL, out=a.out)
    if not a.target:
        raise Refusal(f"edge {a.edge_verb} needs an element id")
    if a.edge_verb == "show":
        x = atom(a.target)
        ev = {r["element"]: r for r in (latest_evidence() or {}).get("results", [])}.get(x["element"])
        return _emit({"atom": x, "binding": bindings()["bindings"].get(x["element"]), "recorded_evidence": ev}, out=a.out)
    if not 30 <= a.deadline <= 3600:
        raise Refusal("deadline must be between 30 and 3600 seconds")
    out = a.out or os.path.join(E.runs_dir(), "edge", f"EDGE_TEST_{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}.json")
    if a.target.lower() == "all":
        r = run_all(jobs=a.jobs, deadline_s=a.deadline)
        return _emit(r, EXIT_OK if r["totals"]["failed"] + r["totals"]["errors"] == 0 else EXIT_FAIL, out=out)
    r = run_atom(atom(a.target), deadline_s=a.deadline)
    return _emit(r, EXIT_OK if r["verdict"] == "SUITE_GREEN" else EXIT_FAIL, out=out)
