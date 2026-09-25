"""MC-010 -- cryptographic randomness provider.

Binds to the OS CSPRNG (``os.urandom`` -> getrandom(2)/BCryptGenRandom).
Requests are bounded per call and rate-limited per instance (token bucket over
an injected monotonic clock).  Failure of the source maps to
ENTROPY_UNAVAILABLE -- it never falls back to a weaker generator.  A seeded
deterministic provider exists for tests/replay but raises unless the profile
is non-production and the caller passes an explicit acknowledgement token.
"""
from __future__ import annotations

import hashlib
import os
import threading
from typing import Callable

from .errors import ErrorCode, Inv13Error

MAX_REQUEST = 1 << 16
INSECURE_ACK = "I-UNDERSTAND-THIS-IS-NOT-RANDOM"


class CsprngProvider:
    def __init__(self, *, bytes_per_sec: int = 1 << 20, clock: Callable[[], float] | None = None,
                 source: Callable[[int], bytes] = os.urandom) -> None:
        import time
        self._src, self._rate = source, bytes_per_sec
        self._clock = clock or time.monotonic
        self._tokens, self._t = float(bytes_per_sec), self._clock()
        self._lock = threading.Lock()

    def get(self, n: int) -> bytes:
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise Inv13Error(ErrorCode.INVALID_ARGUMENT)
        if n > MAX_REQUEST:
            raise Inv13Error(ErrorCode.TOO_LONG, "random request")
        with self._lock:
            now = self._clock()
            self._tokens = min(float(self._rate), self._tokens + (now - self._t) * self._rate)
            self._t = now
            if n > self._tokens:
                raise Inv13Error(ErrorCode.BACKPRESSURE, "entropy rate")
            self._tokens -= n
        try:
            out = self._src(n)
        except (OSError, NotImplementedError) as exc:
            raise Inv13Error(ErrorCode.ENTROPY_UNAVAILABLE, repr(exc)) from None
        if not isinstance(out, bytes) or len(out) != n:
            raise Inv13Error(ErrorCode.ENTROPY_UNAVAILABLE, "short read")
        return out


class DeterministicProvider:
    """SHA-256 counter-mode stream. NEVER for production."""

    def __init__(self, seed: bytes, *, profile: str, ack: str) -> None:
        if profile == "production" or ack != INSECURE_ACK:
            raise Inv13Error(ErrorCode.POLICY_DENIED, "deterministic randomness not permitted")
        self._seed, self._ctr = seed, 0

    def get(self, n: int) -> bytes:
        out = bytearray()
        while len(out) < n:
            out += hashlib.sha256(self._seed + self._ctr.to_bytes(8, "big")).digest()
            self._ctr += 1
        return bytes(out[:n])
