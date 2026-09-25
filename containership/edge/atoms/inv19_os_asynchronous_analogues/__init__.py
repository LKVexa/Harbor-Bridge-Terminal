"""INV-19 - OS asynchronous analogues (master-applied component)."""

__version__ = "5.0.0"

from .backend import (
    BACKENDS,
    BACKEND_PRIORITY,
    FALLBACK,
    AsyncBackend,
    DescriptorBudget,
    InvalidDescriptor,
    NoBackend,
    select,
)
ELEMENT_ID = "INV-19"
ELEMENT_NAME = "OS asynchronous analogues"

# pk_core is an external orchestration dependency.  Keep the backend primitives
# importable for local diagnostics/tests even when that framework is absent.
try:
    from .component import COMPONENT, OsAsynchronousAnaloguesComponent
    from .contract import build as build_contract
except ModuleNotFoundError as exc:
    if exc.name is None or not (exc.name == "pk_core" or exc.name.startswith("pk_core.")):
        raise
    COMPONENT = None
    OsAsynchronousAnaloguesComponent = None
    build_contract = None

__all__ = [
    "__version__", "BACKENDS", "BACKEND_PRIORITY", "FALLBACK", "AsyncBackend",
    "DescriptorBudget", "InvalidDescriptor", "NoBackend", "select", "COMPONENT",
    "OsAsynchronousAnaloguesComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract",
]
