"""Device / network / storage boundary policy (MC-010, MC-044, MC-045; C046).

Deny by default.  A site's ``IsolationPolicy`` lists what may be attached; the manifest's
request must be a subset, and the resulting ``IsolationPlan`` is the ONLY input the VMM
adapter uses to attach anything (the adapter never reads the manifest).  Passthrough
(VFIO/PCI) devices are not representable at all - the device vocabulary is virtio + serial -
so an IOMMU bypass cannot be requested (MC-045 policy half; the proof half needs hardware, W-HW).
"""
from __future__ import annotations

from dataclasses import dataclass

from .errors import UkError
from .manifest import DEVICE_KINDS, IsolationRequest


@dataclass(frozen=True)
class IsolationPolicy:
    allow_network: frozenset = frozenset({"none"})
    allowed_bridges: frozenset = frozenset()
    allowed_devices: frozenset = frozenset({"serial"})
    allowed_storage: frozenset = frozenset()       # digests of approved read-only volumes
    tenant_bridges: dict | None = None             # tenant -> frozenset(bridge); bridges are per tenant

    @classmethod
    def from_dict(cls, d: dict) -> "IsolationPolicy":
        try:
            devs = frozenset(d.get("allowed_devices", ["serial"]))
            if not devs <= set(DEVICE_KINDS):
                raise ValueError(f"unknown device kinds {sorted(devs - set(DEVICE_KINDS))}")
            return cls(frozenset(d.get("allow_network", ["none"])), frozenset(d.get("allowed_bridges", [])), devs,
                       frozenset(d.get("allowed_storage", [])),
                       {k: frozenset(v) for k, v in (d.get("tenant_bridges") or {}).items()})
        except (TypeError, ValueError) as e:
            raise UkError("UK_CONFIG_INVALID", f"isolation policy: {e}") from None


@dataclass(frozen=True)
class IsolationPlan:
    tenant: str
    network: str
    bridge: str | None
    devices: tuple
    storage: tuple

    def to_dict(self) -> dict:
        return {"tenant": self.tenant, "network": self.network, "bridge": self.bridge,
                "devices": list(self.devices), "storage": [list(s) for s in self.storage]}


def plan(req: IsolationRequest, policy: IsolationPolicy, tenant: str) -> IsolationPlan:
    if req.network not in policy.allow_network:
        raise UkError("UK_ISOLATION_POLICY", f"network mode {req.network!r} not allowed here")
    if req.network == "tap":
        if req.network_bridge not in policy.allowed_bridges:
            raise UkError("UK_ISOLATION_POLICY", f"bridge {req.network_bridge!r} not allowed")
        owners = policy.tenant_bridges or {}
        if req.network_bridge not in owners.get(tenant, frozenset()):
            raise UkError("UK_ISOLATION_POLICY", "bridge is not assigned to this tenant (cross-tenant network)")
        if "virtio-net" not in req.devices:
            raise UkError("UK_ISOLATION_POLICY", "tap networking requires the virtio-net device")
    elif "virtio-net" in req.devices:
        raise UkError("UK_ISOLATION_POLICY", "virtio-net requested with network=none")
    bad = [d for d in req.devices if d not in policy.allowed_devices]
    if bad:
        raise UkError("UK_ISOLATION_POLICY", f"devices not allowed: {bad}")
    for dig, ro in req.storage:
        if not ro or dig not in policy.allowed_storage:
            raise UkError("UK_ISOLATION_POLICY", f"volume {dig} not an approved read-only volume")
    if req.storage and "virtio-blk" not in req.devices:
        raise UkError("UK_ISOLATION_POLICY", "storage requires virtio-blk")
    return IsolationPlan(tenant, req.network, req.network_bridge, tuple(sorted(req.devices)), tuple(req.storage))
