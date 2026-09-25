"""Structured observability and tamper-evident audit log (checklist components 16 and 17).

* ``Metrics`` — counters/gauges/histograms with declared label sets and a hard cardinality
  budget; unknown label values collapse to ``"other"`` instead of creating series.
* ``StructuredLogger`` — JSON lines with stable fields, header/query/credential redaction and
  bounded attacker-controlled strings.
* ``AuditLog`` — append-only, hash-chained, HMAC-signed records with key ids (rotation keeps
  the chain verifiable) and ``verify_audit_stream`` — an independent verifier that detects
  modification, deletion, truncation (against an anchored head), reordering and duplication.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import re
import time
import uuid
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from .errors import Inv20Error, safe_detail
from .identity import KeyProvider

AUDIT_SCHEMA = "INV20_AUDIT/1"
LOG_SCHEMA = "INV20_LOG/1"
MAX_SERIES = 1000

# ---------------------------------------------------------------- metrics
METRIC_SPECS: Dict[str, Tuple[str, str, Tuple[str, ...], Dict[str, Tuple[str, ...]]]] = {
    # name: (type, unit, labels, allowed values per label)
    "requests_handled": ("counter", "1", ("status_class",), {"status_class": ("1xx", "2xx", "3xx", "4xx", "5xx", "error")}),
    "egress_denials": ("counter", "1", ("reason",), {}),   # reason bounded by egress.REASONS
    "body_bytes": ("histogram", "By", ("direction",), {"direction": ("in", "out")}),
    "trailer_resolutions": ("counter", "1", ("outcome",), {"outcome": ("resolved", "failed", "cancelled")}),
    "request_duration": ("histogram", "s", (), {}),
    "queue_wait": ("histogram", "s", (), {}),
    "active_requests": ("gauge", "1", (), {}),
    "active_connections": ("gauge", "1", (), {}),
    "retries": ("counter", "1", ("code",), {}),
    "cancellations": ("counter", "1", (), {}),
    "timeouts": ("counter", "1", ("stage",), {"stage": ("dns", "connect", "head", "body", "request")}),
    "dependency_up": ("gauge", "1", ("dependency",), {"dependency": ("config", "policy", "identity", "resolver", "audit")}),
    "saturation": ("gauge", "1", ("resource",), {"resource": ("queue", "concurrency", "connections", "memory")}),
}
BUCKETS = (0.0005, 0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5, 10, 1024, 65536, 1 << 20, 1 << 24)


class Metrics:
    def __init__(self) -> None:
        from .egress import REASONS
        from .errors import REGISTRY
        self._allowed = {k: dict(v[3]) for k, v in METRIC_SPECS.items()}
        self._allowed["egress_denials"]["reason"] = tuple(REASONS) + ("capability_scope",)
        self._allowed["retries"]["code"] = tuple(REGISTRY)
        self.series: Dict[Tuple[str, Tuple[str, ...]], object] = {}

    def _key(self, name: str, labels: Dict[str, str]) -> Tuple[str, Tuple[str, ...]]:
        if name not in METRIC_SPECS:
            raise KeyError(f"undeclared metric {name}")
        spec_labels = METRIC_SPECS[name][2]
        if set(labels) != set(spec_labels):
            raise KeyError(f"{name} requires labels {spec_labels}")
        vals = []
        for l in spec_labels:
            v = str(labels[l])
            allowed = self._allowed[name].get(l)
            vals.append(v if allowed is None or v in allowed else "other")
        key = (name, tuple(vals))
        if key not in self.series and len(self.series) >= MAX_SERIES:
            key = (name, tuple("other" for _ in vals))
        return key

    def inc(self, name: str, n: float = 1, **labels: str) -> None:
        k = self._key(name, labels)
        self.series[k] = float(self.series.get(k, 0.0)) + n  # type: ignore[arg-type]

    def set(self, name: str, v: float, **labels: str) -> None:
        self.series[self._key(name, labels)] = float(v)

    def observe(self, name: str, v: float, **labels: str) -> None:
        k = self._key(name, labels)
        h = self.series.setdefault(k, {"count": 0, "sum": 0.0, "buckets": [0] * (len(BUCKETS) + 1)})
        h["count"] += 1  # type: ignore[index]
        h["sum"] += v    # type: ignore[index]
        idx = next((i for i, b in enumerate(BUCKETS) if v <= b), len(BUCKETS))
        h["buckets"][idx] += 1  # type: ignore[index]

    def get(self, name: str, **labels: str):
        return self.series.get(self._key(name, labels))

    def export(self) -> dict:
        return {"schema": "INV20_METRICS/1",
                "series": [{"name": n, "labels": dict(zip(METRIC_SPECS[n][2], v)), "value": val}
                           for (n, v), val in sorted(self.series.items(), key=lambda kv: str(kv[0]))]}


# ---------------------------------------------------------------- logs
REDACT_FIELDS = {"authorization", "proxy-authorization", "cookie", "set-cookie", "x-api-key",
                 "x-auth-token", "password", "secret", "token", "access_token", "refresh_token", "key"}
_QUERY_SECRET = re.compile(r"(?i)([?&](?:token|key|sig|signature|password|secret|access_token|code)=)[^&#]*")
MAX_FIELD = 256


def redact(value: object, key: str = "") -> object:
    if key.lower() in REDACT_FIELDS:
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: redact(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        if len(value) == 2 and all(isinstance(x, str) for x in value) and value[0].lower() in REDACT_FIELDS:
            return [value[0], "[REDACTED]"]
        return [redact(v) for v in value]
    if isinstance(value, str):
        return safe_detail(_QUERY_SECRET.sub(r"\1[REDACTED]", value), MAX_FIELD)
    return value


@dataclass
class StructuredLogger:
    node: str
    site: str
    environment: str
    release: str
    config_revision: str = "-"
    sink: Callable[[str], None] = print
    clock: Callable[[], float] = time.time
    records: List[dict] = field(default_factory=list)

    def log(self, severity: str, event: str, *, tenant: str = "-", workload: str = "-", trace_id: str = "-",
            reason: str = "-", **fields: object) -> dict:
        if severity not in ("debug", "info", "warn", "error", "critical"):
            severity = "info"
        rec = {"schema": LOG_SCHEMA, "ts": round(self.clock(), 6), "severity": severity,
               "event": safe_detail(event, 64), "node": self.node, "site": self.site, "env": self.environment,
               "release": self.release, "config_revision": self.config_revision,
               "tenant": _pseudonym(tenant), "workload": safe_detail(workload, 64), "trace_id": safe_detail(trace_id, 64),
               "reason": safe_detail(reason, 64), "fields": redact(fields)}
        self.records.append(rec)
        self.sink(json.dumps(rec, sort_keys=True))
        return rec


def _pseudonym(tenant: str) -> str:
    """Privacy-safe, stable tenant identifier for logs shared across tenant boundaries."""
    if tenant == "-":
        return tenant
    return "t_" + hashlib.sha256(("inv20-log:" + tenant).encode()).hexdigest()[:12]


# ---------------------------------------------------------------- tracing
_TRACEPARENT = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def accept_traceparent(value: Optional[str], trusted_peer: bool) -> Tuple[str, str]:
    """Only a trusted (same-tenant, authenticated) peer's W3C traceparent is continued."""
    if trusted_peer and value and _TRACEPARENT.fullmatch(value):
        m = _TRACEPARENT.fullmatch(value)
        if m.group(1) != "0" * 32 and m.group(2) != "0" * 16:  # type: ignore[union-attr]
            return m.group(1), uuid.uuid4().hex[:16]  # type: ignore[union-attr]
    return uuid.uuid4().hex, uuid.uuid4().hex[:16]


