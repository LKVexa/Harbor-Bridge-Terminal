"""Production claim path (MC-04/05): fresh probe + policy + cross-process fenced claim.

Returns PK_VIRT_CLAIM/2.  The legacy in-process ``VirtPrimitive.claim`` (PK_VIRT_CLAIM/1)
remains for the pk_core reference assessment only.
"""

from __future__ import annotations

from typing import Optional

from .backends.base import USABLE
from .model import PrimitiveUnavailable
from .ownership import Claim, ClaimProvider, default_provider
from .probe import Prober
from .schema import validate_claim_response


class ClaimManager:
    def __init__(self, prober: Optional[Prober] = None, provider: Optional[ClaimProvider] = None) -> None:
        self.prober = prober or Prober()
        self.provider = provider or default_provider(telemetry=self.prober.telemetry)

    def claim(
        self, holder: str, *, max_nesting: int = 1, resource: str = "hw-virt", lease_s: float = 30.0, allow_unknown_depth: bool = False
    ) -> tuple:
        """Return ``(public_response, claim)``; the ``Claim`` carries the secret token."""
        if type(max_nesting) is not int or max_nesting < 0:
            raise ValueError("max_nesting must be a non-negative int")
        # TOCTOU: always a fresh probe immediately before acquisition.
        res = self.prober.probe(use_cache=False)
        if res.state != USABLE:
            raise PrimitiveUnavailable(f"{res.host}: primitive is {res.state} ({res.reason})")
        depth = res.nesting_depth
        if depth is None and not allow_unknown_depth:
            raise PrimitiveUnavailable(f"{res.host}: nesting depth unknown; policy requires a known depth")
        if depth is not None and depth > max_nesting:
            raise PrimitiveUnavailable(f"{res.host}: nesting depth {depth} exceeds the permitted {max_nesting}")
        c = self.provider.acquire(holder, resource=resource, lease_s=lease_s)
        return self.response(res, c), c

    @staticmethod
    def response(res, c: Claim) -> dict:
        out = {
            "schema": "PK_VIRT_CLAIM/2",
            "host": res.host,
            "resource": c.resource,
            "claim_id": c.claim_id,
            "holder": c.holder,
            "generation": c.generation,
            "acquired_at": round(c.acquired_at, 6),
            "lease_expires_at": round(c.lease_expires_at, 6),
            "nesting_depth": res.nesting_depth,
            "bare_metal": bool(res.bare_metal),
            "provider": c.provider,
            "backend": res.backend,
        }
        validate_claim_response(out)
        return out

    def renew(self, c: Claim) -> Claim:
        return self.provider.renew(c)

    def release(self, c: Claim) -> None:
        self.provider.release(c)

    def fence(self, c: Claim) -> int:
        return self.provider.validate(c)
