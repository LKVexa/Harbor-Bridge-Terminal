"""INV-34 - Legacy CPU expansion path."""

__version__ = "5.1.0"

from .expansion import (
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    STATUS_SCHEMA,
    CpuExpansionController,
    ExpansionError,
    ExpansionResult,
    VmCpuState,
)

PK_CORE_AVAILABLE = True
try:
    from .component import COMPONENT, LegacyCpuExpansionPathComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
except ModuleNotFoundError as exc:  # package logic remains usable without the external framework
    if exc.name != "pk_core":
        raise
    PK_CORE_AVAILABLE = False
    COMPONENT = None
    LegacyCpuExpansionPathComponent = None
    ELEMENT_ID = "INV-34"
    ELEMENT_NAME = "Legacy CPU expansion path"

    def build_contract():
        raise RuntimeError("pk_core is required to build the framework contract")


__all__ = [
    "__version__",
    "PK_CORE_AVAILABLE",
    "COMPONENT",
    "LegacyCpuExpansionPathComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "REQUEST_SCHEMA",
    "RESULT_SCHEMA",
    "STATUS_SCHEMA",
    "CpuExpansionController",
    "ExpansionError",
    "ExpansionResult",
    "VmCpuState",
]
