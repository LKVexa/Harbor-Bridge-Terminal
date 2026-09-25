"""M19/M20 - ownership leases with fencing tokens, quarantine/freeze, and
durable restart/replay of the small amount of mutable state INV-61 keeps.

INV-61 is stateless with respect to *application* data (component logic is
not owned).  The protocol layer itself keeps four pieces of mutable state,
inventoried in docs/STATE_INVENTORY.md:

  1. idempotency results (must survive restart to prevent duplicate execution)
  2. fencing epoch (must be monotonic across restarts)
  3. audit chain head (anchors truncation detection)
  4. emergency-disable flag (must persist so a restart cannot silently re-enable)

``StateStore`` checkpoints these atomically (write temp + fsync + rename) with
an embedded SHA-256; a corrupt checkpoint is refused, never half-loaded.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable

STATE_FORMAT = "inv61-state/1"


class FenceError(Exception):
    pass


@dataclass
class Lease:
    holder: str
    epoch: int
    expires: float


class LeaseAuthority:
    """Single-authority lease table with strictly increasing fencing epochs.

    In production this role is delegated to a linearizable store (see
    ADR-0003); this reference authority defines and tests the contract a
    backing store must satisfy.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic, epoch: int = 0) -> None:
        self.clock, self._epoch = clock, epoch
        self._leases: dict[str, Lease] = {}
        self._lock = threading.Lock()

    @property
    def epoch(self) -> int:
        return self._epoch

    def acquire(self, resource: str, holder: str, ttl_s: float) -> Lease | None:
        with self._lock:
            cur = self._leases.get(resource)
            now = self.clock()
            if cur is not None and cur.expires > now and cur.holder != holder:
                return None  # someone else owns it: no split-brain
            if cur is not None and cur.holder == holder and cur.expires > now:
                cur.expires = now + ttl_s
                return cur
            self._epoch += 1
            lease = self._leases[resource] = Lease(holder, self._epoch, now + ttl_s)
            return lease

    def release(self, resource: str, holder: str) -> None:
        with self._lock:
            cur = self._leases.get(resource)
            if cur and cur.holder == holder:
                del self._leases[resource]


class FencedResource:
    """Rejects any write carrying an epoch lower than the highest seen."""

    def __init__(self, highest: int = 0) -> None:
        self.highest = highest
        self._lock = threading.Lock()

    def check(self, epoch: int) -> None:
        with self._lock:
            if epoch < self.highest:
                raise FenceError(f"stale epoch {epoch} < {self.highest}")
            self.highest = epoch


class StateStore:
    def __init__(self, path: str | os.PathLike) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def save(self, state: dict[str, Any]) -> str:
        body = json.dumps(state, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(body.encode()).hexdigest()
        doc = json.dumps({"format": STATE_FORMAT, "sha256": digest, "state": json.loads(body)},
                         sort_keys=True, separators=(",", ":"))
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with self._lock:
            with open(tmp, "w", encoding="utf-8") as fh:
                fh.write(doc)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
        return digest

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        doc = json.loads(self.path.read_text(encoding="utf-8"))
        if doc.get("format") != STATE_FORMAT:
            raise ValueError("unsupported state format")
        body = json.dumps(doc["state"], sort_keys=True, separators=(",", ":"))
        if hashlib.sha256(body.encode()).hexdigest() != doc.get("sha256"):
            raise ValueError("state checkpoint digest mismatch")
        return doc["state"]
