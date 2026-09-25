"""Rich placement model for the 4.3.0 service path (MC-07, MC-11..MC-15, MC-26).

The 4.2.0 :mod:`engine` types remain the v1 contract.  These types add the fields the
missing-component audit found absent: deployment context, topology, residency, runtimes,
accelerators, latency, and per-occupant isolation metadata.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .engine import TIER_ORDER, Workload, NodeReport

# MC-07 deployment contexts and their semantics.
DEPLOYMENT_CONTEXTS = {
    "cloud": {"max_report_age": 30, "disconnected_ok": False},
    "datacenter": {"max_report_age": 30, "disconnected_ok": False},
    "near-edge": {"max_report_age": 60, "disconnected_ok": False},
    "far-edge": {"max_report_age": 120, "disconnected_ok": True},
    "disconnected": {"max_report_age": 600, "disconnected_ok": True},
}
LATENCY_BUDGET_MS = {"interactive": 20, "batch": None}


def _txt(v: object, name: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return v


@dataclass(frozen=True)
class Accelerator:
    device_id: str
    kind: str            # e.g. gpu.a100
    partition: str = "whole"   # whole | mig-1g | ...
    numa: int = 0
    healthy: bool = True

    def __post_init__(self):
        _txt(self.device_id, "device_id"); _txt(self.kind, "accelerator kind"); _txt(self.partition, "partition")
        if not isinstance(self.healthy, bool) or not isinstance(self.numa, int) or isinstance(self.numa, bool):
            raise ValueError("accelerator health must be bool and numa int")


@dataclass(frozen=True)
class Occupant:
    """MC-26: what is needed to *prove* a shared placement is safe."""
    workload: str
    tenant: str
    trust_class: str
    tier: str
    tier_instance: str
    runtime: str
    devices: tuple[str, ...] = ()
    namespace: str = "default"
    attested: bool = False

    def __post_init__(self):
        for n in ("workload", "tenant", "trust_class", "tier", "tier_instance", "runtime", "namespace"):
            _txt(getattr(self, n), n)
        if self.tier not in TIER_ORDER:
            raise ValueError("occupant tier unsupported")


@dataclass
class NodeSpec:
    """A NodeReport plus the metadata needed by MC-07/11..15/26."""
    report: NodeReport
    environment: str = "prod"
    context: str = "datacenter"
    zone: str = "z0"
    rack: str = "r0"
    jurisdiction: str = "unspecified"
    runtimes: Mapping[str, str] = field(default_factory=dict)   # tier -> runtime impl
    accelerators: tuple[Accelerator, ...] = ()
    latency_ms: Mapping[str, int] = field(default_factory=dict)  # site -> rtt
    data_paths: frozenset[str] = frozenset()                     # dataset ids locally reachable
    rich_occupants: dict[str, Occupant] = field(default_factory=dict)
    attestation: Mapping[str, Any] | None = None
    connected: bool = True

    def __post_init__(self):
        if not isinstance(self.report, NodeReport):
            raise TypeError("report must be a NodeReport")
        if self.context not in DEPLOYMENT_CONTEXTS:
            raise ValueError(f"unknown deployment context {self.context!r}")
        for t, r in dict(self.runtimes).items():
            if t not in TIER_ORDER:
                raise ValueError(f"runtime declared for unsupported tier {t!r}")
            _txt(r, "runtime")
        ids = [a.device_id for a in self.accelerators]
        if len(ids) != len(set(ids)):
            raise ValueError("accelerator ids must be unique per node")
        self.data_paths = frozenset(self.data_paths)

    @property
    def name(self) -> str:
        return self.report.name


@dataclass(frozen=True)
class PlacementRequest:
    workload: Workload
    environment: str = "prod"
    accelerators: Mapping[str, int] = field(default_factory=dict)   # kind -> count
    accelerator_exclusive: bool = True
    residency: frozenset[str] = frozenset()     # allowed jurisdictions; empty = unconstrained
    dataset: str | None = None                  # data-path affinity (hard when set)
    anti_affinity_zone: str | None = None
    preferred_zone: str | None = None
    origin_site: str | None = None              # for latency-aware placement
    runtime: str | None = None                  # required runtime implementation
    slots: int = 1

    def __post_init__(self):
        if not isinstance(self.workload, Workload):
            raise TypeError("workload must be a Workload")
        _txt(self.environment, "environment")
        for k, n in dict(self.accelerators).items():
            _txt(k, "accelerator kind")
            if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
                raise ValueError("accelerator count must be a positive int")
        object.__setattr__(self, "residency", frozenset(self.residency))
        if not isinstance(self.slots, int) or isinstance(self.slots, bool) or self.slots <= 0:
            raise ValueError("slots must be a positive int")
