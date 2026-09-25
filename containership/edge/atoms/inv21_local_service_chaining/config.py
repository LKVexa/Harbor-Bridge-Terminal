"""Declarative configuration schema, provenance and atomic activation.

GAP-012 (schema, environment/site overrides), GAP-013 (provenance,
transactional activation, rollback snapshot).

A configuration document (``PK_CHAIN_CONFIG/1``, JSON) is validated against
``schemas/chain_config.schema.json`` *and* the typed constructor below. It is
activated atomically: the new revision becomes visible only after validation
and every registered applier succeed; a failing applier rolls every earlier
applier back to the previous revision. Every revision records author, source,
sha256 digest and activation time.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Callable, Mapping, Optional

from .errors import ValidationFailed
from .schema import load_schema, validate

CONFIG_SCHEMA = "PK_CHAIN_CONFIG/1"
MAX_HISTORY = 32


@dataclass(frozen=True)
class ChainConfig:
    mode: str = "development"               # "production" refuses non-authoritative policy
    max_depth: int = 4
    max_telemetry_events: int = 1024
    telemetry_sample_rate: float = 1.0
    residency_lease_s: Optional[float] = None
    max_in_flight: int = 1024
    max_in_flight_per_tenant: int = 256
    tenant_rate: Optional[float] = None
    policy_timeout_s: float = 0.25
    policy_cache_ttl_s: float = 0.0
    breaker_failure_threshold: int = 5
    breaker_reset_s: float = 5.0
    retry_max_attempts: int = 1
    remote_timeout_s: float = 2.0
    handler_stall_s: float = 1.0
    require_remote_transport: bool = False
    schema: str = CONFIG_SCHEMA

    @classmethod
    def from_mapping(cls, doc: Mapping, *, environment: Optional[str] = None,
                     site: Optional[str] = None) -> "ChainConfig":
        if not isinstance(doc, Mapping):
            raise ValidationFailed("config must be an object")
        errs = validate(doc, load_schema("chain_config"))
        if errs:
            raise ValidationFailed("config schema violation: " + errs[0], field="config")
        base = {k: v for k, v in doc.items() if k not in ("overrides",)}
        ov = doc.get("overrides", {})
        for scope, key in (("environment", environment), ("site", site)):
            if key is not None and key in ov.get(scope, {}):
                base.update(ov[scope][key])
        errs = validate({**base, "schema": CONFIG_SCHEMA}, load_schema("chain_config"))
        if errs:
            raise ValidationFailed("config override violation: " + errs[0], field="config")
        cfg = cls(**base)
        if cfg.max_in_flight_per_tenant > cfg.max_in_flight:
            raise ValidationFailed("per-tenant in-flight exceeds global", field="max_in_flight_per_tenant")
        return cfg

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ConfigRevision:
    revision: int
    config: ChainConfig
    author: str
    source: str
    activated_at: float
    digest: str


class ConfigStore:
    def __init__(self, initial: Optional[ChainConfig] = None) -> None:
        cfg = initial or ChainConfig()
        self._lock = threading.RLock()
        self._appliers: list = []
        self._committed: list = []
        self._history = [ConfigRevision(1, cfg, "bootstrap", "defaults", time.time(), cfg.digest())]

    @property
    def current(self) -> ConfigRevision:
        with self._lock:
            return self._history[-1]

    @property
    def history(self) -> list:
        with self._lock:
            return list(self._history)

    def on_activate(self, fn: Callable[[ChainConfig], None]) -> None:
        self._appliers.append(fn)

    def on_committed(self, fn: Callable[[ConfigRevision], None]) -> None:
        self._committed.append(fn)

    def activate(self, cfg: ChainConfig, *, author: str, source: str) -> ConfigRevision:
        if not author or not source:
            raise ValidationFailed("config activation requires author and source", field="provenance")
        with self._lock:
            prev = self._history[-1]
            applied = []
            try:
                for fn in self._appliers:
                    fn(cfg); applied.append(fn)
            except Exception as exc:
                for fn in reversed(applied):
                    try:
                        fn(prev.config)
                    except Exception:
                        pass
                raise ValidationFailed("config activation failed; rolled back",
                                       reason=type(exc).__name__) from exc
            rev = ConfigRevision(prev.revision + 1, cfg, author[:64], source[:128], time.time(), cfg.digest())
            self._history.append(rev)
            del self._history[:-MAX_HISTORY]
            for fn in self._committed:
                fn(rev)
            return rev

    def rollback(self, *, author: str) -> ConfigRevision:
        with self._lock:
            if len(self._history) < 2:
                raise ValidationFailed("no prior configuration to roll back to")
            target = self._history[-2]
            return self.activate(copy.copy(target.config), author=author,
                                 source=f"rollback-to-{target.revision}")
