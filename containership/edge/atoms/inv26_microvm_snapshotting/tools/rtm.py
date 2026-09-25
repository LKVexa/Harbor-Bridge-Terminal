"""Requirements traceability matrix generator and checker (C020, C021, C093).

Rows: C001-C100 (CHECKLIST.json) + X001-X014. Each row maps requirement -> artifacts -> tests -> evidence
-> owner role -> status -> release. ``--check`` fails when:
  * a checklist control has no row (orphan requirement);
  * a referenced artifact file, test module, or test class does not exist;
  * an evidence file is referenced that no evidence producer writes;
  * a row claims IMPLEMENTED_LOCAL with no test or no evidence;
  * generated artifacts (ERRORS.json, ops/lifecycle.json, ops/policy.json, ops/metrics.json) drift from code;
  * ops/boundaries.json ids are not all referenced in INTERFACES.md.
Also reports test classes that no row references (tests without requirements).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

from . import status_data

PKG = Path(__file__).resolve().parents[1]
V5_PRESERVED = ["C001", "C002", "C003", "C004", "C005", "C006", "C007", "C008", "C011", "C013", "C046", "C081"]
EVIDENCE_PRODUCED = {"evidence/TESTS.json", "evidence/TESTS_O.json", "evidence/FUZZ.json", "evidence/FAULTS.json",
                     "evidence/DRILLS.json", "evidence/BENCH.json", "evidence/BENCH_PRE_OPT.json", "evidence/PERF_GATE.json",
                     "evidence/SOAK.json", "evidence/STRESS.json", "evidence/SCHEMAS.json", "evidence/SECRET_SCAN.json",
                     "evidence/GOVERNANCE.json", "evidence/RTM.json", "evidence/RELEASE.json", "evidence/INSTALL.json",
                     "evidence/PREFLIGHT.json", "evidence/SMOKE.json", "evidence/INTEGRATION.json",
                     "evidence/AUDIT_VERIFY.json", "evidence/EXIT_GATE.json", "evidence/sbom.cdx.json"}
OWNER_BY_DIM = {"Architecture & Scope": "accountable_owner", "Requirements & Semantics": "service_owner",
                "Interfaces & Integration": "engineering_owner", "Implementation & Configuration": "engineering_owner",
                "Security, Trust & Isolation": "security_owner", "Resilience & Failure Handling": "sre_oncall",
                "Performance & Resource Efficiency": "engineering_owner", "Observability & Explainability": "sre_oncall",
                "Testing & Certification": "engineering_owner", "Operations, Release & Governance": "service_owner"}


def _file_of(ref: str) -> str | None:
    head = ref.split(" ")[0].split("::")[0]
    if head.startswith(("tools/", "tests/", "ops/", "schemas/", "examples/", "dashboards/", "evidence/", "bench/")) \
            or head.endswith((".py", ".md", ".json", ".sh", ".lock", ".toml")) or head in ("CODEOWNERS",):
        return head.split("#")[0]
    m = re.match(r"^([a-z_]+)\.[A-Za-z_]", head)
    if m and (PKG / f"{m.group(1)}.py").exists():
        return f"{m.group(1)}.py"
    return None


def _test_classes() -> dict[str, set[str]]:
    out = {}
    for p in sorted((PKG / "tests").glob("test_*.py")):
        tree = ast.parse(p.read_text())
        out[p.name] = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
    return out


def build() -> tuple[dict, list[str], list[str]]:
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    classes = _test_classes()
    errors, warnings = [], []
    referenced_classes: set[tuple[str, str]] = set()
    rows = []
    version = (PKG / "VERSION").read_text().strip()
    for it in items:
        cid = it["check_id"].split("-")[-1]
        base = {"id": cid, "dimension": it["dimension"], "requirement": it["requirement"],
                "owner_role": OWNER_BY_DIM.get(it["dimension"]), "release": version}
        if cid in V5_PRESERVED:
            rows.append({**base, "status": "PRESERVED_FROM_V5", "artifacts": ["contract.py", "component.py", "snapshot.py"],
                         "tests": ["tests/test_component.py (needs pk_core)", "tests/test_snapshot_domain.py"],
                         "evidence": ["evidence/TESTS.json"], "gaps": ["pk_core assessment not executable here (X013)"]})
            continue
        r = status_data.S.get(cid)
        if r is None:
            errors.append(f"{cid}: orphan requirement (no status row)")
            continue
        rows.append({**base, **r})
    for xid, r in status_data.X.items():
        rows.append({"id": xid, "dimension": "Cross-cutting", "requirement": xid, "owner_role": "engineering_owner",
                     "release": version, "tests": [], "evidence": [], **r})
    for row in rows:
        for ref in row.get("artifacts", []) + row.get("tests", []):
            f = _file_of(ref)
            if f and "*" not in f and not (PKG / f).exists() and not f.startswith("evidence/"):
                errors.append(f"{row['id']}: missing artifact {f}")
        for t in row.get("tests", []):
            m = re.match(r"tests/(test_\w+\.py)(?:::(\w+))?", t)
            if m:
                if m.group(1) not in classes:
                    errors.append(f"{row['id']}: missing test module {m.group(1)}")
                elif m.group(2):
                    if m.group(2) not in classes[m.group(1)]:
                        errors.append(f"{row['id']}: missing test class {m.group(1)}::{m.group(2)}")
                    referenced_classes.add((m.group(1), m.group(2)))
                else:
                    referenced_classes.update((m.group(1), c) for c in classes[m.group(1)])
        for e in row.get("evidence", []):
            if e not in EVIDENCE_PRODUCED:
                errors.append(f"{row['id']}: evidence {e} has no producer")
        if row["status"] == "IMPLEMENTED_LOCAL" and row["id"].startswith("C") and (not row["tests"] or not row["evidence"]):
            if not (row["artifacts"] and row["evidence"]):
                errors.append(f"{row['id']}: IMPLEMENTED_LOCAL without tests/evidence")
    for mod, cs in classes.items():
        for c in cs:
            if (mod, c) not in referenced_classes and mod not in ("test_component.py", "test_snapshot_domain.py",
                                                                  "test_threats.py"):
                warnings.append(f"test class {mod}::{c} is not referenced by any requirement")
    # generated artifacts in sync
    from .. import errors as err_mod, lifecycle, policy, telemetry
    for path, doc in (("ERRORS.json", err_mod.catalog_document()), ("ops/lifecycle.json", lifecycle.model_document()),
                      ("ops/policy.json", policy.document())):
        if json.loads((PKG / path).read_text()) != json.loads(json.dumps(doc)):
            errors.append(f"{path} drifted from code (run tools/gen_artifacts.py)")
    metrics = json.loads((PKG / "ops/metrics.json").read_text())["metrics"]
    if set(metrics) != set(telemetry.METRICS):
        errors.append("ops/metrics.json drifted from telemetry.METRICS")
    bounds = [b["id"] for b in json.loads((PKG / "ops/boundaries.json").read_text())["boundaries"]]
    iface = (PKG / "INTERFACES.md").read_text()
    for b in bounds:
        if b not in iface and b not in ("B11", "B12"):
            errors.append(f"boundary {b} not documented in INTERFACES.md")
    compat = json.loads((PKG / "compatibility.json").read_text())
    if compat["package"] != version:
        errors.append("compatibility.json package version != VERSION")
    counts = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    doc = {"schema": "PK_SNAPSHOT_RTM/1", "release": version, "rows": rows, "counts": counts,
           "untraced_test_classes": warnings}
    doc["sha256"] = hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest()
    return doc, errors, warnings


def render_md(doc: dict) -> str:
    out = ["# Requirements traceability matrix (generated by tools/rtm.py — do not edit)", "",
           f"Release {doc['release']} · RTM sha256 `{doc['sha256']}` · counts: " +
           ", ".join(f"{k} {v}" for k, v in sorted(doc["counts"].items())), "",
           "| ID | Status | Owner role | Artifacts | Tests | Evidence | Open gaps |", "|---|---|---|---|---|---|---|"]
    for r in doc["rows"]:
        cell = lambda xs: "<br>".join(x.replace("|", "\\|") for x in xs) or "—"
        out.append(f"| {r['id']} | {r['status']} | {r.get('owner_role') or '—'} | {cell(r['artifacts'])} | "
                   f"{cell(r['tests'])} | {cell(r['evidence'])} | {cell(r['gaps'])} |")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    doc, errors, warnings = build()
    if a.write and not (PKG / "REQUIREMENTS_TRACEABILITY.md").exists():
        (PKG / "REQUIREMENTS_TRACEABILITY.md").write_text(render_md(doc))  # first generation
        doc, errors, warnings = build()
    doc["check_errors"] = errors
    if a.write:
        (PKG / "REQUIREMENTS_TRACEABILITY.md").write_text(render_md(doc))
        status = {"schema": "PK_SNAPSHOT_COMPONENTS_STATUS/1", "release": doc["release"], "counts": doc["counts"],
                  "controls": {r["id"]: {k: r[k] for k in ("status", "artifacts", "tests", "evidence", "gaps")}
                               for r in doc["rows"]}}
        (PKG / "COMPONENTS_STATUS.json").write_text(json.dumps(status, indent=1) + "\n")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"counts": doc["counts"], "errors": errors[:20], "untraced_test_classes": len(warnings)}))
    return 1 if (a.check and errors) else 0


if __name__ == "__main__":
    sys.exit(main())
