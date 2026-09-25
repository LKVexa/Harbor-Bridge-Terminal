"""Components 13 + 23 - stable result envelope and error-code catalogue.

``core.py`` owns ``Outcome`` and ``Inv08Error``; this module adds:

* ``CATALOG``: every error code this overlay may raise, with its fixed outcome
  (and therefore retryability), severity and operator remediation hint.  Codes
  are ``INV08.<DOMAIN>.<NAME>``; the catalogue version is ``CATALOG_VERSION``.
* ``error()``: the only sanctioned constructor - unknown codes are rejected so
  a code cannot appear on the wire without a catalogue entry.
* ``evolution_ok()``: compatibility rule for result codes and error codes:
  adding is minor; deprecating keeps the code for two minors; removing or
  changing the outcome/severity of an existing code requires a major bump.
* ``result()``: the machine-readable result envelope (PK_DYN_RESULT/1) with the
  mandatory reason/correlation/timestamp fields.
"""
from __future__ import annotations

from typing import Any

from .core import RESULT_CODE_POLICY, Inv08Error, Outcome, redact, redact_text

CATALOG_VERSION = "1.0.0"
R, T, O, D = (Outcome.RETRYABLE_FAILURE, Outcome.TERMINAL_FAILURE,
              Outcome.OPERATOR_REQUIRED, Outcome.DEGRADED)

# code: (outcome, severity, remediation, deprecated_since or None)
CATALOG: dict[str, tuple[Outcome, str, str, str | None]] = {
    "INV08.PROVIDER.RETRYABLE": (R, "error", "check provider status; retry is automatic", None),
    "INV08.PROVIDER.TERMINAL": (T, "error", "operator review required", None),
    "INV08.LIFECYCLE.FORBIDDEN_TRANSITION": (T, "error", "inspect node history; transition is not allowed from current state", None),
    "INV08.LIFECYCLE.GUARD_FAILED": (R, "warning", "satisfy the entry guard (e.g. drain workload) then retry", None),
    "INV08.LIFECYCLE.UNKNOWN_NODE": (T, "error", "node was never registered; check node id", None),
    "INV08.LIFECYCLE.JOURNAL_CORRUPT": (O, "critical", "restore journal from backup; do not auto-repair", None),
    "INV08.COMPAT.UNSUPPORTED_PEER": (T, "error", "upgrade the peer to a supported version (N or N-1)", None),
    "INV08.COMPAT.NO_COMMON_VERSION": (T, "error", "peers share no protocol version; upgrade the older side", None),
    "INV08.COMPAT.MISSING_FEATURE": (T, "error", "peer lacks a required feature; upgrade peer or disable feature", None),
    "INV08.COMPAT.BAD_SEQUENCE": (T, "error", "follow the documented upgrade order: controller first, then nodes", None),
    "INV08.QUOTA.EXCEEDED": (R, "warning", "reduce request or raise tenant quota", None),
    "INV08.QUOTA.UNKNOWN_TENANT": (T, "error", "register the tenant quota first", None),
    "INV08.QUOTA.INVALID": (T, "error", "fix quota definition", None),
    "INV08.PARTITION.STALE_COMMAND": (T, "warning", "command from an old controller epoch/sequence was dropped; resend from current leader", None),
    "INV08.PARTITION.AUTONOMY_LIMIT": (O, "warning", "action not permitted while disconnected; wait for reconnect", None),
    "INV08.PARTITION.FENCED": (O, "critical", "node self-fenced after grace expiry; reconcile then rejoin", None),
    "INV08.CONSTRAINT.UNSATISFIABLE": (O, "error", "relax the named constraint or add capacity satisfying it", None),
    "INV08.CONSTRAINT.INVALID": (T, "error", "fix constraint definition", None),
    "INV08.SCHEMA.INVALID": (T, "error", "message does not match its schema; fix the producer", None),
    "INV08.SCHEMA.UNSUPPORTED_VERSION": (T, "error", "negotiate a supported schema version", None),
    "INV08.AUTHN.INVALID_TOKEN": (T, "error", "credential rejected; re-issue identity", None),
    "INV08.AUTHN.EXPIRED": (R, "warning", "refresh credential and retry", None),
    "INV08.AUTHN.REVOKED": (O, "critical", "credential revoked; investigate possible compromise", None),
    "INV08.AUTHN.REPLAY": (T, "critical", "handshake nonce reused; possible replay attack", None),
    "INV08.AUTHN.BAD_BOOTSTRAP": (T, "error", "join token unknown or already used", None),
    "INV08.AUTHZ.DENIED": (T, "warning", "request a role granting this capability via privilege review", None),
    "INV08.IDEMP.KEY_REUSE": (T, "error", "idempotency key reused with a different payload; use a new operation id", None),
    "INV08.IDEMP.IN_PROGRESS": (R, "info", "original request still running; retry later", None),
    "INV08.IDEMP.STORE_FULL": (R, "warning", "dedup store at capacity; retry after window expiry", None),
    "INV08.IDEMP.DEADLINE": (R, "warning", "timeout budget exhausted; retry with a new budget", None),
    "INV08.IDEMP.CANCELLED": (T, "info", "operation cancelled by caller", None),
    "INV08.BACKPRESSURE.SHED": (R, "warning", "queue overloaded; honour retry_after", None),
    "INV08.LIMIT.PAYLOAD_TOO_LARGE": (T, "error", "split the message below the payload limit", None),
    "INV08.LIMIT.CONNECTIONS": (R, "warning", "connection limit reached; retry later", None),
    "INV08.LIMIT.STREAMS": (R, "warning", "per-connection stream limit reached", None),
    "INV08.LIMIT.RATE": (R, "warning", "rate limit exceeded; honour retry_after", None),
    "INV08.LIMIT.CONCURRENCY": (R, "warning", "concurrency limit reached", None),
    "INV08.LIMIT.QUEUE_DEPTH": (R, "warning", "queue depth limit reached", None),
    "INV08.LIMIT.MEMORY": (R, "error", "memory budget exhausted; reduce in-flight work", None),
    "INV08.CATALOG.UNKNOWN_CODE": (T, "critical", "a code was raised without a catalogue entry - fix the caller", None),
}


