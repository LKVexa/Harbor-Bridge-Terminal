"""INV-38-C090 — Machine-readable release acceptance builder + gate.

Builds a versioned acceptance record from the RTM and evidence artifacts, signs
it, and enforces the release gate.  A release is only GO when every checklist
item is PRESENT/DONE or carries an unexpired approved waiver.  Missing external
dependencies (pk_core / hardware qualification) yield CONDITIONAL_GO or NO_GO,
never a silent conversion of skipped work into PASS (C090-T05).
"""
from __future__ import annotations
import hashlib, hmac, json, time
from . import rtm_tools

ACCEPTANCE_SCHEMA = "acceptance/1"
ACCEPTABLE_TERMINAL = {"DONE", "PRESENT", "WAIVED"}

class GateRejected(RuntimeError):
    code = "PK_BYPASS_RELEASE_REJECTED"

def build(*, source_revision: str, package_digest: str, waivers: list[dict] | None = None,
          now: float | None = None) -> dict:
    now = now if now is not None else time.time()
    rtm = rtm_tools.build()
    problems = rtm_tools.validate(rtm)
    if problems:
        raise GateRejected("RTM invalid: " + "; ".join(problems))
    waivers = waivers or []
    waived_ids = {w["requirement"] for w in waivers}
    open_items, conditional = [], []
    for r in rtm["rows"]:
        st = r["status"]
        if st in ACCEPTABLE_TERMINAL or r["id"] in waived_ids:
            continue
        if st in ("IN_PROGRESS", "BLOCKED"):
            conditional.append({"id": r["id"], "status": st, "note": r["note"]})
        else:
            open_items.append({"id": r["id"], "status": st})
    if open_items:
        verdict = "NO_GO"
    elif conditional:
        verdict = "CONDITIONAL_GO"
    else:
        verdict = "GO"
    record = {
        "schema": ACCEPTANCE_SCHEMA, "element": "INV-38", "generated_at": now,
        "source_revision": source_revision, "package_digest": package_digest,
        "rtm_digest": rtm_tools.digest(rtm), "rollup": rtm_tools.rollup(rtm),
        "verdict": verdict,
        "conditions": conditional,        # must be accepted & recorded for CONDITIONAL_GO
        "blocking_open_items": open_items,
        "waivers": waivers,
    }
    return record

def sign(record: dict, key: bytes) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()

def verify(record: dict, signature: str, key: bytes) -> None:
    if not hmac.compare_digest(sign(record, key), signature):
        raise GateRejected("acceptance signature mismatch (tamper)")

def enforce(record: dict, *, now: float | None = None) -> str:
    """Return the verdict, rejecting expired waivers / skip-as-pass attempts."""
    now = now if now is not None else time.time()
    for w in record.get("waivers", []):
        if w.get("expiry", 0) < now:
            raise GateRejected(f"expired waiver for {w.get('requirement')}")
        if not w.get("approver"):
            raise GateRejected(f"unapproved waiver for {w.get('requirement')}")
    if record["verdict"] == "NO_GO":
        raise GateRejected(f"NO_GO: {record['blocking_open_items']}")
    return record["verdict"]
