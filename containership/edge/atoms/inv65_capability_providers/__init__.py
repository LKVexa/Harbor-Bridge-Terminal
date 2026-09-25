"""INV-65 - Capability providers (master-applied component).

4.3.0: the production runtime modules (identity, authn/authz, secrets, durable
state, host, audit, ...) are importable without ``pk_core``; only the 100-item
conformance component needs it and is loaded lazily.
"""

__version__ = "4.3.0"
from .provider import InvalidLink, NoLink, Provider, ProviderError, ProviderUnavailable
from .contract_ids import ELEMENT_ID, ELEMENT_NAME

__all__ = [
    "__version__", "ELEMENT_ID", "ELEMENT_NAME",
    "Provider", "ProviderError", "NoLink", "InvalidLink", "ProviderUnavailable",
    "COMPONENT", "CapabilityProvidersComponent", "build_contract",
]


def __getattr__(name):  # PEP 562 lazy import of the pk_core-dependent parts
    if name in ("COMPONENT", "CapabilityProvidersComponent"):
        from . import component
        return getattr(component, name)
    if name == "build_contract":
        from .contract import build
        return build
    raise AttributeError(name)
