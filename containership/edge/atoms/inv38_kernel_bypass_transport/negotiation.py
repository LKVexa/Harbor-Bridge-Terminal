"""INV-38-C027 — Protocol/feature version negotiation with downgrade protection."""
from __future__ import annotations

SUPPORTED = {1, 2}          # supported schema major versions
MIN_SECURITY_VERSION = 1    # below this, sealing/auth cannot be guaranteed


class NegotiationError(ValueError):
    code = "PK_BYPASS_INCOMPATIBLE_VERSION"


class DowngradeAttack(ValueError):
    code = "PK_BYPASS_DOWNGRADE_REJECTED"


def negotiate(local: set[int], peer: set[int], *, require_security: bool = True) -> int:
    common = (local & peer) & SUPPORTED
    if not common:
        raise NegotiationError(f"no common supported version (local={sorted(local)}, peer={sorted(peer)})")
    chosen = max(common)
    if require_security and chosen < MIN_SECURITY_VERSION:
        raise DowngradeAttack("negotiated below minimum security version")
    return chosen


def negotiate_features(local: set[str], peer: set[str], *, mandatory: set[str] | None = None) -> set[str]:
    agreed = local & peer
    mandatory = mandatory or set()
    missing = mandatory - agreed
    if missing:
        raise NegotiationError(f"peer lacks mandatory features {sorted(missing)}")
    return agreed
