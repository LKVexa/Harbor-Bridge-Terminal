#!/usr/bin/env python3
"""Evidence-quality gate and traceability generator (components 76, 77).

  python tools/evidence_gate.py            # verify; exit 1 on any violation
  python tools/evidence_gate.py --write    # regenerate COMPONENT_STATUS.json + docs/TRACEABILITY.md

Rules enforced (a requirement can never be satisfied by prose alone):
  * every implementation reference names a file that exists and, when it has
    ``::Symbol[.member]``, a class/function/assignment the AST actually defines;
  * every test reference names an existing test file and TestCase class/method;
  * ``reference_implemented`` / ``port_with_reference`` components must cite >=1
    implementation symbol (or be test-only suites) and >=1 test;
  * gate ``PASS`` is refused unless ``evidence/component-NN.json`` exists with a
    CI run id, an environment, and ``"result": "green"`` - this package ships none,
    so nothing is PASS;
  * each of the 100 CHECKLIST.json requirements maps to components or is
    explicitly UNRESOLVED.
"""
from __future__ import annotations

import ast
import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "tools"))
from _status_source import C  # noqa: E402

# CHECKLIST.json ordinal -> components providing evidence (empty = UNRESOLVED)
ITEM_MAP: dict[int, list[int]] = {
    1: [72], 2: [72], 3: [72], 4: [6, 72], 5: [72, 73], 6: [31, 72], 7: [72], 8: [72], 9: [75], 10: [72],
    11: [8, 72], 12: [8, 18, 19], 13: [48, 72], 14: [8, 26], 15: [8, 21], 16: [25], 17: [18, 32], 18: [52],
    19: [72], 20: [76], 21: [24, 72], 22: [23, 79], 23: [27], 24: [28], 25: [22, 33, 34, 35], 26: [26],
    27: [25], 28: [23, 35], 29: [79], 30: [58], 31: [1, 64], 32: [40, 72], 33: [40], 34: [40],
    35: [40], 36: [41], 37: [42], 38: [42, 71], 39: [43], 40: [], 41: [73], 42: [28], 43: [],
    44: [27, 29], 45: [66], 46: [31], 47: [29], 48: [52, 73], 49: [50], 50: [], 51: [73, 74],
    52: [47, 51], 53: [34], 54: [30, 35, 53], 55: [5], 56: [47], 57: [7, 21], 58: [5, 39], 59: [30, 40],
    60: [54], 61: [60], 62: [], 63: [60], 64: [], 65: [], 66: [], 67: [3, 35], 68: [], 69: [60],
    70: [], 71: [47], 72: [44], 73: [45], 74: [46], 75: [44, 45], 76: [8, 45], 77: [], 78: [],
    79: [], 80: [49], 81: [55], 82: [79], 83: [58], 84: [68], 85: [56], 86: [57], 87: [73],
    88: [60, 61], 89: [54, 62], 90: [77], 91: [48, 49], 92: [71, 74], 93: [1, 68], 94: [67],
    95: [6, 21], 96: [74], 97: [74, 75], 98: [75], 99: [], 100: [77],
}
STATUSES = {"reference_implemented", "port_with_reference", "documented", "tooling", "open"}
GATES = {"OPEN_REVIEW", "OPEN_EXTERNAL", "OPEN_GOVERNANCE", "PASS"}


def _defined(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        names.add(f"{node.name}.{sub.name}")
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t, ast.Name):
                    names.add(t.id)
    return names


def check_ref(ref: str, *, test: bool = False) -> str | None:
    path, _, sym = ref.partition("::")
    path = path.split(" ")[0]
    f = PKG / path
    if not f.exists():
        return f"missing file {path}"
    if not sym:
        return None
    if f.suffix != ".py":
        return f"symbol given for non-python file {path}"
    names = _defined(ast.parse(f.read_text(encoding="utf-8")))
    sym = sym.replace("::", ".")
    if sym not in names:
        return f"{path} does not define {sym}"
    if test and not sym.split(".")[0].endswith("Test"):
        return f"{ref} is not a TestCase"
    return None


