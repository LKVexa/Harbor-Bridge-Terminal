"""Deterministic, dependency-free orchestration model for INV-04.

The model is deliberately small: it represents the incumbent scheduler semantics
that INV-04 must preserve during migration.  It is independent of ``pk_core`` so
its safety properties can be tested even when the estate-level conformance
framework is not installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypeAlias

Pod: TypeAlias = tuple[str, str]  # (workload, node)


class OrchestrationError(RuntimeError):
    """Base class for runtime orchestration failures with a stable error code."""

    code = "ORCH_RUNTIME_ERROR"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class ConfigurationError(ValueError):
    """Raised when desired state or cluster configuration is invalid."""

    code = "ORCH_CONFIGURATION_INVALID"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class StateIntegrityError(OrchestrationError):
    """Raised when observed running state violates model invariants."""

    code = "ORCH_STATE_INTEGRITY"


class BudgetBreach(OrchestrationError):
    """Raised before a drain that would violate a workload disruption budget."""

    code = "ORCH_BUDGET_BREACH"


class UnknownNode(LookupError, OrchestrationError):
    """Raised when a drain names a node the cluster does not have."""

    code = "ORCH_UNKNOWN_NODE"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class NoCapacity(OrchestrationError):
    """Raised before an operation that needs scheduling but has no target node."""

    code = "ORCH_NO_CAPACITY"


def _workload_name(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{field_name} workload names must be non-empty strings, got {value!r}")
    return value


def _count(value: object, *, field_name: str, workload: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ConfigurationError(
            f"{field_name} for {workload} must be a non-negative int, got {value!r}"
        )
    return value


@dataclass
class Cluster:
    """In-memory reference model of desired replica reconciliation and drain.

    Mutating operations are *plan then commit*: all configuration and capacity
    checks complete against a copy before the instance is changed.  Therefore a
    failed reconcile or drain leaves ``nodes`` and ``pods`` unchanged.
    """

    nodes: list[str]
    pods: list[Pod] = field(default_factory=list)
    desired: dict[str, int] = field(default_factory=dict)
    min_available: dict[str, int] = field(default_factory=dict)

    def _validated(self) -> None:
        if not isinstance(self.nodes, list):
            raise ConfigurationError("nodes must be a list of node names")
        if any(not isinstance(n, str) or not n.strip() for n in self.nodes):
            raise ConfigurationError("node names must be non-empty strings")
        if len(set(self.nodes)) != len(self.nodes):
            raise ConfigurationError("node names must be unique")

        if not isinstance(self.desired, dict):
            raise ConfigurationError("desired must be a workload->replica-count mapping")
        if not isinstance(self.min_available, dict):
            raise ConfigurationError("min_available must be a workload->minimum-count mapping")

        desired: dict[str, int] = {}
        for workload, replicas in self.desired.items():
            name = _workload_name(workload, field_name="desired")
            desired[name] = _count(replicas, field_name="desired replicas", workload=name)

        for workload, minimum in self.min_available.items():
            name = _workload_name(workload, field_name="min_available")
            if name not in desired:
                raise ConfigurationError(f"min_available references unmanaged workload {name!r}")
            value = _count(minimum, field_name="min_available", workload=name)
            if value > desired[name]:
                raise ConfigurationError(
                    f"min_available for {name} ({value}) exceeds desired replicas ({desired[name]})"
                )

        node_set = set(self.nodes)
        for index, pod in enumerate(self.pods):
            if not isinstance(pod, tuple) or len(pod) != 2:
                raise StateIntegrityError(f"pod[{index}] must be a (workload, node) tuple, got {pod!r}")
            workload, node = pod
            if not isinstance(workload, str) or not workload.strip():
                raise StateIntegrityError(f"pod[{index}] has invalid workload {workload!r}")
            if not isinstance(node, str) or not node.strip():
                raise StateIntegrityError(f"pod[{index}] has invalid node {node!r}")
            if node not in node_set:
                raise StateIntegrityError(f"pod[{index}] references unknown node {node!r}")
            if workload not in desired:
                raise StateIntegrityError(
                    f"pod[{index}] references unmanaged workload {workload!r}; "
                    "drain/reconcile could not safely recreate it"
                )

    @staticmethod
    def _reconcile_plan(nodes: list[str], pods: list[Pod], desired: dict[str, int]) -> tuple[list[Pod], int]:
        """Return reconciled pods and change count without mutating the caller."""
        planned = list(pods)
        changes = 0
        for workload in sorted(desired):
            target = desired[workload]
            running = [pod for pod in planned if pod[0] == workload]
            deficit = target - len(running)
            if deficit > 0 and not nodes:
                raise NoCapacity(f"{workload}: {deficit} replica(s) to schedule but no nodes remain")

            for _ in range(max(deficit, 0)):
                load = {node: sum(1 for pod in planned if pod[1] == node) for node in nodes}
                target_node = min(nodes, key=lambda node: (load[node], node))
                planned.append((workload, target_node))
                changes += 1

            if target < len(running):
                # Preserve the original model's stable pod-order scale-down semantics.
                for pod in running[target:]:
                    planned.remove(pod)
                    changes += 1
        return planned, changes

    def reconcile(self) -> int:
        """Atomically reconcile managed workloads to desired replica counts."""
        self._validated()
        planned, changes = self._reconcile_plan(self.nodes, self.pods, self.desired)
        self.pods = planned
        return changes

    def drain(self, node: str) -> int:
        """Atomically drain *node*, enforcing disruption budgets before commit.

        The method returns the number of reconciliation changes after eviction,
        preserving the v4.1 API.  Evictions themselves are not included in the
        returned count.
        """
        self._validated()
        if not isinstance(node, str) or not node.strip():
            raise UnknownNode(f"{node!r}: not a valid node name")
        if node not in self.nodes:
            raise UnknownNode(f"{node}: not a node of this cluster")

        victims = [pod for pod in self.pods if pod[1] == node]
        for workload in sorted({pod[0] for pod in victims}):
            remaining = sum(1 for pod in self.pods if pod[0] == workload and pod[1] != node)
            minimum = self.min_available.get(workload, 0)
            if remaining < minimum:
                raise BudgetBreach(
                    f"draining {node} leaves {workload} with {remaining} < {minimum}"
                )

        planned_nodes = [candidate for candidate in self.nodes if candidate != node]
        planned_pods = [pod for pod in self.pods if pod[1] != node]
        # Capacity and desired-state reconciliation are proven on copies first.
        reconciled_pods, changes = self._reconcile_plan(planned_nodes, planned_pods, self.desired)

        self.nodes = planned_nodes
        self.pods = reconciled_pods
        return changes

    def inventory(self) -> dict[str, list[str]]:
        """Return a deterministic workload -> sorted node list hand-off snapshot."""
        self._validated()
        out: dict[str, list[str]] = {}
        for workload, node in self.pods:
            out.setdefault(workload, []).append(node)
        return {workload: sorted(nodes) for workload, nodes in sorted(out.items())}
