"""INV-23 - Hardware virtualization primitive.

The primitive, probe, ownership, schema and telemetry layers are pure stdlib and import
without ``pk_core``.  ``COMPONENT`` (the pk_core conformance class) is loaded lazily so a
missing conformance engine is reported by ``pkcore_compat.resolve()`` rather than
breaking every import.
"""

from ._version import __version__
from .contract_meta import ELEMENT_ID, ELEMENT_NAME
from .model import ABSENT, CLAIMED, PRESENT_DISABLED, USABLE, PrimitiveUnavailable, VirtPrimitive

__all__ = [
    "__version__",
    "COMPONENT",
    "HardwareVirtualizationPrimitiveComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "VirtPrimitive",
    "PrimitiveUnavailable",
    "USABLE",
    "PRESENT_DISABLED",
    "ABSENT",
    "CLAIMED",
]


def __getattr__(name):
    if name in ("COMPONENT", "HardwareVirtualizationPrimitiveComponent"):
        from . import component

        return getattr(component, name)
    if name == "build_contract":
        from .contract import build

        return build
    raise AttributeError(name)
