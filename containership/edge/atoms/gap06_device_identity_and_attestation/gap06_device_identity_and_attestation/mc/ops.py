"""MC-11 / MC-12 / MC-22 / MC-23 / MC-24 / MC-25 / MC-26 / MC-30.

Quarantine enforcement outbox, re-attestation scheduler, offline mode, health,
telemetry (metrics/logs/traces with redaction and cardinality caps), decision
explain, sharding and the typed configuration model.
"""
from __future__ import annotations

import hashlib
import json
import random
import threading
import uuid
from bisect import bisect
from dataclasses import dataclass, field

from .errors import fail, redact


# ---------------------------------------------------------------- MC-11
@dataclass
class QuarantineEnforcer:
    """Durable outbox of cordon commands delivered to enforcement sinks
    (GAP-01 supervisor, SCH-01 placement).  A node counts as *enforced* only
    when every sink acked; until then ``enforced()`` is False and callers must
    treat the node as untrusted anyway (quarantine is fail-closed locally)."""
    store: object
    sinks: dict  # name -> callable(cmd) -> bool (ack)

    def quarantine(self, node: str, reason: str, now: float) -> None:
        cmd = {"node": node, "action": "cordon", "reason": reason, "at": now, "acks": {}}
        self.store.put("quarantine", node, cmd)
        self.deliver(node)

    def deliver(self, node: str) -> dict:
        cmd = self.store.get("quarantine", node)
        if cmd is None:
            return {}
        for name, sink in self.sinks.items():
            if cmd["acks"].get(name):
                continue
            try:
                cmd["acks"][name] = bool(sink(dict(cmd)))
            except Exception:
                cmd["acks"][name] = False
        self.store.put("quarantine", node, cmd)
        return cmd["acks"]

    def enforced(self, node: str) -> bool:
        cmd = self.store.get("quarantine", node)
        return bool(cmd) and all(cmd["acks"].get(s) for s in self.sinks)

    def is_quarantined(self, node: str) -> bool:
        return self.store.get("quarantine", node) is not None

    def release(self, node: str, *, fresh_verdict_ok: bool, authorizer, principal) -> None:
        authorizer.require(principal, "quarantine_release")
        if not fresh_verdict_ok:
            raise fail("E_FORBIDDEN", "release requires a fresh passing attestation")
        with self.store.transaction() as tx:
            tx.delete("quarantine", node)


# ---------------------------------------------------------------- MC-12
@dataclass
class ReattestScheduler:
    ttl: float
    renew_fraction: float = 0.7
    jitter_fraction: float = 0.1
    max_backoff: float = 60.0
    rng: random.Random = field(default_factory=lambda: random.Random(0))

    def next_due(self, issued_at: float) -> float:
        base = issued_at + self.ttl * self.renew_fraction
        j = self.ttl * self.jitter_fraction
        due = base + self.rng.uniform(-j, j)
        return min(due, issued_at + self.ttl * 0.95)  # always strictly before expiry

    def backoff(self, attempt: int) -> float:
        return min(self.max_backoff, (2 ** attempt)) * self.rng.uniform(0.5, 1.0)

    @staticmethod
    def level(verdict_expires: float, now: float, level: str) -> str:
        return level if now < verdict_expires else "untrusted"  # fail-closed expiry


# ---------------------------------------------------------------- MC-22
@dataclass
class OfflineMode:
    """Disconnected site: verify against a cached policy/anchor set no older
    than ``max_offline_age``.  Offline verdicts are capped at ``software``
    level and flagged for reconciliation; beyond max age everything is untrusted."""
    max_offline_age: float
    cached_at: float | None = None
    cached_policy_version: int | None = None
    pending: list = field(default_factory=list)

    def cache(self, policy_version: int, now: float):
        self.cached_policy_version, self.cached_at = policy_version, now

    def decide(self, node: str, verified_level: str, now: float) -> str:
        if self.cached_at is None or now - self.cached_at > self.max_offline_age:
            return "untrusted"
        lvl = "software" if verified_level == "hardware" else verified_level
        self.pending.append({"node": node, "level": lvl, "at": now, "policy": self.cached_policy_version})
        return lvl

    def reconcile(self, online_policy_version: int) -> list:
        """Return offline verdicts made under a policy older than the online one
        (conflicts -> must re-attest)."""
        stale = [p for p in self.pending if p["policy"] != online_policy_version]
        self.pending = []
        return stale


# ---------------------------------------------------------------- MC-23
@dataclass
class Health:
    checks: dict = field(default_factory=dict)  # name -> callable() -> (ok, detail)
    critical: set = field(default_factory=set)

    def report(self) -> dict:
        res = {}
        for n, fn in self.checks.items():
            try:
                ok, d = fn()
            except Exception as e:
                ok, d = False, f"check raised {type(e).__name__}"
            res[n] = {"ok": bool(ok), "detail": redact(str(d))}
        live = True
        ready = all(v["ok"] for k, v in res.items() if k in self.critical)
        degraded = ready and not all(v["ok"] for v in res.values())
        return {"live": live, "ready": ready, "status": "degraded" if degraded else ("ready" if ready else "unready"),
                "checks": res}


# ---------------------------------------------------------------- MC-24
ALLOWED_LABELS = {"code", "level", "result", "site", "op"}


