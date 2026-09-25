"""Cross-process, fenced, lease-based claim providers for INV-23."""

import sys

from .base import (
    Claim,
    ClaimConflict,
    ClaimProvider,
    FencingRejected,
    LeaseLost,
    OwnershipCorrupt,
    OwnershipError,
    StaleToken,
)
from .memory import MemoryClaimProvider


def default_provider(**kw):
    if sys.platform == "win32":
        from .windows import WindowsClaimProvider

        return WindowsClaimProvider(**kw)
    from .posix import PosixClaimProvider

    return PosixClaimProvider(**kw)


__all__ = [
    "Claim",
    "ClaimConflict",
    "ClaimProvider",
    "FencingRejected",
    "LeaseLost",
    "OwnershipCorrupt",
    "OwnershipError",
    "StaleToken",
    "MemoryClaimProvider",
    "default_provider",
]
