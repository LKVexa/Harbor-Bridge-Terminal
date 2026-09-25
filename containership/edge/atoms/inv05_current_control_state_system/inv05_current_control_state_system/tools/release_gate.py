"""Release promotion gate (MC-048-05, C100): PROMOTE only if the CI gate passed, evidence digests match,
the report is signed, and no P0/P1 component required by the target topology is open."""
import argparse, json, os, sys
import _path  # noqa: F401
from inv05_current_control_state_system import tools_check as tc

TOPOLOGY_REQUIRES = {  # components that may stay 'blocked-external' only if the topology does not need them
    "single-member": set(),
    "ha": {"MC-004", "MC-005", "MC-007", "MC-041", "MC-046"},
}

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--topology", choices=sorted(TOPOLOGY_REQUIRES), default="single-member")
    ap.add_argument("--allow-unsigned", action="store_true")
    a = ap.parse_args()
    reasons = []
    gp = os.path.join(tc.PKG, "evidence", "gate_report.json")
    if not os.path.exists(gp):
        reasons.append("no CI gate report")
    else:
        g = json.load(open(gp))
        if not g.get("ok"):
            reasons.append("CI gate failed")
        if g.get("tree_sha256") != tc.tree_digest():
            reasons.append("evidence is stale: source tree changed since the gate ran")
        for f, d in g.get("evidence_sha256", {}).items():
            if tc.digest_file(os.path.join(tc.PKG, "evidence", f)) != d:
                reasons.append(f"evidence file {f} modified")
        if not g.get("signature") and not a.allow_unsigned:
            reasons.append("evidence unsigned (EX-008)")
    reasons += tc.check_trace(tc.load_json("traceability/trace_matrix.json"), require_generated=True)
    st = tc.load_json("traceability/mc_status.json")
    for mc in st["components"]:
        if mc["priority"] in ("P0", "P1") and mc["status"] != "done":
            if mc["status"] == "done-single-member" and a.topology == "single-member":
                continue
            if mc["status"] in ("blocked-external", "partial") and mc.get("topology_optional") \
                    and mc["id"] not in TOPOLOGY_REQUIRES[a.topology]:
                continue
            reasons.append(f"{mc['id']} [{mc['priority']}] {mc['status']}: {mc['title']}")
    decision = "PROMOTE" if not reasons else "BLOCK"
    print(json.dumps({"decision": decision, "topology": a.topology, "reasons": reasons}, indent=2))
    sys.exit(0 if decision == "PROMOTE" else 1)
