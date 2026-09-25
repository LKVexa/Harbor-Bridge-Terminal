"""Component 37 - tenant/workload isolation policy model and checker (``PK_DYN_ISOLATION/1``).

A ``TenantPolicy`` states the five boundaries; ``check_isolation`` evaluates a
placement plan (what each tenant was given) against all policies and returns
violations.  ``NamespacedState`` enforces the persistent-state boundary in-process.

What this does NOT do: enforce compute/memory/network/device isolation in the OS
or hypervisor (cgroups, namespaces, seccomp, VLAN/network policy, IOMMU/MIG).  Those
enforcement points are BLOCKED on a real node runtime; the checker here is the
admission-time policy decision that such runtimes would apply.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterator

from .core import Inv08Error, Outcome

SCHEMA = "PK_DYN_ISOLATION/1"
_TENANT_RE = re.compile(r"^[a-z][a-z0-9-]{0,62}$")


def _check_tenant(t: str) -> str:
    if not isinstance(t, str) or not _TENANT_RE.match(t):
        raise Inv08Error("INV08.ISOLATION.BAD_TENANT", f"invalid tenant id {t!r}")
    return t


@dataclass(frozen=True)
class TenantPolicy:
    tenant: str
    dedicated_nodes: bool = True              # compute/process
    mem_limit_mib: int = 1024                 # memory/resource
    cpu_millis: int = 1000
    allowed_peers: frozenset = frozenset()    # network/identity: tenants it may talk to
    identity_prefix: str = ""                 # workload identities must start with this
    exclusive_devices: bool = True            # device/accelerator

    def __post_init__(self) -> None:
        _check_tenant(self.tenant)
        for n in ("mem_limit_mib", "cpu_millis"):
            v = getattr(self, n)
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0:
                raise Inv08Error("INV08.ISOLATION.BAD_POLICY", f"{n} must be a positive int")
        if not self.identity_prefix:
            object.__setattr__(self, "identity_prefix", f"spiffe://inv08/{self.tenant}/")


@dataclass
class Placement:
    """Observed/planned assignment for one workload."""
    tenant: str
    workload: str
    node: str
    identity: str
    mem_mib: int
    cpu_millis: int
    devices: tuple = ()
    peers: tuple = ()          # tenants this workload opens connections to


@dataclass
class NodeCapacity:
    mem_mib: int
    cpu_millis: int


def check_isolation(policies: dict[str, TenantPolicy], placements: list[Placement],
                    nodes: dict[str, NodeCapacity]) -> list[dict]:
    """Return a list of violations ``{"boundary", "tenant", "detail"}`` (empty = compliant)."""
    v: list[dict] = []

    def bad(boundary: str, tenant: str, detail: str) -> None:
        v.append({"boundary": boundary, "tenant": tenant, "detail": detail})

    node_tenants: dict[str, set] = {}
    mem: dict[str, int] = {}
    cpu: dict[str, int] = {}
    t_mem: dict[str, int] = {}
    t_cpu: dict[str, int] = {}
    dev_owner: dict[str, set] = {}
    for p in placements:
        pol = policies.get(p.tenant)
        if pol is None:
            bad("compute", p.tenant, f"{p.workload}: no isolation policy (default deny)")
            continue
        if p.node not in nodes:
            bad("compute", p.tenant, f"{p.workload}: unknown node {p.node}")
            continue
        node_tenants.setdefault(p.node, set()).add(p.tenant)
        mem[p.node] = mem.get(p.node, 0) + p.mem_mib
        cpu[p.node] = cpu.get(p.node, 0) + p.cpu_millis
        t_mem[p.tenant] = t_mem.get(p.tenant, 0) + p.mem_mib
        t_cpu[p.tenant] = t_cpu.get(p.tenant, 0) + p.cpu_millis
        if not p.identity.startswith(pol.identity_prefix):
            bad("network", p.tenant, f"{p.workload}: identity {p.identity!r} outside tenant prefix")
        for peer in p.peers:
            if peer != p.tenant and peer not in pol.allowed_peers:
                bad("network", p.tenant, f"{p.workload}: egress to tenant {peer} not allowed")
        for d in p.devices:
            dev_owner.setdefault(d, set()).add(p.tenant)
    for node, ts in node_tenants.items():
        if len(ts) > 1:
            for t in sorted(ts):
                if policies[t].dedicated_nodes:
                    bad("compute", t, f"node {node} shared with {sorted(ts - {t})}")
        cap = nodes[node]
        if mem[node] > cap.mem_mib or cpu[node] > cap.cpu_millis:
            for t in sorted(ts):
                bad("memory", t, f"node {node} overcommitted")
    for t, used in t_mem.items():
        if used > policies[t].mem_limit_mib or t_cpu[t] > policies[t].cpu_millis:
            bad("memory", t, "tenant resource limit exceeded")
    for d, ts in dev_owner.items():
        if len(ts) > 1:
            for t in sorted(ts):
                if policies[t].exclusive_devices:
                    bad("device", t, f"device {d} shared with {sorted(ts - {t})}")
    return v


class NamespacedState:
    """Per-tenant view over a shared backing dict. Keys are stored as ``tenant\\x00key``;
    a tenant can never read, write, enumerate or delete another tenant's keys."""

    SEP = "\x00"

    def __init__(self, backing: dict, tenant: str) -> None:
        self._b, self.tenant = backing, _check_tenant(tenant)

    def _k(self, key: str) -> str:
        if not isinstance(key, str) or not key or self.SEP in key or len(key) > 512:
            raise Inv08Error("INV08.ISOLATION.BAD_KEY", "invalid state key", outcome=Outcome.TERMINAL_FAILURE)
        return f"{self.tenant}{self.SEP}{key}"

    def __getitem__(self, key: str) -> Any:
        return self._b[self._k(key)]

    def __setitem__(self, key: str, value: Any) -> None:
        self._b[self._k(key)] = value

    def __delitem__(self, key: str) -> None:
        del self._b[self._k(key)]

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and self._k(key) in self._b

    def keys(self) -> Iterator[str]:
        pre = self.tenant + self.SEP
        return iter(sorted(k[len(pre):] for k in self._b if k.startswith(pre)))

    def __len__(self) -> int:
        return sum(1 for _ in self.keys())
