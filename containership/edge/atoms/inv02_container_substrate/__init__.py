"""INV-02 - Container substrate.

v5.0.0 adds a stdlib-only production substrate around the v4.2 reference model:
``oci`` (image spec, platform selection), ``store`` (durable CAS, tags, leases, GC,
repair, backup), ``distribution`` (registry client), ``rootfs`` (unpack, snapshotter),
``runtime`` (OCI runtime spec, cgroups v2, lifecycle, supervision), ``trust``
(Ed25519, attestations, SBOM, scan states), ``policy`` (admission, waivers), ``audit``,
``observability``, ``resilience``, ``config``, ``migrations`` and ``timeutil``.
Submodules are imported on demand.

The stdlib-only registry integrity model is importable without the optional ``pk_core``
conformance framework.  Conformance exports are loaded lazily when requested.
"""
from __future__ import annotations

__version__ = "5.0.0"

from .registry import (
    IntegrityError,
    LimitExceeded,
    Limits,
    MutableTagRefused,
    ProvenanceRecord,
    QuarantinedDigest,
    Registry,
    RegistryError,
    UnknownReference,
    ValidationError,
    digest,
    parse_reference,
)

__all__ = [
    "__version__",
    "Registry",
    "Limits",
    "ProvenanceRecord",
    "RegistryError",
    "ValidationError",
    "IntegrityError",
    "MutableTagRefused",
    "UnknownReference",
    "LimitExceeded",
    "QuarantinedDigest",
    "digest",
    "parse_reference",
    "COMPONENT",
    "ContainerSubstrateComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]


def __getattr__(name: str):
    """Load pk_core-dependent exports only when they are actually requested."""
    if name in {"COMPONENT", "ContainerSubstrateComponent"}:
        from .component import COMPONENT, ContainerSubstrateComponent

        globals().update(
            COMPONENT=COMPONENT,
            ContainerSubstrateComponent=ContainerSubstrateComponent,
        )
        return globals()[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build

        globals().update(
            ELEMENT_ID=ELEMENT_ID,
            ELEMENT_NAME=ELEMENT_NAME,
            build_contract=build,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
