"""MC-016 / MC-029 -- metrics, structured logs, trace context, privacy filter.

* Counters / gauges / latency histograms keyed by a *bounded* label set;
  label values outside declared enumerations collapse to ``other`` so an
  attacker cannot explode cardinality.
* Outcomes are classified into denial / attack / dependency / overload /
  defect so alerts can separate them (see ``classify``).
* W3C ``traceparent`` parsing/propagation with strict validation.
* ``PrivacyFilter`` applies the MC-029 retention classes: host paths are
  hashed, secrets dropped, tenant IDs pseudonymised per region salt.
* Prometheus text exposition for export.
"""
from __future__ import annotations

import bisect
import hashlib
import hmac
import json
import re
import secrets
import threading
from typing import Any

from .errors import Category, Inv13Error

BUCKETS_US = (1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 5000, 25000, 100000)
LABELS = {
    "capability": {"filesystem", "wall-clock", "monotonic-clock", "random", "sockets",
                   "environment", "stdio", "http-outgoing"},
    "outcome": {"ok", "denial", "attack", "dependency", "overload", "defect"},
    "op": {"open", "resolve", "grant", "revoke", "connect", "listen", "http", "random", "clock", "instantiate"},
}
_ATTACK_HINTS = ("path-escape", "dotdot", "absolute", "nul", "symlink", "cross-tenant",
                 "rights amplification", "scope widening", "private address", "signature", "replay")


def classify(err: Exception | None) -> str:
    if err is None:
        return "ok"
    if isinstance(err, Inv13Error):
        detail = str(err.host_detail).lower()
        if err.code.name in ("PATH_ESCAPE", "SYMLINK_REFUSED") or any(h in detail for h in _ATTACK_HINTS):
            return "attack"
        return {Category.DENIED: "denial", Category.INVALID: "denial",
                Category.UNAVAILABLE: "dependency", Category.TIMEOUT: "dependency",
                Category.QUOTA: "overload", Category.CANCELLED: "ok",
                Category.NOT_FOUND: "denial", Category.CONFLICT: "denial"}.get(err.category, "defect")
    return "defect"


class Metrics:
    def __init__(self) -> None:
        self._c: dict[tuple, float] = {}
        self._h: dict[tuple, list[int]] = {}
        self._g: dict[tuple, float] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(name: str, labels: dict[str, str]) -> tuple:
        norm = []
        for k in sorted(labels):
            allowed = LABELS.get(k)
            v = labels[k] if allowed is None or labels[k] in allowed else "other"
            if allowed is None:
                v = "other"  # undeclared label keys never carry user data
            norm.append((k, v))
        return (name, tuple(norm))

    def inc(self, name: str, n: float = 1, **labels: str) -> None:
        k = self._key(name, labels)
        with self._lock:
            self._c[k] = self._c.get(k, 0) + n

    def gauge(self, name: str, v: float, **labels: str) -> None:
        with self._lock:
            self._g[self._key(name, labels)] = v

    def observe_us(self, name: str, us: float, **labels: str) -> None:
        k = self._key(name, labels)
        with self._lock:
            h = self._h.setdefault(k, [0] * (len(BUCKETS_US) + 1))
            h[bisect.bisect_left(BUCKETS_US, us)] += 1

    def get(self, name: str, **labels: str) -> float:
        return self._c.get(self._key(name, labels), 0)

    def series_count(self) -> int:
        return len(self._c) + len(self._h) + len(self._g)

    def exposition(self) -> str:
        out = []
        def lab(t): return ",".join(f'{k}="{v}"' for k, v in t)
        with self._lock:
            for (n, t), v in sorted(self._c.items()):
                out.append(f"inv13_{n}_total{{{lab(t)}}} {v}")
            for (n, t), v in sorted(self._g.items()):
                out.append(f"inv13_{n}{{{lab(t)}}} {v}")
            for (n, t), h in sorted(self._h.items()):
                cum = 0
                for b, c in zip(list(BUCKETS_US) + ["+Inf"], h):
                    cum += c
                    sep = "," if t else ""
                    out.append(f'inv13_{n}_bucket{{{lab(t)}{sep}le="{b}"}} {cum}')
        return "\n".join(out) + "\n"


_TP = re.compile(r"^00-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})$")


def parse_traceparent(value: Any) -> tuple[str, str, int] | None:
    if not isinstance(value, str) or len(value) != 55:
        return None
    m = _TP.match(value)
    if not m or m.group(1) == "0" * 32 or m.group(2) == "0" * 16:
        return None
    return m.group(1), m.group(2), int(m.group(3), 16)


def child_traceparent(parent: str | None) -> str:
    p = parse_traceparent(parent)
    trace = p[0] if p else secrets.token_hex(16)
    flags = p[2] if p else 1
    return f"00-{trace}-{secrets.token_hex(8)}-{flags:02x}"


class StructuredLog:
    def __init__(self, privacy: "PrivacyFilter", limit: int = 10000) -> None:
        self.records: list[str] = []
        self._privacy, self._limit = privacy, limit
        self.dropped = 0

    def emit(self, level: str, event: str, trace: str | None = None, **fields: Any) -> None:
        if len(self.records) >= self._limit:
            self.dropped += 1
            return
        rec = {"level": level, "event": event, "traceparent": trace, **self._privacy(fields)}
        self.records.append(json.dumps(rec, sort_keys=True, default=str))


class PrivacyFilter:
    """MC-029 field classes. Unknown fields are dropped (allowlist, not denylist)."""

    CLASSES = {
        "public": {"capability", "op", "outcome", "code", "world", "rule_id", "policy_digest",
                   "release", "node", "count", "latency_us", "reason", "action", "seq"},
        "pseudonymise": {"tenant", "workload", "component"},
        "hash": {"path", "host_root", "logical", "requested", "normalized", "url", "host"},
        "drop": {"secret", "env", "argv", "token", "body", "headers", "stack"},
    }

    def __init__(self, region_salt: bytes) -> None:
        if len(region_salt) < 16:
            raise ValueError("salt too short")
        self._salt = region_salt

    def _h(self, v: Any, tag: str) -> str:
        return tag + ":" + hmac.new(self._salt, str(v).encode(), hashlib.sha256).hexdigest()[:16]

    def __call__(self, fields: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in fields.items():
            if k in self.CLASSES["public"]:
                out[k] = v if isinstance(v, (int, float, bool)) or v is None else str(v)[:256]
            elif k in self.CLASSES["pseudonymise"]:
                out[k] = self._h(v, "p")
            elif k in self.CLASSES["hash"]:
                out[k] = self._h(v, "h")
            # 'drop' and unknown keys are omitted
        return out
