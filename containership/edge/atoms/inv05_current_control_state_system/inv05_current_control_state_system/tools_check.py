"""Verification library behind the CI tools (MC-002-03/04, MC-003, MC-012-06, MC-048, MC-049, MC-052-03).

Everything here is deterministic and stdlib-only so the checks run in a hermetic
CI job and can be unit-tested (``tests/test_tooling.py``).
"""
from __future__ import annotations

import ast
import datetime as _dt
import hashlib
import hmac
import json
import os
import re
from typing import Any

PKG = os.path.dirname(os.path.abspath(__file__))
EXCLUDE_DIRS = {"__pycache__", "evidence", ".git"}


def rel(path: str) -> str:
    return os.path.relpath(path, PKG).replace(os.sep, "/")


def load_json(relpath: str) -> Any:
    with open(os.path.join(PKG, relpath), encoding="utf-8") as fh:
        return json.load(fh)


def version() -> str:
    with open(os.path.join(PKG, "VERSION"), encoding="utf-8") as fh:
        return fh.read().strip()


# ------------------------------------------------------------------ schema compatibility (MC-012-06)

def schema_breaking_changes(lock: dict[str, Any], cur: dict[str, Any]) -> list[str]:
    out = []
    if cur.get("major") != lock.get("major"):
        out.append(f"protocol major changed {lock.get('major')} -> {cur.get('major')}")
    if cur.get("minor", 0) < lock.get("minor", 0):
        out.append("protocol minor went backwards")
    for msg, fields in lock["messages"].items():
        cm = cur["messages"].get(msg)
        if cm is None:
            out.append(f"message {msg} removed")
            continue
        for f, spec in fields.items():
            if f not in cm:
                out.append(f"{msg}.{f} removed")
            elif [t for t in cm[f] if t != "required"] != [t for t in spec if t != "required"]:
                out.append(f"{msg}.{f} type changed")
            elif ("required" in cm[f]) and ("required" not in spec):
                out.append(f"{msg}.{f} became required")
        for f, spec in cm.items():
            if f not in fields and "required" in spec:
                out.append(f"{msg}.{f} added as required")
    for op, fields in lock["ops"].items():
        missing = set(fields) - set(cur["ops"].get(op, []))
        if missing:
            out.append(f"op {op} lost fields {sorted(missing)}")
    for t, ops in lock["compare_targets"].items():
        if not set(ops) <= set(cur["compare_targets"].get(t, [])):
            out.append(f"compare target {t} lost operators")
    lost = set(lock["capabilities"]) - set(cur["capabilities"])
    if lost:
        out.append(f"capabilities removed {sorted(lost)}")
    return out


# ------------------------------------------------------------------ test inventory

