"""Ownership leases, fencing epochs and an operation journal (MC-031, MC-028).

``LeaseStore`` persists (owner, epoch, expiry) per resource in a JSON file
updated with atomic rename under an ``flock``; every acquisition increments
the epoch, and every side-effecting call must present the epoch, so a
restarted or partitioned stale owner is fenced (``STALE_EPOCH``).

``OperationJournal`` binds idempotency keys to a request digest and result,
persisted append-only, so retries and controller restarts never duplicate a
microVM.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import pathlib
import threading
import time
from contextlib import contextmanager

from ..errors import Inv24Error


@contextmanager
def _locked(path: pathlib.Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_suffix(".lock"), "a+") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _atomic_json(path: pathlib.Path, data: object) -> None:
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as fh:
        json.dump(data, fh, sort_keys=True)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


class LeaseStore:
    def __init__(self, path: str, *, clock=time.time) -> None:
        self.path, self.clock = pathlib.Path(path), clock
        self._tl = threading.Lock()

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text())
        except FileNotFoundError:
            return {}

    def acquire(self, resource: str, owner: str, ttl_s: float = 15.0) -> int:
        with self._tl, _locked(self.path):
            data = self._read()
            cur = data.get(resource)
            now = self.clock()
            if cur and cur["owner"] != owner and cur["expires"] > now:
                raise Inv24Error("LEASE_HELD", f"{resource} held by another owner")
            epoch = (cur["epoch"] + 1) if cur else 1
            data[resource] = {"owner": owner, "epoch": epoch, "expires": now + ttl_s}
            _atomic_json(self.path, data)
            return epoch

    def renew(self, resource: str, owner: str, epoch: int, ttl_s: float = 15.0) -> None:
        with self._tl, _locked(self.path):
            data = self._read()
            cur = data.get(resource)
            if not cur or cur["owner"] != owner or cur["epoch"] != epoch:
                raise Inv24Error("STALE_EPOCH", f"{resource}: lease lost")
            cur["expires"] = self.clock() + ttl_s
            _atomic_json(self.path, data)

    def fence(self, resource: str, epoch: int) -> None:
        """Raise unless ``epoch`` is the current, unexpired epoch."""
        cur = self._read().get(resource)
        if not cur or cur["epoch"] != epoch or cur["expires"] <= self.clock():
            raise Inv24Error("STALE_EPOCH", f"{resource}: epoch {epoch} is not current")

    def current(self, resource: str) -> dict | None:
        return self._read().get(resource)


def request_digest(payload: dict) -> str:
    clean = {k: v for k, v in payload.items() if k not in {"capability_token", "deadline_ms"}}
    return hashlib.sha256(json.dumps(clean, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class OperationJournal:
    MAX_ENTRIES = 1_000_000

    def __init__(self, path: str) -> None:
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._index: dict[str, dict] = {}
        if self.path.exists():
            with open(self.path) as fh:
                for line in fh:
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue  # torn final line after crash: ignored, op will be re-evaluated
                    self._index[rec["key"]] = rec

    def lookup(self, key: str, digest: str) -> dict | None:
        with self._lock:
            rec = self._index.get(key)
        if rec is None:
            return None
        if rec["digest"] != digest:
            raise Inv24Error("DUPLICATE_OPERATION", "operation key reused with a different request")
        return rec

    def record(self, key: str, digest: str, state: str, result: dict) -> dict:
        rec = {"key": key, "digest": digest, "state": state, "result": result, "ts": time.time()}
        with self._lock:
            if len(self._index) >= self.MAX_ENTRIES:
                raise Inv24Error("RESOURCE_EXHAUSTED", "operation journal full")
            with open(self.path, "a") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            self._index[key] = rec
        return rec

    def pending(self) -> list[dict]:
        with self._lock:
            return [r for r in self._index.values() if r["state"] == "pending"]
