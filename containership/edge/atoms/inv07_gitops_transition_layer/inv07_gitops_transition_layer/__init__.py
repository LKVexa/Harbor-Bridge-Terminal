"""INV-07 - GitOps transition layer (master-applied component).

5.0.0: the ``pk_core`` conformance adapter is imported lazily so the
production overlay in ``components/`` is importable (and pip-installable)
without ``pk_core``.  When ``pk_core`` is present the public names are
unchanged.
"""

__version__ = "5.0.0"

try:
    from .component import COMPONENT, GitopsTransitionLayerComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
    PK_CORE_AVAILABLE = True
except ModuleNotFoundError as _exc:  # pragma: no cover - depends on environment
    if _exc.name != "pk_core" and not str(_exc.name or "").startswith("pk_core."):
        raise
    COMPONENT = GitopsTransitionLayerComponent = build_contract = None
    ELEMENT_ID, ELEMENT_NAME = "INV-07", "GitOps transition layer"
    PK_CORE_AVAILABLE = False

__all__ = ["__version__", "COMPONENT", "GitopsTransitionLayerComponent", "ELEMENT_ID", "ELEMENT_NAME",
           "build_contract", "PK_CORE_AVAILABLE"]
