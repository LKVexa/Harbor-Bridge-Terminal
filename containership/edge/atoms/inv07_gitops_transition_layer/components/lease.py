"""Leader election / duplicate-controller protection (component 09).

``FileLease`` is a compare-and-swap lease over a shared directory (one per
tenant/site partition).  Each successful acquisition or takeover increments a
monotonically increasing **epoch** which is the fencing token.  Rules:

* acquire succeeds if the lease is free, expired, or already ours;
* a live lease held by another node is never stolen (``NotLeader``);
* renew succeeds only for the current holder *and* epoch -- a paused leader
  that wakes after takeover gets ``FencedOff`` and must stop;
* the read-modify-write is serialized by an ``O_EXCL`` lock file with a stale
  lock timeout, so two contenders cannot both win;
* every mutation of a target carries the epoch, and ``FenceGate`` (held by the
  target side) rejects any epoch lower than the highest it has seen -- this is
  what makes split-brain harmless even if two nodes believe they lead.

Lease expiry uses the controller's trusted clock (``timeauth``); ``ttl`` must
exceed the maximum tolerated clock skew between nodes (documented in
docs/ADR-001).  A shared filesystem with atomic rename and O_EXCL is required;
a Kubernetes ``coordination.k8s.io/Lease`` adapter is the production
multi-node backend and is BLOCKED without a cluster.
"""
from __future__ import annotations

import json
import os
import threading
import time
from typing import Callable

from .fsutil import load_json, read_bytes, read_text  # noqa: F401
from .errors import FencedOff, NotLeader


class FileLease:
    def __init__(self, directory: str, name: str, *, node: str, ttl: float,
                 clock: Callable[[], float] = time.time, lock_timeout: float = 10.0) -> None:
        os.makedirs(directory, exist_ok=True)
        self.path = os.path.join(directory, f"{name}.lease.json")
        self.lock = self.path + ".lock"
        self.node, self.ttl, self.clock, self.lock_timeout = node, ttl, clock, lock_timeout
        self.epoch: int | None = None
        self._tl = threading.Lock()

    def _read(self) -> dict:
        try:
            return load_json(self.path)
        except FileNotFoundError:
            return {"holder": None, "epoch": 0, "expires": 0}

    def _write(self, doc: dict) -> None:
        tmp = f"{self.path}.{self.node}.tmp"
        with open(tmp, "w") as fh:
            json.dump(doc, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    def _cas(self, fn):
        deadline = time.monotonic() + self.lock_timeout
        while True:
            try:
                fd = os.open(self.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, self.node.encode())
                os.close(fd)
                break
            except FileExistsError:
                try:
                    if time.time() - os.path.getmtime(self.lock) > self.lock_timeout:
                        os.unlink(self.lock)  # stale lock from a crashed contender
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() > deadline:
                    raise NotLeader("lease lock busy") from None
                time.sleep(0.005)
        try:
            return fn(self._read())
        finally:
            try:
                os.unlink(self.lock)
            except FileNotFoundError:
                pass

    def acquire(self) -> int:
        with self._tl:
            def f(cur):
                now = self.clock()
                if cur["holder"] not in (None, self.node) and cur["expires"] > now:
                    raise NotLeader("lease held by another node", holder=cur["holder"])
                epoch = cur["epoch"] if cur["holder"] == self.node and cur["expires"] > now else cur["epoch"] + 1
                self._write({"holder": self.node, "epoch": epoch, "expires": now + self.ttl})
                return epoch
            self.epoch = self._cas(f)
            return self.epoch

    def renew(self) -> int:
        with self._tl:
            def f(cur):
                if cur["holder"] != self.node or cur["epoch"] != self.epoch:
                    raise FencedOff("lease lost to a newer epoch", held_epoch=self.epoch, current=cur["epoch"])
                if cur["expires"] <= self.clock():
                    raise FencedOff("lease expired before renewal", epoch=self.epoch)
                self._write({**cur, "expires": self.clock() + self.ttl})
                return cur["epoch"]
            return self._cas(f)

    def release(self) -> None:
        with self._tl:
            def f(cur):
                if cur["holder"] == self.node and cur["epoch"] == self.epoch:
                    self._write({**cur, "holder": None, "expires": 0})
            self._cas(f)
            self.epoch = None

    def status(self) -> dict:
        cur = self._read()
        return {"holder": cur["holder"], "epoch": cur["epoch"], "is_leader": cur["holder"] == self.node
                and cur["epoch"] == self.epoch and cur["expires"] > self.clock()}


class FenceGate:
    """Target-side fencing: reject any write whose epoch is below the highest seen."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.highest = int(read_text(path) or 0) if path and os.path.exists(path) else 0

    def check(self, epoch: int) -> None:
        with self._lock:
            if epoch < self.highest:
                raise FencedOff("stale fencing token", epoch=epoch, highest=self.highest)
            if epoch > self.highest:
                self.highest = epoch
                if self.path:
                    tmp = self.path + ".tmp"
                    with open(tmp, "w") as fh:
                        fh.write(str(epoch))
                    os.replace(tmp, self.path)
