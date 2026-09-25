"""Formal production exit gate (MC-070). Evaluates mechanically; GO needs every required
role signed by a distinct human principal that is not a tool/agent, plus pk_core PASS,
a signed artifact, and all components Production Accepted or waived."""
from __future__ import annotations

import json
import sys

from _common import PKG, write_json

TOOL_NAMES = ("claude", "agent", "bot", "ci", "tool", "service", "automation", "build")


def evaluate(owners: dict, gate: dict, status: dict, pk: dict, build: dict) -> dict:
    reasons = []
    roles = owners["roles_required_for_exit_gate"]
    signed = {}
    for s in gate.get("signoffs", []):
        who = str(s.get("principal", ""))
        if not who or any(t in who.lower() for t in TOOL_NAMES) or s.get("channel") == "automated":
            reasons.append(f"sign-off by {who!r} refused: not an accountable human")
            continue
        signed.setdefault(s.get("role"), who)
    for r in roles:
        if r not in signed:
            reasons.append(f"role {r} unsigned")
    if len(set(signed.values())) < len(signed):
        reasons.append("one principal signed multiple roles")
    if owners.get("service_owner") in (None, "", "UNASSIGNED"):
        reasons.append("no accountable service owner")
    if not pk.get("verdict", "").startswith("PASS"):
        reasons.append(f"pk_core gate {pk.get('verdict')}")
    if not str(build.get("signature", "")).startswith("SIGNED"):
        reasons.append("release artifact unsigned")
    not_acc = [c["id"] for c in status["detail"] if c["id"].startswith("MC-") and c["lifecycle"] != "Production Accepted"]
    if not_acc:
        reasons.append(f"{len(not_acc)} components not Production Accepted")
    return {"schema": "INV34_EXIT_GATE_RESULT/1", "decision": "GO" if not reasons else "NO_GO", "reasons": reasons,
            "artifact_sha256": build.get("sha256")}


def main() -> int:
    r = lambda p: json.loads((PKG / p).read_text())
    res = evaluate(r("governance/OWNERS.json"), r("governance/EXIT_GATE.json"), r("governance/CHECKLIST_STATUS.json"),
                   r("governance/PK_CORE_GATE.json"), r("governance/BUILD_RESULT.json"))
    write_json("governance/EXIT_GATE_RESULT.json", res)
    print(json.dumps(res, indent=1))
    return 0 if res["decision"] == "GO" else 3


if __name__ == "__main__":
    sys.exit(main())
