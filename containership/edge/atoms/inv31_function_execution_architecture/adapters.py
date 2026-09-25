"""Adjacent-layer contracts for INV-31 (A06, C030/C083 - contract level only).

These Protocols state exactly what INV-31 expects from PLN-04, INV-26, PLN-05
and GAP-09.  The ``Reference*`` classes are in-memory *test doubles*: they let
the contract tests run, and they are NOT evidence of interoperation with the
real layers, none of which were supplied.  C030/C083 therefore stay PARTIAL.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .boundary import Gateway


@runtime_checkable
class ExecutionPlane(Protocol):  # PLN-04, upstream, CRITICAL
    def healthy(self) -> bool: ...
    def isolation_tier(self) -> str: ...


@runtime_checkable
class SnapshotService(Protocol):  # INV-26, upstream, noncritical (cold start stays safe)
    def healthy(self) -> bool: ...
    def restore_cost_hint(self, version: str) -> int: ...


@runtime_checkable
class ElasticityPlane(Protocol):  # PLN-05, downstream consumer of saturation
    def observe_saturation(self, health: dict[str, Any]) -> None: ...


@runtime_checkable
class ObservabilitySink(Protocol):  # GAP-09, downstream consumer of signals
    def healthy(self) -> bool: ...
    def export(self, records: list[dict[str, Any]]) -> int: ...


class ReferenceExecutionPlane:
    def __init__(self, up: bool = True, tier: str = "reference-microvm") -> None:
        self.up, self.tier = up, tier

    def healthy(self) -> bool:
        return self.up

    def isolation_tier(self) -> str:
        return self.tier


class ReferenceSnapshotService:
    def __init__(self, up: bool = True) -> None:
        self.up = up

    def healthy(self) -> bool:
        return self.up

    def restore_cost_hint(self, version: str) -> int:
        return 1


class ReferenceElasticityPlane:
    def __init__(self) -> None:
        self.observations: list[dict[str, Any]] = []

    def observe_saturation(self, health: dict[str, Any]) -> None:
        self.observations.append(health["saturation"])


class ReferenceObservabilitySink:
    def __init__(self, up: bool = True) -> None:
        self.up = up
        self.received: list[dict[str, Any]] = []

    def healthy(self) -> bool:
        return self.up

    def export(self, records: list[dict[str, Any]]) -> int:
        if not self.up:
            raise ConnectionError("sink unavailable")
        self.received.extend(records)
        return len(records)


def sync_dependencies(gateway: Gateway, *, execution: ExecutionPlane,
                      snapshots: SnapshotService, observability: ObservabilitySink) -> None:
    """Refresh the gateway's dependency view from adapter health probes."""
    gateway.set_dependency("PLN-04 Execution plane", execution.healthy())
    gateway.set_dependency("INV-26 MicroVM snapshotting", snapshots.healthy())
    gateway.set_dependency("GAP-09 Unified observability", observability.healthy())


def flush_telemetry(gateway: Gateway, sink: ObservabilitySink, *, batch: int = 500) -> int:
    """Export buffered records; on sink failure keep them (bounded) and report 0.

    Loss is bounded by the telemetry buffer size and counted, never silent.
    """
    buf = gateway.telemetry.export_buffer
    sent = 0
    while buf:
        chunk = [buf[i] for i in range(min(batch, len(buf)))]
        try:
            sink.export(chunk)
        except Exception:  # noqa: BLE001 - a sink outage must not affect invocations
            gateway.telemetry.incr("telemetry_export_failures")
            gateway.set_dependency("GAP-09 Unified observability", False)
            return sent
        for _ in chunk:
            buf.popleft()
        sent += len(chunk)
    return sent


def publish_saturation(gateway: Gateway, elasticity: ElasticityPlane, *, now: int) -> None:
    elasticity.observe_saturation(gateway.health(now))
