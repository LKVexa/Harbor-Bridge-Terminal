"""Optional INV-35 accelerated datapath negotiation and safety (MC-006).

The runtime never assumes acceleration.  ``negotiate`` applies the configured
``datapath_policy`` (``require`` | ``prefer`` | ``disabled``): absence under
``require`` rejects admission, under ``prefer`` falls back *observably* to the
standard virtio path.  Descriptor/region validation is enforced here before
any buffer is exposed, independently of the INV-35 implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final, Protocol

from ..errors import Inv24Error

MAX_QUEUE_SIZE: Final[int] = 1024
MAX_DESCRIPTOR_LEN: Final[int] = 1 << 20
MAX_REGIONS: Final[int] = 16


class Datapath(Protocol):
    name: str
    version: str

    def healthy(self) -> bool: ...


@dataclass(frozen=True, slots=True)
class Region:
    gpa: int
    size: int
    tenant: str


@dataclass
class DatapathDecision:
    mode: str  # "accelerated" | "standard"
    reason: str
    provider: str | None = None
    counters: dict[str, int] = field(default_factory=dict)


def negotiate(policy: str, provider: Datapath | None) -> DatapathDecision:
    if policy not in {"require", "prefer", "disabled"}:
        raise Inv24Error("CONFIG_REJECTED", f"unknown datapath policy {policy!r}")
    if policy == "disabled":
        return DatapathDecision("standard", "policy disabled")
    ok = provider is not None and provider.healthy()
    if ok:
        return DatapathDecision("accelerated", "provider healthy", f"{provider.name}/{provider.version}")
    if policy == "require":
        raise Inv24Error("DATAPATH_UNAVAILABLE", "INV-35 required but absent/unhealthy")
    return DatapathDecision("standard", "INV-35 absent or unhealthy; fell back (observable)")


def validate_regions(regions: list[Region], *, guest_memory_bytes: int) -> None:
    if len(regions) > MAX_REGIONS:
        raise Inv24Error("RESOURCE_EXHAUSTED", "too many guest memory regions")
    spans = sorted((r.gpa, r.gpa + r.size, r.tenant) for r in regions)
    tenants = {r.tenant for r in regions}
    if len(tenants) > 1:
        raise Inv24Error("TENANT_MISMATCH", "regions from multiple tenants in one queue set")
    prev_end = -1
    for start, end, _ in spans:
        if start < 0 or end <= start or end > guest_memory_bytes:
            raise Inv24Error("DESCRIPTOR_OUT_OF_BOUNDS", "region outside guest memory")
        if start < prev_end:
            raise Inv24Error("DESCRIPTOR_OUT_OF_BOUNDS", "overlapping guest regions")
        prev_end = end


def validate_descriptor(addr: int, length: int, regions: list[Region], *, queue_size: int) -> None:
    if not 1 <= queue_size <= MAX_QUEUE_SIZE or queue_size & (queue_size - 1):
        raise Inv24Error("CONFIG_REJECTED", "queue size must be a power of two <= 1024")
    if not 0 < length <= MAX_DESCRIPTOR_LEN:
        raise Inv24Error("DESCRIPTOR_OUT_OF_BOUNDS", "descriptor length out of range")
    if not any(r.gpa <= addr and addr + length <= r.gpa + r.size for r in regions):
        raise Inv24Error("DESCRIPTOR_OUT_OF_BOUNDS", "descriptor not within one registered region")
