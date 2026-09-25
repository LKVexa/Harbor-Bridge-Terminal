"""INV-71 - Heavy agent sandbox."""
from __future__ import annotations

__version__ = "4.3.0"

from .sandbox import (
    BASE_DIGEST,
    EgressDenied,
    LimitExceeded,
    Session,
    SessionClosed,
    SessionState,
    new_session,
)


def __getattr__(name: str):
    """Lazily load pk_core integration so the reference model works standalone."""
    if name in {"COMPONENT", "HeavyAgentSandboxComponent"}:
        from .component import COMPONENT, HeavyAgentSandboxComponent
        return COMPONENT if name == "COMPONENT" else HeavyAgentSandboxComponent
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build
        return {"ELEMENT_ID": ELEMENT_ID, "ELEMENT_NAME": ELEMENT_NAME, "build_contract": build}[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "BASE_DIGEST",
    "EgressDenied",
    "LimitExceeded",
    "Session",
    "SessionClosed",
    "SessionState",
    "new_session",
    "COMPONENT",
    "HeavyAgentSandboxComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]
