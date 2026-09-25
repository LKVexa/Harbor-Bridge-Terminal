"""Component 27 - clock-source/time-service strategy.

Freshness decisions use a TrustedClock that combines a monotonic source with a
wall-clock source synchronised to an (authenticated) time service. If the time
service is lost for longer than ``max_sync_age`` or a wall-clock jump larger
than ``max_jump`` is detected, the clock reports itself untrusted and every
freshness decision fails closed.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class TrustedClock:
    wall: Callable[[], float] = time.time
    mono: Callable[[], float] = time.monotonic
    max_sync_age: float = 300.0
    max_jump: float = 2.0
    _anchor_wall: float | None = field(default=None, init=False)
    _anchor_mono: float | None = field(default=None, init=False)
    _last_sync_mono: float | None = field(default=None, init=False)
    jump_detected: bool = field(default=False, init=False)

    def sync(self, authenticated: bool = True) -> None:
        """Record a successful (authenticated) time-service sync."""
        if not authenticated:
            return
        self._anchor_wall = self.wall()
        self._anchor_mono = self.mono()
        self._last_sync_mono = self._anchor_mono
        self.jump_detected = False

    def now(self) -> float:
        """Wall time derived from the monotonic anchor (immune to wall jumps)."""
        if self._anchor_wall is None:
            return self.wall()
        expected = self._anchor_wall + (self.mono() - self._anchor_mono)
        if abs(self.wall() - expected) > self.max_jump:
            self.jump_detected = True
        return expected

    def trusted(self) -> bool:
        if self._last_sync_mono is None:
            return False
        self.now()
        if self.jump_detected:
            return False
        return (self.mono() - self._last_sync_mono) <= self.max_sync_age

    def status(self) -> dict:
        synced = self._last_sync_mono is not None
        return {
            "trusted": self.trusted(),
            "synced": synced,
            "sync_age_s": None if not synced else self.mono() - self._last_sync_mono,
            "jump_detected": self.jump_detected,
        }


class ManualClock:
    """Deterministic clock for tests: wall and monotonic can be moved separately."""

    def __init__(self, t: float = 1000.0):
        self.w = t
        self.m = 0.0

    def advance(self, dt: float) -> None:
        self.w += dt
        self.m += dt

    def jump_wall(self, dt: float) -> None:
        self.w += dt

    def wall(self) -> float:
        return self.w

    def mono(self) -> float:
        return self.m
