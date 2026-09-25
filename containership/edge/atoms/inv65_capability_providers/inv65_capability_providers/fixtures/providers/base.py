"""Backend adapter seam (M38).  Fixtures only -- INV-65 does not implement backends."""
from __future__ import annotations

from typing import Protocol


class Backend(Protocol):
    operations: tuple[str, ...]

    def invoke(self, op: str, config: dict, secret, payload: dict) -> dict: ...

    def healthy(self) -> bool: ...


class FaultyMixin:
    """Fault-injection knobs shared by fixture backends (M26)."""
    fail_next = 0
    latency_s = 0.0
    up = True

    def _faults(self):
        import time
        if self.latency_s:
            time.sleep(self.latency_s)
        if not self.up:
            raise ConnectionError("backend down")
        if self.fail_next:
            self.fail_next -= 1
            raise ConnectionError("injected failure")

    def healthy(self) -> bool:
        return self.up
