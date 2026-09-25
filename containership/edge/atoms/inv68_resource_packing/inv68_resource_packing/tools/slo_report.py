"""Measured SLO compliance and support commitments (INV-68 MC-33; C091).

    python -m inv68_resource_packing.tools.slo_report [--evidence evidence/]

Binds the three contract SLOs to measured evidence from this build:

* no memory overcommit -- zero violations across FUZZ engine oracle, SOAK host
  checks and FAULTS F04 (budget: none);
* efficiency -- hosts within 10% of the placeable lower bound in >= 95% of
  batches (PERF.efficiency);
* pack time -- p99 < 100 ms for 1000 workloads (PERF steady-1000).

Lab compliance is necessary but not sufficient: SLOs are *production*
commitments, so ``SLO.json`` stays FAIL until production telemetry is bound
(``production_source``) and support hours/response targets have a named owner.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .common import PKG, write


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=str(PKG / "evidence"))
    ap.add_argument("--production-source", help="path to production SLI export (PK_PACK_SLI/1)")
    a = ap.parse_args(argv)
    ev = Path(a.evidence)
    load = lambda n: json.loads((ev / n).read_text()) if (ev / n).exists() else {}
    perf, fuzz, soak, faults = load("PERF.json"), load("FUZZ.json"), load("SOAK.json"), load("FAULTS.json")
    f04 = next((s for s in faults.get("scenarios", []) if s["id"] == "F04"), {})
    over = [f for f in fuzz.get("findings", []) if "capacity violated" in f.get("problem", "")]
    slos = [
        {"slo": "no memory overcommit", "target": "0 hosts above capacity minus headroom", "budget": "none",
         "measured": {"fuzz_violations": len(over), "soak_violations": soak.get("invariant_violations"),
                      "fault_node_loss_limits_respected": f04.get("observed", {}).get("limits_respected")},
         "lab_compliant": bool(fuzz) and not over and soak.get("invariant_violations") == 0 and f04.get("result") == "PASS"},
        {"slo": "efficiency", "target": "hosts within 10% of lower bound in >= 95% of batches", "budget": "5% of batches",
         "measured": perf.get("efficiency"), "lab_compliant": perf.get("efficiency", {}).get("result") == "PASS"},
        {"slo": "pack time", "target": "p99 < 100 ms for 1000 workloads", "budget": "1% of requests",
         "measured": {"p99_ms": perf.get("profiles", {}).get("steady-1000", {}).get("p99_ms"),
                      "machine": perf.get("machine", {}).get("platform")},
         "lab_compliant": perf.get("slo_pack_time_p99_under_100ms_for_1000") is True},
    ]
    owners = json.loads((PKG / "ops" / "owners.json").read_text())
    support = {"service_owner": next(r["assignee"] for r in owners["roles"] if r["role"] == "service_owner"),
               "support_hours": None, "response_targets": {"page": "15 min (proposed)", "ticket": "1 business day (proposed)"},
               "error_budget_policy": "SLO breach exhausting budget -> freeze config changes; rollouts halted (proposed)"}
    prod = None
    if a.production_source and Path(a.production_source).exists():
        prod = json.loads(Path(a.production_source).read_text())
    lab = all(s["lab_compliant"] for s in slos)
    ok = lab and prod is not None and support["service_owner"] is not None
    write(ev / "SLO.json", {"schema": "PK_PACK_SLO/1", "slos": slos, "lab_compliant": lab,
                            "production_source": a.production_source if prod else None, "support": support,
                            "result": "PASS" if ok else "FAIL",
                            "reason": None if ok else "lab-measured only; production SLI export and named support owner required"})
    print(f"SLO lab_compliant={lab} result={'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
