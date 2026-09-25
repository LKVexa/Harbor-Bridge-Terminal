"""Stable error catalog and outcome taxonomy for INV-26 (C014, C026, C025).

Every failure that crosses the public service boundary is a
:class:`SnapshotServiceError` carrying a code from :data:`CATALOG`. The public
envelope (:func:`envelope`) contains only the code, the outcome class, the
catalog's public-safe message, retryability and a correlation id; free-form
exception text never leaves the process (it goes to protected diagnostics
after redaction).

Codes are never recycled: retired codes move to :data:`RESERVED`.
``ERRORS.json`` is generated from this module and checked in CI
(``tools/rtm.py`` fails if they drift).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

CATALOG_VERSION = "PK_SNAPSHOT_ERRORS/1"

# Closed outcome taxonomy (C014).
OUTCOMES = (
    "success",            # operation committed, guest (restore) READY
    "partial_success",    # capture committed but a best-effort step (e.g. telemetry) failed
    "degraded_success",   # committed while a non-critical dependency was down (C056)
    "retryable_failure",  # nothing committed; same request may be retried with the same idempotency key
    "terminal_failure",   # nothing committed; retrying the same request cannot succeed
    "policy_rejection",   # refused by authn/authz/tenancy/quota/residency before any side effect
    "integrity_rejection",  # refused because bytes/signature/fingerprint/AEAD did not verify
    "operator_aborted",   # cancelled/quarantined/frozen by an operator control
)


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    number: int
    outcome: str
    retryable: bool
    http: int
    security: bool
    public_message: str
    operator_action: str


_SPECS = [
    ErrorSpec("SNAP_NOT_FOUND", 1001, "terminal_failure", False, 404, False,
              "snapshot not found", "verify snapshot id; check deletion/quarantine audit trail"),
    ErrorSpec("SNAP_DUPLICATE", 1002, "terminal_failure", False, 409, False,
              "snapshot already exists", "use a new snapshot id or delete the existing one"),
    ErrorSpec("SNAP_TENANT_MISMATCH", 1101, "policy_rejection", False, 403, True,
              "restore refused by security boundary", "investigate as possible cross-tenant attempt (SEV per INCIDENT_RESPONSE)"),
    ErrorSpec("SNAP_WORKLOAD_MISMATCH", 1102, "policy_rejection", False, 403, True,
              "restore refused by security boundary", "check workload identity binding"),
    ErrorSpec("SNAP_ENVIRONMENT_MISMATCH", 1103, "policy_rejection", False, 403, True,
              "restore refused by security boundary", "snapshots do not cross environments; re-capture"),
    ErrorSpec("SNAP_MODEL_MISMATCH", 1201, "integrity_rejection", False, 409, False,
              "device model incompatible with snapshot", "re-capture on the current device model"),
    ErrorSpec("SNAP_UNSUPPORTED_VERSION", 1202, "terminal_failure", False, 400, False,
              "unsupported schema version", "upgrade client or re-capture (COMPATIBILITY.md)"),
    ErrorSpec("SNAP_SIGNATURE_INVALID", 1301, "integrity_rejection", False, 422, True,
              "snapshot integrity verification failed", "quarantine snapshot; investigate tampering"),
    ErrorSpec("SNAP_CIPHERTEXT_INVALID", 1302, "integrity_rejection", False, 422, True,
              "snapshot integrity verification failed", "quarantine snapshot; check storage corruption"),
    ErrorSpec("SNAP_STORAGE_CORRUPT", 1303, "integrity_rejection", False, 422, True,
              "snapshot integrity verification failed", "quarantine; restore from backup or re-capture"),
    ErrorSpec("SNAP_KMS_UNAVAILABLE", 1401, "retryable_failure", True, 503, False,
              "key service unavailable", "check KMS health; restores fail closed until it returns"),
    ErrorSpec("SNAP_KEY_REVOKED", 1402, "terminal_failure", False, 403, True,
              "key revoked or disabled", "snapshot is cryptographically erased or key disabled; re-capture"),
    ErrorSpec("SNAP_ENTROPY_FAILED", 1501, "retryable_failure", True, 500, True,
              "guest entropy injection failed", "guest kept paused and destroyed; check guest agent/VMGenID"),
    ErrorSpec("SNAP_HYPERVISOR_FAILED", 1502, "retryable_failure", True, 502, False,
              "hypervisor operation failed", "check hypervisor adapter health"),
    ErrorSpec("SNAP_STORAGE_UNAVAILABLE", 1503, "retryable_failure", True, 503, False,
              "snapshot storage unavailable", "check storage backend"),
    ErrorSpec("SNAP_STORAGE_FULL", 1504, "retryable_failure", True, 507, False,
              "snapshot storage full", "free capacity or raise quota"),
    ErrorSpec("SNAP_TIMEOUT", 1601, "retryable_failure", True, 504, False,
              "operation deadline exceeded", "inspect dependency latency; retry with same idempotency key"),
    ErrorSpec("SNAP_CANCELLED", 1602, "operator_aborted", False, 499, False,
              "operation cancelled", "none; cleanup already performed"),
    ErrorSpec("SNAP_OVERLOADED", 1603, "retryable_failure", True, 429, False,
              "service overloaded", "honour retry_after_s; check capacity (C069)"),
    ErrorSpec("SNAP_QUOTA_EXCEEDED", 1604, "policy_rejection", False, 429, False,
              "quota exceeded", "raise quota via config change or delete snapshots"),
    ErrorSpec("SNAP_CIRCUIT_OPEN", 1605, "retryable_failure", True, 503, False,
              "dependency circuit open", "wait for half-open probe; check dependency"),
    ErrorSpec("SNAP_QUARANTINED", 1701, "operator_aborted", False, 423, True,
              "snapshot quarantined", "security owner must review before release (RUNBOOK)"),
    ErrorSpec("SNAP_DISABLED", 1702, "operator_aborted", False, 503, False,
              "snapshotting disabled by operator", "emergency disable is active (RUNBOOK)"),
    ErrorSpec("SNAP_UNAUTHENTICATED", 1801, "policy_rejection", False, 401, True,
              "authentication required", "check caller credentials/audience/expiry"),
    ErrorSpec("SNAP_FORBIDDEN", 1802, "policy_rejection", False, 403, True,
              "not authorized", "grant capability through policy change"),
    ErrorSpec("SNAP_GRANT_INVALID", 1803, "policy_rejection", False, 403, True,
              "restore grant invalid", "issue a new restore grant"),
    ErrorSpec("SNAP_GRANT_REPLAYED", 1804, "policy_rejection", False, 409, True,
              "restore grant already consumed", "possible replay; investigate (INCIDENT_RESPONSE)"),
    ErrorSpec("SNAP_RESIDENCY_VIOLATION", 1805, "policy_rejection", False, 403, True,
              "placement violates residency policy", "restore only in permitted site/region"),
    ErrorSpec("SNAP_TIER_UNSUPPORTED", 1806, "policy_rejection", False, 403, False,
              "operation not supported in this deployment tier", "see APPLICABILITY.md"),
    ErrorSpec("SNAP_INVALID_REQUEST", 1901, "terminal_failure", False, 400, False,
              "invalid request", "fix request per schema"),
    ErrorSpec("SNAP_LIMIT_EXCEEDED", 1902, "terminal_failure", False, 413, False,
              "request exceeds interface limits", "see INTERFACES.md limits"),
    ErrorSpec("SNAP_ILLEGAL_TRANSITION", 1903, "terminal_failure", False, 409, False,
              "snapshot not in a state that permits this operation", "inspect lifecycle state"),
    ErrorSpec("SNAP_STALE_GENERATION", 1904, "retryable_failure", True, 409, False,
              "concurrent modification", "re-read and retry"),
    ErrorSpec("SNAP_FENCED", 1905, "terminal_failure", False, 409, True,
              "controller lease lost", "stale controller must stop; check split-brain alert"),
    ErrorSpec("SNAP_CONFIG_INVALID", 2001, "terminal_failure", False, 400, False,
              "configuration invalid", "fix fields listed in detail; last-known-good kept"),
    ErrorSpec("SNAP_DEPENDENCY_UNAVAILABLE", 2002, "retryable_failure", True, 503, False,
              "required dependency unavailable", "see outage policy (OFFLINE.md)"),
    ErrorSpec("SNAP_AUDIT_UNAVAILABLE", 2003, "retryable_failure", True, 503, True,
              "audit sink unavailable", "privileged operations refused until audit recovers"),
    ErrorSpec("SNAP_INTERNAL", 9999, "terminal_failure", False, 500, False,
              "internal error", "file a defect with the correlation id"),
]

CATALOG: dict[str, ErrorSpec] = {s.code: s for s in _SPECS}
RESERVED: dict[str, str] = {}  # retired code -> reason; never reuse

if len({s.number for s in _SPECS}) != len(_SPECS):  # import-time invariant, survives python -O
    raise RuntimeError("duplicate error number in catalog")


class SnapshotServiceError(Exception):
    """Public-boundary failure with a stable code."""

    def __init__(self, code: str, detail: str = "", *, retry_after_s: float | None = None, **info):
        if code not in CATALOG:
            code, detail = "SNAP_INTERNAL", f"unknown code {code!r}: {detail}"
        self.code = code
        self.spec = CATALOG[code]
        self.detail = detail  # protected diagnostics only; redacted before logging
        self.retry_after_s = retry_after_s
        self.info = info
        super().__init__(f"{code}: {detail}" if detail else code)

    @property
    def retryable(self) -> bool:
        return self.spec.retryable

    @property
    def outcome(self) -> str:
        return self.spec.outcome


def envelope(err: SnapshotServiceError, correlation_id: str) -> dict:
    """Non-leaking public error envelope (PK_SNAPSHOT_ERROR/1)."""
    body = {
        "schema": "PK_SNAPSHOT_ERROR/1",
        "code": err.code,
        "number": err.spec.number,
        "outcome": err.spec.outcome,
        "retryable": err.spec.retryable,
        "message": err.spec.public_message,
        "correlation_id": correlation_id,
    }
    if err.retry_after_s is not None:
        body["retry_after_s"] = round(float(err.retry_after_s), 3)
    return body


def catalog_document() -> dict:
    return {
        "schema": CATALOG_VERSION,
        "outcomes": list(OUTCOMES),
        "codes": [s.__dict__ for s in _SPECS],
        "reserved": RESERVED,
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(catalog_document(), indent=1, sort_keys=True))
