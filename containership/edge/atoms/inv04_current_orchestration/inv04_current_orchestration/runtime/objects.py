"""Typed object model for the runtime layer (component 1 accessor shapes, 13-19).

These are dependency-free, immutable projections of the Kubernetes fields the
orchestrator reasons about.  A production API adapter converts wire objects to
these types at the boundary (``from_k8s``) so the safety logic never touches
untyped dictionaries.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from typing import Mapping

RESOURCE_KEYS = ("cpu_m", "memory_mi", "ephemeral_mi", "pods")


def _freeze(mapping: Mapping | None) -> tuple:
    return tuple(sorted((mapping or {}).items()))


@dataclass(frozen=True)
class Meta:
    name: str
    namespace: str = "default"
    uid: str = ""
    resource_version: int = 0
    generation: int = 1
    labels: tuple[tuple[str, str], ...] = ()
    annotations: tuple[tuple[str, str], ...] = ()
    owner_kind: str = ""  # ReplicaSet | StatefulSet | DaemonSet | Job | Node(mirror) | ""
    owner_name: str = ""
    owner_uid: str = ""
    deletion_timestamp: float | None = None
    finalizers: tuple[str, ...] = ()

    @property
    def key(self) -> str:
        return f"{self.namespace}/{self.name}"

    def label(self, k: str, default: str | None = None) -> str | None:
        return dict(self.labels).get(k, default)


@dataclass(frozen=True)
class Toleration:
    key: str = ""
    operator: str = "Equal"  # Equal | Exists
    value: str = ""
    effect: str = ""  # "" matches all effects

    def tolerates(self, taint: "Taint") -> bool:
        if self.effect and self.effect != taint.effect:
            return False
        if self.operator == "Exists":
            return self.key == "" or self.key == taint.key
        return self.key == taint.key and self.value == taint.value


@dataclass(frozen=True)
class Taint:
    key: str
    value: str = ""
    effect: str = "NoSchedule"  # NoSchedule | PreferNoSchedule | NoExecute


@dataclass(frozen=True)
class Volume:
    claim: str
    access_mode: str = "ReadWriteOnce"  # RWO | RWX | ROX | ReadWriteOncePod
    local: bool = False  # local PV / hostPath / emptyDir-with-data
    zone: str = ""
    attached_node: str = ""


@dataclass(frozen=True)
class PodSpec:
    meta: Meta
    node: str = ""
    workload: str = ""
    phase: str = "Running"  # Pending | Running | Succeeded | Failed | Unknown
    ready: bool = True
    requests: tuple[tuple[str, int], ...] = ()
    priority: int = 0
    priority_class: str = ""
    preemption_policy: str = "PreemptLowerPriority"
    tolerations: tuple[Toleration, ...] = ()
    node_selector: tuple[tuple[str, str], ...] = ()
    required_node_labels_in: tuple[tuple[str, tuple[str, ...]], ...] = ()  # nodeAffinity In
    anti_affinity_key: str = ""  # topology key for required pod anti-affinity against same workload
    spread_key: str = ""  # topology spread key
    max_skew: int = 0
    volumes: tuple[Volume, ...] = ()
    grace_seconds: int = 30
    has_prestop: bool = False
    restart_policy: str = "Always"
    ordinal: int | None = None  # StatefulSet ordinal
    mirror: bool = False  # kubernetes.io/config.mirror
    nominated_node: str = ""

    def request(self, key: str) -> int:
        return dict(self.requests).get(key, 0)

    def replace(self, **changes) -> "PodSpec":
        return dataclasses.replace(self, **changes)


@dataclass(frozen=True)
class NodeSpec:
    meta: Meta
    allocatable: tuple[tuple[str, int], ...] = (("cpu_m", 4000), ("memory_mi", 16384), ("ephemeral_mi", 100000), ("pods", 110))
    taints: tuple[Taint, ...] = ()
    unschedulable: bool = False
    ready: str = "True"  # True | False | Unknown
    last_heartbeat: float = 0.0
    zone: str = ""
    arch: str = "amd64"
    os: str = "linux"

    @property
    def name(self) -> str:
        return self.meta.name

    def alloc(self, key: str) -> int:
        return dict(self.allocatable).get(key, 0)

    def labels(self) -> dict[str, str]:
        base = dict(self.meta.labels)
        base.setdefault("kubernetes.io/hostname", self.meta.name)
        base.setdefault("kubernetes.io/arch", self.arch)
        base.setdefault("kubernetes.io/os", self.os)
        if self.zone:
            base.setdefault("topology.kubernetes.io/zone", self.zone)
        return base

    def replace(self, **changes) -> "NodeSpec":
        return dataclasses.replace(self, **changes)


@dataclass(frozen=True)
class DisruptionBudget:
    meta: Meta
    selector: tuple[tuple[str, str], ...] = ()
    min_available: int | str | None = None  # int or "NN%"
    max_unavailable: int | str | None = None
    unhealthy_pod_eviction_policy: str = "IfHealthyBudget"  # or AlwaysAllow
    expected_pods: int | None = None  # from controller scale; None -> count matching pods


def make_pod(name: str, workload: str, node: str, *, ns: str = "default", uid: str | None = None,
             labels: Mapping[str, str] | None = None, owner_kind: str = "ReplicaSet", **kw) -> PodSpec:
    lab = {"app": workload, **(labels or {})}
    meta = Meta(name=name, namespace=ns, uid=uid or f"uid-{ns}-{name}", labels=_freeze(lab),
                owner_kind=owner_kind, owner_name=workload if owner_kind else "",
                owner_uid=f"owner-{workload}" if owner_kind else "")
    if "requests" in kw and isinstance(kw["requests"], Mapping):
        kw["requests"] = _freeze(kw["requests"])
    return PodSpec(meta=meta, node=node, workload=workload, **kw)


def make_node(name: str, *, labels: Mapping[str, str] | None = None, **kw) -> NodeSpec:
    if "allocatable" in kw and isinstance(kw["allocatable"], Mapping):
        kw["allocatable"] = _freeze(kw["allocatable"])
    return NodeSpec(meta=Meta(name=name, namespace="", uid=f"uid-node-{name}", labels=_freeze(labels)), **kw)


def from_k8s_pod(obj: Mapping) -> PodSpec:
    """Convert a Kubernetes core/v1 Pod dict into ``PodSpec`` (adapter boundary).

    Unknown or malformed fields fail closed with ``ValueError`` rather than
    silently defaulting safety-relevant state.
    """
    if not isinstance(obj, Mapping) or obj.get("kind", "Pod") != "Pod":
        raise ValueError("not a Pod object")
    md = obj.get("metadata") or {}
    spec = obj.get("spec") or {}
    status = obj.get("status") or {}
    owners = md.get("ownerReferences") or []
    ctrl = next((o for o in owners if o.get("controller")), None)
    ann = md.get("annotations") or {}
    mirror = "kubernetes.io/config.mirror" in ann
    reqs: dict[str, int] = {}
    for c in spec.get("containers") or []:
        r = ((c.get("resources") or {}).get("requests") or {})
        reqs["cpu_m"] = reqs.get("cpu_m", 0) + parse_cpu(r.get("cpu", "0"))
        reqs["memory_mi"] = reqs.get("memory_mi", 0) + parse_mem(r.get("memory", "0"))
    reqs["pods"] = 1
    conds = {c.get("type"): c.get("status") for c in status.get("conditions") or []}
    vols = tuple(
        Volume(claim=v["persistentVolumeClaim"]["claimName"])
        for v in spec.get("volumes") or [] if "persistentVolumeClaim" in v
    )
    ts = md.get("deletionTimestamp")
    return PodSpec(
        meta=Meta(
            name=str(md["name"]), namespace=str(md.get("namespace", "default")), uid=str(md.get("uid", "")),
            resource_version=int(md.get("resourceVersion", 0) or 0), generation=int(md.get("generation", 1) or 1),
            labels=_freeze(md.get("labels")), annotations=_freeze(ann),
            owner_kind=("Node" if mirror else (ctrl or {}).get("kind", "")),
            owner_name=(ctrl or {}).get("name", ""), owner_uid=(ctrl or {}).get("uid", ""),
            deletion_timestamp=1.0 if ts else None, finalizers=tuple(md.get("finalizers") or ()),
        ),
        node=str(spec.get("nodeName", "")),
        workload=(ctrl or {}).get("name", ""),
        phase=str(status.get("phase", "Unknown")),
        ready=conds.get("Ready") == "True",
        requests=_freeze(reqs),
        priority=int(spec.get("priority", 0) or 0),
        priority_class=str(spec.get("priorityClassName", "")),
        tolerations=tuple(Toleration(t.get("key", ""), t.get("operator", "Equal"), t.get("value", ""), t.get("effect", ""))
                          for t in spec.get("tolerations") or []),
        node_selector=_freeze(spec.get("nodeSelector")),
        volumes=vols,
        grace_seconds=int(spec.get("terminationGracePeriodSeconds", 30)),
        restart_policy=str(spec.get("restartPolicy", "Always")),
        mirror=mirror,
    )


def parse_cpu(v: object) -> int:
    s = str(v).strip()
    if not s:
        return 0
    if s.endswith("m"):
        return int(s[:-1])
    return int(round(float(s) * 1000))


_MEM = {"Ki": 1 / 1024, "Mi": 1, "Gi": 1024, "Ti": 1024 * 1024, "K": 1000 / 1048576, "M": 1e6 / 1048576, "G": 1e9 / 1048576}


def parse_mem(v: object) -> int:
    s = str(v).strip()
    if not s:
        return 0
    for suffix in sorted(_MEM, key=len, reverse=True):
        if s.endswith(suffix):
            return int(round(float(s[: -len(suffix)]) * _MEM[suffix]))
    return int(round(float(s) / 1048576))
