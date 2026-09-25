"""MC-44 / EXT-02..EXT-08 adjacent-layer ports.

Each adjacent element gets a typed port.  In-repo fakes implement them for the integration
matrix; **no real adjacent element is bundled**, so these tests prove the SCH-01 side of each
seam only.  End-to-end certification (EXT-*) remains blocked on the real components.
"""
from __future__ import annotations

from typing import Any, Mapping, Protocol

from .errors import SchedulerError
from .model import NodeSpec, PlacementRequest


class ApplicationPlane(Protocol):          # PLN-02
    def resolve(self, app: str, revision: str) -> list[PlacementRequest]: ...


class ElasticityPlane(Protocol):           # PLN-05
    def desired_instances(self, app: str) -> int: ...


class HardwareDiscovery(Protocol):         # GAP-02
    def reports(self) -> list[tuple[Mapping[str, Any], NodeSpec]]: ...   # (node token, spec)


class ExecutionPlane(Protocol):            # PLN-04
    def admit(self, placement: Mapping[str, Any]) -> bool: ...


class TopologyService(Protocol):           # GAP-03
    def zone_of(self, node: str) -> str: ...


class ThermalService(Protocol):            # GAP-10
    def excluded(self) -> set[str]: ...


class VirtualizationController(Protocol):  # INV-33
    def reclaim(self, lease_id: str) -> None: ...


PORTS = {"EXT-02": "ApplicationPlane", "EXT-03": "ElasticityPlane", "EXT-04": "HardwareDiscovery",
         "EXT-05": "ExecutionPlane", "EXT-06": "TopologyService", "EXT-07": "ThermalService",
         "EXT-08": "VirtualizationController"}


def reconcile(sched, *, app: str, revision: str, app_plane: ApplicationPlane, elastic: ElasticityPlane,
              discovery: HardwareDiscovery, execution: ExecutionPlane, thermal: ThermalService | None,
              virt: VirtualizationController, token_factory, ctx_factory) -> dict[str, Any]:
    """One reconcile pass across every seam.  Placement refused by the execution plane is
    revoked and reclaimed, never left dangling."""
    excluded = thermal.excluded() if thermal else set()
    for tok, spec in discovery.reports():
        spec.report.thermally_excluded = spec.report.thermally_excluded or spec.name in excluded
        sched.report_node(tok, spec)
    templates = app_plane.resolve(app, revision)
    want = elastic.desired_instances(app)
    if want < 0: raise SchedulerError("INVALID_REQUEST", "negative instance count from elasticity plane")
    placed, refused = [], []
    for i in range(want):
        for tmpl in templates:
            w = tmpl.workload
            from dataclasses import replace
            req = replace(tmpl, workload=replace(w, name=f"{w.name}-{i}"))
            try:
                p = sched.place(token_factory(), req, ctx_factory())
            except SchedulerError as e:
                refused.append((req.workload.name, e.code)); continue
            if execution.admit(p):
                sched.transition(token_factory(), p["lease_id"], "ADMITTED"); placed.append(p)
            else:
                sched.transition(token_factory(), p["lease_id"], "REVOKED"); virt.reclaim(p["lease_id"])
                refused.append((req.workload.name, "EXECUTION_REFUSED"))
    return {"placed": placed, "refused": refused}
