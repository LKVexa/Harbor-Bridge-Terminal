"""MC-58 production exit gate + MC-57 waiver validation.  Exit 0 GO, 2 NO_GO.

GO requires, simultaneously: owners assigned (not a tool/model), every MC/EXT component
free of BLOCKED_* and DRAFTED_UNAPPROVED, every SHALL approved, MASTER provenance VERIFIED
or an approved unexpired waiver, CI evidence PASS, bench gate met under APPROVED
thresholds, and a signed release approval.  Skipped/unknown is never pass.
"""
from _common import PKG, dump
import json, re, sys
from registry import R

TOOLISH = re.compile(r"(claude|gpt|model|bot|tool|ci|automation|service)", re.I)
WAIVER_FIELDS = ("id", "item", "owner", "scope", "risk", "compensating_control", "approver", "expires")

def validate_waivers(doc, today: str) -> tuple[list[dict], list[str]]:
    ok, errs = [], []
    for w in doc.get("waivers", []):
        miss = [f for f in WAIVER_FIELDS if not w.get(f)]
        if miss: errs.append(f"{w.get('id')}: missing {miss}"); continue
        if w["expires"] <= today: errs.append(f"{w['id']}: expired"); continue
        if w["owner"] == w["approver"]: errs.append(f"{w['id']}: self-approved"); continue
        if TOOLISH.search(w["approver"]): errs.append(f"{w['id']}: approver reads as a tool"); continue
        ok.append(w)
    return ok, errs

def evaluate(root=PKG, today="2026-09-23", inputs=None):
    inputs = inputs or {}
    load = lambda p: json.loads((root / p).read_text()) if (root / p).exists() else None
    owners = inputs.get("owners") or load("governance/OWNERS.json") or {}
    shall = inputs.get("shall") or load("governance/SHALL.json") or {}
    prov = inputs.get("provenance") or load("evidence/master_provenance.json") or {}
    ci = inputs.get("ci") or load("evidence/ci_result.json") or {}
    bench_gate = inputs.get("bench_gate") or load("evidence/bench_gate.json") or {}
    approval = inputs.get("release_approval") or load("evidence/release_approval.json")
    registry = inputs.get("registry", R)
    waivers, werrs = validate_waivers(inputs.get("waivers") or load("governance/WAIVERS.json") or {}, today)
    waived = {w["item"] for w in waivers}
    checks = []
    def c(name, passed, why): checks.append({"check": name, "result": "PASS" if passed else "FAIL", "why": why})
    for role in ("service_owner", "backup_owner", "approver"):
        v = owners.get(role, "UNASSIGNED")
        c(f"owner:{role}", v not in ("", "UNASSIGNED") and not TOOLISH.search(v), v)
    for comp, (state, _, _, blocker) in sorted(registry.items()):
        c(f"component:{comp}", state == "IMPLEMENTED_TESTED" or comp in waived, f"{state}: {blocker}".strip(": "))
    c("shall:approved", shall.get("status") == "APPROVED" and shall.get("approver") not in (None, "UNASSIGNED"), shall.get("status"))
    c("provenance:master", prov.get("status") == "VERIFIED" or "MC-01" in waived, prov.get("status", "ABSENT"))
    c("ci:pass", ci.get("verdict") == "PASS", ci.get("verdict", "ABSENT"))
    c("bench:approved", bench_gate.get("verdict") == "PASS" and bench_gate.get("thresholds", {}).get("status") == "APPROVED",
      bench_gate.get("verdict", "ABSENT"))
    c("release:approval", bool(approval) and not TOOLISH.search(str(approval.get("approver", "tool"))), "none" if not approval else approval.get("approver"))
    c("waivers:valid", not werrs, "; ".join(werrs) or "ok")
    failed = [x for x in checks if x["result"] != "PASS"]
    return {"schema": "PK_EXIT_GATE/1", "verdict": "NO_GO" if failed else "GO", "checks": len(checks),
            "failed": len(failed), "results": checks}

if __name__ == "__main__":
    res = evaluate(); dump(PKG / "evidence/EXIT_GATE.json", res)
    print(json.dumps({k: res[k] for k in ("verdict", "checks", "failed")})); sys.exit(0 if res["verdict"] == "GO" else 2)
