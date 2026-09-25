"""INV-32 - Elastic virtualization (master-applied component)."""

from pathlib import Path as _Path

__version__ = "4.3.0"
_VERSION_FILE = _Path(__file__).with_name("VERSION")
if _VERSION_FILE.exists() and _VERSION_FILE.read_text().strip() != __version__:  # canonical-source guard
    raise ImportError("VERSION file disagrees with __version__; package is inconsistent")

ELEMENT_ID = "INV-32"
ELEMENT_NAME = "Elastic virtualization"
from .model import (
    AUDIT_EVENT_SCHEMA,
    HOST_RESOURCES_SCHEMA,
    RESOURCE_ADJUSTMENT_SCHEMA,
    AuditIntegrityError,
    ElasticHost,
    FloorBreach,
    Guest,
    InvalidAdjustmentRecord,
    ReplayConflict,
    ReserveBreach,
    StaleAdjustment,
    StateIntegrityError,
    UnknownGuest,
)


_PK_CORE_EXPORTS = {"COMPONENT", "ElasticVirtualizationComponent", "build_contract"}


def __getattr__(name):
    """pk_core-bound symbols load lazily: the control plane itself has no pk_core dependency (WS 2)."""
    if name in _PK_CORE_EXPORTS:
        try:
            from . import component, contract
        except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
            raise ImportError(
                f"{name} requires the optional 'pk_core' framework (pip install inv32-elastic-virtualization[inventory])"
            ) from exc
        return {"COMPONENT": component.COMPONENT, "ElasticVirtualizationComponent": component.ElasticVirtualizationComponent,
                "build_contract": contract.build}[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "COMPONENT",
    "ElasticVirtualizationComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "ElasticHost",
    "Guest",
    "ReserveBreach",
    "FloorBreach",
    "UnknownGuest",
    "InvalidAdjustmentRecord",
    "StaleAdjustment",
    "ReplayConflict",
    "StateIntegrityError",
    "AuditIntegrityError",
    "RESOURCE_ADJUSTMENT_SCHEMA",
    "HOST_RESOURCES_SCHEMA",
    "AUDIT_EVENT_SCHEMA",
]
