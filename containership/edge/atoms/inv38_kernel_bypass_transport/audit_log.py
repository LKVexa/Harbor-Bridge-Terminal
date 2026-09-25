"""INV-38-C049 — Tamper-evident security audit event stream (+offline verifier).

Append-only, hash-chained audit log.  Each record links to the previous record's
digest, so deletion, insertion, reordering or mutation is detectable offline by
``verify_chain``.  Secrets and payload bytes are never stored (C049-T03); only
safe fingerprints/IDs.  Control characters in free-text fields are rejected so a
record cannot be forged via log injection (C049-T08).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field

AUDIT_SCHEMA_VERSION = "audit/1"
GENESIS = "0" * 64

_CTRL = re.compile(r"[\x00-\x1f\x7f]")  # reject ALL C0 controls incl. tab/newline (anti log-injection)

SECURITY_EVENTS = frozenset({
    "REGISTER", "DEREGISTER", "PRIVILEGED_CONFIG", "AUTHN_FAILURE", "AUTHZ_FAILURE",
    "PROVIDER_RESET", "FALLBACK_ACTIVATED", "POLICY_OVERRIDE", "RELEASE_ACTIVATION",
    "AUDIT_POLICY_CHANGE", "KEY_REVOKED",
})


def _digest(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _reject_ctrl(value: str, *, field_name: str) -> str:
    if _CTRL.search(value):
        raise ValueError(f"control characters not allowed in {field_name}")
    return value


@dataclass
class AuditLog:
    _records: list[dict] = field(default_factory=list)
    _head: str = GENESIS
    _seq: int = 0

    def emit(self, *, event: str, actor: str, resource: str, decision: str,
             reason_code: str, tenant: str = "-", node: str = "-",
             correlation_id: str = "-", timestamp: float | None = None) -> dict:
        if event not in SECURITY_EVENTS:
            raise ValueError(f"unknown security event {event!r}")
        for name, val in (("actor", actor), ("resource", resource),
                          ("reason_code", reason_code), ("correlation_id", correlation_id)):
            _reject_ctrl(str(val), field_name=name)
        self._seq += 1
        body = {
            "schema": AUDIT_SCHEMA_VERSION,
            "seq": self._seq,
            "event": event,
            "timestamp": timestamp if timestamp is not None else float(self._seq),
            "node": node,
            "tenant": tenant,
            "actor": actor,
            "resource": resource,
            "decision": decision,
            "reason_code": reason_code,
            "correlation_id": correlation_id,
            "prev": self._head,
        }
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        body["digest"] = _digest(self._head + canonical)
        self._head = body["digest"]
        self._records.append(body)
        return body

    @property
    def head(self) -> str:
        return self._head

    def records(self) -> list[dict]:
        return list(self._records)

    def dumps(self) -> str:
        return "\n".join(json.dumps(r, sort_keys=True) for r in self._records)


def verify_chain(records: list[dict]) -> tuple[bool, str]:
    """Offline verifier (C049-T07): detects deletion/insertion/reorder/tamper."""
    prev = GENESIS
    expected_seq = 0
    for rec in records:
        expected_seq += 1
        if rec.get("seq") != expected_seq:
            return False, f"sequence discontinuity at seq={rec.get('seq')} (expected {expected_seq})"
        if rec.get("prev") != prev:
            return False, f"broken prev-link at seq={rec.get('seq')}"
        body = {k: v for k, v in rec.items() if k != "digest"}
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
        if _digest(prev + canonical) != rec.get("digest"):
            return False, f"digest mismatch at seq={rec.get('seq')}"
        prev = rec["digest"]
    return True, "chain intact"
