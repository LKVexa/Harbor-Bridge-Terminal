"""PLN-05 - Elasticity plane.

The runtime (controller, boundary codec, IAM, configuration, state/coordination,
reliability, telemetry, explain, emergency controls) is stdlib-only and imports
without the ``pk_core`` framework.  The framework adapter (``component``) and
the ``pk_core`` contract object (``contract``) are loaded lazily on first
access, so a missing framework is reported where it is needed instead of
breaking the whole package.
"""

__version__ = "4.2.0"

from .controller import ElasticityController, Limits  # noqa: E402
from .spec import ELEMENT_ID, ELEMENT_NAME  # noqa: E402

__all__ = ["__version__", "COMPONENT", "ElasticityPlaneComponent", "ElasticityController",
           "Limits", "ELEMENT_ID", "ELEMENT_NAME", "build_contract", "ElasticityPlane"]


def __getattr__(name):
    if name in ("COMPONENT", "ElasticityPlaneComponent"):
        from . import component
        return getattr(component, name)
    if name == "build_contract":
        from .contract import build
        return build
    if name == "ElasticityPlane":
        from .plane import ElasticityPlane
        return ElasticityPlane
    raise AttributeError(name)
