"""HypervisorAdapter boundary (WS 1).

``ElasticHost`` (model.py) stays the policy/accounting reference; the adapter is
the *only* thing allowed to touch a hypervisor.  The controller never trusts a
caller's idea of current state: it reads live state through the adapter, fences
on ``state_version`` + ``incarnation``, mutates, and re-reads.

Atomicity contract per primitive (documented, enforced by the controller):

=====================  ==========================================================
primitive              semantics
=====================  ==========================================================
memory_grow            may be PARTIAL (hot-plug of N blocks, some fail); result
                       carries confirmed ``applied``; no automatic compensation.
memory_reclaim         cooperative balloon; may be PARTIAL or REFUSED by guest;
                       confirmed ``applied`` is recorded, never the request.
memory_hot_unplug      optional capability; all-or-nothing per block.
vcpu_set               all-or-nothing required; a PARTIAL result is compensated
                       back to ``from`` by the controller, then reported.
=====================  ==========================================================

Timeouts: every call takes ``deadline`` (monotonic seconds).  A provider that
does not confirm before the deadline yields ``ProviderTimeout`` which is an
UNKNOWN outcome: the operation is journalled as ``provider_requested`` and must
be reconciled from live state before anything else touches that guest.
Cancellation is honoured *before* the provider call only; once the provider has
been asked the controller waits for confirmation or deadline (never abandons).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

ADAPTER_API_VERSION = "PK_HYPERVISOR_ADAPTER/1"
MEMORY_BLOCK_MIB_DEFAULT = 128  # typical virtio-mem / DIMM block granularity


class GuestLifecycle(str, Enum):
    BOOTING = "booting"
    RUNNING = "running"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    MIGRATING = "migrating"
    SNAPSHOTTING = "snapshotting"
    SHUTTING_DOWN = "shutting_down"
    CRASHED = "crashed"
    STOPPED = "stopped"


# Which lifecycle states permit which mutations (WS 1 "define behaviour for paused, migrating ...").
MUTABLE_STATES: dict[str, frozenset[GuestLifecycle]] = {
    "memory_grow": frozenset({GuestLifecycle.RUNNING}),
    "memory_reclaim": frozenset({GuestLifecycle.RUNNING}),
    "vcpu_add": frozenset({GuestLifecycle.RUNNING}),
    "vcpu_remove": frozenset({GuestLifecycle.RUNNING}),
    "read": frozenset(GuestLifecycle),
}


class ProviderStatus(str, Enum):
    APPLIED = "applied"
    PARTIAL = "partial"
    REFUSED = "refused"  # guest did not cooperate


@dataclass(frozen=True)
class Capabilities:
    provider: str
    provider_version: str
    api_version: str = ADAPTER_API_VERSION
    memory_grow: bool = True
    memory_reclaim: bool = True
    memory_hot_unplug: bool = False
    vcpu_hotplug: bool = True
    vcpu_hot_unplug: bool = True
    free_page_reporting: bool = False
    fencing_tokens: bool = False  # provider enforces fencing token itself
    idempotency_keys: bool = False  # provider dedupes by operation key
    memory_block_mib: int = MEMORY_BLOCK_MIB_DEFAULT
    numa_preserving_vcpu: bool = False
    generation: int = 0  # bumps whenever hypervisor/agent/kernel/VM config changes

    def supports(self, primitive: str) -> bool:
        return {
            "memory_grow": self.memory_grow,
            "memory_reclaim": self.memory_reclaim,
            "memory_hot_unplug": self.memory_hot_unplug,
            "vcpu_add": self.vcpu_hotplug,
            "vcpu_remove": self.vcpu_hot_unplug,
            "free_page_query": self.free_page_reporting,
        }.get(primitive, False)


@dataclass(frozen=True)
class LiveGuest:
    """Hypervisor-confirmed guest state (never caller-supplied)."""

    guest_id: str
    tenant: str
    incarnation: str  # provider-unique per boot/create; defeats identifier reuse
    lifecycle: GuestLifecycle
    memory_mib: int
    vcpus: int
    state_version: int  # provider- or adapter-maintained monotonic version
    non_balloonable_mib: int = 0  # pinned / DMA / device memory
    min_boot_vcpus: int = 1
    numa_nodes: tuple[int, ...] = (0,)


@dataclass(frozen=True)
class HostCapacity:
    total_mib: int
    hypervisor_overhead_mib: int
    reserved_pool_mib: int
    fragmentation_loss_mib: int
    trusted: bool = True
    measured_at: float = 0.0

    @property
    def usable_mib(self) -> int:
        """Memory usable by guests *before* the INV-32 host reserve is removed."""
        return self.total_mib - self.hypervisor_overhead_mib - self.reserved_pool_mib - self.fragmentation_loss_mib


@dataclass(frozen=True)
class ProviderResult:
    request_id: str
    status: ProviderStatus
    applied: int  # confirmed memory MiB or vCPU count *after* the call
    state_version: int
    provider_latency_s: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)  # redacted before any audit/log use


class HypervisorAdapter(ABC):
    """Everything INV-32 may ask of a hypervisor.  Implementations must be side-effect free on reads."""

    @abstractmethod
    def capabilities(self) -> Capabilities: ...

    @abstractmethod
    def health(self) -> dict[str, Any]: ...

    @abstractmethod
    def host_capacity(self) -> HostCapacity: ...

    @abstractmethod
    def list_guests(self) -> list[LiveGuest]: ...

    @abstractmethod
    def get_guest(self, guest_id: str) -> LiveGuest: ...

    @abstractmethod
    def set_memory(self, guest_id: str, target_mib: int, *, expected_version: int, incarnation: str,
                   idempotency_key: str, fencing_token: int, deadline: float) -> ProviderResult: ...

    @abstractmethod
    def set_vcpus(self, guest_id: str, target: int, *, expected_version: int, incarnation: str,
                  idempotency_key: str, fencing_token: int, deadline: float) -> ProviderResult: ...

    def free_pages(self, guest_id: str) -> int | None:
        return None

    def cancel(self, request_id: str) -> bool:
        """Best-effort cancel of a queued provider request.  Default: unsupported."""
        return False

    def drain(self) -> None:  # noqa: B027 - optional hook, default no-op
        """Stop accepting new mutations (process termination / upgrade)."""
