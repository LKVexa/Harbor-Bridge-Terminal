"""GAP-02 - Hardware capability discovery."""
from __future__ import annotations

__version__ = "4.3.0"

from .capabilities import (
    ABSENT,
    FRESHNESS_BOUND,
    FRESHNESS_BOUND_SECONDS,
    PRESENT,
    UNPROBED,
    CapabilityReport,
    ProbeSchedule,
    ProbeUnavailable,
    ReportInvalid,
    ReportStale,
    probe,
)
from .discovery import HardwareInventory, collect_inventory, discover, report_from_inventory

ELEMENT_ID = "GAP-02"
ELEMENT_NAME = "Hardware capability discovery"
PK_CORE_AVAILABLE = True
PK_CORE_IMPORT_ERROR: str | None = None

try:
    from .component import COMPONENT, HardwareCapabilityDiscoveryComponent
    from .contract import build as build_contract
except ModuleNotFoundError as exc:
    if exc.name == "pk_core" or (exc.name and exc.name.startswith("pk_core.")):
        PK_CORE_AVAILABLE = False
        PK_CORE_IMPORT_ERROR = str(exc)
        _PK_CORE_CAUSE = exc
        COMPONENT = None
        HardwareCapabilityDiscoveryComponent = None

        def build_contract():
            raise RuntimeError(
                "pk_core is required to build the GAP-02 integration contract; "
                "add the suite's pk_core package to PYTHONPATH"
            ) from _PK_CORE_CAUSE
    else:
        raise

__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "PK_CORE_AVAILABLE",
    "PK_CORE_IMPORT_ERROR",
    "COMPONENT",
    "HardwareCapabilityDiscoveryComponent",
    "build_contract",
    "PRESENT",
    "ABSENT",
    "UNPROBED",
    "FRESHNESS_BOUND",
    "FRESHNESS_BOUND_SECONDS",
    "CapabilityReport",
    "ProbeSchedule",
    "ProbeUnavailable",
    "ReportInvalid",
    "ReportStale",
    "probe",
    "HardwareInventory",
    "collect_inventory",
    "report_from_inventory",
    "discover",
]
