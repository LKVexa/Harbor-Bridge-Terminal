"""Key-compromise workflow (v6).

``respond_to_compromise`` performs, in order and with audit evidence:

1. build an *urgent* signed ``trust-delta`` revoking the kid (and optionally
   the identity) - ready for immediate distribution/preemption;
2. discover the blast radius from the admission decision log: every allowed
   decision that relied on a signature by that kid since ``compromised_since``;
3. quarantine every affected artifact digest (execution blocked fleet-wide
   once distributed);
4. emit a re-sign / rebuild campaign plan (one work item per affected digest,
   ordered by most recent admission) and an evidence package whose digest is
   anchored in the audit ledger.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable, Mapping, Sequence

from .canonical import canonical_bytes
from .distribution import make_delta
from .trust import Namespace


def blast_radius(decisions: Sequence[Mapping[str, Any]], kid: str, since: int) -> list[dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for d in decisions:
        if d.get("outcome") != "allow" or d.get("decided_at", 0) < since:
            continue
        if any(s.get("kid") == kid for s in d.get("signatures", [])):
            e = out.setdefault(d["digest"], {"digest": d["digest"], "kind": d.get("kind"), "admissions": 0, "last_admitted": 0, "workloads": []})
            e["admissions"] += 1
            e["last_admitted"] = max(e["last_admitted"], d.get("decided_at", 0))
            if d.get("workload") and d["workload"] not in e["workloads"]:
                e["workloads"].append(d["workload"])
    return sorted(out.values(), key=lambda e: -e["last_admitted"])


def respond_to_compromise(*, incident_id: str, kid: str, identity: str | None, compromised_since: int, now: int, namespace: Namespace,
                          active_generation: int, decisions: Sequence[Mapping[str, Any]], quarantine: Any, audit: Any,
                          authority: tuple[str, str, Callable[[bytes], bytes]]) -> dict[str, Any]:
    ops = [{"op": "revoke_kid", "value": kid}]
    if identity:
        ops.append({"op": "revoke_identity", "value": identity})
    akid, aalg, asign = authority
    delta = make_delta(namespace, active_generation, ops, issued_at=now, expires=now + 7 * 86400, urgent=True, kid=akid, alg=aalg, signer=asign)
    affected = blast_radius(decisions, kid, compromised_since)
    for a in affected:
        quarantine.quarantine(a["digest"], "KEY_COMPROMISE", now=now, evidence={"incident_id": incident_id, "kid": kid})
    campaign = [{"item": i + 1, "digest": a["digest"], "kind": a["kind"], "action": "rebuild-from-verified-source-and-resign",
                 "workloads": a["workloads"]} for i, a in enumerate(affected)]
    package = {"schema": "PK_INCIDENT_EVIDENCE/1", "incident_id": incident_id, "kid": kid, "identity": identity,
               "compromised_since": compromised_since, "responded_at": now, "revocation_delta_digest": hashlib.sha256(canonical_bytes(delta)).hexdigest(),
               "affected": affected, "campaign": campaign,
               "decision_log_digest": hashlib.sha256(canonical_bytes([dict(d) for d in decisions])).hexdigest()}
    package_digest = hashlib.sha256(canonical_bytes(package)).hexdigest()
    audit.append("incident.key_compromise", {"incident_id": incident_id, "kid": kid, "affected": len(affected), "evidence_digest": package_digest}, now=now)
    return {"delta": delta, "evidence": package, "evidence_digest": package_digest}
