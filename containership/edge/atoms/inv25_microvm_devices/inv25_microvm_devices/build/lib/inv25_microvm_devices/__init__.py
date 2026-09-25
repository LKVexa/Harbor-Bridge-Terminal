"""INV-25 - MicroVM devices (master-applied component).

The catalogue model, error contract, control plane, audit, provenance and
compatibility modules are dependency-free.  ``COMPONENT`` /
``MicrovmDevicesComponent`` / ``build_contract`` need ``pk_core`` and are
resolved lazily, so a missing or unsupported ``pk_core`` yields a
machine-readable INV25_DEPENDENCY_UNAVAILABLE / INV25_COMPATIBILITY_MISMATCH
error instead of breaking the whole package import.
"""

__version__ = "4.3.0"
from .model import DeviceCatalogue, DeviceRejected, DeviceSpec, catalogue_from_export
from .errors import CODES as ERROR_CODES, Inv25Error, to_error

ELEMENT_ID = "INV-25"
ELEMENT_NAME = "MicroVM devices"

_LAZY = {"COMPONENT", "MicrovmDevicesComponent", "build_contract"}


def __getattr__(name):
    if name in _LAZY:
        from .pk_bootstrap import require_pk_core
        require_pk_core()
        from . import component, contract
        return {"COMPONENT": component.COMPONENT, "MicrovmDevicesComponent": component.MicrovmDevicesComponent,
                "build_contract": contract.build}[name]
    raise AttributeError(name)


__all__ = ["__version__", "COMPONENT", "MicrovmDevicesComponent", "DeviceCatalogue", "DeviceRejected",
           "DeviceSpec", "ELEMENT_ID", "ELEMENT_NAME", "build_contract", "catalogue_from_export",
           "ERROR_CODES", "Inv25Error", "to_error"]
