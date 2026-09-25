"""GAP02-MC-13 — Versioned declarative probe configuration with secure defaults.

Unknown keys are rejected (typo = error, not silent default). Environment
overrides are limited to an explicit allow-list of non-security keys.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields
import json
import os
from typing import Any, Mapping

from .errors import Code, Gap02Error

CONFIG_SCHEMA = "GAP02_PROBE_CONFIG/1"
ENV_PREFIX = "GAP02_"
ENV_OVERRIDABLE = frozenset({"interval_seconds", "probe_timeout_seconds", "max_concurrency", "log_level"})
ALL_PROBES = ("cpu", "numa", "storage", "nic", "virt", "confidential", "tpm", "accelerators")


@dataclass(frozen=True)
class ProbeConfig:
    schema: str = CONFIG_SCHEMA
    node: str = "node"
    enabled_probes: tuple[str, ...] = ALL_PROBES
    denied_probes: tuple[str, ...] = ()
    interval_seconds: int = 60
    probe_timeout_seconds: float = 3.0
    sweep_deadline_seconds: float = 20.0
    max_concurrency: int = 4
    privileged_probes: tuple[str, ...] = ()      # must be routed through broker
    expected_devices: Mapping[str, int] = field(default_factory=dict)  # capability -> min count
    cuda_runtime_version: str | None = None
    npu_runtime_checks: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    log_level: str = "INFO"
    allow_reference_signer: bool = False          # secure default: production signer required

    def __post_init__(self) -> None:
        if self.schema != CONFIG_SCHEMA:
            raise Gap02Error(Code.SCHEMA_INCOMPATIBLE, self.schema)
        bad = set(self.enabled_probes) - set(ALL_PROBES)
        if bad:
            raise Gap02Error(Code.CONFIG_INVALID, f"unknown probes {sorted(bad)}")
        if not 1 <= self.interval_seconds <= 86_400:
            raise Gap02Error(Code.CONFIG_INVALID, "interval_seconds out of range 1..86400")
        if not 0.05 <= self.probe_timeout_seconds <= 60:
            raise Gap02Error(Code.CONFIG_INVALID, "probe_timeout_seconds out of range")
        if not self.probe_timeout_seconds <= self.sweep_deadline_seconds <= 600:
            raise Gap02Error(Code.CONFIG_INVALID, "sweep_deadline_seconds out of range")
        if not 1 <= self.max_concurrency <= 32:
            raise Gap02Error(Code.CONFIG_INVALID, "max_concurrency out of range 1..32")
        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise Gap02Error(Code.CONFIG_INVALID, "log_level")
        for v, argv in self.npu_runtime_checks.items():
            if not argv or not os.path.isabs(argv[0]):
                raise Gap02Error(Code.CONFIG_INVALID, f"npu check {v}: absolute path required")

    @property
    def active_probes(self) -> tuple[str, ...]:
        return tuple(p for p in self.enabled_probes if p not in self.denied_probes)

    @classmethod
    def from_dict(cls, d: Mapping[str, Any], env: Mapping[str, str] | None = None) -> "ProbeConfig":
        names = {f.name for f in fields(cls)}
        unknown = set(d) - names
        if unknown:
            raise Gap02Error(Code.CONFIG_INVALID, f"unknown keys {sorted(unknown)}")
        data = dict(d)
        for k, v in (env if env is not None else os.environ).items():
            if not k.startswith(ENV_PREFIX):
                continue
            key = k[len(ENV_PREFIX):].lower()
            if key not in names:
                continue
            if key not in ENV_OVERRIDABLE:
                raise Gap02Error(Code.CONFIG_INVALID, f"{k} may not be overridden from environment")
            data[key] = v if key == "log_level" else (float(v) if "." in v else int(v))
        for k in ("enabled_probes", "denied_probes", "privileged_probes"):
            if k in data:
                data[k] = tuple(data[k])
        if "npu_runtime_checks" in data:
            data["npu_runtime_checks"] = {k: tuple(v) for k, v in data["npu_runtime_checks"].items()}
        return cls(**data)

    @classmethod
    def load(cls, path: str, env: Mapping[str, str] | None = None) -> "ProbeConfig":
        with open(path, "r", encoding="utf-8") as h:
            raw = h.read(262_144)
        try:
            return cls.from_dict(json.loads(raw), env)
        except json.JSONDecodeError as e:
            raise Gap02Error(Code.CONFIG_INVALID, f"json: {e}") from e

    def probe_cfg(self) -> dict[str, Any]:
        return {"timeout": self.probe_timeout_seconds, "cuda_runtime_version": self.cuda_runtime_version,
                "npu_runtime_checks": dict(self.npu_runtime_checks)}
