"""MC-024 - Telemetry privacy, retention and export policy (GAP03-PRIV/1).

Every telemetry field is classified; identifiers are pseudonymised by keyed
hash; nested payloads are redacted recursively; retention is per class with a
security-evidence exception; export destinations are allow-listed.
"""
from __future__ import annotations

import hashlib
import hmac
import re

CLASSES = ("public", "internal", "confidential", "sensitive")
FIELD_CLASS = {
    "event": "public", "code": "public", "severity": "public", "service": "public", "version": "public",
    "ts": "internal", "instance": "internal", "trace_id": "internal", "span_id": "internal", "request_id": "internal",
    "txn": "internal", "generation": "internal", "candidate_count": "internal", "duration_ms": "internal",
    "tenant": "confidential", "node": "confidential", "workload": "confidential", "site": "confidential",
    "region": "internal", "dataset": "sensitive", "labels": "confidential", "message": "internal",
    "token": "sensitive", "secret": "sensitive", "attestation_raw": "sensitive", "error": "internal", "detail": "internal",
}
ALLOWED_IDS = {  # signal -> identifiers allowed (pseudonymised where confidential)
    "metrics": set(),
    "logs": {"tenant", "node", "workload", "txn", "request_id", "trace_id"},
    "traces": {"txn", "request_id", "trace_id"},
    "explain": {"tenant", "node", "workload", "txn", "request_id"},
    "audit": {"tenant", "node", "workload", "txn", "request_id"},
}
RETENTION_DAYS = {"public": 400, "internal": 90, "confidential": 30, "sensitive": 0}
SECURITY_EVIDENCE_DAYS = 400
EXPORT_ALLOWLIST = {"otlp://collector.observability.internal:4317", "file://local-spool"}
_SECRET_RE = re.compile(r"(?i)(bearer\s+[A-Za-z0-9._\-]+|secret://\S+|-----BEGIN [A-Z ]+-----)")


def classify(field: str) -> str:
    return FIELD_CLASS.get(field, "confidential")  # unknown fields default to confidential


def pseudonym(value: str, key: bytes) -> str:
    return "p:" + hmac.new(key, value.encode(), hashlib.sha256).hexdigest()[:16]


def sanitize(record, *, signal: str, key: bytes, depth: int = 0):
    """Return a copy safe for ``signal``: sensitive dropped, confidential pseudonymised
    unless allowed, secrets scrubbed from free text, nesting bounded."""
    if depth > 5:
        return "<truncated>"
    if isinstance(record, dict):
        out = {}
        for k, v in record.items():
            cls = classify(k)
            if cls == "sensitive":
                continue
            if cls == "confidential" and not isinstance(v, (dict, list)):
                if k in ALLOWED_IDS[signal]:
                    out[k] = pseudonym(str(v), key)
                continue
            out[k] = sanitize(v, signal=signal, key=key, depth=depth + 1)
        return out
    if isinstance(record, list):
        return [sanitize(v, signal=signal, key=key, depth=depth + 1) for v in record[:100]]
    if isinstance(record, str):
        return _SECRET_RE.sub("<redacted>", record)[:1024]
    return record


def retention_days(field_class: str, *, security_evidence: bool = False) -> int:
    return max(RETENTION_DAYS[field_class], SECURITY_EVIDENCE_DAYS if security_evidence else 0)


def check_export(destination: str) -> None:
    from .errors import SchedulerError
    if destination not in EXPORT_ALLOWLIST:
        raise SchedulerError("PERMISSION_DENIED", "export destination not allow-listed")
    if not (destination.startswith("otlp://") or destination.startswith("file://")):
        raise SchedulerError("PERMISSION_DENIED", "unencrypted/unknown transport")


def offboard_tenant(records: list[dict], tenant_pseudonym: str) -> tuple[list[dict], int]:
    """Delete tenant-scoped operational telemetry; security/audit records are retained (separate legal basis)."""
    kept = [r for r in records if r.get("security_evidence") or r.get("tenant") != tenant_pseudonym]
    return kept, len(records) - len(kept)


def expire(records: list[dict], *, now_days: float) -> list[dict]:
    out = []
    for r in records:
        days = retention_days(r.get("class", "internal"), security_evidence=bool(r.get("security_evidence")))
        if now_days - r["day"] <= days:
            out.append(r)
    return out
