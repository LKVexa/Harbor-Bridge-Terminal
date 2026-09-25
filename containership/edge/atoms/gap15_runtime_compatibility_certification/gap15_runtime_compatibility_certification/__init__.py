"""GAP-15 - Runtime compatibility certification (master-applied component)."""

__version__ = "4.3.0"

try:  # the reference component binds to the series' pk_core framework
    from .component import COMPONENT, RuntimeCompatibilityCertificationComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
    PK_CORE_AVAILABLE = True
except ModuleNotFoundError as _exc:  # pragma: no cover - depends on environment
    if not (_exc.name or "").startswith("pk_core"):
        raise
    # The production layer (``.production``) is stdlib-only and must stay
    # importable without pk_core; the pk_core-bound symbols are simply absent.
    COMPONENT = RuntimeCompatibilityCertificationComponent = None
    ELEMENT_ID, ELEMENT_NAME, build_contract = "GAP-15", "Runtime compatibility certification", None
    PK_CORE_AVAILABLE = False

__all__ = ["PK_CORE_AVAILABLE", "__version__", "COMPONENT", "RuntimeCompatibilityCertificationComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
