"""INV-55 - Secrets integration (master-applied component).

The ``pk_core`` conformance binding is loaded lazily so the standalone runtime
(``inv55_secrets_integration.runtime``) can be imported, tested and operated
without the external estate.  Accessing ``COMPONENT`` when ``pk_core`` is absent
raises the original ``ModuleNotFoundError`` - it never substitutes a stub.
"""

__version__ = "4.3.0"
from .contract import ELEMENT_ID, ELEMENT_NAME  # contract imports pk_core lazily too

__all__ = ["__version__", "COMPONENT", "SecretsIntegrationComponent", "ELEMENT_ID", "ELEMENT_NAME", "build_contract"]


def __getattr__(name):
    if name in ("COMPONENT", "SecretsIntegrationComponent"):
        from . import component
        return getattr(component, name)
    if name == "build_contract":
        from .contract import build
        return build
    raise AttributeError(name)
