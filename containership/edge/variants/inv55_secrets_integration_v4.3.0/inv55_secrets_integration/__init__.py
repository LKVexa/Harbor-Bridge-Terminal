"""INV-55 - Secrets integration.

The production service (``service.SecretsService``) and provider adapters depend only
on the CPython standard library.  The pk_core conformance component
(``component.SecretsIntegrationComponent``) is importable only when the external
``pk_core`` estate package is installed (see docs/waivers WVR for the pin).
"""

__version__ = "4.3.0"
from .contract_ids import ELEMENT_ID, ELEMENT_NAME  # noqa: E402

try:  # pk_core is an optional estate dependency
    from .component import COMPONENT, SecretsIntegrationComponent  # noqa: F401
    from .contract import build as build_contract  # noqa: F401
    HAVE_PK_CORE = True
except ModuleNotFoundError as _exc:  # pragma: no cover - depends on environment
    if _exc.name is None or not _exc.name.startswith("pk_core"):
        raise
    HAVE_PK_CORE = False

__all__ = ["__version__", "ELEMENT_ID", "ELEMENT_NAME", "HAVE_PK_CORE"]
