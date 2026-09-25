"""G13-MC-018 environment/site configuration, G13-MC-019 configuration
provenance and G13-MC-030 capacity/hard-limit controls."""
from __future__ import annotations

import time
from dataclasses import dataclass, asdict, fields, replace
from typing import Any, Mapping

from .canonical import digest
from .errors import ConfigRejected

STALE_MODES = ("FAIL_CLOSED", "DENY_ONLY", "FREEZE_LAST_KNOWN_GOOD")


@dataclass(frozen=True)
class Limits:
    """Hard ceilings (G13-MC-030).  Every value is enforced, not advisory."""
    max_bundle_bytes: int = 1_048_576
    max_rules: int = 10_000
    max_match_attributes: int = 32
    max_string_length: int = 1_024
    max_nesting_depth: int = 8
    max_request_attributes: int = 64
    max_request_bytes: int = 65_536
    max_explanation_matches: int = 256
    max_concurrency: int = 64
    max_queue_depth: int = 256
    audit_buffer_records: int = 10_000


@dataclass(frozen=True)
class EngineConfig:
    """Declarative per-environment/site configuration with conservative defaults."""
    environment: str = "prod"
    site: str = "default"
    staleness_warning_seconds: int = 240
    staleness_hard_seconds: int = 300
    stale_mode: str = "FAIL_CLOSED"
    clock_skew_tolerance_seconds: int = 5
    default_deadline_ms: int = 250
    unknown_attribute_policy: str = "reject"      # reject | ignore
    limits: Limits = Limits()

    def __post_init__(self) -> None:
        for name in ("environment", "site"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v.strip() or len(v) > 128:
                raise ConfigRejected(f"{name} must be a non-empty string <=128 chars")
        if self.stale_mode not in STALE_MODES:
            raise ConfigRejected(f"stale_mode must be one of {STALE_MODES}")
        if self.unknown_attribute_policy not in ("reject", "ignore"):
            raise ConfigRejected("unknown_attribute_policy must be reject|ignore")
        for name in ("staleness_warning_seconds", "staleness_hard_seconds", "clock_skew_tolerance_seconds",
                     "default_deadline_ms"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise ConfigRejected(f"{name} must be a non-negative integer")
        if not 0 < self.staleness_warning_seconds < self.staleness_hard_seconds:
            raise ConfigRejected("require 0 < staleness_warning_seconds < staleness_hard_seconds")
        if self.staleness_hard_seconds > 7 * 86400:
            raise ConfigRejected("staleness_hard_seconds above 7 days is not a safe default")
        for f in fields(Limits):
            v = getattr(self.limits, f.name)
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                raise ConfigRejected(f"limits.{f.name} must be a positive integer")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "EngineConfig":
        if not isinstance(data, Mapping):
            raise ConfigRejected("configuration must be a mapping")
        allowed = {f.name for f in fields(cls)}
        unknown = set(data) - allowed
        if unknown:
            raise ConfigRejected(f"unknown configuration keys: {sorted(unknown)}")
        kwargs = dict(data)
        if "limits" in kwargs:
            lim = kwargs["limits"]
            if not isinstance(lim, Mapping):
                raise ConfigRejected("limits must be a mapping")
            lallowed = {f.name for f in fields(Limits)}
            if set(lim) - lallowed:
                raise ConfigRejected(f"unknown limits keys: {sorted(set(lim) - lallowed)}")
            kwargs["limits"] = Limits(**lim)
        try:
            return cls(**kwargs)
        except TypeError as exc:
            raise ConfigRejected(str(exc)) from exc


@dataclass(frozen=True)
class ConfigProvenance:
    """G13-MC-019: who/what/when for the active configuration, chained to the previous one."""
    config_digest: str
    author: str
    source: str
    version: str
    activated_at: float
    previous_digest: str | None
    record_digest: str

    @classmethod
    def create(cls, config: EngineConfig, *, author: str, source: str, version: str,
               previous: "ConfigProvenance | None" = None, now: float | None = None) -> "ConfigProvenance":
        for n, v in (("author", author), ("source", source), ("version", version)):
            if not isinstance(v, str) or not v.strip():
                raise ConfigRejected(f"provenance {n} must be non-empty")
        cd = digest(config.to_dict())
        ts = float(time.time() if now is None else now)
        prev = previous.record_digest if previous else None
        body = {"config_digest": cd, "author": author, "source": source, "version": version,
                "activated_at": int(ts * 1000), "previous_digest": prev}
        return cls(cd, author, source, version, ts, prev, digest(body))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def with_overrides(config: EngineConfig, **changes: Any) -> EngineConfig:
    return replace(config, **changes)
