"""GAP02-MC-21..26 — Sibling integration adapters.

Each sibling is reached through a narrow Protocol so GAP-02 can be tested
against contract fakes now and bound to the real sibling later. The *real*
sibling integration tests require the sibling packages and are recorded
BLOCKED in the evidence ledger until they are present.
"""
from __future__ import annotations

from typing import Any, Iterable, Protocol

from .accelerators import AcceleratorDevice
from .errors import Code, Gap02Error


# ---- MC-21 GAP-06 device identity / attestation -----------------------------
class IdentityProvider(Protocol):
    def attest(self, node: str, nonce: bytes) -> dict: ...      # {identity_id, evidence_digest, attested, nonce}
    def check(self, identity: dict) -> bool: ...


def bind_identity(idp: IdentityProvider, node: str, nonce: bytes) -> dict:
    try:
        ident = idp.attest(node, nonce)
    except Exception as e:  # noqa: BLE001
        raise Gap02Error(Code.DEPENDENCY_FAILURE, "GAP-06 unavailable") from e
    if not isinstance(ident, dict) or ident.get("attested") is not True:
        raise Gap02Error(Code.UNATTESTED, "GAP-06 did not attest")
    if ident.get("nonce") != nonce.hex():
        raise Gap02Error(Code.REPLAY_DETECTED, "attestation not bound to our nonce")
    for k in ("identity_id", "evidence_digest"):
        if not isinstance(ident.get(k), str) or not ident[k]:
            raise Gap02Error(Code.MALFORMED_RESPONSE, f"GAP-06 missing {k}")
    return ident


# ---- MC-22 GAP-07 trust & signature service ---------------------------------
class KeyRing:
    """Rotation/revocation semantics for any Signer/Verifier set (GAP-07 facade)."""

    def __init__(self) -> None:
        self.keys: dict[str, Any] = {}
        self.active: str | None = None
        self.revoked: set[str] = set()

    def provision(self, signer) -> None:
        self.keys[signer.key_id] = signer
        self.active = signer.key_id

    def rotate(self, new_signer) -> str:
        old = self.active
        self.provision(new_signer)
        return old or ""

    def revoke(self, key_id: str) -> None:
        self.revoked.add(key_id)
        if self.active == key_id:
            self.active = None

    def signer(self):
        if self.active is None:
            raise Gap02Error(Code.SIGNATURE_FAILURE, "no active signing key")
        return self.keys[self.active]

    def verify(self, key_id: str, alg: str, data: bytes, sig: bytes) -> bool:
        if key_id in self.revoked or key_id not in self.keys:
            return False
        return self.keys[key_id].verify(key_id, alg, data, sig)


# ---- MC-23 GAP-01 supervisor ------------------------------------------------
class SupervisorLink:
    """What GAP-01 calls: readiness, restart hook, quarantine, hot-plug routing."""

    def __init__(self, executor):
        self.ex = executor

    def readiness(self, now: int) -> dict:
        from .health import readiness
        return readiness(self.ex, now)[1]

    def route_hotplug(self, families: Iterable[str]) -> None:
        self.ex.notify_hotplug(families)

    def disable(self, principal: str, reason: str) -> None:
        self.ex.quarantine.freeze(principal, reason)


# ---- MC-24 SCH-01 placement -------------------------------------------------
def placement_match(requirements: dict, facts: dict, devices: list[AcceleratorDevice] = ()) -> tuple[bool, str]:
    """``requirements = {"capabilities": [...], "min": {"gpu.memory_bytes": N, "gpu.count": k}}``.
    Only ``facts["present"]`` satisfies a capability; unprobed/absent never do."""
    present = set(facts.get("present", []))
    for cap in requirements.get("capabilities", []):
        if cap not in present:
            state = "unprobed" if cap in facts.get("unprobed", []) else "absent" if cap in facts.get("absent", []) else "unknown"
            return False, f"{cap} is {state}"
    usable = [d for d in devices if d.schedulable and d.kind in ("gpu", "gpu-partition")]
    mins = requirements.get("min", {})
    if "gpu.count" in mins and len(usable) < mins["gpu.count"]:
        return False, "insufficient schedulable GPUs"
    if "gpu.memory_bytes" in mins and not any((d.memory_total_bytes or 0) >= mins["gpu.memory_bytes"] for d in usable):
        return False, "no GPU meets memory floor (unknown memory never satisfies)"
    return True, "ok"


# ---- MC-25 PLN-04 execution plane -------------------------------------------
TIERS = [  # tier, required isolation primitives (all must be present)
    ("confidential-vm", ("virtualization.host", "virtualization.iommu", "cc.sev-snp.attested")),
    ("confidential-vm", ("virtualization.host", "virtualization.iommu", "cc.tdx.attested")),
    ("microvm", ("virtualization.host",)),
    ("passthrough-vm", ("virtualization.host", "virtualization.iommu")),
    ("process", ()),
]


def tier_catalog(facts: dict) -> list[str]:
    present = set(facts.get("present", []))
    return sorted({t for t, req in TIERS if set(req) <= present})


# ---- MC-26 GAP-11 accelerator scheduler -------------------------------------
def allocation_units(devices: list[AcceleratorDevice]) -> list[dict]:
    """Allocatable units: MIG children replace their parent (no double count);
    non-schedulable devices produce no units."""
    parents_with_children = {d.parent_id for d in devices if d.kind == "gpu-partition"}
    units = []
    for d in devices:
        if not d.schedulable:
            continue
        if d.kind == "gpu" and d.stable_id in parents_with_children:
            continue
        units.append({"unit_id": d.stable_id, "backend": d.backend, "kind": d.kind,
                      "parent": d.parent_id, "memory_bytes": d.memory_total_bytes, "health": d.health})
    return units
