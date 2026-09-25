"""Execute the missing-components checklist against this release (M48 + M52).

Reads INV09_v4.2.0_MISSING_COMPONENTS_PRODUCTION_CHECKLIST.md, assesses all
2,704 items (tools/assessments.py), evaluates the production gate (prod/gate.py)
and writes:
  CHECKLIST_STATUS.json / CHECKLIST_STATUS.md   per-item status + evidence
  TRACEABILITY.json                             the 100 base requirements -> evidence
  evidence/production_gate.json                 PK_PRODUCTION_GATE/1
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT / "tools"))

import assessments as A  # noqa: E402
from evidence import release_digest  # noqa: E402
from inv09_portable_compute_isa.prod import gate, waivers  # noqa: E402

SRC = ROOT / "INV09_v4.2.0_MISSING_COMPONENTS_PRODUCTION_CHECKLIST.md"
ICON = {"PASS": "[x]", "PARTIAL": "[~]", "FAIL": "[!]", "OPEN": "[ ]", "BLOCKED_HUMAN": "[H]",
        "BLOCKED_INFRA": "[I]", "WAIVED": "[w]"}


def parse():
    comps, items = {}, []
    comp = sec = None
    for line in SRC.read_text(encoding="utf-8").splitlines():
        m = re.match(r"## (M\d\d) — (.*) \[(P\d)\]", line)
        if m:
            comp = m.group(1)
            comps[comp] = {"name": m.group(2), "priority": m.group(3)}
            continue
        m = re.match(r"### ([A-G])\. (.*)", line)
        if m:
            sec = m.group(1)
            continue
        m = re.match(r"- \[ \] \*\*(M\d\d-\d\d\d)\*\* — (.*)", line)
        if m:
            items.append({"id": m.group(1), "component": comp, "section": sec, "text": m.group(2)})
    ids = [i["id"] for i in items]
    assert len(ids) == 2704 and len(set(ids)) == 2704, (len(ids), len(set(ids)))
    return comps, items


def main() -> int:
    comps, items = parse()
    rel = release_digest()
    today = dt.date.today()
    wv = waivers.load(str(ROOT / "waivers" / "WAIVERS.json"))
    for it in items:
        n = int(it["id"][-3:])
        if 7 <= n <= 16 or 27 <= n <= 31:
            st, ev, note = A.specific(it["id"], it["component"], n)
        elif n < 50:
            st, ev, note = A.generic(it["component"], n)
        else:
            continue
        it.update(status=st, evidence=ev, note=note)
    by_comp = collections.defaultdict(list)
    for it in items:
        by_comp[it["component"]].append(it)
    for comp, its in by_comp.items():
        pre = [i for i in its if int(i["id"][-3:]) < 50]
        bad = [i["id"] for i in pre if i["status"] != "PASS"]
        i50, i51 = its[49], its[50]
        i50.update(status="PASS" if not bad else "FAIL", evidence="CHECKLIST_STATUS.json",
                   note="" if not bad else f"{len(bad)} of 49 mandatory items not PASS")
        if A.CLASS[comp] in ("NONE", "HUMAN"):
            i51.update(status="OPEN" if A.CLASS[comp] == "NONE" else "BLOCKED_HUMAN", evidence="", note="")
        else:
            i51.update(status="PARTIAL", evidence="evidence/fuzz_campaign.json; docs/THREAT_MODEL.md",
                       note="no known unresolved critical/high finding; independent security review pending")
    pre52 = [i for i in items if not i["id"].endswith("-052")]
    result = gate.evaluate(ROOT, rel, pre52, wv, today)
    for comp, its in by_comp.items():
        its[51].update(status="FAIL" if result["verdict"] == "NO_GO" else "PASS",
                       evidence="evidence/production_gate.json", note=f"M52 verdict {result['verdict']}")
    counts = collections.Counter(i["status"] for i in items)
    result["counts_all_2704"] = dict(sorted(counts.items()))
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "production_gate.json").write_text(json.dumps(result, indent=1))

    per_comp = {}
    for comp, its in by_comp.items():
        c = collections.Counter(i["status"] for i in its)
        per_comp[comp] = {"name": comps[comp]["name"], "priority": comps[comp]["priority"],
                          "class": A.CLASS[comp], "counts": dict(sorted(c.items())),
                          "pass_pct": round(100 * c["PASS"] / len(its), 1)}
    doc = {"schema": "PK_CHECKLIST_STATUS/1", "release_digest": rel, "generated_on": today.isoformat(),
           "source": SRC.name, "legend": {k: v for k, v in ICON.items()},
           "totals": dict(sorted(counts.items())), "gate_verdict": result["verdict"],
           "components": per_comp, "items": items}
    (ROOT / "CHECKLIST_STATUS.json").write_text(json.dumps(doc, indent=1))

    # human-readable view from the same dataset (M48-016)
    L = [f"# INV-09 v4.3.0 — Missing-components checklist: execution status",
         "", f"Release digest `{rel}` · generated {today.isoformat()} · production gate **{result['verdict']}**", "",
         "Legend: " + " · ".join(f"`{v}` {k}" for k, v in ICON.items()), "",
         "## Totals (2,704 items)", "", "| Status | Items |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
    L += ["", "## By component", "", "| ID | Component | P | Class | PASS | PARTIAL | FAIL | OPEN | BLOCKED (H/I) |",
          "|---|---|---|---|---|---|---|---|---|"]
    for comp, pc in per_comp.items():
        c = pc["counts"]
        L.append(f"| {comp} | {pc['name']} | {pc['priority']} | {pc['class']} | {c.get('PASS', 0)} | "
                 f"{c.get('PARTIAL', 0)} | {c.get('FAIL', 0)} | {c.get('OPEN', 0)} | "
                 f"{c.get('BLOCKED_HUMAN', 0)}/{c.get('BLOCKED_INFRA', 0)} |")
    L += ["", "## Production gate controls", "", "| Control | Status | Detail |", "|---|---|---|"]
    for c in result["controls"]:
        L.append(f"| {c['control']} | {c['status']} | {str(c['detail'])[:140]} |")
    for comp, its in by_comp.items():
        L += ["", f"## {comp} — {comps[comp]['name']} [{comps[comp]['priority']}]", ""]
        for it in its:
            extra = f" — _{it['evidence']}_" if it["evidence"] else ""
            note = f" — {it['note']}" if it["note"] else ""
            L.append(f"- `{ICON[it['status']]}` **{it['id']}** {it['status']}{extra}{note}")
    (ROOT / "CHECKLIST_STATUS.md").write_text("\n".join(L) + "\n")

    # M48: the 100 base requirements (CHECKLIST.json) -> evidence, by dimension
    base = json.loads((ROOT / "CHECKLIST.json").read_text())["items"]
    dim_ev = {
        "Architecture & Scope": ["README.md", "docs/DESIGN.md#1", "docs/INTEGRATION.md", "OWNERS.yaml"],
        "Requirements & Semantics": ["docs/DESIGN.md#3", "docs/DETERMINISM.md", "docs/adr/ADR-0002"],
        "Interfaces & Integration": ["schemas/", "tests/test_prod.py:SchemaConformanceTest", "docs/INTEGRATION.md"],
        "Implementation & Configuration": ["prod/", "prod/registry.py", "pyproject.toml"],
        "Security, Trust & Isolation": ["docs/THREAT_MODEL.md", "prod/attest.py", "prod/admission.py"],
        "Resilience & Failure Handling": ["tests/test_faults.py", "docs/DESIGN.md#5", "evidence/soak.json"],
        "Observability & Explainability": ["prod/telemetry.py", "ops/", "docs/OPERATIONS.md"],
        "Performance & Resource Efficiency": ["evidence/benchmark.json", "evidence/perf_gate.json", "prod/limits.py"],
        "Testing & Certification": ["tests/", "evidence/fuzz_campaign.json", "evidence/coverage.json", "evidence/tests.json"],
        "Operations, Release & Governance": ["docs/OPERATIONS.md", "prod/canary.py", "docs/adr/", "waivers/",
                                             "evidence/sbom.cdx.json", "evidence/production_gate.json"],
    }
    rows = []
    for b in base:
        ev = dim_ev.get(b["dimension"])
        rows.append({"check_id": b["check_id"], "dimension": b["dimension"], "requirement": b["requirement"],
                     "evidence": ev or [], "status": "MAPPED" if ev else "UNMAPPED",
                     "granularity": "dimension"})
    assert len(rows) == 100 and len({r["check_id"] for r in rows}) == 100
    (ROOT / "TRACEABILITY.json").write_text(json.dumps(
        {"schema": "PK_TRACEABILITY/1", "release_digest": rel, "rows": rows,
         "unmapped": [r["check_id"] for r in rows if r["status"] == "UNMAPPED"]}, indent=1))
    print(json.dumps({"verdict": result["verdict"], "totals": dict(counts)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