def error(code: str, message: str, *, details: dict | None = None,
          cause: Inv08Error | None = None) -> Inv08Error:
    """Build an Inv08Error whose outcome/severity/remediation come from CATALOG."""
    if code not in CATALOG:
        raise Inv08Error("INV08.CATALOG.UNKNOWN_CODE", f"uncatalogued code {code!r}",
                         severity="critical", details={"code": code})
    outcome, severity, remediation, _ = CATALOG[code]
    return Inv08Error(code, message, outcome=outcome, severity=severity,
                      remediation=remediation, details=dict(details or {}), cause=cause)


def catalog_document() -> dict:
    return {"version": CATALOG_VERSION, "result_policy": RESULT_CODE_POLICY,
            "outcomes": [o.value for o in Outcome],
            "codes": {c: {"outcome": o.value, "retryable": o in {R, D}, "severity": s,
                          "remediation": r, "deprecated_since": dep}
                      for c, (o, s, r, dep) in sorted(CATALOG.items())}}


def _major(v: str) -> int:
    return int(v.split(".")[0])


def evolution_ok(old: dict, new: dict) -> tuple[bool, list[str]]:
    """Check a catalogue (or result-code) change against the compatibility rules.

    ``old``/``new`` are ``catalog_document()``-shaped.  Returns (ok, problems)."""
    problems: list[str] = []
    major_bump = _major(new["version"]) > _major(old["version"])
    for code, entry in old["codes"].items():
        n = new["codes"].get(code)
        if n is None:
            if not major_bump:
                problems.append(f"{code} removed without major bump")
            elif entry.get("deprecated_since") is None:
                problems.append(f"{code} removed without prior deprecation")
            continue
        for k in ("outcome", "severity", "retryable"):
            if n[k] != entry[k] and not major_bump:
                problems.append(f"{code}.{k} changed without major bump")
    for o in old["outcomes"]:
        if o not in new["outcomes"] and not major_bump:
            problems.append(f"outcome {o} removed without major bump")
    return (not problems), problems


def result(outcome: Outcome, reason: str, *, correlation_id: str, ts: float,
           details: dict | None = None, error_obj: Inv08Error | None = None) -> dict:
    """PK_DYN_RESULT/1 envelope.  reason/correlation_id/ts are mandatory."""
    if not isinstance(outcome, Outcome):
        raise ValueError(f"outcome must be Outcome, got {outcome!r}")
    if not reason or not correlation_id:
        raise ValueError("reason and correlation_id are mandatory")
    if outcome is Outcome.SUCCESS and error_obj is not None:
        raise ValueError("SUCCESS cannot carry an error")
    if outcome in {Outcome.RETRYABLE_FAILURE, Outcome.TERMINAL_FAILURE} and error_obj is None:
        raise ValueError(f"{outcome.value} requires an error")
    env: dict[str, Any] = {"schema": RESULT_CODE_POLICY["version"], "outcome": outcome.value,
                           "reason": redact_text(reason), "correlation_id": correlation_id,
                           "ts": ts, "details": redact(details or {})}
    if error_obj is not None:
        env["error"] = error_obj.to_dict()
    return env
