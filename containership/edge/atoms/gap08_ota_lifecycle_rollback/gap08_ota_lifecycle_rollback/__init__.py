"""GAP-08 - OTA lifecycle/rollback (master-applied component).

The safety-critical engine (``rollout``) and the integrated control plane
(``controller`` and its components) import only the standard library.  The
``pk_core`` checklist binding (``component``) is loaded lazily so the package
is importable when the wider framework is absent.
"""

__version__ = "4.3.0"

from .contract_data import ELEMENT_ID, ELEMENT_NAME  # noqa: E402
from .rollout import (  # noqa: E402
    BundleRejected,
    GateFailed,
    InvalidRollout,
    NoRollbackTarget,
    Rollout,
    RolloutError,
    RolloutState,
    StateIntegrityError,
)


def __getattr__(name):  # lazy pk_core-dependent exports
    if name in ("COMPONENT", "OtaLifecycleRollbackComponent"):
        from . import component
        return getattr(component, name)
    if name == "build_contract":
        from .contract import build
        return build
    raise AttributeError(name)


__all__ = [
    "__version__",
    "COMPONENT",
    "OtaLifecycleRollbackComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "Rollout",
    "RolloutState",
    "RolloutError",
    "BundleRejected",
    "GateFailed",
    "NoRollbackTarget",
    "InvalidRollout",
    "StateIntegrityError",
]