def outbound_traceparent(trace_id: str, span_id: str, destination_trusted: bool) -> Optional[str]:
    return f"00-{trace_id}-{span_id}-01" if destination_trusted else None


# ---------------------------------------------------------------- audit
class AuditUnavailable(Inv20Error):
    code = "E_AUDIT_UNAVAILABLE"


GENESIS = "0" * 64


class AuditLog:
    """Append-only, hash-chained, HMAC-signed audit stream."""

    def __init__(self, keys: KeyProvider, sink: Optional[Callable[[str], None]] = None,
                 clock: Callable[[], float] = time.time, release: str = "", config_revision: str = "",
                 policy_version: str = "") -> None:
        self.keys, self.clock = keys, clock
        self.records: List[dict] = []
        self.head = GENESIS
        self.seq = 0
        self.sink = sink
        self.available = True
        self.context = {"release": release, "config_revision": config_revision, "policy_version": policy_version}

    def emit(self, actor: str, scope: str, action: str, target: str, result: str, reason: str,
             trace_id: str = "-", critical: bool = True) -> Optional[dict]:
        if not self.available:
            if critical:
                raise AuditUnavailable(action)      # fail closed for security-critical actions
            return None                             # fail safe for non-critical telemetry
        self.seq += 1
        body = {"schema": AUDIT_SCHEMA, "id": str(uuid.uuid4()), "seq": self.seq, "ts": self.clock(),
                "actor": safe_detail(actor, 128), "scope": safe_detail(scope, 128), "action": action,
                "target": safe_detail(target, 128), "result": result, "reason": reason, "trace_id": trace_id,
                **self.context, "prev": self.head, "kid": self.keys.active}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        body["hash"] = hashlib.sha256(raw).hexdigest()
        body["sig"] = hmac.new(self.keys.get(self.keys.active), body["hash"].encode(), hashlib.sha256).hexdigest()
        self.head = body["hash"]
        self.records.append(body)
        if self.sink:
            self.sink(json.dumps(body, sort_keys=True))
        return body

    def anchor(self) -> dict:
        """Publish (seq, head) out-of-band; lets the verifier detect tail truncation."""
        return {"seq": self.seq, "head": self.head}


def verify_audit_stream(records: Sequence[dict], keys: KeyProvider, anchor: Optional[dict] = None) -> dict:
    """Independent verifier: trusts only the key provider and the published anchor."""
    problems: List[str] = []
    prev, expect_seq, seen = GENESIS, 1, set()
    for i, rec in enumerate(records):
        body = {k: v for k, v in rec.items() if k not in ("hash", "sig")}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        h = hashlib.sha256(raw).hexdigest()
        if h != rec.get("hash"):
            problems.append(f"record {i}: content modified")
        try:
            key = keys.get(rec.get("kid", ""))
            if not hmac.compare_digest(hmac.new(key, str(rec.get("hash")).encode(), hashlib.sha256).hexdigest(),
                                       str(rec.get("sig"))):
                problems.append(f"record {i}: bad signature")
        except Inv20Error:
            problems.append(f"record {i}: unknown key")
        if rec.get("id") in seen:
            problems.append(f"record {i}: duplicate")
        seen.add(rec.get("id"))
        if rec.get("prev") != prev:
            problems.append(f"record {i}: chain break (deleted/reordered)")
        if rec.get("seq") != expect_seq:
            problems.append(f"record {i}: sequence gap/reorder")
        prev, expect_seq = rec.get("hash"), (rec.get("seq") or 0) + 1
    if anchor is not None and (anchor.get("seq") != expect_seq - 1 or anchor.get("head") != prev):
        problems.append("stream truncated or extended relative to anchor")
    return {"schema": "INV20_AUDIT_VERIFY/1", "records": len(records), "ok": not problems, "problems": problems}
