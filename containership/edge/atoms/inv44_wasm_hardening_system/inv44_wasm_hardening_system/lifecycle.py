"""PK_WASM_INSTANCE/1 lifecycle states and legal transitions (C015, C025).

Also provides the bounded-retry helper (C053) used only for operations whose
error code is marked retryable in ``errors.CODES``; terminal failures are
never retried.
"""
from __future__ import annotations

import random
import time
from typing import Callable, Final, TypeVar

from .errors import CODES, HardeningError

STATES: Final[tuple[str, ...]] = ("requested", "admitted", "running", "trapped", "terminated", "refused")
TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    "requested": frozenset({"admitted", "refused"}),
    "admitted": frozenset({"running", "terminated"}),
    "running": frozenset({"trapped", "terminated"}),
    "trapped": frozenset({"terminated"}),
    "terminated": frozenset(),
    "refused": frozenset(),
}


def check_transition(src: str, dst: str) -> None:
    if src not in TRANSITIONS or dst not in TRANSITIONS[src]:
        raise HardeningError(f"illegal lifecycle transition {src} -> {dst}", code="WH-INVALID-ARGUMENT")


T = TypeVar("T")


def retry(op: Callable[[], T], *, attempts: int = 4, base_s: float = 0.05, cap_s: float = 1.0,
          sleep: Callable[[float], None] = time.sleep, rng: random.Random | None = None) -> T:
    """Full-jitter exponential backoff, only for retryable structured errors."""
    if not 1 <= attempts <= 10:
        raise ValueError("attempts must be 1..10")
    rng = rng or random.Random()
    for i in range(attempts):
        try:
            return op()
        except HardeningError as exc:
            if not CODES[exc.code].retryable or i == attempts - 1:
                raise
            sleep(rng.uniform(0, min(cap_s, base_s * (2 ** i))))
    raise AssertionError("unreachable")
