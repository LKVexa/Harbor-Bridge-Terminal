"""Preflight capacity, scheduling constraints and priority (components 18-20).

``place`` answers "where can this pod go" using the same filter order as the
kube-scheduler's required predicates: node condition/unschedulable, OS/arch,
node selector + required node affinity, taints/tolerations, resource fit,
required anti-affinity, topology spread; then scores by least-allocated and
name for determinism.  ``plan_drain_capacity`` proves that every evicted pod
can be re-homed on the remaining nodes *before* a drain starts.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .objects import RESOURCE_KEYS, NodeSpec, PodSpec
from .policy import volume_blockers


@dataclass(frozen=True)
class Placement:
    pod: str
    node: str | None
    reasons: tuple[str, ...] = ()


def used(node: str, pods: Sequence[PodSpec]) -> dict[str, int]:
    out = {k: 0 for k in RESOURCE_KEYS}
    for p in pods:
        if p.node == node and p.phase not in ("Succeeded", "Failed"):
            for k in RESOURCE_KEYS:
                out[k] += p.request(k) if k != "pods" else 1
    return out


def filter_node(pod: PodSpec, node: NodeSpec, pods: Sequence[PodSpec], nodes: Sequence[NodeSpec]) -> list[str]:
    reasons: list[str] = []
    if node.unschedulable:
        reasons.append("unschedulable")
    if node.ready != "True":
        reasons.append("not_ready")
    labels = node.labels()
    for k, v in pod.node_selector:
        if labels.get(k) != v:
            reasons.append(f"node_selector:{k}")
    for k, allowed in pod.required_node_labels_in:
        if labels.get(k) not in allowed:
            reasons.append(f"node_affinity:{k}")
    for t in node.taints:
        if t.effect in ("NoSchedule", "NoExecute") and not any(tol.tolerates(t) for tol in pod.tolerations):
            reasons.append(f"taint:{t.key}")
    u = used(node.name, pods)
    for k in RESOURCE_KEYS:
        need = pod.request(k) if k != "pods" else 1
        if need and u[k] + need > node.alloc(k):
            reasons.append(f"insufficient:{k}")
    if pod.anti_affinity_key:
        domain = labels.get(pod.anti_affinity_key)
        by_name = {n.name: n for n in nodes}
        for other in pods:
            if other.workload == pod.workload and other.meta.uid != pod.meta.uid and other.node in by_name:
                if by_name[other.node].labels().get(pod.anti_affinity_key) == domain:
                    reasons.append("pod_anti_affinity")
                    break
    if pod.spread_key and pod.max_skew > 0:
        counts: dict[str, int] = {}
        for n in nodes:
            d = n.labels().get(pod.spread_key)
            if d is not None and n.ready == "True" and not n.unschedulable:
                counts.setdefault(d, 0)
        by_name = {n.name: n for n in nodes}
        for other in pods:
            if other.workload == pod.workload and other.meta.uid != pod.meta.uid and other.node in by_name:
                d = by_name[other.node].labels().get(pod.spread_key)
                if d in counts:
                    counts[d] += 1
        d = labels.get(pod.spread_key)
        if d is None:
            reasons.append("spread:missing_topology_label")
        elif counts:
            if counts.get(d, 0) + 1 - min(counts.values()) > pod.max_skew:
                reasons.append("spread:max_skew")
    reasons.extend(volume_blockers(pod, node, other_pods=pods))
    return reasons


def place(pod: PodSpec, nodes: Sequence[NodeSpec], pods: Sequence[PodSpec], *, exclude: frozenset[str] | set[str] = frozenset()) -> Placement:
    candidates = []
    why: list[str] = []
    for n in sorted(nodes, key=lambda n: n.name):
        if n.name in exclude:
            continue
        r = filter_node(pod, n, pods, nodes)
        if r:
            why.extend(f"{n.name}:{x}" for x in r)
            continue
        u = used(n.name, pods)
        cpu = n.alloc("cpu_m") or 1
        mem = n.alloc("memory_mi") or 1
        score = (u["cpu_m"] / cpu + u["memory_mi"] / mem, u["pods"], n.name)
        candidates.append((score, n.name))
    if not candidates:
        return Placement(pod.meta.key, None, tuple(why) or ("no_nodes",))
    return Placement(pod.meta.key, min(candidates)[1])


def plan_drain_capacity(victims: Sequence[PodSpec], nodes: Sequence[NodeSpec], pods: Sequence[PodSpec],
                        drained: str) -> tuple[dict[str, str], list[Placement]]:
    """Simulate re-homing ``victims`` (highest priority first). Returns
    (assignment uid->node, unplaceable)."""
    remaining = [p for p in pods if p.node != drained]
    assignment: dict[str, str] = {}
    failures: list[Placement] = []
    for v in sorted(victims, key=lambda p: (-p.priority, p.meta.key)):
        pl = place(v, nodes, remaining, exclude={drained})
        if pl.node is None:
            failures.append(pl)
            continue
        assignment[v.meta.uid] = pl.node
        remaining.append(v.replace(node=pl.node))
    return assignment, failures


# -------------------------------------------------------------- priority (20)


def preemption_candidates(pod: PodSpec, node: NodeSpec, pods: Sequence[PodSpec], nodes: Sequence[NodeSpec],
                          *, protected_uids: frozenset[str] | set[str] = frozenset()) -> list[PodSpec] | None:
    """Minimal set of strictly lower-priority victims on ``node`` whose removal
    lets ``pod`` fit.  Pods protected by a disruption budget are excluded, so
    preemption never becomes a budget bypass.  Returns None when impossible."""
    if pod.preemption_policy == "Never":
        return None
    on_node = sorted((p for p in pods if p.node == node.name and p.priority < pod.priority
                      and p.meta.uid not in protected_uids), key=lambda p: (p.priority, p.meta.key))
    current = list(pods)
    chosen: list[PodSpec] = []
    if not filter_node(pod, node, current, nodes):
        return []
    for victim in on_node:
        current = [p for p in current if p.meta.uid != victim.meta.uid]
        chosen.append(victim)
        if not filter_node(pod, node, current, nodes):
            return chosen
    return None
