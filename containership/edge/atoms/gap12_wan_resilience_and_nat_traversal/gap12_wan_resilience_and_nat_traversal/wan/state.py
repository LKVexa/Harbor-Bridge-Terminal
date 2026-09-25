"""State, concurrency, persistence and failure containment (G12-E056..E066).

Concurrency model (E056): **lock-based with a single owner per object**.
``PathStore`` is the sole owner of every ``Path``; all mutation goes through
``PathStore.transition`` under one ``RLock`` per peer, which also bumps a
per-peer generation.  Readers get immutable snapshots (``dict`` copies) taken
under the same lock, so a probe completion, timer, route event, disconnect or
config reload can never observe or produce a torn state.  Callbacks run
outside the lock.  ``transition`` is idempotent per ``event_id`` (a bounded
LRU of applied ids) so redelivered/duplicate events are no-ops, and a
compare-and-set on the generation rejects late timers and stale callers.

Persistence (E058): durable = peer list, last strategy, failures, retry_at
converted to *remaining* duration, relay bytes; reconstructable = candidate
cache, quality windows; discarded = in-flight attempts; revalidated = health
(a restored path is ``unknown`` until re-probed — success never survives a
restart as "healthy").  Snapshots are written atomically (temp + fsync +
rename) with a schema version and digest.

Clock (E059/E060): ``Clock`` exposes monotonic() for durations and wall() for
audit only; ``ClockWatch`` detects wall jumps and suspend/resume by comparing
the two and tells the store to revalidate.

Supervision (E061), dependency health (E062), degraded control-plane policy
(E063), quarantine (E064), fencing tokens for stale controllers (E065) and
snapshot schema migration (E066) are here too.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field

from ..path import Partitioned, Path

SNAPSHOT_SCHEMA = 2


class Clock:
    def monotonic(self) -> float:
        return time.monotonic()

    def wall(self) -> float:
        return time.time()


class FakeClock(Clock):
    """Deterministic test clock: advance without sleeping; can simulate jumps/suspend."""

    def __init__(self, mono: float = 1000.0, wall: float = 1_700_000_000.0):
        self.m, self.w = mono, wall

    def monotonic(self):
        return self.m

    def wall(self):
        return self.w

    def advance(self, s: float):
        self.m += s
        self.w += s

    def jump_wall(self, s: float):
        self.w += s

    def suspend(self, s: float):
        # CLOCK_MONOTONIC does not advance across suspend on Linux; wall does
        self.w += s


@dataclass
class ClockWatch:
    tolerance: float = 2.0
    last_mono: float | None = None
    last_wall: float | None = None

    def check(self, clock: Clock) -> str:
        m, w = clock.monotonic(), clock.wall()
        verdict = "ok"
        if self.last_mono is not None:
            dm, dw = m - self.last_mono, w - self.last_wall
            if dm < 0:
                verdict = "monotonic_regression"
            elif dw - dm > self.tolerance:
                verdict = "suspend_or_forward_jump"
            elif dm - dw > self.tolerance:
                verdict = "wall_backward_jump"
        self.last_mono, self.last_wall = m, w
        return verdict


class StaleGeneration(RuntimeError):
    pass


class PathStore:
    def __init__(self, clock: Clock | None = None, *, max_peers: int = 10000, event_memory: int = 4096):
        self.clock = clock or Clock()
        self.max_peers = max_peers
        self._paths: dict[str, Path] = {}
        self._gen: dict[str, int] = {}
        self._locks: dict[str, threading.RLock] = {}
        self._global = threading.Lock()
        self._applied: OrderedDict[str, None] = OrderedDict()
        self._event_memory = event_memory
        self.revalidate: set[str] = set()

    def _lock(self, peer: str) -> threading.RLock:
        with self._global:
            if peer not in self._locks:
                if len(self._paths) >= self.max_peers:
                    raise OverflowError("peer ceiling reached")
                self._locks[peer] = threading.RLock()
                self._paths[peer] = Path(peer)
                self._gen[peer] = 0
            return self._locks[peer]

    def snapshot(self, peer: str) -> dict:
        with self._lock(peer):
            st = self._paths[peer].state(self.clock.monotonic())
            st["generation"] = self._gen[peer]
            st["revalidate"] = peer in self.revalidate
            return st

    def transition(self, peer: str, fn, *, event_id: str | None = None, expect_generation: int | None = None):
        """Apply ``fn(path, now)`` atomically.  Duplicate event ids are no-ops;
        a stale expected generation is rejected."""
        lock = self._lock(peer)
        with lock:
            if event_id is not None:
                with self._global:
                    if event_id in self._applied:
                        return "duplicate", self._gen[peer]
            if expect_generation is not None and expect_generation != self._gen[peer]:
                raise StaleGeneration(f"{peer}: expected {expect_generation}, at {self._gen[peer]}")
            path = self._paths[peer]
            backup = copy.copy(path)                       # attempts records are never mutated in place,
            backup.attempts = list(path.attempts)          # so a shallow copy + list copy is a full backup
            try:
                result = fn(path, self.clock.monotonic())
            except Partitioned as exc:
                result = exc                                   # a legitimate state change, keep it
            except Exception:
                self._paths[peer] = backup                     # all-or-nothing
                raise
            self._gen[peer] += 1
            self.revalidate.discard(peer)
            if event_id is not None:
                with self._global:
                    self._applied[event_id] = None
                    while len(self._applied) > self._event_memory:
                        self._applied.popitem(last=False)
            return result, self._gen[peer]

    def peers(self) -> list[str]:
        with self._global:
            return list(self._paths)

    # --- persistence ------------------------------------------------------------------------
    def dump(self) -> dict:
        now = self.clock.monotonic()
        out = {"schema": SNAPSHOT_SCHEMA, "written_wall": self.clock.wall(), "peers": {}}
        for peer in self.peers():
            with self._lock(peer):
                p = self._paths[peer]
                out["peers"][peer] = {"strategy": p.strategy, "failures": p.failures,
                                      "retry_in": None if p.retry_at is None else max(0.0, p.retry_at - now),
                                      "relay_bytes": p.relay_bytes, "partitioned": p.partitioned,
                                      "generation": self._gen[peer]}
        body = json.dumps(out["peers"], sort_keys=True)
        out["digest"] = hashlib.sha256(body.encode()).hexdigest()
        return out

    def save(self, path: str) -> str:
        data = json.dumps(self.dump(), sort_keys=True, indent=1)
        d = os.path.dirname(os.path.abspath(path))
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".g12-state-")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
        return hashlib.sha256(data.encode()).hexdigest()

    @classmethod
    def restore(cls, path: str, clock: Clock | None = None) -> "PathStore":
        with open(path) as fh:
            raw = json.load(fh)
        raw = migrate(raw)
        body = json.dumps(raw["peers"], sort_keys=True)
        if hashlib.sha256(body.encode()).hexdigest() != raw.get("digest"):
            raise ValueError("state snapshot digest mismatch")
        store = cls(clock)
        now = store.clock.monotonic()
        for peer, d in raw["peers"].items():
            store._lock(peer)
            p = store._paths[peer]
            p.failures = int(d["failures"])
            p.retry_at = None if d["retry_in"] is None else now + float(d["retry_in"])
            p.relay_bytes = int(d["relay_bytes"])
            p.partitioned = bool(d.get("partitioned", False))
            p.strategy = None                   # revalidated: no path is healthy until re-probed
            p.last_success = None
            store.revalidate.add(peer)
        return store


def migrate(raw: dict) -> dict:
    """Snapshot schema migration; refuse unknown future majors."""
    v = raw.get("schema", 1)
    if v > SNAPSHOT_SCHEMA:
        raise ValueError(f"snapshot schema {v} is newer than supported {SNAPSHOT_SCHEMA}")
    if v == 1:
        # v1 stored absolute retry_at (monotonic of a dead process) - meaningless after restart.
        peers = {}
        for peer, d in raw["peers"].items():
            peers[peer] = {"strategy": d.get("strategy"), "failures": d.get("failures", 0), "retry_in": None,
                           "relay_bytes": d.get("relay_bytes", 0), "partitioned": d.get("partitioned", False),
                           "generation": 0}
        raw = {"schema": 2, "written_wall": raw.get("written_wall"), "peers": peers}
        raw["digest"] = hashlib.sha256(json.dumps(peers, sort_keys=True).encode()).hexdigest()
    return raw


# --- E061 supervision --------------------------------------------------------------------------------

@dataclass
class RestartPolicy:
    max_restarts: int = 5
    window: float = 60.0
    base_backoff: float = 0.5
    max_backoff: float = 30.0
    history: list[float] = field(default_factory=list)

    def on_exit(self, now: float) -> tuple[str, float]:
        self.history = [t for t in self.history if now - t <= self.window]
        if len(self.history) >= self.max_restarts:
            return "give_up", 0.0                         # escalate instead of crash-looping
        delay = min(self.max_backoff, self.base_backoff * (2 ** len(self.history)))
        self.history.append(now)
        return "restart", delay


class Supervisor:
    """Runs a worker callable in a thread and restarts it per ``RestartPolicy``."""

    def __init__(self, worker, policy: RestartPolicy | None = None, clock=time.monotonic, sleep=time.sleep):
        self.worker, self.policy, self.clock, self.sleep = worker, policy or RestartPolicy(), clock, sleep
        self.starts = 0
        self.gave_up = False
        self._stop = threading.Event()

    def run(self):
        while not self._stop.is_set():
            self.starts += 1
            try:
                self.worker(self._stop)
                if self._stop.is_set():
                    return
            except Exception:
                pass
            action, delay = self.policy.on_exit(self.clock())
            if action == "give_up":
                self.gave_up = True
                return
            self.sleep(delay)

    def stop(self):
        self._stop.set()


# --- E062/E063 dependency health and degraded policy -----------------------------------------------------

DEPENDENCIES = ("stun", "turn", "dns", "identity", "keys", "observability", "control_plane")


@dataclass
class DependencyHealth:
    stale_after: float = 60.0
    status: dict[str, tuple[str, float]] = field(default_factory=dict)

    def report(self, dep: str, ok: bool, now: float) -> None:
        if dep not in DEPENDENCIES:
            raise KeyError(dep)
        self.status[dep] = ("up" if ok else "down", now)

    def state(self, dep: str, now: float) -> str:
        s = self.status.get(dep)
        if s is None:
            return "unknown"
        return "stale" if now - s[1] > self.stale_after else s[0]

    def view(self, now: float) -> dict[str, str]:
        return {d: self.state(d, now) for d in DEPENDENCIES}


def degraded_policy(view: dict[str, str]) -> dict:
    """Which operations continue when dependencies are down/stale/unknown."""
    cp = view.get("control_plane") == "up"
    ident = view.get("identity") == "up"
    keys = view.get("keys") == "up"
    return {
        "existing_trusted_sessions": "continue_until_trust_expiry" if not ident else "continue",
        "new_sessions": "allowed" if (ident and keys) else "refused",
        "new_relay_allocations": "allowed" if view.get("turn") == "up" and ident else "refused",
        "config_changes": "allowed" if cp else "frozen_last_known_good",
        "path_escalation": "allowed" if ident else "existing_only",
        "observability_outage": "buffer_bounded_and_continue" if view.get("observability") != "up" else "normal",
    }


# --- E064 quarantine ---------------------------------------------------------------------------------------

@dataclass
class Quarantine:
    entries: dict[str, tuple[float | None, str, str]] = field(default_factory=dict)   # key -> (until, reason, actor)

    def add(self, key: str, *, reason: str, actor: str, until: float | None = None) -> None:
        self.entries[key] = (until, reason, actor)

    def release(self, key: str) -> None:
        self.entries.pop(key, None)

    def blocked(self, key: str, now: float) -> bool:
        e = self.entries.get(key)
        if e is None:
            return False
        if e[0] is not None and now >= e[0]:
            del self.entries[key]
            return False
        return True


# --- E065 fencing -------------------------------------------------------------------------------------------

class FencedLease:
    """Monotonic fencing token per controller lease; writes carrying an older token are refused."""

    def __init__(self):
        self.token = 0
        self.holder: str | None = None
        self.expires = 0.0
        self._lock = threading.Lock()

    def acquire(self, who: str, now: float, ttl: float = 10.0) -> int | None:
        with self._lock:
            if self.holder not in (None, who) and now < self.expires:
                return None
            self.token += 1
            self.holder, self.expires = who, now + ttl
            return self.token

    def check(self, token: int) -> bool:
        with self._lock:
            return token == self.token
