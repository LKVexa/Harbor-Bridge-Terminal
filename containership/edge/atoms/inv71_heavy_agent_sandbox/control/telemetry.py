"""Metrics, trace context, structured events, explain records (C072-C077).

* Metric labels are drawn from declared, bounded vocabularies; raw session IDs,
  hosts, URLs and tenant strings are refused as label values (C072-IMP-03).
* W3C ``traceparent`` is parsed strictly; an invalid or guest-supplied header
  starts a fresh trace rather than being forwarded into privileged components.
* Explain records capture decision inputs by digest so later policy changes do
  not rewrite an earlier explanation (C076, C077-IMP-04).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import os
import re
import threading
from typing import Callable, Iterable, Mapping

# ----------------------------------------------------------------- metric catalog
BUCKETS_S = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
LABEL_VALUES: Mapping[str, frozenset[str]] = {
    "operation": frozenset({"session.create", "session.stop", "session.teardown", "egress.decide",
                            "config.activate", "artifact.verify", "session.exec", "session.freeze",
                            "emergency.disable", "emergency.enable", "session.inspect"}),
    "outcome": frozenset({"SUCCESS", "PARTIAL", "DEGRADED", "RETRYABLE_FAILURE", "TERMINAL_FAILURE",
                          "SECURITY_REJECTED"}),
    "reason": frozenset(),  # filled from errors.REGISTRY codes + admission reasons at import
    "dependency": frozenset({"identity", "attestation", "policy", "keys", "time", "artifact_verify",
                             "audit_sink", "dns_resolver", "telemetry", "dashboard", "secondary_registry", "metadata"}),
    "state": frozenset(),  # lifecycle states
    "tier": frozenset({"gold", "silver", "bronze"}),  # tenant *tier*, never tenant id
}
CATALOG: Mapping[str, tuple[str, str, tuple[str, ...], str]] = {
    # name: (type, unit, labels, help)
    "heavybox_sessions": ("gauge", "sessions", ("state",), "Sessions by lifecycle state"),
    "heavybox_requests_total": ("counter", "requests", ("operation", "outcome"), "Control-plane requests"),
    "heavybox_rejections_total": ("counter", "requests", ("reason",), "Rejections by stable reason code"),
    "heavybox_operation_seconds": ("histogram", "seconds", ("operation",), "Operation latency"),
    "heavybox_egress_denied_total": ("counter", "connections", ("reason",), "Egress denials by reason (never by host)"),
    "heavybox_teardowns_verified_total": ("counter", "sessions", (), "Verified teardowns"),
    "heavybox_teardown_failures_total": ("counter", "sessions", (), "Teardown verification failures (zero budget)"),
    "heavybox_dependency_up": ("gauge", "bool", ("dependency",), "Dependency health"),
    "heavybox_admission_headroom_ratio": ("gauge", "ratio", (), "Free fraction of node capacity"),
    "heavybox_audit_spool_bytes": ("gauge", "bytes", (), "Unanchored audit spool size"),
}


def _init_vocab() -> None:
    from .errors import REGISTRY
    from .lifecycle import State
    extra = {"tenant_quota", "node_saturated", "fair_share", "unknown_tenant", "not_allowlisted",
             "port_or_protocol", "malformed_host", "cname_chain_too_long", "cname_not_allowlisted",
             "no_addresses", "blocked_range"}
    d = dict(LABEL_VALUES)
    d["reason"] = frozenset(REGISTRY) | frozenset(extra)
    d["state"] = frozenset(s.value for s in State)
    globals()["LABEL_VALUES"] = d


_init_vocab()


class CardinalityError(ValueError):
    pass


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._v: dict[tuple[str, tuple[tuple[str, str], ...]], float] = {}
        self._h: dict[tuple[str, tuple[tuple[str, str], ...]], list[float]] = {}

    def _key(self, name: str, labels: Mapping[str, str]):
        if name not in CATALOG:
            raise KeyError(name)
        declared = CATALOG[name][2]
        if set(labels) != set(declared):
            raise CardinalityError(f"{name}: labels {sorted(labels)} != {list(declared)}")
        for k, v in labels.items():
            if v not in LABEL_VALUES[k]:
                raise CardinalityError(f"{name}: {k}={v!r} not in bounded vocabulary")
        return name, tuple(sorted(labels.items()))

    def inc(self, name: str, n: float = 1.0, **labels: str) -> None:
        k = self._key(name, labels)
        with self._lock:
            self._v[k] = self._v.get(k, 0.0) + n

    def set(self, name: str, value: float, **labels: str) -> None:
        k = self._key(name, labels)
        with self._lock:
            self._v[k] = float(value)

    def observe(self, name: str, seconds: float, **labels: str) -> None:
        k = self._key(name, labels)
        with self._lock:
            b = self._h.setdefault(k, [0.0] * (len(BUCKETS_S) + 2))  # buckets.., +Inf, sum
            for i, le in enumerate(BUCKETS_S):
                if seconds <= le:
                    b[i] += 1
            b[len(BUCKETS_S)] += 1
            b[-1] += seconds

    def value(self, name: str, **labels: str) -> float:
        return self._v.get(self._key(name, labels), 0.0)

    def exposition(self) -> str:
        """Prometheus text format 0.0.4."""
        out: list[str] = []
        with self._lock:
            for name, (typ, unit, _labels, help_) in sorted(CATALOG.items()):
                out.append(f"# HELP {name} {help_} ({unit})")
                out.append(f"# TYPE {name} {typ}")
                for (n, lab), v in sorted(self._v.items()):
                    if n == name:
                        out.append(f"{name}{_fmt(lab)} {v:g}")
                for (n, lab), b in sorted(self._h.items()):
                    if n == name:
                        for i, le in enumerate(BUCKETS_S):
                            out.append(f"{name}_bucket{_fmt(lab + (('le', f'{le:g}'),))} {b[i]:g}")
                        out.append(f"{name}_bucket{_fmt(lab + (('le', '+Inf'),))} {b[len(BUCKETS_S)]:g}")
                        out.append(f"{name}_count{_fmt(lab)} {b[len(BUCKETS_S)]:g}")
                        out.append(f"{name}_sum{_fmt(lab)} {b[-1]:g}")
        return "\n".join(out) + "\n"


def _fmt(lab) -> str:
    return "{" + ",".join(f'{k}="{v}"' for k, v in lab) + "}" if lab else ""


# ----------------------------------------------------------------- trace context
_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    sampled: bool

    def header(self) -> str:
        return f"00-{self.trace_id}-{self.span_id}-{'01' if self.sampled else '00'}"

    def child(self, rand: Callable[[int], bytes] = os.urandom) -> "TraceContext":
        return TraceContext(self.trace_id, rand(8).hex(), self.sampled)


def parse_traceparent(value: str | None, *, trusted: bool, rand: Callable[[int], bytes] = os.urandom,
                      force_sample: bool = False) -> TraceContext:
    """Accept a caller trace only from a trusted (authenticated control-plane) peer."""
    if trusted and isinstance(value, str) and len(value) == 55:
        m = _TP.match(value)
        if m and m.group(1) != "0" * 32 and m.group(2) != "0" * 16:
            return TraceContext(m.group(1), m.group(2), force_sample or m.group(3) == "01")
    return TraceContext(rand(16).hex(), rand(8).hex(), force_sample)


# ----------------------------------------------------------------- events & explain
EVENT_CLASSES = ("security_rejection", "dependency_failure", "resource_rejection", "guest_failure",
                 "internal_defect", "lifecycle", "operator_action")


def classify(code: str) -> str:
    ns = code.split(".")[0]
    return {"AUTHN": "security_rejection", "AUTHZ": "security_rejection", "POLICY": "security_rejection",
            "ARTIFACT": "security_rejection", "DEPENDENCY": "dependency_failure", "AUDIT": "dependency_failure",
            "CAPACITY": "resource_rejection", "GUEST": "guest_failure", "INTERNAL": "internal_defect",
            "LIFECYCLE": "lifecycle", "TEARDOWN": "lifecycle"}.get(ns, "internal_defect")


@dataclass
class ExplainLog:
    """Point-in-time decision records (bounded)."""
    limit: int = 1024
    records: list[dict] = field(default_factory=list)

    def record(self, *, decision: str, reason_code: str, operation: str, session: str, tenant_tier: str,
               inputs: Mapping[str, str], rejected_alternatives: Iterable[str] = (), correlation_id: str = "") -> dict:
        if not re.fullmatch(r"[A-Z_]+(\.[A-Z_]+)+", reason_code):
            raise ValueError("reason codes are generated from the registry, not free text")
        rec = {"decision": decision, "reason_code": reason_code, "operation": operation, "session": session,
               "tenant_tier": tenant_tier, "inputs": dict(inputs), "rejected": list(rejected_alternatives),
               "correlation_id": correlation_id}
        if len(self.records) >= self.limit:
            del self.records[0]
        self.records.append(rec)
        return rec

    def explain(self, session: str, *, caller_sessions: frozenset[str] | None = None) -> list[dict]:
        """Operator explain view; a tenant-scoped caller sees only its own sessions."""
        if caller_sessions is not None and session not in caller_sessions:
            return []
        return [r for r in self.records if r["session"] == session]