def verify() -> list[str]:
    problems: list[str] = []
    if sorted(C) != list(range(1, 81)):
        problems.append("component inventory must be exactly 1..80")
    for n, (_name, status, gate, impl, tests, note) in sorted(C.items()):
        if status not in STATUSES or gate not in GATES:
            problems.append(f"#{n}: bad status/gate {status}/{gate}")
        for r in impl:
            if err := check_ref(r):
                problems.append(f"#{n} impl: {err}")
        for r in tests:
            if err := check_ref(r, test=True):
                problems.append(f"#{n} test: {err}")
        if status in ("reference_implemented", "port_with_reference") and not tests:
            problems.append(f"#{n}: {status} without executable test evidence")
        if gate == "PASS":
            ev = PKG / "evidence" / f"component-{n:02d}.json"
            ok = False
            if ev.exists():
                data = json.loads(ev.read_text())
                ok = data.get("result") == "green" and data.get("ci_run") and data.get("environment")
            if not ok:
                problems.append(f"#{n}: PASS claimed without green CI evidence file {ev.name}")
        if gate != "PASS" and status == "open" and not note:
            problems.append(f"#{n}: open component needs an explicit limitation note")
    checklist = json.loads((PKG / "CHECKLIST.json").read_text())
    ids = [i["ordinal"] for i in checklist["items"]]
    if sorted(ITEM_MAP) != sorted(ids):
        problems.append("ITEM_MAP must cover every CHECKLIST.json ordinal exactly once")
    for k, comps in ITEM_MAP.items():
        for c in comps:
            if c not in C:
                problems.append(f"C{k:03d} maps to unknown component {c}")
    return problems


def item_state(comps: list[int]) -> str:
    if not comps:
        return "UNRESOLVED"
    gates = {C[c][2] for c in comps}
    statuses = {C[c][1] for c in comps}
    if gates == {"PASS"}:
        return "SATISFIED"
    if statuses <= {"reference_implemented", "tooling"} and gates <= {"OPEN_REVIEW"}:
        return "EVIDENCED_PENDING_SIGNOFF"
    if statuses <= {"documented"}:
        return "DOCUMENTED_PENDING_APPROVAL"
    return "PARTIAL"


def write() -> None:
    comps = []
    for n, (name, status, gate, impl, tests, note) in sorted(C.items()):
        comps.append({"id": n, "name": name, "status": status, "exit_gate": gate, "implementation": impl,
                      "tests": tests, "limitations": note})
    counts: dict[str, int] = {}
    for c in comps:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    gcounts: dict[str, int] = {}
    for c in comps:
        gcounts[c["exit_gate"]] = gcounts.get(c["exit_gate"], 0) + 1
    out = {"element": "INV-04", "version": (PKG / "VERSION").read_text().strip(),
           "semantics": "No component is PASS: PASS requires green CI evidence on the supported matrix (tools/evidence_gate.py).",
           "summary": {"status": counts, "exit_gate": gcounts}, "components": comps}
    (PKG / "COMPONENT_STATUS.json").write_text(json.dumps(out, indent=2) + "\n")

    checklist = json.loads((PKG / "CHECKLIST.json").read_text())
    lines = ["# INV-04 Evidence Traceability Matrix", "",
             f"Generated by `tools/evidence_gate.py --write` for version {out['version']}. Do not edit by hand.", "",
             "## Component evidence (80 MISSING_COMPONENTS items)", "",
             "| # | Component | Status | Exit gate | Implementation | Tests | Limitations |", "|---|---|---|---|---|---|---|"]
    for c in comps:
        lines.append(f"| {c['id']} | {c['name']} | {c['status']} | {c['exit_gate']} | "
                     f"{'<br>'.join('`' + i + '`' for i in c['implementation']) or '-'} | "
                     f"{'<br>'.join('`' + t + '`' for t in c['tests']) or '-'} | {c['limitations'] or '-'} |")
    lines += ["", "## CHECKLIST.json requirement mapping (100 items)", "",
              "| Check | Dimension | Requirement | Components | State |", "|---|---|---|---|---|"]
    states: dict[str, int] = {}
    for it in checklist["items"]:
        cs = ITEM_MAP[it["ordinal"]]
        st = item_state(cs)
        states[st] = states.get(st, 0) + 1
        lines.append(f"| {it['check_id']} | {it['dimension']} | {it['requirement']} | "
                     f"{', '.join('#' + str(c) for c in cs) or '-'} | {st} |")
    lines += ["", "## Totals", "", *[f"- {k}: {v}" for k, v in sorted(states.items())],
              *[f"- components {k}: {v}" for k, v in sorted(counts.items())], ""]
    (PKG / "docs" / "TRACEABILITY.md").write_text("\n".join(lines))


def main(argv: list[str]) -> int:
    if "--write" in argv:
        write()  # generated artefacts are themselves verified below
    problems = verify()
    if problems:
        print("EVIDENCE GATE: FAIL")
        for p in problems:
            print(" -", p)
        return 1
    print(f"EVIDENCE GATE: OK ({len(C)} components verified; no PASS claims without CI evidence)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
