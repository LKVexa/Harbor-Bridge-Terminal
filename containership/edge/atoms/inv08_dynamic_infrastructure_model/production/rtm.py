"""Component 12 - requirements traceability matrix (PK_DYN_RTM/1).

Inputs: ``requirements.json`` (component 11), every ``components/*.json`` written by
any overlay builder (tolerant: malformed files are reported, never fatal) and
``CHECKLIST.json`` (100 C-controls).  Output rows link
requirement -> controls -> design -> code -> tests -> evidence, plus:

* orphan requirements   (no code link)
* unverified requirements (no tests, or listed test ids not resolvable)
* uncovered controls    (C-control with no requirement)
* component sub-parts   with no tests / non-IMPLEMENTED state / unresolvable tests

Test ids are resolved statically (module file exists and contains ``def name``) so
the RTM never imports or runs other builders' code.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .core import digest

PROD = Path(__file__).resolve().parent
PKG = PROD.parent
ROOT = PKG.parent
REQ_RE = re.compile(r"^REQ-INV08-\d{3}$")


def load_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_test(test_id: str, root: Path = ROOT) -> bool:
    """True when ``pkg.mod[.Class[.method]]`` names a module file containing that class/def."""
    parts = test_id.split(".")
    for i in range(len(parts), 0, -1):
        f = root.joinpath(*parts[:i]).with_suffix(".py")
        if not f.is_file():
            continue
        rest = parts[i:]
        if len(rest) > 2:
            return False
        src = f.read_text(encoding="utf-8")
        if rest and not re.search(rf"^class {re.escape(rest[0])}\b", src, re.M):
            return False
        if len(rest) == 2 and not re.search(rf"^\s+def {re.escape(rest[1])}\(", src, re.M):
            return False
        return True
    return False


def validate_requirements(doc: dict) -> list[str]:
    p = []
    seen = set()
    for r in doc.get("requirements", []):
        rid = r.get("id", "")
        if not REQ_RE.match(rid):
            p.append(f"bad id {rid!r}")
        if rid in seen:
            p.append(f"duplicate id {rid}")
        seen.add(rid)
        if " SHALL " not in f" {r.get('text', '')} ":
            p.append(f"{rid}: text lacks SHALL")
        if not isinstance(r.get("version"), int) or r["version"] < 1:
            p.append(f"{rid}: version must be int >= 1")
    return p


def check_change_control(doc: dict, baseline: dict) -> list[str]:
    """Compare against a previous baseline: changed text needs version bump; ids never reused/removed silently."""
    p = []
    old = {r["id"]: r for r in baseline.get("requirements", [])}
    new = {r["id"]: r for r in doc.get("requirements", [])}
    for rid, o in old.items():
        n = new.get(rid)
        if n is None:
            if doc.get("version", "0").split(".")[0] == baseline.get("version", "0").split(".")[0]:
                p.append(f"{rid} removed without major version bump")
            continue
        strip = lambda r: {k: v for k, v in r.items() if k not in {"version", "tests", "code", "design"}}
        if digest(strip(o)) != digest(strip(n)) and n["version"] <= o["version"]:
            p.append(f"{rid} changed without per-requirement version bump")
    if digest(doc.get("requirements")) != digest(baseline.get("requirements")) and \
            doc.get("version") == baseline.get("version"):
        p.append("requirement set changed without set version bump")
    return p


def load_components(cdir: Path) -> tuple[list[dict], list[str]]:
    comps, errs = [], []
    for f in sorted(Path(cdir).glob("*.json")):
        try:
            c = load_json(f)
            if not isinstance(c, dict) or "component" not in c or not isinstance(c.get("subparts"), list):
                raise ValueError("missing component/subparts")
            comps.append(c)
        except (ValueError, OSError) as exc:
            errs.append(f"{f.name}: {type(exc).__name__}: {exc}")
    return comps, errs


def build(requirements: dict, components_dir: Path, checklist: dict, *, root: Path = ROOT) -> dict:
    controls = [i["check_id"] for i in checklist.get("items", [])]
    comps, comp_errs = load_components(components_dir)
    rows, orphans, unverified = [], [], []
    covered: set[str] = set()
    for r in requirements.get("requirements", []):
        tests = r.get("tests", [])
        resolved = [t for t in tests if resolve_test(t, root)]
        covered |= set(r.get("controls", []))
        row = {"id": r["id"], "controls": r.get("controls", []), "design": r.get("design", []),
               "code": r.get("code", []), "tests": tests, "tests_resolved": len(resolved),
               "evidence": r.get("evidence", [])}
        rows.append(row)
        if not row["code"]:
            orphans.append(r["id"])
        if not tests or len(resolved) != len(tests):
            unverified.append(r["id"])
    sub_rows, sub_unverified = [], []
    for c in comps:
        for s in c["subparts"]:
            tests = s.get("tests") or []
            ok = [t for t in tests if resolve_test(t, root)]
            row = {"component": c["component"], "subpart": s.get("name"), "state": s.get("state"),
                   "spec": s.get("spec"), "modules": s.get("modules", []), "tests": len(tests),
                   "tests_resolved": len(ok)}
            sub_rows.append(row)
            if s.get("state") == "IMPLEMENTED" and (not tests or len(ok) != len(tests)):
                sub_unverified.append(f"{c['component']}:{s.get('name')}")
    return {"schema": "PK_DYN_RTM/1", "requirements_version": requirements.get("version"),
            "rows": rows, "orphan_requirements": orphans, "unverified_requirements": unverified,
            "uncovered_controls": [c for c in controls if c not in covered],
            "unknown_controls": sorted(covered - set(controls)),
            "component_rows": sub_rows, "component_errors": comp_errs,
            "implemented_but_unverified": sub_unverified,
            "coverage": {"controls_total": len(controls), "controls_covered": len(set(controls) & covered),
                         "requirements": len(rows), "components": len(comps)}}


def main(argv: list[str] | None = None) -> int:
    rtm = build(load_json(PROD / "requirements.json"), PROD / "components", load_json(PKG / "CHECKLIST.json"))
    print(json.dumps({k: rtm[k] for k in ("coverage", "orphan_requirements", "unverified_requirements",
                                          "implemented_but_unverified", "component_errors")}, indent=1))
    return 0 if not (rtm["orphan_requirements"] or rtm["unverified_requirements"]
                     or rtm["implemented_but_unverified"]) else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
