"""PLN-02 - Application plane.

The deterministic resolver is usable without ``pk_core``. v4.3 adds the
production controls around it (``service.ApplicationPlaneService`` wires them);
each control module is importable on its own.  The conformance
adapter and contract are imported lazily when those integration surfaces are
requested.
"""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "PLN-02"
ELEMENT_NAME = "Application plane"

from .resolver import (
    APPLICATION_SCHEMA,
    CATALOGUE_SCHEMA,
    REVISION_SCHEMA,
    IncompatibleInterface,
    ResolutionError,
    RevisionIntegrityError,
    UnsatisfiedRequirement,
    ValidationError,
    resolve,
    resolve_document,
    verify_revision,
)


from .errors import PlaneError, to_public  # noqa: E402
from .context import RequestContext  # noqa: E402


def build_contract():
    """Build the pk_core contract, importing pk_core only when requested."""
    from .contract import build

    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "ApplicationPlaneComponent"}:
        from .component import ApplicationPlaneComponent, COMPONENT

        return {"COMPONENT": COMPONENT, "ApplicationPlaneComponent": ApplicationPlaneComponent}[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "APPLICATION_SCHEMA",
    "CATALOGUE_SCHEMA",
    "REVISION_SCHEMA",
    "ResolutionError",
    "ValidationError",
    "UnsatisfiedRequirement",
    "IncompatibleInterface",
    "RevisionIntegrityError",
    "resolve",
    "resolve_document",
    "verify_revision",
    "PlaneError",
    "to_public",
    "RequestContext",
    "build_contract",
    "COMPONENT",
    "ApplicationPlaneComponent",
]
