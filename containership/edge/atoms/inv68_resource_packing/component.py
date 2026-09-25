"""INV-68 - Resource packing control-plane integration.

The packing algorithm lives in :mod:`inv68_resource_packing.packing` so it can
be tested without the external ``pk_core`` framework.  This module adapts that
engine into the master checklist component.
"""
from __future__ import annotations

import math

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build
from .packing import (
    DIMENSIONS,
    OVERCOMMIT,
    Host,
    PackingResult,
    PlacementDecision,
    capacity_report,
    effective_capacity,
    fragmentation,
    lower_bound,
    pack,
    pack_detailed,
)


def _verify(condition: bool, message: str = "behavioural check failed") -> None:
    """Fail behavioural checks even when Python is run with ``-O``."""
    if not condition:
        raise AssertionError(message)


class ResourcePackingComponent(Component):
    """Master-applied component for INV-68."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    def _work(self):
        import random

        rng = random.Random(7)
        return [
            {
                "name": f"w{i}",
                "cpu": rng.choice([0.5, 1, 2, 4]),
                "mem": rng.choice([1, 2, 4, 8]),
            }
            for i in range(60)
        ]

    def assess_performance(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_performance(items)
        work = self._work()
        result = pack_detailed(work, host_cpu=16, host_mem=64)
        lb = lower_bound(work, 16, 64)
        naive = len(work)
        _verify(
            not result.unplaced and len(result.hosts) <= math.ceil(lb * 1.1) + 1,
            "packing efficiency exceeded the permitted demonstration envelope",
        )
        findings[0] = self.satisfied(
            items[0],
            f"Sixty mixed workloads pack onto {len(result.hosts)} hosts against a theoretical lower bound of "
            f"{lb} (one-per-host would need {naive}); fragmentation left behind is "
            f"{fragmentation(result.hosts)}, reported rather than hidden.",
            *self._evidence("packing.py::pack_detailed", "packing.py::lower_bound"),
        )
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        result = pack_detailed(
            self._work() + [{"name": "whale", "cpu": 1, "mem": 60}],
            16,
            64,
            headroom=0.1,
        )
        worst_mem = max(host.used["mem"] / host.mem for host in result.hosts)
        _verify(
            "whale" in result.unplaced and worst_mem <= 0.9 + 1e-9,
            "memory headroom invariant was violated",
        )
        findings[0] = self.satisfied(
            items[0],
            f"Memory is never overcommitted and every host keeps its 10% headroom (peak memory use "
            f"{worst_mem:.0%}); a workload that could only fit by eating the headroom is reported "
            "unplaced instead.",
            *self._evidence("packing.py::Host.fits", "packing.py::OVERCOMMIT"),
        )
        return findings


COMPONENT = ResourcePackingComponent

__all__ = [
    "COMPONENT",
    "DIMENSIONS",
    "OVERCOMMIT",
    "Host",
    "PackingResult",
    "PlacementDecision",
    "ResourcePackingComponent",
    "effective_capacity",
    "fragmentation",
    "lower_bound",
    "pack",
    "pack_detailed",
]
