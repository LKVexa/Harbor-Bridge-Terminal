"""Hypervisor adapters: boundary definition, deterministic fake/reference, and the fail-closed HyperFlux shell."""
from .base import (
    ADAPTER_API_VERSION,
    MUTABLE_STATES,
    Capabilities,
    GuestLifecycle,
    HostCapacity,
    HypervisorAdapter,
    LiveGuest,
    ProviderResult,
    ProviderStatus,
)
from .fake import FakeHypervisor

__all__ = [
    "ADAPTER_API_VERSION", "MUTABLE_STATES", "Capabilities", "GuestLifecycle", "HostCapacity",
    "HypervisorAdapter", "LiveGuest", "ProviderResult", "ProviderStatus", "FakeHypervisor",
]
