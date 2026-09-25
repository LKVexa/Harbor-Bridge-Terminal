"""Declarative configuration (M17), residency (M38), co-residency (M39) and rollout/kill switch (M30)."""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from .errors import PlaneError
from .runtime import TIERS, TRUST_CLASSES
from .validation import validate

PROFILES = ("development", "staging", "production")

DEFAULT_CONFIG: dict = {
    "schema": "PK_PLANE_CONFIG/1",
    "profile": "development",
    "node_id": "node-local",
    "site": "local",
    "limits": {"max_instances": 4096, "per_tenant_limit": 1024, "max_inflight": 32, "max_queue": 256,
               "per_tenant_queue": 32, "cpu_milli": 64000, "memory_mib": 262144, "headroom": 0.1},
    "tenant_weights": {},
    "attestation": {"max_age_s": 300, "clock_skew_s": 30},
    "residency": {},
    "coresidency": {"trusted": "shared", "first-party": "shared", "third-party": "shared",
                    "untrusted": "tenant-exclusive", "hostile": "dedicated"},
    "rollout": {"stage": "full", "canary_tenants": []},
    "telemetry": {"trace_sample_rate": 0.1, "tenant_identifier_mode": "hashed",
                  "retention_days_logs": 30, "retention_days_audit": 400},
    "slo": {"p50_ms": 5.0, "p99_ms": 50.0},
}

#: Controls the production profile will not start without.
PRODUCTION_REQUIREMENTS = (
    "actor authentication (Authenticator)",
    "signed classification verifier",
    "artifact policy",
    "attestation verifier",
    "durable state store",
    "durable audit sink",
    "no reference providers",
)


def _merge(base: dict, over: Mapping) -> dict:
    out = dict(base)
    for k, v in over.items():
        out[k] = _merge(out[k], v) if isinstance(v, Mapping) and isinstance(out.get(k), dict) else v
    return out


@dataclass(frozen=True)
class PlaneConfig:
    doc: Mapping
    generation: str

    @classmethod
    def load(cls, overrides: Mapping | None = None) -> "PlaneConfig":
        doc = _merge(DEFAULT_CONFIG, overrides or {})
        validate(doc, "PK_PLANE_CONFIG/1")
        lim = doc["limits"]
        if lim["per_tenant_limit"] > lim["max_instances"]:
            raise PlaneError("PLN04-VAL-001", details={"field": "limits.per_tenant_limit", "reason": "exceeds max_instances"})
        for tenant, sites in doc["residency"].items():
            if not sites:
                raise PlaneError("PLN04-VAL-001", details={"field": f"residency.{tenant}", "reason": "empty site list"})
        gen = "sha256:" + hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        return cls(doc=json.loads(json.dumps(doc)), generation=gen)

    @classmethod
    def from_file(cls, path: str) -> "PlaneConfig":
        with open(path, encoding="utf-8") as fh:
            return cls.load(json.load(fh))

    def __getitem__(self, key: str):
        return self.doc[key]

    @property
    def production(self) -> bool:
        return self.doc["profile"] == "production"


def check_residency(config: PlaneConfig, tenant: str, requested_site: str | None) -> None:
    """M38 - a tenant with a residency rule may only run at listed sites; the node's site is authoritative."""
    node_site = config["site"]
    if requested_site is not None and requested_site != node_site:
        raise PlaneError("PLN04-POL-004", details={"tenant": tenant, "site": node_site, "reason": "request pinned to another site"})
    allowed = config["residency"].get(tenant)
    if allowed is not None and node_site not in allowed:
        raise PlaneError("PLN04-POL-004", details={"tenant": tenant, "site": node_site})


def check_coresidency(config: PlaneConfig, tenant: str, trust_class: str, tier: str,
                      residents: Iterable) -> None:
    """M39 - side-channel mitigation by placement.

    * ``shared``            no restriction beyond tier isolation.
    * ``tenant-exclusive``  the tier on this node must not host another tenant.
    * ``dedicated``         the *node* must not host another tenant at all.
    Also enforced in reverse: a new workload may not join a node/tier that a
    resident's policy reserved exclusively for another tenant.
    """
    rules = config["coresidency"]
    mode = rules[trust_class]
    for r in residents:
        if r.tenant == tenant or r.state not in ("active", "quarantined"):
            continue
        their = rules[r.trust_class]
        if mode == "dedicated" or their == "dedicated":
            raise PlaneError("PLN04-POL-005", details={"tenant": tenant, "tier": tier, "reason": "dedicated-node policy"})
        if r.tier == tier and (mode == "tenant-exclusive" or their == "tenant-exclusive"):
            raise PlaneError("PLN04-POL-005", details={"tenant": tenant, "tier": tier, "reason": "tenant-exclusive tier policy"})


class RolloutControl:
    """M30 - staged rollout and emergency disable.

    Stages: ``disabled`` (refuse all new admissions) -> ``canary`` (only listed
    tenants) -> ``full``.  ``emergency_disable()`` flips to disabled
    immediately and is audited by the plane; teardown is always permitted so
    operators can drain.
    """

    STAGES = ("disabled", "canary", "full")

    def __init__(self, stage: str = "full", canary_tenants: Iterable[str] = ()) -> None:
        self._lock = threading.Lock()
        self.set_stage(stage, canary_tenants)
        self.reason = ""

    def set_stage(self, stage: str, canary_tenants: Iterable[str] = ()) -> None:
        if stage not in self.STAGES:
            raise ValueError(f"unknown rollout stage {stage!r}")
        with self._lock:
            self.stage = stage
            self.canary = frozenset(canary_tenants)

    def emergency_disable(self, reason: str) -> None:
        with self._lock:
            self.stage, self.reason = "disabled", reason

    def check(self, tenant: str) -> None:
        with self._lock:
            stage, canary = self.stage, self.canary
        if stage == "disabled" or (stage == "canary" and tenant not in canary):
            raise PlaneError("PLN04-POL-006", details={"tenant": tenant, "reason": f"rollout stage {stage}"}, retry_after_s=30.0)
