"""INV-67 - Kubernetes integration mechanism (master-applied component).

v4.3.0: the pure translator (``translator``) and the integration plane
(``plane``) are importable without ``pk_core``. The pk_core checklist
component is exported only when ``pk_core`` is importable.
"""

__version__ = "4.3.0"

from .contract import ELEMENT_ID, ELEMENT_NAME  # noqa: E402  (contract imports pk_core lazily below)

try:  # pk_core is a sibling package in the full estate, absent standalone
    from .component import COMPONENT, KubernetesIntegrationMechanismComponent
    from .contract import build as build_contract
except ModuleNotFoundError as _exc:  # pragma: no cover - exercised in standalone archive
    if _exc.name != "pk_core" and not str(_exc.name).startswith("pk_core."):
        raise
    COMPONENT = KubernetesIntegrationMechanismComponent = build_contract = None  # type: ignore[assignment,misc]

__all__ = ["__version__", "COMPONENT", "KubernetesIntegrationMechanismComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]
