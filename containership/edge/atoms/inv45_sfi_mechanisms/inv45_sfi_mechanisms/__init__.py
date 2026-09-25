"""INV-45 - SFI mechanisms (master-applied component).

v4.3.0: the package is importable without ``pk_core``.  The ``pk_core`` checklist
binding (``component.py``) is loaded only when the pinned ``pk_core`` dependency is
importable; otherwise ``COMPONENT`` is ``None`` and ``PK_CORE_ERROR`` says why.
The production enforcement layer lives in ``inv45_sfi_mechanisms.production``.
"""

__version__ = "4.3.0"

from .sfi_core import (
    Access,
    BranchOutsideTargets,
    ModuleNotVerified,
    SandboxRegion,
    SfiModule,
    SfiSecurityError,
    UnmaskedAccess,
)

try:  # pk_core is an external, pinned dependency (docs/architecture/DEPENDENCIES.md)
    from .component import COMPONENT, SfiMechanismsComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
    PK_CORE_ERROR = None
except ModuleNotFoundError as _exc:  # pragma: no cover - depends on environment
    if _exc.name is None or not _exc.name.startswith("pk_core"):
        raise
    COMPONENT = None
    SfiMechanismsComponent = None
    ELEMENT_ID, ELEMENT_NAME = "INV-45", "SFI mechanisms"
    build_contract = None
    PK_CORE_ERROR = f"pk_core not importable: {_exc}"

__all__ = [
    "__version__",
    "COMPONENT",
    "PK_CORE_ERROR",
    "SfiMechanismsComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "Access",
    "BranchOutsideTargets",
    "ModuleNotVerified",
    "SandboxRegion",
    "SfiModule",
    "SfiSecurityError",
    "UnmaskedAccess",
]
