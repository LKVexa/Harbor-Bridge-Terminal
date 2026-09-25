"""INV-38-C076/C077 — Decision records and operator-readable explain view.

Every automated decision (backend selection, kernel fallback, admission/reject,
retry/no-retry, config activation, version negotiation) produces a durable
record with a stable reason code and input-state fingerprints — never payload
bytes or secrets (C076-T03).  ``explain`` renders one decision as an ordered
causal chain for operators (C077).
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field

DECISION_SCHEMA_VERSION = "decision/1"

DECISION_KINDS = frozenset({
    "BACKEND_SELECTION", "KERNEL_FALLBACK", "ADMISSION", "REJECTION",
    "RETRY", "NO_RETRY", "DRAIN", "CONFIG_ACTIVATION", "VERSION_NEGOTIATION",
    "PRECEDENCE_RESOLUTION",
})


def fingerprint(*parts: object) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(repr(p).encode("utf-8"))
    return h.hexdigest()[:16]


@dataclass
class DecisionLog:
    _records: list[dict] = field(default_factory=list)
    _seq: int = 0

    def record(self, *, kind: str, operation_id: str, action: str, reason_code: str,
               inputs: dict | None = None, policy_generation: int = 0,
               dependency: dict | None = None, correlation_id: str = "-",
               timestamp: float | None = None) -> dict:
        if kind not in DECISION_KINDS:
            raise ValueError(f"unknown decision kind {kind!r}")
        self._seq += 1
        rec = {
            "schema": DECISION_SCHEMA_VERSION,
            "decision_id": f"D{self._seq:06d}",
            "kind": kind,
            "operation_id": operation_id,
            "timestamp": timestamp if timestamp is not None else time.time(),
            "action": action,
            "reason_code": reason_code,
            "policy_generation": policy_generation,
            # Only fingerprints of input state, never the state itself.
            "input_fingerprints": {k: fingerprint(v) for k, v in (inputs or {}).items()},
            "dependency": dependency or {},
            "correlation_id": correlation_id,
        }
        self._records.append(rec)
        return rec

    def get(self, decision_id: str) -> dict | None:
        return next((r for r in self._records if r["decision_id"] == decision_id), None)

    def by_operation(self, operation_id: str) -> list[dict]:
        return [r for r in self._records if r["operation_id"] == operation_id]

    def records(self) -> list[dict]:
        return list(self._records)


def explain(decision: dict, *, machine: bool = False) -> dict | str:
    """C077: render a single decision as an ordered causal chain."""
    if decision is None:
        raise ValueError("no such decision")
    steps = [
        ("decision", decision["decision_id"]),
        ("kind", decision["kind"]),
        ("operation", decision["operation_id"]),
        ("action", decision["action"]),
        ("reason_code", decision["reason_code"]),
        ("policy_generation", decision["policy_generation"]),
        ("dependency", decision.get("dependency", {})),
    ]
    if machine:
        return {"schema": "explain/1", "decision_id": decision["decision_id"], "steps": dict(steps)}
    lines = [f"explain {decision['decision_id']} ({decision['kind']})"]
    lines += [f"  - {k}: {v}" for k, v in steps[2:]]
    return "\n".join(lines)
