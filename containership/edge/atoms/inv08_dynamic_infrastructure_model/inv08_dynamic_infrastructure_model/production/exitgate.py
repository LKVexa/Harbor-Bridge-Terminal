"""Component 66 - formal production exit gate (PK_DYN_EXITGATE/1).

Consumes: the check-status ledger (status.py), the waiver registry (65), the
ownership map (08), and a signed evidence envelope.  Produces a decision
artifact that is signed (HMAC, NONPRODUCTION) and replayable: ``replay``
recomputes the decision from the recorded inputs' digests and must agree.

Policy (blocking unless stated):
  D1 every P0 check LOCALLY_VERIFIED or (non 05-19) covered by a valid waiver
  D2 every P1 check likewise; P2 checks are NONBLOCKING but must be waived or done
  D3 no BLOCKED check anywhere without a valid, unexpired waiver
  D4 ownership has no UNASSIGNED role
  D5 the evidence envelope verifies under a PRODUCTION trust root
  D6 every check must also carry independent-review status (check 36) - never
     satisfiable by the builder, so D1..D3 already fail while 36 is BLOCKED
A GO needs D1-D5 true.  Waivers can never suppress D4, D5 or P0 checks 05-19.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import waivers as W
from .core import TrustRoot, digest

SCHEMA = "PK_DYN_EXITGATE/1"
DEFINITION = {
    "schema": SCHEMA,
    "domains": ["architecture", "requirements", "interfaces", "implementation", "security",
                "resilience", "performance", "observability", "operations", "governance"],
    "evidence_inputs": {"check_status": "PK_DYN_CHECKSTATUS/1", "waivers": "PK_DYN_WAIVER/1",
                        "ownership": "ownership.json", "evidence_envelope": "HMAC-SHA256 signed digest set"},
    "blocking": ["D1", "D2", "D3", "D4", "D5"], "nonblocking": ["P2-open-items"],
}


def evaluate(status: dict, waivers: list[dict], ownership_blockers: list[str], envelope: dict,
             trust: TrustRoot, *, now: float, verifier=None) -> dict:
    if status.get("schema") != "PK_DYN_CHECKSTATUS/1" or len(status.get("checks", [])) != 2376:
        return {"decision": "NO_GO", "reason": "malformed or incomplete check-status input", "failed": ["INPUT"]}
    prio = {r["component"]: r["priority"] for r in status["checks"]}
    open_items = [(r["component"], r["check"]) for r in status["checks"] if r["state"] != "LOCALLY_VERIFIED"]
    blocking_items = [i for i in open_items if prio[i[0]] in ("P0", "P1")]
    p2_items = [i for i in open_items if prio[i[0]] == "P2"]
    g = W.gate(blocking_items, waivers, now=now, priorities=prio)
    verify = verifier or (lambda env: trust.verify(env.get("payload"), env.get("signature", {}), require_production=True))
    env_ok = bool(envelope) and verify(envelope)
    failed = []
    if g["blocking"]:
        failed.append("D1/D2/D3")
    if ownership_blockers:
        failed.append("D4")
    if not env_ok:
        failed.append("D5")
    return {"schema": SCHEMA, "decision": "NO_GO" if failed else "GO", "failed": failed,
            "open_blocking": len(g["blocking"]), "waived": len(g["waived"]),
            "invalid_waivers": g["invalid"], "p2_open_nonblocking": len(p2_items),
            "ownership_blockers": len(ownership_blockers), "evidence_production_verified": env_ok,
            "inputs": {"check_status": digest(status["checks"]), "waivers": digest(waivers),
                       "ownership_blockers": digest(ownership_blockers), "envelope": digest(envelope or {})},
            "now": now}


def sign_decision(decision: dict, trust: TrustRoot, kid: str) -> dict:
    return {"decision": decision, "signature": trust.sign(kid, decision)}


def replay(signed: dict, status: dict, waivers: list[dict], ownership_blockers: list[str], envelope: dict,
           trust: TrustRoot) -> tuple[bool, str]:
    d = signed["decision"]
    if not trust.verify(d, signed["signature"]):
        return False, "decision signature invalid"
    again = evaluate(status, waivers, ownership_blockers, envelope, trust, now=d["now"])
    if digest(again) != digest(d):
        return False, "replay disagrees with recorded decision"
    return True, "replayed identically"


def main(argv: list[str] | None = None) -> int:
    import argparse, os
    from . import ownership
    prod = Path(__file__).resolve().parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", default=str(prod / "CHECK_STATUS.json"))
    ap.add_argument("--now", type=float, default=0.0)
    ap.add_argument("--out", default=str(prod / "EXIT_GATE_DECISION.json"))
    a = ap.parse_args(argv)
    status = json.loads(Path(a.status).read_text(encoding="utf-8"))
    trust = TrustRoot()
    trust.add("nonprod-gate", (os.environ.get("INV08_GATE_KEY", "nonproduction-demo-key-" + "0" * 16)).encode())
    envelope = {"payload": {"status": digest(status["checks"])}}
    envelope["signature"] = trust.sign("nonprod-gate", envelope["payload"])
    d = evaluate(status, W.load(), ownership.blockers(ownership.load()), envelope, trust, now=a.now)
    signed = sign_decision(d, trust, "nonprod-gate")
    Path(a.out).write_text(json.dumps(signed, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: d[k] for k in ("decision", "failed", "open_blocking", "ownership_blockers")}))
    return 0 if d["decision"] == "GO" else 3


if __name__ == "__main__":
    raise SystemExit(main())
