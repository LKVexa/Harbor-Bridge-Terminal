"""INV-21 - Local service chaining (master-applied component).

The runtime (``chain``, ``context``, ``policy`` ...) is stdlib-only. The pk_core
component adapter (``COMPONENT``) and contract are exported only when pk_core is
importable; the conformance gate treats its absence as a FAILURE, never a skip.
"""

__version__ = "4.3.0"

from .chain import Chainer, Hop  # noqa: E402
from .context import CallContext, CancelToken, Deadline, IdentityVerifier, Principal  # noqa: E402
from .residency import Placement, Residency  # noqa: E402
from . import errors  # noqa: E402

try:  # pk_core adapter is optional at import time, mandatory at the release gate
    from .component import COMPONENT, LocalServiceChainingComponent  # noqa: E402
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract  # noqa: E402
    PK_CORE_AVAILABLE = True
except ModuleNotFoundError as _exc:  # pragma: no cover - depends on environment
    if _exc.name is None or not _exc.name.startswith("pk_core"):
        raise
    COMPONENT = LocalServiceChainingComponent = build_contract = None
    ELEMENT_ID, ELEMENT_NAME = "INV-21", "Local service chaining"
    PK_CORE_AVAILABLE = False

__all__ = ["__version__", "COMPONENT", "LocalServiceChainingComponent", "ELEMENT_ID", "ELEMENT_NAME",
           "build_contract", "Chainer", "Hop", "CallContext", "CancelToken", "Deadline",
           "IdentityVerifier", "Principal", "Placement", "Residency", "errors", "PK_CORE_AVAILABLE"]
