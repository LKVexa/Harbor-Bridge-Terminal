"""C096-C097: simulated Sev-1 tabletop (credit/backlog incident) driven through the real
runtime and the runbook. It resolves the pager target from governance/OWNERS.json -- and
reports UNRESOLVED when it is a placeholder, which is the honest current state. Writes
evidence/drill-sev1.json. A human-attended drill is still required to close the item."""
import json, time
from _tools_pkg import ROOT, mod

C = mod("control"); O = mod("observability"); S = mod("stream")


def main():
    owners = json.loads((ROOT / "governance" / "OWNERS.json").read_text())
    runbook = (ROOT / "operations" / "RUNBOOK.md").read_text()
    reg = C.StreamRegistry(); steps = []
    t0 = time.monotonic()
    for i in range(3):
        tok = reg.authority.issue(f"s{i}", "tenant-a", "w", ["open", "write"])
        s = reg.open(int, tenant="tenant-a", workload="w", token=tok, stream_id=f"s{i}")
        s.grant(1); s.write(1)
        for _ in range(40):
            try: s.write(1)
            except S.CreditExhausted: pass
    h = reg.health(); steps.append({"step": "detect", "health": h.status, "reasons": h.reasons[:3]})
    pager = owners.get("paging_target")
    steps.append({"step": "page", "target": pager, "resolved": pager not in (None, "", "UNASSIGNED")})
    steps.append({"step": "diagnose", "explain_decisions": len(O.explain(reg)["decisions"]),
                  "metrics_lines": len(O.MetricsExporter(reg).render().splitlines())})
    n = reg.quarantine("sre-oncall", scope="tenant", value="tenant-a", reason="drill: contain stall storm")
    steps.append({"step": "contain", "action": "quarantine tenant-a", "streams_frozen": n, "health_after": reg.health().status})
    reg.release("sre-oncall", scope="tenant", value="tenant-a")
    for s in reg.streams():
        while s.read() not in (S.NOT_READY, None): pass
        s.grant(5)
    steps.append({"step": "recover", "health_after": reg.health().status})
    steps.append({"step": "close", "audit_chain_ok": reg.audit.verify() == [], "audit_events": len(reg.audit.events)})
    out = {"drill": "sev1-credit-backlog", "simulated": True, "human_attended": False,
           "runbook_sections_referenced": [k for k in ("credit stall", "quarantine", "emergency", "rollback") if k in runbook.lower()],
           "duration_s": round(time.monotonic() - t0, 3), "steps": steps,
           "verdict": "PASS_WITH_GAPS" if not steps[1]["resolved"] else "PASS",
           "gaps": [] if steps[1]["resolved"] else ["pager target unresolved: OWNERS.json paging_target is UNASSIGNED"]}
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence" / "drill-sev1.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"verdict": out["verdict"], "gaps": out["gaps"], "steps": [s["step"] for s in steps]}))


if __name__ == "__main__":
    main()
