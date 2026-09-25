"""M86 - production exit gate. Mechanical and fail-closed:

GO requires: every M-item LOCALLY_VERIFIED *and* production-boundary evidence, zero
failing/release-critical-skipped tests, pk_core certified, traceability problem-free,
ownership filled, every waiver approved by someone other than the requester and
unexpired, an independent reviewer recorded, and a signature over the gate record.
Anything less is NO_GO (blocked items / missing approvals) or CONDITIONAL_GO (only
approved, unexpired waivers outstanding). The builder can never satisfy the
independent-review condition itself."""
import datetime, json, os, pathlib, sys
PKG = pathlib.Path(os.environ.get("INV60_ROOT") or pathlib.Path(__file__).resolve().parents[1])
rel = PKG / "release"
acc = json.loads((rel / "ACCEPTANCE.json").read_text())
tr = json.loads((rel / "TRACEABILITY.json").read_text())
wv = {w["id"]: w for w in json.loads((PKG / "WAIVERS.json").read_text())["waivers"]}
own = json.loads((PKG / "OWNERSHIP.json").read_text())
reviews = json.loads((PKG / "REVIEWS.json").read_text())["reviews"]
today = datetime.date.today().isoformat()
blockers, conditions, checks = [], [], {}


def check(name, ok, why):
    checks[name] = {"pass": bool(ok), "detail": why}
    if not ok:
        blockers.append(f"{name}: {why}")


ts = acc["test_summary"]
check("tests", ts["failed"] == 0 and ts["errors"] == 0, f"{ts['failed']} failed, {ts['errors']} errors")
check("critical_skips", ts["critical_skipped"] == 0, f"{ts['critical_skipped']} release-critical skips")
check("pk_core", acc["conformance"]["pk_core_certified"], f"pk_core gate {acc['conformance']['pk_core_gate']}")
check("traceability", not tr["problems"], f"{len(tr['problems'])} problems")
unassigned = [k for k, v in {"service_owner": own["service_owner"], "team": own["team"], **own["escalation"]}.items() if v == "UNASSIGNED"]
check("ownership", not unassigned, f"UNASSIGNED: {unassigned}")
check("independent_review", any(r.get("kind") == "release" and r.get("reviewer") and r.get("independent") for r in reviews),
      "no independent release review recorded")
for m, it in acc["items"].items():
    if it["status"] == "LOCALLY_VERIFIED":
        continue
    w = wv.get(it["waiver"])
    valid = w and w["status"] == "approved" and w["approver"] and w["approver"] != w["requested_by"] and w["expires"] >= today
    (conditions if valid else blockers).append(f"{m} {it['status']}: {it['blocker']} (waiver {it['waiver']}: {w['status'] if w else 'missing'})")
checks["production_boundary"] = {"pass": False, "detail": "no item has been exercised through a real wasmCloud/NATS boundary (W-M25)"}
blockers.append("production_boundary: reference-tier evidence only (W-M25)")
verdict = "NO_GO" if blockers else ("CONDITIONAL_GO" if conditions else "GO")
out = {"schema": "inv60.exit-gate/1", "release": acc["release"], "evaluated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
       "verdict": verdict, "checks": checks, "blockers": blockers, "conditions": conditions,
       "item_status": acc["traceability"]["m_effective"], "signature": None,
       "signed_by": None, "note": "An exit gate record is valid for promotion only when signed by the release approver named in OWNERSHIP.json."}
(rel / "EXIT_GATE.json").write_text(json.dumps(out, indent=1))
print(json.dumps({"verdict": verdict, "blockers": len(blockers), "conditions": len(conditions)}))
