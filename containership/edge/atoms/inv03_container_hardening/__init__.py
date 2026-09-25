"""INV-03 - Container hardening (master-applied component)."""

__version__ = "4.3.0"
from .contract_ids import ELEMENT_ID, ELEMENT_NAME
from .policy import BASELINE_VERSION, CONTROLS, evaluate, get_baseline

# The framework-bound pieces need ``pk_core``. It is not carried in this archive
# (checklist item 46), so the security-critical policy and the 4.3.0 hardening
# runtime stay importable without it, and the absence is reported, never hidden.
try:
    from .component import COMPONENT, ContainerHardeningComponent
    from .contract import build as build_contract
    PK_CORE_AVAILABLE = True
    PK_CORE_ERROR = None
except ModuleNotFoundError as exc:  # pragma: no cover - depends on host
    if exc.name != "pk_core" and not str(exc.name).startswith("pk_core."):
        raise
    COMPONENT = ContainerHardeningComponent = build_contract = None
    PK_CORE_AVAILABLE = False
    PK_CORE_ERROR = f"pk_core unavailable: {exc}"

__all__ = [
    "__version__", "BASELINE_VERSION", "COMPONENT", "ContainerHardeningComponent",
    "CONTROLS", "ELEMENT_ID", "ELEMENT_NAME", "PK_CORE_AVAILABLE", "PK_CORE_ERROR",
    "build_contract", "evaluate", "get_baseline",
]
