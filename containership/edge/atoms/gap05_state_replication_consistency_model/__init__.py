"""GAP-05 - State replication/consistency model."""
from __future__ import annotations

__version__ = "4.3.0"

from .model import (
    InvalidWrite,
    ReplicatedKey,
    UnknownReplica,
    VectorEquivocationError,
    Write,
    concurrent,
    dominates,
)


def __getattr__(name: str):
    """Load pk_core-backed integration symbols only when they are requested.

    Keeping the causal model importable without ``pk_core`` allows isolated unit tests
    and embedding in tools that only need the state-machine primitives.
    """
    if name in {"COMPONENT", "StateReplicationConsistencyModelComponent"}:
        from .component import COMPONENT, StateReplicationConsistencyModelComponent
        return {
            "COMPONENT": COMPONENT,
            "StateReplicationConsistencyModelComponent": StateReplicationConsistencyModelComponent,
        }[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build
        return {
            "ELEMENT_ID": ELEMENT_ID,
            "ELEMENT_NAME": ELEMENT_NAME,
            "build_contract": build,
        }[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "Write",
    "ReplicatedKey",
    "UnknownReplica",
    "InvalidWrite",
    "VectorEquivocationError",
    "dominates",
    "concurrent",
    "COMPONENT",
    "StateReplicationConsistencyModelComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]
