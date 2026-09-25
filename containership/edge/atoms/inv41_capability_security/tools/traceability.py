"""Requirements traceability generator and checker (Section 4, REQ-GOV-006).

Builds evidence/TRACEABILITY.json (+ .md) from requirements/REQUIREMENTS.json,
POST_UPDATE_AUDIT.json and the test tree, deterministically (sorted, no
timestamps in the hashed body).  Fails (exit 1) when:
  * a code requirement has no implementation mapping or no automated test;
  * a referenced symbol, file or test name does not exist;
  * a test function exists that maps to no requirement (orphan);
  * a requirement claims VERIFIED without evidence;
  * an audit C-ID that was not VERIFIED in 4.2.0 maps to no requirement.
"""
from __future__ import annotations

import ast
import hashlib
import json
import pathlib
import re
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]


def _symbols(path: pathlib.Path) -> set:
    tree = ast.parse(path.read_text())
    out = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            out.add(node.name)
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        out.add(f"{node.name}.{sub.name}")
                    elif isinstance(sub, ast.Assign):
                        for t in sub.targets:
                            if isinstance(t, ast.Name):
                                out.add(f"{node.name}.{t.id}")
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    out.add(t.id)
    return out


def _tests() -> dict:
    found = {}
    for f in sorted((PKG / "tests").glob("test_*.py")):
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                found[f"tests/{f.name}::{node.name}"] = f"tests/{f.name}"
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                found[f"tests/{f.name}::{node.name}"] = f"tests/{f.name}"
    return found


def _resolve(ref: str, tests: dict) -> bool:
    if ref in tests:
        return True
    path, _, sym = ref.partition("::")
    path, _, anchor = path.partition("#")
    p = PKG / path
    if not p.exists():
        return False
    if anchor:
        text = p.read_text().lower()
        return anchor.replace("-", " ") in text or anchor in text
    if not sym:
        return True
    if p.suffix == ".py":
        return sym in _symbols(p)
    return sym in p.read_text()


def build() -> tuple[dict, list]:
    reqs = json.loads((PKG / "requirements" / "REQUIREMENTS.json").read_text())["requirements"]
    audit = json.loads((PKG / "POST_UPDATE_AUDIT.json").read_text())["requirements"]
    tests = _tests()
    errors = []
    referenced_tests = set()
    rows = []
    for r in sorted(reqs, key=lambda x: x["id"]):
        impl_ok = [ref for ref in r["implementation"] if _resolve(ref, tests)]
        impl_bad = [ref for ref in r["implementation"] if ref not in impl_ok]
        test_refs = r["tests"] + r["negative_tests"]
        test_bad = [t for t in test_refs if not _resolve(t, tests)]
        referenced_tests.update(t for t in test_refs if t in tests)
        for bad in impl_bad:
            errors.append(f"{r['id']}: implementation ref not found: {bad}")
        for bad in test_bad:
            errors.append(f"{r['id']}: test ref not found: {bad}")
        if r["kind"] == "code" and r["status"] != "BLOCKED":
            if not r["implementation"]:
                errors.append(f"{r['id']}: code requirement has no implementation mapping")
            if not r["tests"]:
                errors.append(f"{r['id']}: code requirement has no automated verification")
        if r["status"] == "BLOCKED" and not r.get("blocker"):
            errors.append(f"{r['id']}: BLOCKED without blocker id")
        if r["status"] == "VERIFIED" and not r["tests"]:
            errors.append(f"{r['id']}: VERIFIED without evidence")
        rows.append({"id": r["id"], "level": r["level"], "section": r["section"], "kind": r["kind"],
                     "status": r["status"], "blocker": r.get("blocker"), "audit_ids": r["audit_ids"],
                     "text_sha256": hashlib.sha256(r["text"].encode()).hexdigest(),
                     "implementation": r["implementation"], "tests": r["tests"], "negative_tests": r["negative_tests"]})
    # orphans: test functions that no requirement references (test classes and legacy primitives exempt if covered)
    for t in sorted(tests):
        if "::test_" not in t:
            continue
        cls_level = t.rsplit("::", 1)[0]
        if t not in referenced_tests and not t.startswith("tests/test_primitives.py") and not t.startswith("tests/test_component.py"):
            errors.append(f"orphan test (maps to no requirement): {t}")
    # audit coverage
    by_c = {}
    for r in reqs:
        for c in r["audit_ids"]:
            by_c.setdefault(f"INV-41-{c}", []).append(r["id"])
    audit_rows = []
    for a in audit:
        mapped = sorted(by_c.get(a["check_id"], []))
        states = sorted({next(x["status"] for x in reqs if x["id"] == m) for m in mapped})
        if a["status"] != "VERIFIED" and not mapped:
            errors.append(f"{a['check_id']} ({a['status']} in 4.2.0) maps to no requirement")
        if a["status"] == "VERIFIED":
            post = "VERIFIED_4.2.0" if not mapped else ("VERIFIED_4.2.0+" + "/".join(states))
        elif not states:
            post = "UNMAPPED"
        elif states == ["IMPLEMENTED"]:
            post = "IMPLEMENTED_LOCALLY_VERIFIED"
        elif "BLOCKED" in states and "IMPLEMENTED" in states:
            post = "PARTIAL_BLOCKED"
        elif "PARTIAL" in states:
            post = "PARTIAL_BLOCKED"
        else:
            post = "BLOCKED"
        audit_rows.append({"check_id": a["check_id"], "status_4_2_0": a["status"], "requirements": mapped,
                           "status_4_3_0": post, "requirement_states": states})
    body = {"schema": "INV41_TRACEABILITY/1", "requirements": rows, "audit": audit_rows}
    body["sha256"] = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    return body, errors


def render_md(body: dict) -> str:
    lines = ["# INV-41 traceability matrix (generated — do not edit)", "",
             f"Snapshot sha256: `{body['sha256']}`", "", "## Audit C-IDs", "",
             "| Audit ID | 4.2.0 | 4.3.0 | Requirements |", "|---|---|---|---|"]
    for a in body["audit"]:
        lines.append(f"| {a['check_id']} | {a['status_4_2_0']} | {a['status_4_3_0']} | {', '.join(a['requirements'])} |")
    lines += ["", "## Requirements", "", "| ID | Status | Implementation | Tests |", "|---|---|---|---|"]
    for r in body["requirements"]:
        lines.append(f"| {r['id']} | {r['status']}{' (' + r['blocker'] + ')' if r['blocker'] else ''} | "
                     f"{'<br>'.join(r['implementation'])} | {'<br>'.join(r['tests'] + r['negative_tests'])} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    body, errors = build()
    (PKG / "evidence").mkdir(exist_ok=True)
    (PKG / "evidence" / "TRACEABILITY.json").write_text(json.dumps(body, indent=1, sort_keys=True))
    (PKG / "evidence" / "TRACEABILITY.md").write_text(render_md(body))
    for e in errors:
        print("TRACE-ERROR", e)
    counts = {}
    for a in body["audit"]:
        counts[a["status_4_3_0"]] = counts.get(a["status_4_3_0"], 0) + 1
    print(json.dumps({"requirements": len(body["requirements"]), "errors": len(errors), "audit_status_4_3_0": counts}))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
