"""INV-40 production-hardening layer (v4.3.0).

Stdlib-only modules built on top of the unchanged v4.2.0 reference runtime
(``runtime.py``).  Nothing here imports ``pk_core``.
"""
from __future__ import annotations

__all__ = [
    "errors", "schema", "config", "identity", "audit", "integrity", "provider",
    "journal", "resilience", "fencing", "telemetry", "service", "compat", "gate",
]
PROTOCOL_VERSIONS = {"PK_FULL_VM": (1, 1), "PK_FULL_VM_BOOT": (1, 1),
                     "PK_FULL_VM_STATE": (1, 1), "PK_FULL_VM_ERROR": (1, 1)}
