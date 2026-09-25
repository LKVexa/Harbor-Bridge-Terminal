"""INV-36 - Control transport.

The cryptographic transport can be imported and tested without the external
``pk_core`` estate package.  Component/gate integration is loaded lazily.
"""
from __future__ import annotations

from .transport import (
    ALGORITHM_AES_256_GCM_SIV,
    FRAME_VERSION,
    MAX_FRAME,
    MAX_WIRE_FRAME,
    AuthFailure,
    FrameFormatError,
    FrameTooLarge,
    OutOfOrder,
    Relay,
    Replay,
    SequenceExhausted,
    Session,
    SessionClosed,
    new_session_id,
)

__version__ = "5.1.0"
ELEMENT_ID = "INV-36"
ELEMENT_NAME = "Control transport"


def build_contract():
    from .contract import build
    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "ControlTransportComponent"}:
        from .component import COMPONENT, ControlTransportComponent
        return {"COMPONENT": COMPONENT, "ControlTransportComponent": ControlTransportComponent}[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "COMPONENT",
    "ControlTransportComponent",
    "Session",
    "Relay",
    "AuthFailure",
    "Replay",
    "OutOfOrder",
    "FrameTooLarge",
    "FrameFormatError",
    "SequenceExhausted",
    "SessionClosed",
    "new_session_id",
    "FRAME_VERSION",
    "ALGORITHM_AES_256_GCM_SIV",
    "MAX_FRAME",
    "MAX_WIRE_FRAME",
]
