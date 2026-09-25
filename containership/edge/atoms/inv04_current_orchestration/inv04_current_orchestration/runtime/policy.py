"""Disruption and pod-lifecycle policy (components 10-17).

Pure functions over typed objects; they decide, they never mutate.  The drain
coordinator consumes the decisions.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from .objects import DisruptionBudget, NodeSpec, PodSpec

# --------------------------------------------------------------------- PDB (10)


def _resolve(value: int | str, total: int, *, round_up: bool) -> int:
    if isinstance(value, bool):
        raise ValueError("PDB value may not be boolean")
    if isinstance(value, int):
        if value < 0:
            raise ValueError("PDB value must be non-negative")
        return value
    s = str(value).strip()
    if not s.endswith("%"):
        raise ValueError(f"PDB value {value!r} is neither int nor percentage")
    pct = int(s[:-1])
    if not 0 <= pct <= 100:
        raise ValueError("PDB percentage must be 0..100")
    raw = pct * total / 100
    return math.ceil(raw) if round_up else math.floor(raw)


def selects(pdb: DisruptionBudget, pod: PodSpec) -> bool:
    if pdb.meta.namespace != pod.meta.namespace:
        return False
    # policy/v1: an empty (non-null) selector matches every pod in the namespace.
    labels = dict(pod.meta.labels)
    return all(labels.get(k) == v for k, v in pdb.selector)


@dataclass(frozen=True)
class PdbStatus:
    name: str
    expected: int
    healthy: int
    desired_healthy: int
    disruptions_allowed: int


def pdb_status(pdb: DisruptionBudget, pods: Iterable[PodSpec]) -> PdbStatus:
    """Compute policy/v1 status. ``maxUnavailable`` and percentages use the
    controller's expected scale when known (``expected_pods``)."""
    if (pdb.min_available is None) == (pdb.max_unavailable is None):
        raise ValueError(f"PDB {pdb.meta.key} must set exactly one of minAvailable / maxUnavailable")
    matched = [p for p in pods if selects(pdb, p) and p.meta.deletion_timestamp is None]
    expected = pdb.expected_pods if pdb.expected_pods is not None else len(matched)
    healthy = sum(1 for p in matched if p.phase == "Running" and p.ready)
    if pdb.min_available is not None:
        desired = _resolve(pdb.min_available, expected, round_up=True)
    else:
        desired = max(0, expected - _resolve(pdb.max_unavailable, expected, round_up=True))  # type: ignore[arg-type]
    return PdbStatus(pdb.meta.key, expected, healthy, desired, max(0, healthy - desired))


def eviction_allowed(pod: PodSpec, pdbs: Sequence[DisruptionBudget], pods: Sequence[PodSpec]) -> tuple[bool, str]:
    """Emulates the Eviction subresource decision for ``pod``."""
    matching = [b for b in pdbs if selects(b, pod)]
    if len(matching) > 1:
        return False, "multiple_pdbs"  # API server refuses with 500 in this case
    if not matching:
        return True, "no_pdb"
    pdb = matching[0]
    st = pdb_status(pdb, pods)
    unhealthy = not (pod.phase == "Running" and pod.ready)
    if unhealthy:
        if pdb.unhealthy_pod_eviction_policy == "AlwaysAllow":
            return True, "unhealthy_always_allow"
        if st.healthy >= st.desired_healthy:
            return True, "unhealthy_budget_healthy"
        return False, "budget_unhealthy"
    if st.disruptions_allowed >= 1:
        return True, "within_budget"
    return False, "disruption_budget"


# --------------------------------------------------- pod classification (11-17)


@dataclass(frozen=True)
class DrainDecision:
    pod: str
    action: str  # evict | skip | block
    reason: str


def classify_for_drain(pod: PodSpec, *, delete_emptydir_data: bool = False, force_unmanaged: bool = False,
                       ignore_daemonsets: bool = True, now: float = 0.0) -> DrainDecision:
    """kubectl-drain-equivalent filtering with explicit reasons."""
    key = pod.meta.key
    if pod.mirror or pod.meta.owner_kind == "Node":
        return DrainDecision(key, "skip", "mirror_static_pod")  # 11: kubelet owns it
    if pod.phase in ("Succeeded", "Failed"):
        return DrainDecision(key, "evict", "terminal_pod")  # 16: completed Job pods are safe
    if pod.meta.deletion_timestamp is not None:
        return DrainDecision(key, "skip", "already_terminating")  # 13
    if pod.meta.owner_kind == "DaemonSet":
        return DrainDecision(key, "skip" if ignore_daemonsets else "block", "daemonset_managed")  # 15
    if not pod.meta.owner_kind:
        return DrainDecision(key, "evict" if force_unmanaged else "block", "unmanaged_pod")  # 11
    for v in pod.volumes:  # 17
        if v.local and not delete_emptydir_data:
            return DrainDecision(key, "block", "local_storage")
    return DrainDecision(key, "evict", "managed")


