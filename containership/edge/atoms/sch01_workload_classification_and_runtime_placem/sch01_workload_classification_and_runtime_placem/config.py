"""MC-16 governed policy inputs, MC-22 declarative configuration, MC-23 provenance and
transactional activation.

A *revision* is an immutable, content-addressed document signed by the configured key.
Activation is all-or-nothing: validate -> verify signature -> check parent -> swap under a
lock -> record.  A rejected revision leaves the previous revision active.  Rollback is an
activation of an earlier revision, recorded like any other.
"""
from __future__ import annotations

import copy
import hashlib
import threading
from dataclasses import dataclass
from typing import Any, Mapping

from .engine import REQUIRED_TIER, TIER_ORDER
from .errors import SchedulerError
from .security import SecretProvider, canonical, mac

CONFIG_SCHEMA = "PK_SCHEDULER_CONFIG/1"

DEFAULT_CONFIG: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
    "environment": "prod",
    "freshness_bound": 30,
    "lease_ticks": 60,
    "provenance_trust": {"internal": "trusted", "first-party": "first-party", "partner": "third-party",
                         "public": "untrusted", "quarantined": "hostile"},
    "scoring": {"weights": {"tier": 1000, "latency": 10, "topology": 5, "free_slots": 1}},
    "latency_budget_ms": {"interactive": 20},
    "require_attestation": True,
    "tenant_quota": {},           # tenant -> slots; absent tenant => default_quota
    "default_quota": 100,
    "fair_share_max_fraction": 0.5,
    "admission": {"max_inflight": 64, "max_queue": 256},
    "breaker": {"failure_threshold": 5, "reset_after": 30},
    "retry": {"max_attempts": 3, "base_ms": 50, "max_ms": 2000},
    "features": {"latency_aware": True, "topology_aware": True},
    # precedence: operator overrides > policy bundle > defaults (MC-16)
    "precedence": ["operator", "policy", "default"],
}

REQUIRED_KEYS = set(DEFAULT_CONFIG)


def validate_config(doc: Mapping[str, Any]) -> list[str]:
    errs: list[str] = []
    missing = REQUIRED_KEYS - set(doc)
    extra = set(doc) - REQUIRED_KEYS
    if missing: errs.append(f"missing keys {sorted(missing)}")
    if extra: errs.append(f"unknown keys {sorted(extra)}")
    if errs: return errs
    if doc["schema"] != CONFIG_SCHEMA: errs.append("schema mismatch")
    for k in ("freshness_bound", "lease_ticks", "default_quota"):
        v = doc[k]
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0: errs.append(f"{k} must be a positive int")
    pt = doc["provenance_trust"]
    if not isinstance(pt, dict) or not pt: errs.append("provenance_trust must be a non-empty mapping")
    else:
        for p, t in pt.items():
            if t not in REQUIRED_TIER: errs.append(f"provenance {p!r} maps to unknown trust {t!r}")
        # a policy must never weaken the hostile/quarantined floor
        if pt.get("quarantined", "hostile") != "hostile": errs.append("quarantined provenance must stay hostile")
    f = doc["fair_share_max_fraction"]
    if not isinstance(f, (int, float)) or not 0 < f <= 1: errs.append("fair_share_max_fraction must be in (0,1]")
    if doc["precedence"] != ["operator", "policy", "default"]: errs.append("precedence order is fixed")
    if not isinstance(doc["require_attestation"], bool): errs.append("require_attestation must be bool")
    for q, v in dict(doc["tenant_quota"]).items():
        if not isinstance(v, int) or isinstance(v, bool) or v < 0: errs.append(f"quota for {q!r} invalid")
    return errs


def digest(doc: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical(doc)).hexdigest()


@dataclass(frozen=True)
class Revision:
    rev: int
    digest: str
    parent: str | None
    author: str
    activated_at: int
    doc: Mapping[str, Any]
    reason: str

    @property
    def rev_id(self) -> str:
        """Unique per activation even when content repeats (a rollback re-activates old content)."""
        return hashlib.sha256(f"{self.rev}|{self.digest}|{self.parent}".encode()).hexdigest()


class ConfigStore:
    def __init__(self, secrets: SecretProvider, *, key_id: str = "config", initial: Mapping[str, Any] | None = None,
                 author: str = "bootstrap", at: int = 0):
        self.secrets, self.key_id = secrets, key_id
        self._lock = threading.Lock()
        self.history: list[Revision] = []
        self.rejected: list[dict[str, Any]] = []
        doc = copy.deepcopy(dict(initial or DEFAULT_CONFIG))
        errs = validate_config(doc)
        if errs:
            raise SchedulerError("CONFIG_INVALID", "; ".join(errs))
        self.history.append(Revision(1, digest(doc), None, author, at, doc, "bootstrap"))

    @property
    def active(self) -> Revision:
        return self.history[-1]

    def get(self, key: str) -> Any:
        return copy.deepcopy(self.active.doc[key])

    def sign(self, doc: Mapping[str, Any], parent: str) -> dict[str, Any]:
        body = {"doc": dict(doc), "parent": parent}
        return {"body": body, "mac": mac(self.secrets, self.key_id, body)}

    def activate(self, signed: Mapping[str, Any], *, author: str, at: int, reason: str = "") -> Revision:
        with self._lock:
            try:
                body = dict(signed["body"]); sig = str(signed["mac"])
            except Exception:
                return self._reject(author, at, "malformed signed revision")
            import hmac as _h
            if not _h.compare_digest(mac(self.secrets, self.key_id, body), sig):
                return self._reject(author, at, "signature invalid")
            if body.get("parent") != self.active.rev_id:
                return self._reject(author, at, "stale parent (concurrent activation or replay)")
            doc = copy.deepcopy(dict(body["doc"]))
            errs = validate_config(doc)
            if errs:
                return self._reject(author, at, "; ".join(errs))
            rev = Revision(self.active.rev + 1, digest(doc), self.active.rev_id, author, at, doc, reason)
            self.history.append(rev)
            return rev

    def rollback(self, to_rev: int, *, author: str, at: int) -> Revision:
        with self._lock:
            target = next((r for r in self.history if r.rev == to_rev), None)
            if target is None:
                raise SchedulerError("NOT_FOUND", f"no revision {to_rev}")
            rev = Revision(self.active.rev + 1, target.digest, self.active.rev_id, author, at,
                           copy.deepcopy(dict(target.doc)), f"rollback to rev {to_rev}")
            self.history.append(rev)
            return rev

    def _reject(self, author: str, at: int, why: str):
        self.rejected.append({"author": author, "at": at, "reason": why, "active_rev": self.active.rev})
        raise SchedulerError("CONFIG_INVALID", why, details={"active_rev": self.active.rev})

    def provenance(self) -> list[dict[str, Any]]:
        return [{"rev": r.rev, "digest": r.digest, "parent": r.parent, "author": r.author,
                 "activated_at": r.activated_at, "reason": r.reason} for r in self.history]
