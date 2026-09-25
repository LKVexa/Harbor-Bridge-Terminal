"""INV-20 - HTTP component worlds (master-applied component).

The runtime/security modules are importable without ``pk_core``. ``COMPONENT`` (the
pk_core conformance adapter) is loaded lazily so that a missing framework produces a precise
``PkCoreUnavailable`` error at the point of use instead of breaking every import.
"""
from ._version import __version__
from .contract_meta import ELEMENT_ID, ELEMENT_NAME

__all__ = ["__version__", "COMPONENT", "HttpComponentWorldsComponent", "ELEMENT_ID", "ELEMENT_NAME",
           "build_contract"]


def __getattr__(name):
    if name in ("COMPONENT", "HttpComponentWorldsComponent", "build_contract"):
        from .pk_compat import require_pk_core
        require_pk_core()
        from . import component, contract
        return {"COMPONENT": component.COMPONENT,
                "HttpComponentWorldsComponent": component.HttpComponentWorldsComponent,
                "build_contract": contract.build}[name]
    raise AttributeError(name)
