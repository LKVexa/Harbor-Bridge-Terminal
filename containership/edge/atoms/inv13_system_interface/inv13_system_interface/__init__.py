"""INV-13 - System interface (master-applied component)."""

__version__ = "4.3.0"
ELEMENT_ID, ELEMENT_NAME = "INV-13", "System interface"
from .runtime import (  # noqa: E402
    CAPABILITIES, CapabilityDenied, Instance, PathEscape, World,
)

try:  # the pk_core assessment glue is optional; the host layer is stdlib-only
    from .component import COMPONENT, SystemInterfaceComponent
    from .contract import build as build_contract
except ModuleNotFoundError as _exc:  # pragma: no cover - depends on environment
    if _exc.name != "pk_core" and not str(_exc.name).startswith("pk_core"):
        raise
    COMPONENT = SystemInterfaceComponent = build_contract = None

__all__ = [
    "__version__", "COMPONENT", "SystemInterfaceComponent", "ELEMENT_ID",
    "ELEMENT_NAME", "build_contract", "CAPABILITIES", "CapabilityDenied",
    "Instance", "PathEscape", "World",
]
