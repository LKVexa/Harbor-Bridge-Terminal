"""INV-62 - Edge topology.

The core topology model is importable without the optional external ``pk_core``
conformance framework.  ``COMPONENT`` and ``build_contract`` are loaded lazily.
"""
from __future__ import annotations

from .metadata import ELEMENT_ID, ELEMENT_NAME
from .topology import (
    CapacityExceeded,
    Link,
    NoCoordinatorCandidate,
    Node,
    Topology,
    TopologyError,
    TopologyLimits,
    UnknownNode,
    UnknownSite,
)

__version__ = "4.3.0"


def build_contract():
    from .contract import build

    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "EdgeTopologyComponent"}:
        from .component import COMPONENT, EdgeTopologyComponent

        return {"COMPONENT": COMPONENT, "EdgeTopologyComponent": EdgeTopologyComponent}[name]
    raise AttributeError(name)


__all__ = [
    "COMPONENT",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "CapacityExceeded",
    "EdgeTopologyComponent",
    "Link",
    "NoCoordinatorCandidate",
    "Node",
    "Topology",
    "TopologyError",
    "TopologyLimits",
    "UnknownNode",
    "UnknownSite",
    "__version__",
    "build_contract",
]
