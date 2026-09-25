"""Typed runtime configuration, provenance and transactional rollback
(components 40, 41, 42).

Configuration is a JSON document validated against ``RuntimeConfig`` fields
with bounds; overlays (environment, then site) merge key-by-key over the
defaults.  Unknown keys are rejected (typos must not become silent defaults).
``ConfigManager`` stages a candidate, activates it, runs a health check, and
reverts automatically on failure; every activation is recorded with digest,
issuer, time and previous pointer in the journal.
"""
from __future__ import annotations

import dataclasses
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .errors import ConfigRejected
from .journal import Journal, digest


@dataclass(frozen=True)
class RuntimeConfig:
    workers: int = 2
    queue_max_depth: int = 10_000
    api_qps: float = 20.0
    api_burst: int = 40
    request_timeout_s: float = 10.0
    drain_timeout_s: float = 600.0
    eviction_attempts: int = 6
    verify_timeout_s: float = 120.0
    lease_seconds: float = 15.0
    renew_deadline_s: float = 10.0
    max_cache_lag: int = 1000
    heartbeat_grace_s: float = 40.0
    max_concurrent_drains_per_site: int = 1
    per_tenant_inflight: int = 4
    retry_budget_ratio: float = 0.2
    circuit_threshold: int = 5
    circuit_reset_s: float = 30.0
    convergence_slo_s: float = 30.0
    convergence_objective: float = 0.99
    feature_gates: tuple[tuple[str, bool], ...] = (("drain", True), ("reconcile", True), ("handoff", True))
    namespace_tenants: tuple[tuple[str, str], ...] = ()
    site: str = "default"
    environment: str = "dev"

    def gate(self, name: str) -> bool:
        return dict(self.feature_gates).get(name, False)


BOUNDS: dict[str, tuple[float, float]] = {
    "workers": (1, 64), "queue_max_depth": (1, 1_000_000), "api_qps": (0.1, 10_000), "api_burst": (1, 100_000),
    "request_timeout_s": (0.1, 300), "drain_timeout_s": (1, 86_400), "eviction_attempts": (1, 100),
    "verify_timeout_s": (1, 86_400), "lease_seconds": (2, 600), "renew_deadline_s": (1, 599),
    "max_cache_lag": (0, 10_000_000), "heartbeat_grace_s": (1, 3600), "max_concurrent_drains_per_site": (1, 100),
    "per_tenant_inflight": (1, 10_000), "retry_budget_ratio": (0, 1), "circuit_threshold": (1, 1000),
    "circuit_reset_s": (0.1, 3600), "convergence_slo_s": (1, 3600), "convergence_objective": (0.5, 1),
}


def load_config(base: Mapping[str, Any] | None = None, *overlays: Mapping[str, Any] | None) -> RuntimeConfig:
    merged: dict[str, Any] = {}
    for layer in (base, *overlays):
        if layer is None:
            continue
        if not isinstance(layer, Mapping):
            raise ConfigRejected("configuration layer must be an object")
        for k, v in layer.items():
            if k == "feature_gates" and isinstance(v, Mapping):
                merged["feature_gates"] = {**dict(merged.get("feature_gates", {})), **v}
            else:
                merged[k] = v
    names = {f.name: f for f in dataclasses.fields(RuntimeConfig)}
    unknown = sorted(set(merged) - set(names))
    if unknown:
        raise ConfigRejected(f"unknown configuration keys {unknown}", details={"keys": unknown})
    out: dict[str, Any] = {}
    defaults = RuntimeConfig()
    for k, v in merged.items():
        d = getattr(defaults, k)
        if k == "feature_gates":
            if not isinstance(v, Mapping) or not all(isinstance(x, bool) for x in v.values()):
                raise ConfigRejected("feature_gates must map names to booleans")
            out[k] = tuple(sorted({**dict(d), **v}.items()))
        elif k == "namespace_tenants":
            if not isinstance(v, Mapping) or not all(isinstance(a, str) and isinstance(b, str) for a, b in v.items()):
                raise ConfigRejected("namespace_tenants must map namespace to tenant")
            out[k] = tuple(sorted(v.items()))
        elif isinstance(d, bool) or isinstance(v, bool):
            raise ConfigRejected(f"{k}: booleans are not valid here")
        elif isinstance(d, int) and not isinstance(d, bool):
            if not isinstance(v, int):
                raise ConfigRejected(f"{k} must be an integer")
            out[k] = v
        elif isinstance(d, float):
            if not isinstance(v, (int, float)):
                raise ConfigRejected(f"{k} must be a number")
            out[k] = float(v)
        elif isinstance(d, str):
            if not isinstance(v, str) or not v or len(v) > 63:
                raise ConfigRejected(f"{k} must be a short non-empty string")
            out[k] = v
        if k in BOUNDS:
            lo, hi = BOUNDS[k]
            if not lo <= out[k] <= hi:
                raise ConfigRejected(f"{k}={out[k]} outside [{lo}, {hi}]", details={"key": k})
    cfg = dataclasses.replace(defaults, **out)
    if cfg.renew_deadline_s >= cfg.lease_seconds:
        raise ConfigRejected("renew_deadline_s must be < lease_seconds")
    if cfg.api_burst < cfg.api_qps:
        raise ConfigRejected("api_burst must be >= api_qps")
    return cfg


