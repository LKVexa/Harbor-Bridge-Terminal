"""INV-06 - Traditional IaC.

The state engine can be imported without ``pk_core``.  The master component and
contract adapter become available when ``pk_core`` is installed/provided by the
parent Post-Kubernetes workspace.

4.3.0 production-component modules (stdlib only, import on demand):
``durable``, ``locking``, ``graph``, ``config``, ``policy``, ``security``,
``resilience``, ``observability``, ``execution``, ``release``, ``service``.
"""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "INV-06"
ELEMENT_NAME = "Traditional IaC"

from .state import (  # noqa: E402
    DRIFT_SCHEMA,
    PLAN_SCHEMA,
    STATE_SCHEMA,
    IacError,
    IacState,
    InvalidPlan,
    InvalidState,
    ProtectedResource,
    StalePlan,
)

PK_CORE_AVAILABLE = True
try:
    from .component import COMPONENT, TraditionalIacComponent
    from .contract import build as build_contract
except ModuleNotFoundError as exc:  # permit isolated state-engine testing
    if exc.name != "pk_core" and not (exc.name or "").startswith("pk_core."):
        raise
    PK_CORE_AVAILABLE = False
    COMPONENT = None
    TraditionalIacComponent = None
    _PK_CORE_IMPORT_ERROR = str(exc)

    def build_contract():
        raise RuntimeError(
            "pk_core is required to build the INV-06 master contract: " + _PK_CORE_IMPORT_ERROR
        )


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "PK_CORE_AVAILABLE",
    "COMPONENT",
    "TraditionalIacComponent",
    "build_contract",
    "PLAN_SCHEMA",
    "STATE_SCHEMA",
    "DRIFT_SCHEMA",
    "IacError",
    "IacState",
    "StalePlan",
    "ProtectedResource",
    "InvalidPlan",
    "InvalidState",
]
