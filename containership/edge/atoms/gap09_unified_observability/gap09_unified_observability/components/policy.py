"""Retention/sampling/privacy policy engine (34) and high-cardinality safety
controls (35).  Every drop/redaction/sample decision is explained through a
``DecisionLog`` (37)."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from .controls import DecisionLog
from .errors import Malformed

# Secret detectors: patterns only, never echo the match (report kind + offset).
SECRET_PATTERNS = (
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[a-z0-9\-._~+/]{16,}=*")),
    ("password_assignment", re.compile(r"(?i)\b(pass(word)?|pwd|secret|token|access[_-]?key|api[_-]?key)\s*[=:]\s*\S{4,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ipv4", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
)


def find_secrets(text: str) -> list[tuple[str, int]]:
    return [(kind, m.start()) for kind, rx in SECRET_PATTERNS for m in rx.finditer(text)]


def redact(text: str, kinds: frozenset | None = None) -> tuple[str, list[str]]:
    hits = []
    for kind, rx in SECRET_PATTERNS:
        if kinds is not None and kind not in kinds:
            continue
        text, n = rx.subn(f"<redacted:{kind}>", text)
        if n:
            hits.append(kind)
    return text, hits


@dataclass
class TenantPolicy:
    retention_seconds: int
    residency: str = "any"
    log_sample_rate: float = 1.0      # probability kept for INFO and below
    trace_sample_rate: float = 1.0
    export_allowed: bool = False
    redact_kinds: frozenset = frozenset(k for k, _ in SECRET_PATTERNS)

    def __post_init__(self) -> None:
        if self.retention_seconds <= 0:
            raise Malformed("retention must be positive")
        for r in (self.log_sample_rate, self.trace_sample_rate):
            if not 0.0 <= r <= 1.0:
                raise Malformed("sample rates must be within [0,1]")


def deterministic_keep(key: str, rate: float) -> bool:
    """Consistent sampling: same key -> same decision on every node."""
    if rate >= 1.0:
        return True
    if rate <= 0.0:
        return False
    h = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "big")
    return h / 2**64 < rate


class PolicyEngine:
    def __init__(self, default: TenantPolicy, per_tenant: dict[str, TenantPolicy] | None = None,
                 decisions: DecisionLog | None = None) -> None:
        self.default = default
        self.per_tenant = dict(per_tenant or {})
        self.decisions = decisions or DecisionLog()

    def for_tenant(self, tenant: str) -> TenantPolicy:
        return self.per_tenant.get(tenant, self.default)

    def expired(self, tenant: str, at: int, now: int) -> bool:
        return now - at >= self.for_tenant(tenant).retention_seconds

    def may_export(self, tenant: str, *, destination_region: str) -> bool:
        p = self.for_tenant(tenant)
        ok = p.export_allowed and (p.residency == "any" or p.residency == destination_region)
        if not ok:
            self.decisions.record(decision="deny_export", reason="policy/residency", rule="POL-EXPORT",
                                  subject={"tenant": tenant, "region": destination_region}, at=0)
        return ok


@dataclass
class CardinalityGuard:
    """Label/field budgets with an explicit overflow policy.

    * at most ``max_labels`` labels per record, keys <= 64 chars, values <= 256;
    * at most ``max_values_per_label`` distinct values per (tenant, signal, label);
      overflow values are replaced by the literal ``"__overflow__"`` (policy
      ``fold``) or the record is refused (policy ``refuse``) -- never silently
      grown;
    * label values that look like secrets are replaced with a digest marker.
    """
    max_labels: int = 16
    max_values_per_label: int = 1000
    overflow: str = "fold"
    decisions: DecisionLog = field(default_factory=DecisionLog)
    _seen: dict = field(default_factory=dict)

    def apply(self, tenant: str, signal: str, labels: dict[str, Any], at: int = 0) -> dict[str, str]:
        if len(labels) > self.max_labels:
            raise Malformed("too many labels", limit=self.max_labels)
        out = {}
        for k, v in sorted(labels.items()):
            if not isinstance(k, str) or not re.fullmatch(r"[a-z_][a-z0-9_.]{0,63}", k):
                raise Malformed("label key invalid")
            v = str(v)
            if len(v) > 256:
                raise Malformed("label value too long", label=k)
            if find_secrets(v):
                self.decisions.record(decision="redact", reason="secret-like label value", rule="CARD-SECRET",
                                      subject={"tenant": tenant, "signal": signal, "label": k}, at=at)
                v = "<secret:" + hashlib.sha256(v.encode()).hexdigest()[:12] + ">"
            key = (tenant, signal, k)
            vals = self._seen.setdefault(key, set())
            if v not in vals and len(vals) >= self.max_values_per_label:
                self.decisions.record(decision=self.overflow, reason="label value budget", rule="CARD-BUDGET",
                                      subject={"tenant": tenant, "signal": signal, "label": k}, at=at)
                if self.overflow == "refuse":
                    raise Malformed("label value budget exhausted", label=k)
                v = "__overflow__"
            vals.add(v)
            out[k] = v
        return out
