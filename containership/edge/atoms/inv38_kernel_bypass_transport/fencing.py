"""INV-38-C058 — Ownership fencing via lease epochs (single-writer)."""
from __future__ import annotations
from dataclasses import dataclass

class FencedOut(RuntimeError):
    code = "PK_BYPASS_FENCED"

@dataclass
class Lease:
    owner: str
    epoch: int
    expires_at: float

@dataclass
class OwnershipRegistry:
    current: Lease | None = None
    def acquire(self, owner: str, now: float, ttl: float) -> Lease:
        if self.current and self.current.expires_at > now and self.current.owner != owner:
            raise FencedOut(f"held by {self.current.owner}")
        epoch = (self.current.epoch + 1) if self.current else 1
        self.current = Lease(owner, epoch, now + ttl)
        return self.current
    def guard(self, epoch: int) -> None:
        """Reject stale-epoch mutation even from a former owner (C058-T02)."""
        if not self.current or epoch != self.current.epoch:
            raise FencedOut(f"stale epoch {epoch}")
