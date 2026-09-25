"""Operational controls: quarantine/freeze/emergency disable (20), time
service behaviour (28) and offline/disconnected policy (18).
Freeze registry and time authority adapted from the shop's GAP-09 v5.1.0
``controls.py``.

FreezeRegistry
  scopes ``global`` (kill switch), ``tenant``, ``ref``, ``target``; each
  freeze has reason, actor, optional expiry; state is durable (JSON, atomic
  replace) so a restart cannot silently unfreeze; every change is audited.
  Releasing a freeze someone else set, or overriding the global kill switch,
  needs the privileged ``freeze.override`` capability (checked by the caller
  via ``authz``).  ``check`` raises ``Quarantined`` naming the blocking scope.

TimeAuthority
  wall-clock time comes from a trusted source ``() -> (unix_seconds,
  last_sync_unix)``; elapsed-time decisions (lease renewal, backoff,
  deadlines) use ``time.monotonic``.  The authority refuses (``TimeUntrusted``)
  when the source is unsynchronised for longer than ``max_sync_age``, detects
  clock jumps by comparing wall and monotonic deltas (``max_jump``), and in
  that degraded mode the controller stops mutating (reads/status continue).

OfflinePolicy
  modes: ``fail_closed`` (default -- no reconciliation without a fresh fetch),
  ``read_only`` (report drift, never mutate), ``cache_backed`` (reconcile from
  the last verified cached ref while ``cached_ref_age <= max_cached_ref_age``
  and trust roots are no older than ``max_trust_age``).  On reconnect the
  controller refetches and re-verifies before the next mutation, and a cached
  head that the remote no longer contains (divergence) freezes the ref.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable

from .fsutil import load_json, read_bytes, read_text  # noqa: F401
from .errors import Quarantined, StaleRef, TimeUntrusted

SCOPES = ("global", "tenant", "ref", "target")


class FreezeRegistry:
    def __init__(self, path: str | None = None, *, audit=None, clock=time.time) -> None:
        self.path, self.audit, self.clock = path, audit, clock
        self._lock = threading.Lock()
        self._f: dict[str, dict] = {}
        if path and os.path.exists(path):
            self._f = load_json(path)["freezes"]

    def _persist(self) -> None:
        if not self.path:
            return
        tmp = self.path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump({"schema": "PK_GITOPS_FREEZE/1", "freezes": self._f}, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    def freeze(self, scope: str, name: str, *, reason: str, actor: str, until: float | None = None) -> dict:
        if scope not in SCOPES:
            raise ValueError("unknown freeze scope")
        with self._lock:
            rec = {"scope": scope, "name": name, "reason": reason, "actor": actor, "at": self.clock(),
                   "until": until}
            self._f[f"{scope}:{name}"] = rec
            self._persist()
        if self.audit:
            self.audit.append("freeze.set", rec, actor=actor)
        return rec

    def release(self, scope: str, name: str, *, actor: str, override: bool = False) -> None:
        with self._lock:
            key = f"{scope}:{name}"
            rec = self._f.get(key)
            if rec is None:
                return
            if (rec["actor"] != actor or scope == "global") and not override:
                raise Quarantined("releasing this freeze requires freeze.override", scope=scope)
            del self._f[key]
            self._persist()
        if self.audit:
            self.audit.append("freeze.release", {"scope": scope, "name": name, "override": override}, actor=actor)

    def check(self, *, tenant: str, ref: str, target: str) -> None:
        now = self.clock()
        with self._lock:
            for key in (("global", "*"), ("tenant", tenant), ("ref", ref), ("target", target)):
                rec = self._f.get(f"{key[0]}:{key[1]}")
                if rec and (rec["until"] is None or now < rec["until"]):
                    raise Quarantined("reconciliation frozen", scope=key[0], name=key[1], reason=rec["reason"])

    def active(self) -> list[dict]:
        now = self.clock()
        with self._lock:
            return [r for r in self._f.values() if r["until"] is None or now < r["until"]]


class TimeAuthority:
    def __init__(self, source: Callable[[], tuple[float, float]], *, max_sync_age: float, max_jump: float = 5.0,
                 mono: Callable[[], float] = time.monotonic) -> None:
        self.source, self.max_sync_age, self.max_jump, self.mono = source, max_sync_age, max_jump, mono
        self._last: tuple[float, float] | None = None
        self.degraded_reason: str | None = None

    def now(self) -> float:
        wall, synced = self.source()
        m = self.mono()
        if wall - synced > self.max_sync_age:
            self.degraded_reason = "unsynchronised"
            raise TimeUntrusted("trusted time source unsynchronised", age=round(wall - synced, 3))
        if self._last is not None:
            dw, dm = wall - self._last[0], m - self._last[1]
            if abs(dw - dm) > self.max_jump:
                self._last = (wall, m)
                self.degraded_reason = "clock_jump"
                raise TimeUntrusted("wall clock jumped relative to monotonic clock", jump=round(dw - dm, 3))
        self._last = (wall, m)
        self.degraded_reason = None
        return wall


class OfflinePolicy:
    MODES = ("fail_closed", "read_only", "cache_backed")

    def __init__(self, mode: str, *, max_cached_ref_age: float, max_trust_age: float | None = None) -> None:
        if mode not in self.MODES:
            raise ValueError("unknown offline mode")
        self.mode, self.max_age, self.max_trust_age = mode, max_cached_ref_age, max_trust_age

    def decide(self, *, online: bool, last_fetch_ok: float | None, now: float,
               trust_loaded_at: float | None = None) -> dict:
        """Return {'mutate': bool, 'source': 'remote'|'cache'|None, 'reason': str}."""
        if online:
            return {"mutate": True, "source": "remote", "reason": "online"}
        if self.mode == "fail_closed":
            return {"mutate": False, "source": None, "reason": "offline: fail_closed"}
        if self.mode == "read_only":
            return {"mutate": False, "source": "cache", "reason": "offline: read_only (drift reported, not reverted)"}
        if last_fetch_ok is None or now - last_fetch_ok > self.max_age:
            return {"mutate": False, "source": None, "reason": "offline: cached ref older than limit"}
        if self.max_trust_age is not None and (trust_loaded_at is None or now - trust_loaded_at > self.max_trust_age):
            return {"mutate": False, "source": None, "reason": "offline: trust roots older than limit"}
        return {"mutate": True, "source": "cache", "reason": "offline: cache_backed within limits"}

    @staticmethod
    def reconnect_check(cached_head: str | None, remote_contains: bool) -> None:
        if cached_head and not remote_contains:
            raise StaleRef("cached head diverged from remote after reconnect; ref must be frozen")
