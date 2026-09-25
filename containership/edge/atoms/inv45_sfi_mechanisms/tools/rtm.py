"""Requirements traceability: check and generate (C020, C090).

    python tools/rtm.py check      # CI: fails on orphan/stale links (exit 1)
    python tools/rtm.py generate   # writes docs/requirements/TRACEABILITY.md and CHECKLIST_AUDIT.json

Checks (all must hold):

1. all 100 ``INV-45-Cxxx`` items present exactly once, statuses from the vocabulary;
2. every design path exists (the part before ``#``);
3. every symbol ``pkg.module:name`` is defined at top level of that file (AST check - works without pk_core);
4. every test id ``tests.<module>.<Class>`` exists as a class in that test file;
5. no orphan tests: every test class under ``tests/`` is referenced by some requirement, or listed in
   ``SUPPORTING_TESTS`` with a reason;
6. ``engineered_unreviewed`` / ``implemented`` items (except pre-existing documentation items) have at
   least one test, and every non-complete item states a blocker;
7. every Critical/High threat in THREAT_MODEL.md names at least one existing test class;
8. every ``S-*`` requirement id defined in SPEC.md is unique.

The generated CHECKLIST_AUDIT.json is derived from the registry, never hand-edited.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "requirements" / "requirements.json"
DOC_ONLY_OK = {"C001", "C002", "C003", "C004", "C006", "C007", "C019", "C051", "C055", "C064", "C065", "C069",
               "C079", "C096"}  # definitional items whose evidence is the document itself (+ benchmark output)
SUPPORTING_TESTS = {
    "tests.test_component.ConformanceTest": "pk_core 100-item gate (lane NOT RUN without pk_core)",
    "tests.unit.test_wasm_parser.LebTest": "decoder building block of C046/C085",
    "tests.unit.test_wasm_parser.ValidationTest": "type validation building block of C046",
    "tests.unit.test_wasm_parser.EncodeTest": "encoder building block of the rewriter (C031)",
    "tests.unit.test_sfi_rewriter_verifier.ProfileAndPolicyTest": "policy checks of C046/C024",
    "tests.unit.test_ops_modules.TrustTest": "secret refs and key windows (C039/C048)",
}


def _defined(path: Path, name: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.name == name:
            return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                return True
    return False


def _test_classes() -> set[str]:
    out = set()
    for p in (ROOT / "tests").rglob("test_*.py"):
        mod = ".".join(p.relative_to(ROOT).with_suffix("").parts)
        for node in ast.parse(p.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_") and any(
                    isinstance(b, (ast.Attribute, ast.Name)) for b in node.bases):
                if any(isinstance(n, ast.FunctionDef) and n.name.startswith("test") for n in node.body):
                    out.add(f"{mod}.{node.name}")
    return out


def _test_methods() -> set[str]:
    out = set()
    for p in (ROOT / "tests").rglob("test_*.py"):
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                out.add(node.name)
    return out


def load() -> dict:
    return json.loads(REG.read_text())


def check() -> list[str]:
    reg = load()
    errs: list[str] = []
    vocab = set(reg["status_vocabulary"])
    ids = [r["id"] for r in reg["requirements"]]
    if sorted(ids) != [f"INV-45-C{i:03d}" for i in range(1, 101)]:
        errs.append("requirement ids are not exactly INV-45-C001..C100")
    tests = _test_classes()
    referenced: set[str] = set()
    for r in reg["requirements"]:
        rid = r["id"]
        if r["status"] not in vocab:
            errs.append(f"{rid}: unknown status {r['status']}")
        for d in r["design"]:
            if not (ROOT / d.split("#")[0]).exists():
                errs.append(f"{rid}: design link missing: {d}")
        for s in r["symbols"]:
            mod, _, name = s.partition(":")
            f = ROOT / (mod.replace(".", "/") + ".py")
            if not f.exists() or not _defined(f, name):
                errs.append(f"{rid}: stale symbol {s}")
        for t in r["tests"]:
            referenced.add(t)
            if t not in tests:
                errs.append(f"{rid}: test id does not exist: {t}")
        short = rid[-4:]
        if r["status"] in ("engineered_unreviewed", "implemented") and not r["tests"] and short not in DOC_ONLY_OK:
            errs.append(f"{rid}: {r['status']} without any test")
        if r["status"] not in ("engineered_unreviewed", "implemented") and not r.get("blocker"):
            errs.append(f"{rid}: {r['status']} without a stated blocker")
    for t in sorted(tests - referenced - set(SUPPORTING_TESTS)):
        errs.append(f"orphan test class (not traced to any requirement): {t}")
    for t in SUPPORTING_TESTS:
        if t not in tests:
            errs.append(f"supporting test id does not exist: {t}")
    tm = (ROOT / "docs/security/THREAT_MODEL.md").read_text()
    all_classes = {t.rsplit(".", 1)[1] for t in tests} | _test_methods()
    for line in tm.splitlines():
        m = re.match(r"\| (T\d\d) \|[^|]*\| ([CH]) \|", line)
        if m:
            named = set(re.findall(r"`([A-Za-z0-9_]+)(?:\.[a-z_0-9]+)?`", line.split("|")[-2]))
            if not (named & all_classes):
                if "ACCEPTED-PENDING" not in line:
                    errs.append(f"threat {m.group(1)} (sev {m.group(2)}) has no existing test class")
    spec = (ROOT / "docs/requirements/SPEC.md").read_text()
    sids = re.findall(r"(?:^\| |\n)(S-[A-Z]+-\d\d)", spec)
    dup = [k for k, v in Counter(sids).items() if v > 1]
    if dup:
        errs.append(f"duplicate SPEC ids: {dup}")
    return errs


def generate() -> None:
    reg = load()
    rows = ["# Requirements traceability matrix", "",
            "Generated by `tools/rtm.py generate` from `requirements/requirements.json`; do not edit by hand.",
            "Reference-model evidence (`sfi_core.py`) is labelled separately from production-enforcement evidence.", "",
            "| Id | Status (4.2.0 → 4.3.0) | Design | Implementation | Tests | Evidence kind | Owner | Blocker |",
            "|---|---|---|---|---|---|---|---|"]
    for r in reg["requirements"]:
        rows.append("| {} | {} → **{}** | {} | {} | {} | {} | {} | {} |".format(
            r["id"][-4:], r["status_4_2_0"], r["status"], "<br>".join(r["design"]),
            "<br>".join(f"`{s}`" for s in r["symbols"]) or "—",
            "<br>".join(f"`{t.split('.', 1)[1]}`" for t in r["tests"]) or "—",
            r["evidence_kind"], r["owner"], r["blocker"] or ""))
    c = Counter(r["status"] for r in reg["requirements"])
    rows += ["", "## Summary", ""] + [f"* {k}: {v}" for k, v in sorted(c.items())] + [
        "", "## Reverse map (test → requirements)", ""]
    rev: dict[str, list[str]] = {}
    for r in reg["requirements"]:
        for t in r["tests"]:
            rev.setdefault(t, []).append(r["id"][-4:])
    for t in sorted(rev):
        rows.append(f"* `{t}` → {', '.join(rev[t])}")
    for t, why in sorted(SUPPORTING_TESTS.items()):
        rows.append(f"* `{t}` → supporting: {why}")
    (ROOT / "docs/requirements/TRACEABILITY.md").write_text("\n".join(rows) + "\n")
    audit = {"element": "INV-45", "version": reg["version"],
             "scope": "repository-local evidence in the 4.3.0 archive; derived from requirements/requirements.json",
             "status_vocabulary": reg["status_vocabulary"],
             "summary": dict(sorted(c.items())),
             "certified_for_production": False,
             "certification_blockers": ["no accountable owners bound (C009)", "ADR not approved (C010)",
                                        "pk_core gate NOT RUN (A2)", "perf gate FAIL on PERF-01 (C070)",
                                        "waivers pending approval (C099)", "no release approver (C100)"],
             "items": [{"check_id": r["id"], "status": r["status"], "status_4_2_0": r["status_4_2_0"],
                        "dimension": r["dimension"], "requirement": r["requirement"],
                        "tests": r["tests"], "blocker": r["blocker"]} for r in reg["requirements"]]}
    (ROOT / "CHECKLIST_AUDIT.json").write_text(json.dumps(audit, indent=2) + "\n")
    open_rows = [r for r in reg["requirements"] if r["status"] not in ("implemented", "engineered_unreviewed")]
    md = ["# Remaining components - INV-45 v4.3.0", "",
          "Generated by `tools/rtm.py generate` from `requirements/requirements.json`; do not edit by hand.", "",
          "Status: " + ", ".join(f"**{v} {k}**" for k, v in sorted(c.items())) + ".",
          "No item is certified for production: `engineered_unreviewed` items still need the owner/security "
          "review that the completion standard requires, and the exit gate (`tools/release.py gate`) is NO_GO.", "",
          "## Items that are not engineering-complete", "",
          "| Id | Status | Requirement | Blocker |", "|---|---|---|---|"]
    md += [f"| {r['id'][-4:]} | {r['status']} | {r['requirement']} | {r['blocker']} |" for r in open_rows]
    md += ["", "## Engineering-complete items with a noted limitation", "",
           "| Id | Limitation |", "|---|---|"]
    md += [f"| {r['id'][-4:]} | {r['blocker']} |" for r in reg["requirements"]
           if r["status"] == "engineered_unreviewed" and r["blocker"]]
    md += ["", "## Non-checklist artifacts (A1-A6)", "",
           "| Artifact | 4.3.0 state |", "|---|---|",
           "| A1 MASTER.md | present; doc-link lane |",
           "| A2 pk_core dependency | declared UNRESOLVED; package importable without it; gate lane NOT RUN (W-07) |",
           "| A3 production rewriter/loader | present in `production/` (Wasm-level; native properties delegated to the engine, W-08) |",
           "| A4 CI/release workflow | `tools/ci.py`, `.github/workflows/ci.yml` (matrix defined; only linux/3.11/node22 run here) |",
           "| A5 SBOM/provenance/manifest | generated by `tools/release.py`; signature is NONPRODUCTION-EPHEMERAL |",
           "| A6 license/ownership | no license selected (LICENSE-STATUS.md); CODEOWNERS placeholders; OWNERSHIP roles UNASSIGNED |", ""]
    (ROOT / "MISSING_COMPONENTS.md").write_text("\n".join(md))


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "generate":
        generate()
        print("generated TRACEABILITY.md and CHECKLIST_AUDIT.json")
        return 0
    errs = check()
    for e in errs:
        print("RTM:", e)
    print("RTM OK" if not errs else f"RTM FAILED ({len(errs)} problems)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