def config_dict(cfg: RuntimeConfig) -> dict:
    d = dataclasses.asdict(cfg)
    d["feature_gates"] = dict(cfg.feature_gates)
    d["namespace_tenants"] = dict(cfg.namespace_tenants)
    return d


@dataclass
class Activation:
    revision: int
    digest: str
    issuer: str
    activated_at: float
    previous: str


class ConfigManager:
    def __init__(self, journal: Journal, initial: RuntimeConfig | None = None, *, clock: Callable[[], float] = time.time):
        self.journal, self.clock = journal, clock
        self.active = initial or RuntimeConfig()
        self.previous: RuntimeConfig | None = None
        self.revision = 0
        self.history: list[Activation] = []
        self.listeners: list[Callable[[RuntimeConfig], None]] = []
        # restore last activated config from journal
        for e in journal:
            if e.kind == "config" and e.phase in ("activated", "reverted"):
                self.active = load_config(e.data["config"])
                self.revision = e.data["revision"]

    def apply(self, candidate: Mapping[str, Any], *, issuer: str, health: Callable[[RuntimeConfig], bool] = lambda c: True,
              overlays: tuple = ()) -> Activation:
        if not issuer:
            raise ConfigRejected("configuration changes require an issuer")
        staged = load_config(candidate, *overlays)  # validate
        dg = digest(config_dict(staged))
        prev_cfg, prev_dg = self.active, digest(config_dict(self.active))
        self.journal.append(f"config:{self.revision + 1}", "config", "staged", {"digest": dg, "issuer": issuer})
        self.previous, self.active = prev_cfg, staged
        self.revision += 1
        act = Activation(self.revision, dg, issuer, self.clock(), prev_dg)
        try:
            ok = bool(health(staged))
            for fn in self.listeners:
                fn(staged)
        except Exception:  # noqa: BLE001
            ok = False
        if not ok:
            self.active = prev_cfg
            self.journal.append(f"config:{self.revision}", "config", "reverted",
                                {"digest": prev_dg, "issuer": issuer, "revision": self.revision,
                                 "config": config_dict(prev_cfg), "failed_digest": dg})
            raise ConfigRejected("configuration failed health check and was reverted", details={"digest": dg})
        self.journal.append(f"config:{self.revision}", "config", "activated",
                            {"digest": dg, "issuer": issuer, "revision": self.revision, "previous": prev_dg,
                             "config": config_dict(staged)})
        self.history.append(act)
        return act

    def rollback(self, *, issuer: str) -> Activation:
        if self.previous is None:
            raise ConfigRejected("no previous configuration to roll back to")
        return self.apply(config_dict(self.previous), issuer=issuer)
