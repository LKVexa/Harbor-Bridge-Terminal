"""INV-70 - Fast agent sandbox.

The bounded runtime is usable without the optional external ``pk_core``
conformance framework. Framework-backed component/contract objects are exposed
when that dependency is installed.
"""

__version__ = "4.3.0"
ELEMENT_ID = "INV-70"
ELEMENT_NAME = "Fast agent sandbox"

from .runtime import Trap, run, validate_program
from .service import REASON_CODES, Sandbox

try:
    import pk_core as _pk_core  # noqa: F401
except ModuleNotFoundError as _exc:
    if _exc.name != "pk_core":
        raise
    PK_CORE_AVAILABLE = False
    COMPONENT = None
    FastAgentSandboxComponent = None

    def build_contract():
        """Raise a precise error when the optional contract framework is absent."""
        raise RuntimeError("pk_core is required to build the INV-70 framework contract")
else:
    PK_CORE_AVAILABLE = True
    from .component import COMPONENT, FastAgentSandboxComponent
    from .contract import build as build_contract

__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "PK_CORE_AVAILABLE",
    "COMPONENT",
    "FastAgentSandboxComponent",
    "build_contract",
    "Trap",
    "run",
    "validate_program",
    "Sandbox",
    "REASON_CODES",
]
