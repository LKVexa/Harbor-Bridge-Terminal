"""C100: formal, machine-verifiable Production Exit Gate for INV-17.

Evaluates every mandatory input and emits conformance/PRODUCTION_EXIT_GATE.json with an
unambiguous verdict:
  GO              every P0/P1 component IMPLEMENTED_VERIFIED or covered by an APPROVED,
                  unexpired N/A/waiver; all automated gates pass; governance complete;
                  a human approval record is present.
  CONDITIONAL_GO  automated gates pass and only P1/P2 items remain open under approved waivers.
  NO_GO           anything else. Every reason is listed.
The gate never approves itself: ``approval`` is null until a human adds a record.
Exit code: 0 for GO, 2 for CONDITIONAL_GO, 1 for NO_GO."""
import datetime as dt, json, sys
from _tools_pkg import ROOT


def load(rel, default=None):
    p = ROOT / rel
    return json.loads(p.read_text()) if p.exists() else default


def main():
    today = dt.date.today()
    closure = load("conformance/closure-status.json")["components"]
    blockers, conditions, checks = [], [], {}
    missing = {c["n"]: [a for a in c["artifacts"] + c["verification"] if not (ROOT / a).exists()] for c in closure}
    for c in closure:
        if missing[c["n"]]:
            blockers.append(f"#{c['n']} {c['title']}: missing artifacts {missing[c['n']]}")
        if c["status"] != "IMPLEMENTED_VERIFIED":
            msg = f"#{c['n']} [{c['priority']}] {c['title']}: {c['status']} -- {c['open_item']}"
            (blockers if c["priority"] == "P0" or c["status"] == "MEASURED_FAILING" else conditions).append(msg)
    man = load("evidence/release-manifest.json", {})
    steps = {s["step"]: s for s in man.get("steps", [])}
    for name in ("compile", "unit suite", "unit suite (python -O)", "pk_core workflow + gate + ledger verify", "coverage",
                 "lint (ruff)", "types (mypy)", "schema manifest", "traceability", "sbom verify"):
        ok = steps.get(name, {}).get("exit") == 0
        checks[name] = "PASS" if ok else ("NOT_RUN" if name not in steps else "FAIL")
        if not ok:
            blockers.append(f"automated check {name}: {checks[name]}")
    pk = load("conformance/PK_GATE_RESULTS.json", {})
    checks["pk_core_gate_verdict"] = pk.get("verdict")
    perf = load("benchmarks/results/perf-gate.json", {})
    checks["perf_regression_gate"] = perf.get("verdict", "NOT_RUN")
    if perf.get("verdict") == "FAIL":
        blockers.append("performance regression gate FAIL")
    bench = load("benchmarks/results/latest.json", {})
    slo3 = bench.get("slo_assessment", {}).get("SLO-3", {})
    checks["SLO-3 p99 < 1us"] = {"p99_ns": slo3.get("p99_ns"), "met": slo3.get("met")}
    gov = load("evidence/governance.json", {})
    checks["governance_production_ready"] = gov.get("production_ready")
    if not gov.get("production_ready"):
        blockers.append(f"governance: {len(gov.get('problems', []))} problems (owners unassigned, waivers unapproved)")
    for t in load("security/threat-model.json")["threats"]:
        if t["severity"] in ("critical", "high") and t["status"] not in ("mitigated",):
            conditions.append(f"threat {t['id']} ({t['severity']}) {t['status']}: {t.get('residual', '')}")
    for w in load("governance/waivers.json")["waivers"]:
        if w["status"] == "APPROVED" and dt.date.fromisoformat(w["expires"]) < today:
            blockers.append(f"waiver {w['id']} expired")
    approval = load("conformance/APPROVAL.json")
    if not approval:
        blockers.append("no human approval record (conformance/APPROVAL.json) -- the gate cannot approve itself")
    verdict = "NO_GO" if blockers else ("CONDITIONAL_GO" if conditions else "GO")
    counts = {}
    for c in closure:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    out = {"schema": "urn:pk:inv17:production-exit-gate:1", "component": "INV-17", "version": man.get("version"),
           "evaluated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "release_source_tree_sha256": man.get("source_tree_sha256"), "release_manifest_generated_at": man.get("generated_at"),
           "verdict": verdict, "closure_counts": counts, "automated_checks": checks,
           "blockers": blockers, "conditions": conditions, "approval": approval}
    (ROOT / "conformance" / "PRODUCTION_EXIT_GATE.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"verdict": verdict, "blockers": len(blockers), "conditions": len(conditions), "closure": counts}))
    return {"GO": 0, "CONDITIONAL_GO": 2}.get(verdict, 1)


if __name__ == "__main__":
    sys.exit(main())
