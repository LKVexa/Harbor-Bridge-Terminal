"""Production HyperFlux adapter -- FAIL-CLOSED SHELL (WS 1, BLOCKED on external input).

No HyperFlux specification, version, transport or SDK was supplied with the
v4.2.0 candidate, and the checklist forbids inventing one.  This module pins the
*shape* of the integration so it can be completed without touching the
controller, and refuses every call until an approved spec is pinned:

* ``PINNED_SPEC`` must be set to the approved spec ID + digest (ADR-0001).
* ``transport`` must be an object implementing ``call(method, params, deadline)``
  over a mutually-authenticated channel (daemon/RPC decided in ADR-0001).

Until then ``HyperFluxAdapter(...)`` raises ``CapabilityUnsupported`` at
construction -- *before* any mutation is possible (capability negotiation fails
early, per WS 1).
"""
from __future__ import annotations

from typing import Any, Protocol

from .. import errors as E
from .base import Capabilities, HostCapacity, HypervisorAdapter, LiveGuest, ProviderResult

PINNED_SPEC: dict[str, str] | None = None  # e.g. {"spec": "hyperflux-x.y", "sha256": "..."}
SUPPORTED_PROVIDER_VERSIONS: tuple[str, ...] = ()


class Transport(Protocol):
    def call(self, method: str, params: dict[str, Any], deadline: float) -> dict[str, Any]: ...


class HyperFluxAdapter(HypervisorAdapter):
    def __init__(self, transport: Transport, *, spec: dict[str, str] | None = PINNED_SPEC) -> None:
        if not spec or not spec.get("sha256"):
            raise E.CapabilityUnsupported(
                "HyperFlux spec not pinned; production adapter is disabled (see ADR-0001)",
                blocker="WS1-HYPERFLUX-SPEC",
            )
        self._t = transport
        self._spec = spec
        caps = self.capabilities()
        if caps.provider_version not in SUPPORTED_PROVIDER_VERSIONS:
            raise E.CapabilityUnsupported("provider version outside compatibility matrix",
                                          provider_version=caps.provider_version)

    # All methods below are mapped 1:1 to the transport once the spec exists.
    def capabilities(self) -> Capabilities:  # pragma: no cover - requires real provider
        raise NotImplementedError

    def health(self) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    def host_capacity(self) -> HostCapacity:  # pragma: no cover
        raise NotImplementedError

    def list_guests(self) -> list[LiveGuest]:  # pragma: no cover
        raise NotImplementedError

    def get_guest(self, guest_id: str) -> LiveGuest:  # pragma: no cover
        raise NotImplementedError

    def set_memory(self, *a, **k) -> ProviderResult:  # pragma: no cover
        raise NotImplementedError

    def set_vcpus(self, *a, **k) -> ProviderResult:  # pragma: no cover
        raise NotImplementedError
