"""MC-046 - Formal production exit-gate evidence bundle (GAP03-EXIT/1).

The gate consumes a bundle bound to an exact artifact digest and returns GO
only when every mandatory evidence class is present, current, for the same
digest, all P0/P1 checks are satisfied or waived by an ACTIVE waiver, and all
four named sign-offs (technical, security, SRE, release) are present and
signed by keys in the trust store.  Anything missing => NO_GO (fail closed).
"""
from __future__ import annotations

import time

from . import canonical
from .errors import SchedulerError

EVIDENCE_CLASSES = ("architecture", "requirements", "tests", "optimized_tests", "security", "sbom", "provenance",
                    "signature", "audit_integrity", "resilience", "backup_restore", "canary_rehearsal", "incident_exercise",
                    "performance", "compatibility", "operations", "approvals")
SIGNOFF_ROLES = ("technical", "security", "sre", "release")
MAX_EVIDENCE_AGE_S = 14 * 86400


def evaluate(bundle: dict, *, artifact_digest: str, trust=None, now: float | None = None) -> dict:
    now = now if now is not None else time.time()
    reasons = []
    if bundle.get("artifact_digest") != artifact_digest:
        reasons.append("bundle bound to a different artifact digest")
    rc = bundle.get("release_candidate") or {}
    for k in ("version", "source_commit", "config_digest", "schema_digests"):
        if not rc.get(k):
            reasons.append(f"release candidate missing {k}")
    ev = bundle.get("evidence", {})
    for cls in EVIDENCE_CLASSES:
        item = ev.get(cls)
        if not item:
            reasons.append(f"missing evidence: {cls}")
            continue
        if item.get("artifact_digest") != artifact_digest:
            reasons.append(f"evidence {cls} is for a different artifact")
        if rc and item.get("release_candidate_digest") not in (None, canonical.digest(rc)):
            reasons.append(f"evidence {cls} bound to a different release candidate (version/commit/config/schema)")
        if now - item.get("produced_at", 0) > MAX_EVIDENCE_AGE_S:
            reasons.append(f"evidence {cls} is stale")
        if item.get("status") not in ("PASS", "PASS_WITH_WAIVER"):
            reasons.append(f"evidence {cls} status {item.get('status')}")
    if "defects" not in bundle or "waivers" not in bundle:
        reasons.append("bundle must list unresolved defects and active waivers (even when empty)")
    for d in bundle.get("defects", []):
        if d.get("status") != "FIXED" and d.get("severity") in ("P0", "P1"):
            reasons.append(f"open {d['severity']} defect {d['id']}")
    waived = {c for w in bundle.get("waivers", []) for c in w.get("control_ids", [])}
    for chk in bundle.get("mandatory_checks", []):
        if chk["status"] == "WAIVED" and chk["id"] not in waived:
            reasons.append(f"{chk['id']} claims WAIVED without an active waiver")
        elif chk["status"] not in ("SATISFIED", "WAIVED"):
            reasons.append(f"{chk['id']} not satisfied ({chk['status']})")
    signs = bundle.get("signoffs", {})
    for role in SIGNOFF_ROLES:
        s = signs.get(role)
        if not s:
            reasons.append(f"missing sign-off: {role}")
            continue
        if trust is None:
            reasons.append(f"sign-off {role} unverifiable (no trust store)")
            continue
        from .identity import verify_artifact
        try:
            stmt = verify_artifact(trust, s, {"role": role, "artifact_digest": artifact_digest}, kind="signoff")
        except SchedulerError as exc:
            reasons.append(f"sign-off {role} invalid: {exc.code}")
            continue
        if stmt["issuer"] in {signs[r]["statement"]["issuer"] for r in SIGNOFF_ROLES if r != role and r in signs}:
            reasons.append(f"sign-off {role} not independent (same issuer as another role)")
    decision = "GO" if not reasons else "NO_GO"
    return {"schema": "GAP03-EXIT/1", "decision": decision, "artifact_digest": artifact_digest, "reasons": reasons,
            "waived_controls": sorted(waived), "defects_listed": len(bundle.get("defects", [])),
            "evaluated_at": int(now), "result_digest": canonical.digest({"d": decision, "r": reasons, "a": artifact_digest})}


def sign_result(result: dict, key) -> dict:
    from .identity import sign_artifact
    return {"result": result, "envelope": sign_artifact(key, "exit_gate_result", result)}


def verify_result(trust, signed: dict, *, artifact_digest: str) -> bool:
    from .identity import verify_artifact
    verify_artifact(trust, signed["envelope"], signed["result"], kind="exit_gate_result")
    r = signed["result"]
    return r["decision"] == "GO" and r["artifact_digest"] == artifact_digest
