"""INV-66 - Enterprise Wasm control plane (master-applied component).

The production runtime (``service``, ``http_api`` and friends) is stdlib-only and
imports without ``pk_core``.  The Post-Kubernetes checklist adapter
(:mod:`component`) is exported only when ``pk_core`` is importable.
"""

__version__ = "4.3.0"

try:  # pk_core is an optional, externally supplied conformance runtime.
    from .component import COMPONENT, EnterpriseWasmControlPlaneComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
    PK_CORE_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised when pk_core is absent
    COMPONENT = EnterpriseWasmControlPlaneComponent = build_contract = None
    ELEMENT_ID, ELEMENT_NAME = "INV-66", "Enterprise Wasm control plane"
    PK_CORE_AVAILABLE = False

__all__ = ["__version__", "COMPONENT", "EnterpriseWasmControlPlaneComponent", "ELEMENT_ID",
           "ELEMENT_NAME", "build_contract", "PK_CORE_AVAILABLE"]