@dataclass
class Telemetry:
    max_series: int = 2000
    counters: dict = field(default_factory=dict)
    histos: dict = field(default_factory=dict)
    logs: list = field(default_factory=list)
    max_logs: int = 10_000
    dropped_series: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def _key(self, name, labels):
        bad = set(labels) - ALLOWED_LABELS
        if bad:
            raise ValueError(f"label(s) {bad} not allowed (cardinality control)")
        return (name, tuple(sorted(labels.items())))

    def inc(self, name, n=1, **labels):
        k = self._key(name, labels)
        with self._lock:
            if k not in self.counters and len(self.counters) + len(self.histos) >= self.max_series:
                self.dropped_series += 1
                return
            self.counters[k] = self.counters.get(k, 0) + n

    def observe(self, name, value, **labels):
        k = self._key(name, labels)
        with self._lock:
            if k not in self.histos and len(self.counters) + len(self.histos) >= self.max_series:
                self.dropped_series += 1
                return
            self.histos.setdefault(k, []).append(value)
            if len(self.histos[k]) > 1000:
                del self.histos[k][:500]

    def log(self, event, *, trace_id=None, **fields_):
        rec = {"event": event, "trace_id": trace_id or uuid.uuid4().hex,
               **{k: redact(str(v))[:256] for k, v in fields_.items()}}
        with self._lock:
            self.logs.append(rec)
            if len(self.logs) > self.max_logs:
                del self.logs[: self.max_logs // 2]
        return rec

    def exposition(self) -> str:
        """Prometheus text format."""
        out = []
        for (n, lbl), v in sorted(self.counters.items()):
            ls = ",".join(f'{k}="{val}"' for k, val in lbl)
            out.append(f"{n}{{{ls}}} {v}")
        for (n, lbl), vs in sorted(self.histos.items()):
            ls = ",".join(f'{k}="{val}"' for k, val in lbl)
            s = sorted(vs)
            out.append(f'{n}_count{{{ls}}} {len(s)}')
            out.append(f'{n}_p99{{{ls}}} {s[min(len(s) - 1, int(len(s) * 0.99))]}')
        return "\n".join(out) + "\n"


def trace_context(parent: str | None = None) -> str:
    """W3C traceparent (version 00)."""
    trace = parent.split("-")[1] if parent else uuid.uuid4().hex
    return f"00-{trace}-{uuid.uuid4().hex[:16]}-01"


# ---------------------------------------------------------------- MC-25
def explain(decision_record: dict, policy_rec: dict | None, verdict: dict | None) -> dict:
    return {"schema": "GAP06-EXPLAIN/1", "node": decision_record.get("node"),
            "decision": decision_record.get("decision"), "reason_code": decision_record.get("reason_code"),
            "raw_evidence_sha256": decision_record.get("raw_evidence_sha256"),
            "claims_sha256": decision_record.get("claims_sha256"),
            "policy_version": decision_record.get("policy_version"),
            "policy_digest": (policy_rec or {}).get("digest"),
            "trust_anchor_set": decision_record.get("trust_anchor_set"),
            "verifier_version": decision_record.get("verifier_version"),
            "expires_at": (verdict or {}).get("expires_at")}


# ---------------------------------------------------------------- MC-26
class ShardRing:
    """Consistent hashing of node ids onto shards with virtual nodes."""
    def __init__(self, shards, vnodes: int = 64):
        self.ring = sorted((int(hashlib.sha256(f"{s}#{i}".encode()).hexdigest()[:16], 16), s)
                           for s in shards for i in range(vnodes))
        self.keys = [k for k, _ in self.ring]

    def shard_for(self, node: str) -> str:
        h = int(hashlib.sha256(node.encode()).hexdigest()[:16], 16)
        return self.ring[bisect(self.keys, h) % len(self.ring)][1]


# ---------------------------------------------------------------- MC-30
CONFIG_SCHEMA = {
    # name: (type, default, lo, hi, mutable_at_runtime, restart_required)
    "challenge_ttl_s": (float, 30.0, 5.0, 300.0, True, False),
    "verdict_ttl_s": (float, 3600.0, 60.0, 86400.0, True, False),
    "skew_budget_s": (float, 2.0, 0.1, 30.0, True, False),
    "max_outstanding_challenges": (int, 100_000, 100, 10_000_000, False, True),
    "rate_per_principal": (float, 5.0, 0.1, 1000.0, True, False),
    "policy_threshold": (int, 2, 2, 9, False, True),
    "offline_max_age_s": (float, 86400.0, 0.0, 7 * 86400.0, True, False),
    "require_revocation_info": (bool, True, None, None, False, True),
}


def load_config(values: dict, *, signature_ok: bool) -> dict:
    """Validate a config document; unsigned configs are refused (provenance)."""
    if not signature_ok:
        raise fail("E_POLICY_UNSIGNED", "configuration must be signed")
    unknown = set(values) - set(CONFIG_SCHEMA)
    if unknown:
        raise fail("E_SCHEMA", f"unknown config keys {sorted(unknown)}")
    out = {}
    for k, (typ, default, lo, hi, _m, _r) in CONFIG_SCHEMA.items():
        v = values.get(k, default)
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if not isinstance(v, typ) or (typ is not bool and isinstance(v, bool)):
            raise fail("E_SCHEMA", f"{k} must be {typ.__name__}")
        if lo is not None and not (lo <= v <= hi):
            raise fail("E_SCHEMA", f"{k}={v} outside [{lo},{hi}]")
        out[k] = v
    out["_digest"] = hashlib.sha256(json.dumps(out, sort_keys=True).encode()).hexdigest()
    return out
