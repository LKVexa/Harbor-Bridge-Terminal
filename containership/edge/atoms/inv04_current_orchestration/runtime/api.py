"""Cluster API port (component 1 contract, 9 eviction) and an in-memory
reference API server.

``ClusterAPI`` is the narrow typed port the controller depends on.  A
production adapter implements it over the official Kubernetes client (see
``docs/ADR-0001``); ``InMemoryClusterAPI`` implements identical semantics
over ``VersionedStore`` — UID + resourceVersion preconditions, the Eviction
subresource's PDB check (HTTP 429 equivalent), graceful deletion — and is
what the automated suite, the chaos suite and the parity harness run against.
"""
from __future__ import annotations

import dataclasses
import threading
from typing import Protocol, Sequence

from .errors import Conflict, EvictionBlocked, NotFound
from .objects import DisruptionBudget, NodeSpec, PodSpec
from .policy import eviction_allowed
from .scheduling import place

SUPPORTED_SERVER_MINORS = tuple(range(28, 34))  # Kubernetes 1.28 .. 1.33 (policy/v1, unhealthyPodEvictionPolicy GA in 1.31)


class ClusterAPI(Protocol):
    def list_nodes(self) -> tuple[list[NodeSpec], int]: ...
    def list_pods(self) -> tuple[list[PodSpec], int]: ...
    def list_pdbs(self) -> list[DisruptionBudget]: ...
    def get_node(self, name: str) -> NodeSpec: ...
    def set_unschedulable(self, name: str, value: bool, *, expected_rv: int, uid: str) -> NodeSpec: ...
    def evict(self, pod_key: str, *, uid: str, fencing_token: int = 0) -> str: ...
    def discovery(self) -> dict[str, str]: ...


REQUIRED_RESOURCES = {
    "v1/pods": "core", "v1/nodes": "core", "v1/pods/eviction": "core",
    "policy/v1/poddisruptionbudgets": "policy", "apps/v1/replicasets": "apps",
}


def check_discovery(api: ClusterAPI) -> None:
    """Fail closed if any required group/version/resource is not served (IMPL-01.19)."""
    served = api.discovery()
    missing = sorted(r for r in REQUIRED_RESOURCES if r not in served)
    if missing:
        from .errors import DependencyUnavailable
        raise DependencyUnavailable(f"API server does not serve required resources: {missing}",
                                    details={"missing": missing})


class InMemoryClusterAPI:
    """Reference API server. Pods are keyed by namespace/name and preconditioned on UID."""

    def __init__(self, nodes: Sequence[NodeSpec], pods: Sequence[PodSpec] = (), pdbs: Sequence[DisruptionBudget] = (),
                 *, desired: dict[str, int] | None = None, fencing=None):
        self._lock = threading.RLock()
        self.rv = 0
        self.nodes: dict[str, NodeSpec] = {}
        self.pods: dict[str, PodSpec] = {}
        self.pdbs = list(pdbs)
        self.desired = dict(desired or {})
        self.fencing = fencing
        self.evictions: list[str] = []
        self.fault_hook = None  # callable(op, target) -> None | raises; chaos injection point
        self._seq = 0
        self.templates: dict[str, PodSpec] = {}  # controller pod templates (independent of live pods)
        for n in nodes:
            self._put_node(n)
        for p in pods:
            self._put_pod(p)

    def _bump(self) -> int:
        self.rv += 1
        return self.rv

    def _put_node(self, n: NodeSpec) -> NodeSpec:
        n = n.replace(meta=dataclasses.replace(n.meta, resource_version=self._bump()))
        self.nodes[n.name] = n
        return n

    def _put_pod(self, p: PodSpec) -> PodSpec:
        p = p.replace(meta=dataclasses.replace(p.meta, resource_version=self._bump()))
        if p.workload and p.meta.owner_kind in ("ReplicaSet", "StatefulSet"):
            self.templates.setdefault(p.workload, p)
        self.pods[p.meta.key] = p
        return p

    def _fault(self, op: str, target: str) -> None:
        if self.fault_hook:
            self.fault_hook(op, target)

    # ---------------------------------------------------------------- reads
    def discovery(self) -> dict[str, str]:
        return {r: "served" for r in REQUIRED_RESOURCES}

    def list_nodes(self):
        with self._lock:
            self._fault("list", "nodes")
            return [self.nodes[k] for k in sorted(self.nodes)], self.rv

    def list_pods(self):
        with self._lock:
            self._fault("list", "pods")
            return [self.pods[k] for k in sorted(self.pods)], self.rv

    def list_pdbs(self):
        return list(self.pdbs)

    def get_node(self, name: str) -> NodeSpec:
        with self._lock:
            self._fault("get", name)
            if name not in self.nodes:
                raise NotFound(f"node {name} not found", details={"node": name})
            return self.nodes[name]

    # --------------------------------------------------------------- writes
    def set_unschedulable(self, name: str, value: bool, *, expected_rv: int, uid: str) -> NodeSpec:
        with self._lock:
            self._fault("cordon", name)
            cur = self.get_node(name)
            if cur.meta.uid != uid:
                raise Conflict(f"node {name} was recreated (uid mismatch)", details={"node": name})
            if cur.meta.resource_version != expected_rv:
                raise Conflict(f"node {name} changed since read", details={"node": name})
            if cur.unschedulable == value:
                return cur
            return self._put_node(cur.replace(unschedulable=value))

    def evict(self, pod_key: str, *, uid: str, fencing_token: int = 0) -> str:
        """policy/v1 Eviction. Returns 'evicted' or 'already_gone'. Raises EvictionBlocked on 429."""
        with self._lock:
            if self.fencing is not None:
                self.fencing.check(fencing_token)
            self._fault("evict", pod_key)
            pod = self.pods.get(pod_key)
            if pod is None or pod.meta.uid != uid:
                return "already_gone"  # idempotent: a replacement with a new UID is never evicted
            ok, why = eviction_allowed(pod, self.pdbs, list(self.pods.values()))
            if not ok:
                raise EvictionBlocked(f"cannot evict {pod_key}: {why}", reason=why, details={"pod": pod_key, "reason": why})
            del self.pods[pod_key]
            self._bump()
            self.evictions.append(pod_key)
            return "evicted"

    # ---------------------------------------------------- controller simulator
    def run_controllers(self) -> int:
        """ReplicaSet-controller emulation: recreate missing replicas via the scheduler."""
        created = 0
        with self._lock:
            for workload in sorted(self.desired):
                have = [p for p in self.pods.values() if p.workload == workload and p.meta.deletion_timestamp is None
                        and p.phase not in ("Succeeded", "Failed")]
                template = self.templates.get(workload)
                for _ in range(self.desired[workload] - len(have)):
                    if template is None:
                        break
                    self._seq += 1
                    name = f"{workload}-r{self._seq}"
                    fresh = template.replace(node="", meta=dataclasses.replace(
                        template.meta, name=name, uid=f"uid-{template.meta.namespace}-{name}"))
                    pl = place(fresh, list(self.nodes.values()), list(self.pods.values()))
                    if pl.node is None:
                        break
                    self._put_pod(fresh.replace(node=pl.node))
                    created += 1
        return created