def test_ids() -> set[str]:
    """All ``module.Class.test_method`` ids found statically in tests/."""
    ids: set[str] = set()
    tdir = os.path.join(PKG, "tests")
    for name in os.listdir(tdir):
        if not (name.startswith("test_") and name.endswith(".py")):
            continue
        mod = name[:-3]
        with open(os.path.join(tdir, name), encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                for fn in node.body:
                    if isinstance(fn, ast.FunctionDef) and fn.name.startswith("test"):
                        ids.add(f"{mod}.{node.name}.{fn.name}")
    return ids


def symbol_exists(ref: str) -> bool:
    """``file.py`` or ``file.py::Symbol`` or ``file.py::Class.method``."""
    path, _, sym = ref.partition("::")
    full = os.path.join(PKG, path)
    if not os.path.exists(full):
        return False
    if not sym or not path.endswith(".py"):
        return True
    with open(full, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    parts = sym.split(".")
    nodes = tree.body
    for i, p in enumerate(parts):
        found = None
        for n in nodes:
            if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == p:
                found = n
            elif isinstance(n, (ast.Assign, ast.AnnAssign)):
                targets = n.targets if isinstance(n, ast.Assign) else [n.target]
                if any(isinstance(t, ast.Name) and t.id == p for t in targets):
                    found = n
        if found is None:
            return False
        nodes = getattr(found, "body", [])
    return True


# ------------------------------------------------------------------ traceability (MC-003)

TRACE_STATUSES = {"verified", "verified-single-member", "partial", "blocked-external"}


def check_trace(matrix: dict[str, Any], *, current_version: str | None = None,
                require_generated: bool = False) -> list[str]:
    """``evidence/*`` paths are produced by the CI gate itself; they are only required to
    exist when ``require_generated`` is set (release gate)."""
    problems: list[str] = []
    checklist = load_json("CHECKLIST.json")
    want = [i["check_id"] for i in checklist["items"]]
    rows = matrix.get("rows", [])
    got = [r.get("id") for r in rows]
    if got != want:
        problems.append(f"matrix ids differ from CHECKLIST.json (missing {sorted(set(want) - set(got))[:5]}, "
                        f"extra {sorted(set(got) - set(want))[:5]})")
    tids = test_ids()
    exceptions = {e["id"]: e for e in load_json("docs/EXCEPTIONS.json")["exceptions"]}
    cv = current_version or version()
    for r in rows:
        rid = r.get("id")
        st = r.get("status")
        if st not in TRACE_STATUSES:
            problems.append(f"{rid}: invalid status {st!r}")
        for f in ("owner", "reviewer", "last_verified", "requirement"):
            if not r.get(f):
                problems.append(f"{rid}: missing {f}")
        if st in ("verified", "verified-single-member", "partial"):
            if not r.get("implementation"):
                problems.append(f"{rid}: {st} without implementation references")
            if not r.get("tests") and not r.get("evidence"):
                problems.append(f"{rid}: {st} without tests or evidence")
        if st in ("partial", "blocked-external", "verified-single-member") and not r.get("exception"):
            problems.append(f"{rid}: {st} requires an exception id")
        for ex in ([r["exception"]] if r.get("exception") else []):
            if ex not in exceptions:
                problems.append(f"{rid}: unknown exception {ex}")
        for ref in r.get("implementation", []):
            if not symbol_exists(ref):
                problems.append(f"{rid}: broken implementation ref {ref}")
        for t in r.get("tests", []):
            if t not in tids:
                problems.append(f"{rid}: unknown test id {t}")
        for e in r.get("evidence", []):
            if e.startswith("evidence/") and not require_generated:
                continue
            if not os.path.exists(os.path.join(PKG, e.split("#")[0])):
                problems.append(f"{rid}: missing evidence path {e}")
        if r.get("last_verified") != cv:
            problems.append(f"{rid}: stale evidence (last_verified {r.get('last_verified')} != {cv})")
    return problems


def render_trace_md(matrix: dict[str, Any]) -> str:
    lines = ["# Requirements-to-evidence traceability matrix", "",
             f"Generated from `traceability/trace_matrix.json` for version {matrix.get('version')}. "
             "Do not edit by hand (`python tools/build_trace.py`).", "",
             "| ID | Status | Implementation | Tests | Evidence | Exception |", "|---|---|---|---|---|---|"]
    for r in matrix["rows"]:
        lines.append(f"| {r['id']} | {r['status']} | {'<br>'.join(r.get('implementation', []))} | "
                     f"{len(r.get('tests', []))} tests | {'<br>'.join(r.get('evidence', []))} | {r.get('exception', '')} |")
    counts: dict[str, int] = {}
    for r in matrix["rows"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    lines += ["", "Status totals: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())), ""]
    return "\n".join(lines)


# ------------------------------------------------------------------ MASTER.md (MC-002)

MASTER_REQUIRED_SECTIONS = ["Purpose", "Scope", "Workflow", "Gates", "Traceability"]
_NEGATION = re.compile(r"\b(not present|absent|previously|removed|missing|deprecat|no longer|was not)", re.I)
_CLAIM = re.compile(r"MASTER\.md[^\n]{0,80}\b(included|bundled|present in this archive|see MASTER\.md)\b", re.I)


def check_master_md() -> list[str]:
    problems = []
    master = os.path.join(PKG, "MASTER.md")
    exists = os.path.exists(master)
    for root, dirs, files in os.walk(PKG):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for f in files:
            if f.endswith(".md") and f != "MASTER.md":
                p = os.path.join(root, f)
                with open(p, encoding="utf-8") as fh:
                    txt = fh.read()
                if exists:
                    continue
                for line in txt.splitlines():
                    if _CLAIM.search(line) and not _NEGATION.search(line):
                        problems.append(f"{rel(p)} claims MASTER.md is present but it is absent: {line.strip()[:100]}")
    if exists:
        with open(master, encoding="utf-8") as fh:
            txt = fh.read()
        for s in MASTER_REQUIRED_SECTIONS:
            if not re.search(rf"^#+\s*{s}\b", txt, re.M):
                problems.append(f"MASTER.md missing required section '{s}'")
        prov_p = os.path.join(PKG, "traceability", "master_md_provenance.json")
        if not os.path.exists(prov_p):
            problems.append("MASTER.md present without traceability/master_md_provenance.json")
        else:
            prov = load_json("traceability/master_md_provenance.json")
            if prov.get("sha256") != hashlib.sha256(txt.encode()).hexdigest():
                problems.append("MASTER.md hash does not match provenance record")
    return problems


# ------------------------------------------------------------------ exceptions register (MC-052-03)

def check_exceptions(today: _dt.date | None = None) -> list[str]:
    today = today or _dt.date.today()
    problems = []
    for e in load_json("docs/EXCEPTIONS.json")["exceptions"]:
        for f in ("id", "title", "rationale", "compensating_control", "owner", "expires", "status"):
            if not e.get(f):
                problems.append(f"{e.get('id')}: missing {f}")
        if e.get("status") == "open" and _dt.date.fromisoformat(e["expires"]) < today:
            problems.append(f"{e['id']}: expired on {e['expires']}")
    return problems


# ------------------------------------------------------------------ manifests, SBOM, provenance (MC-048/049)

def source_files() -> list[str]:
    out = []
    for root, dirs, files in os.walk(PKG):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        for f in sorted(files):
            if f.endswith((".pyc",)) or f == "MANIFEST.sha256":
                continue
            out.append(os.path.join(root, f))
    return out


def digest_file(p: str) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest() -> dict[str, str]:
    return {rel(p): digest_file(p) for p in source_files()}


def tree_digest(m: dict[str, str] | None = None) -> str:
    m = m or manifest()
    return hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in sorted(m.items())).encode()).hexdigest()


def sbom() -> dict[str, Any]:
    """CycloneDX 1.5 JSON SBOM (MC-049-02)."""
    comps = [
        {"type": "library", "name": "cryptography", "version": "46.0.7", "purl": "pkg:pypi/cryptography@46.0.7",
         "licenses": [{"expression": "Apache-2.0 OR BSD-3-Clause"}], "scope": "optional",
         "description": "AES-GCM at-rest encryption (required when storage.encrypt_at_rest=true)"},
        {"type": "library", "name": "cffi", "version": "2.0.0", "purl": "pkg:pypi/cffi@2.0.0",
         "licenses": [{"license": {"id": "MIT"}}], "scope": "optional"},
        {"type": "library", "name": "pycparser", "version": "3.0", "purl": "pkg:pypi/pycparser@3.0",
         "licenses": [{"license": {"id": "BSD-3-Clause"}}], "scope": "optional"},
        {"type": "framework", "name": "pk_core", "version": load_json("deploy/pk_core_pin.json").get("version") or "UNPINNED",
         "scope": "excluded", "description": "External certification framework; not bundled (EX-003)"},
        {"type": "platform", "name": "python", "version": ">=3.10,<3.14", "licenses": [{"license": {"id": "PSF-2.0"}}]},
    ]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
            "metadata": {"component": {"type": "application", "name": "inv05-current-control-state-system",
                                       "version": version(),
                                       "hashes": [{"alg": "SHA-256", "content": tree_digest()}]}},
            "components": comps}


def sign(obj: Any, key: bytes) -> str:
    return hmac.new(key, json.dumps(obj, sort_keys=True).encode(), hashlib.sha256).hexdigest()


def provenance(test_report: dict[str, Any] | None = None) -> dict[str, Any]:
    """SLSA v1-style provenance statement (unsigned body; signed by ci_gate)."""
    return {"_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": "inv05_current_control_state_system", "digest": {"sha256": tree_digest()}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": {"buildDefinition": {"buildType": "inv05/ci_gate@1",
                                              "externalParameters": {"version": version()},
                                              "resolvedDependencies": [{"uri": "pkg:pypi/cryptography@46.0.7"}]},
                          "runDetails": {"builder": {"id": os.environ.get("INV05_BUILDER_ID", "local-unverified")},
                                         "metadata": {"invocationId": os.environ.get("GITHUB_RUN_ID", "local"),
                                                      "startedOn": _dt.datetime.now(_dt.timezone.utc).isoformat()}},
                          "tests": test_report or {}}}