def stateful_order(pods: Sequence[PodSpec]) -> list[PodSpec]:
    """StatefulSet pods evict highest ordinal first (14); others keep stable key order."""
    return sorted(pods, key=lambda p: (p.meta.owner_kind != "StatefulSet", -(p.ordinal or 0), p.meta.key))


def quorum_safe(pods_of_set: Sequence[PodSpec], victim: PodSpec, quorum: int) -> bool:
    healthy = [p for p in pods_of_set if p.ready and p.phase == "Running" and p.meta.uid != victim.meta.uid]
    return len(healthy) >= quorum


def volume_blockers(pod: PodSpec, target: NodeSpec, *, other_pods: Sequence[PodSpec] = ()) -> list[str]:
    """PV constraints for moving ``pod`` to ``target`` (17)."""
    reasons = []
    for v in pod.volumes:
        if v.local:
            reasons.append(f"{v.claim}:local_volume_bound_to_node")
        if v.zone and target.zone and v.zone != target.zone:
            reasons.append(f"{v.claim}:zone_mismatch")
        if v.access_mode == "ReadWriteOncePod":
            if any(o.meta.uid != pod.meta.uid and any(ov.claim == v.claim for ov in o.volumes) for o in other_pods):
                reasons.append(f"{v.claim}:rwop_in_use")
        elif v.access_mode == "ReadWriteOnce" and v.attached_node and v.attached_node != target.name:
            if any(o.meta.uid != pod.meta.uid and o.node == v.attached_node and any(ov.claim == v.claim for ov in o.volumes)
                   for o in other_pods):
                reasons.append(f"{v.claim}:rwo_attached_elsewhere")
    return reasons


# ----------------------------------------------------- termination lifecycle (13)


def termination_state(pod: PodSpec, now: float, *, slack: float = 30.0) -> str:
    """running | terminating | stuck_terminating | finalizer_blocked."""
    ts = pod.meta.deletion_timestamp
    if ts is None:
        return "running"
    budget = pod.grace_seconds + slack
    if now - ts <= budget:
        return "terminating"
    return "finalizer_blocked" if pod.meta.finalizers else "stuck_terminating"


# ---------------------------------------------------------------- node health (12)

NODE_STATES = ("ready", "cordoned", "not_ready", "unreachable", "deleted", "partitioned")


def node_state(node: NodeSpec | None, now: float, *, heartbeat_grace: float = 40.0,
               partition_fraction: float | None = None) -> str:
    """Classify a node. ``partition_fraction`` is the fraction of the zone that is
    unreachable; above 0.55 the zone is treated as partitioned (eviction rate
    limiting, like the node-lifecycle controller) rather than unhealthy."""
    if node is None:
        return "deleted"
    if node.ready == "Unknown" or now - node.last_heartbeat > heartbeat_grace:
        if partition_fraction is not None and partition_fraction > 0.55:
            return "partitioned"
        return "unreachable"
    if node.ready == "False":
        return "not_ready"
    if node.unschedulable:
        return "cordoned"
    return "ready"


def may_evict_from(state: str) -> bool:
    """Only reachable or confirmed-deleted nodes may have pods removed; a
    partitioned zone must pause automated eviction (split-brain safeguard)."""
    return state in ("ready", "cordoned", "not_ready", "deleted", "unreachable")


# ------------------------------------------------------------ Job semantics (16)


def job_needs_replacement(pod: PodSpec) -> bool:
    """Job pods are not replica-controller pods: a Succeeded pod is complete and
    must not be recreated; ``restartPolicy: Never`` failed pods are counted by
    the Job controller, not by INV-04."""
    if pod.meta.owner_kind != "Job":
        return True
    return pod.phase not in ("Succeeded", "Failed")
