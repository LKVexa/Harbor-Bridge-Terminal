"""Durable controller state and single-writer coordination for PLN-05.

State (``PLN05_STATE/2``) is written per ownership scope with
write-temp/fsync/rename inside an HMAC envelope; a partially written or
tampered file is refused (``E_STATE_CORRUPT``) and never silently replaced by
defaults.  Version 1 files (4.1.x had no persistence; ``/1`` is the minimal
layout used by the first persistence prototype) are migrated; future versions
are refused (``E_STATE_VERSION``).

Coordination: :class:`LeaseService` is the interface to the coordination
service (etcd/consul/…).  The in-process implementation here is the reference
and test double.  Every grant to a *different* owner increments the epoch; the
fencing token published with each target is the epoch, and
:class:`FencedSink` (the downstream contract) rejects any token lower than the
highest it has seen, so a resurrected stale controller cannot take effect.
"""
from __future__ import annotations

from collections import OrderedDict, deque
from dataclasses import dataclass
import hashlib
import json
import os
import pathlib
import re

from .errors import PlaneError
from .keys import KeyRing

STATE_SCHEMA = "PLN05_STATE/2"
SUPPORTED_READ = ("PLN05_STATE/1", "PLN05_STATE/2")
_SEG = r"[a-z0-9][a-z0-9._-]{0,63}"
_SCOPE = re.compile(rf"^{_SEG}/{_SEG}/{_SEG}$")


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def migrate(doc: dict) -> dict:
    """Upgrade a state document to ``PLN05_STATE/2``."""
    ver = doc.get("schema")
    if ver == "PLN05_STATE/2":
        return doc
    if ver == "PLN05_STATE/1":
        return {"schema": STATE_SCHEMA, "current": doc["current"], "below": doc.get("below", 0),
                "suppressed": 0, "limits": doc["limits"], "controls": {}, "sources": {},
                "seen": [], "epoch": 0, "last_decision_id": None, "config_checksum": None}
    raise PlaneError("E_STATE_VERSION", "unsupported state schema version")


class StateStore:
    def __init__(self, directory: str | os.PathLike, ring: KeyRing) -> None:
        self.dir = pathlib.Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ring = ring
        self.writes = 0

    def _path(self, scope: str) -> pathlib.Path:
        if not _SCOPE.match(scope):
            raise PlaneError("E_AUTHZ_SCOPE", "invalid state scope")
        return self.dir / (hashlib.sha256(scope.encode()).hexdigest()[:32] + ".state.json")

    def save(self, scope: str, state: dict, now: float, crash_hook=None) -> None:
        doc = dict(state, schema=STATE_SCHEMA, scope=scope)
        raw = _canon(doc)
        kid, mac = self.ring.sign(raw, now)
        env = _canon({"doc": doc, "kid": kid, "mac": mac})
        path = self._path(scope)
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "wb") as fh:
            fh.write(env)
            if crash_hook:
                crash_hook("mid-write")
            fh.flush()
            os.fsync(fh.fileno())
        if crash_hook:
            crash_hook("before-rename")
        os.replace(tmp, path)
        self.writes += 1

    def stamp(self, scope: str):
        """Cheap change detector (mtime_ns, size) for a scope file, or None if absent."""
        try:
            st = self._path(scope).stat()
        except FileNotFoundError:
            return None
        return (st.st_mtime_ns, st.st_size)

    def load(self, scope: str, now: float) -> dict | None:
        path = self._path(scope)
        stray = path.with_name(path.name + ".tmp")
        if stray.exists():
            stray.unlink()
        if not path.exists():
            return None
        try:
            env = json.loads(path.read_bytes())
            doc = env["doc"]
            self.ring.verify(env["kid"], _canon(doc), env["mac"], now)
        except PlaneError as exc:
            raise PlaneError("E_STATE_CORRUPT", "state integrity check failed",
                             {"cause": exc.code}) from None
        except (ValueError, KeyError, TypeError):
            raise PlaneError("E_STATE_CORRUPT", "state file unreadable") from None
        if doc.get("scope") != scope:
            raise PlaneError("E_STATE_CORRUPT", "state belongs to another scope")
        if doc.get("schema") not in SUPPORTED_READ:
            raise PlaneError("E_STATE_VERSION", "state written by an unsupported future version")
        return migrate(doc) if "current" in doc else doc


@dataclass
class Lease:
    scope: str
    owner: str
    epoch: int
    expires: float


class LeaseService:
    """Reference coordination service: one holder per scope, epoch bumps on owner change."""

    def __init__(self) -> None:
        self._leases: dict[str, Lease] = {}
        self._epochs: dict[str, int] = {}
        self.available = True

    def _up(self) -> None:
        if not self.available:
            raise PlaneError("E_SECURITY_DEPENDENCY", "coordination service unavailable")

    def acquire(self, scope: str, owner: str, now: float, duration: float) -> Lease:
        self._up()
        cur = self._leases.get(scope)
        if cur is not None and cur.expires > now and cur.owner != owner:
            raise PlaneError("E_NOT_LEADER", "scope held by another controller")
        if cur is None or cur.owner != owner or cur.expires <= now:
            self._epochs[scope] = self._epochs.get(scope, 0) + 1
        lease = Lease(scope, owner, self._epochs[scope], now + duration)
        self._leases[scope] = lease
        return lease

    def renew(self, lease: Lease, now: float, duration: float) -> Lease:
        self._up()
        cur = self._leases.get(lease.scope)
        if cur is None or cur.owner != lease.owner or cur.epoch != lease.epoch or cur.expires <= now:
            raise PlaneError("E_NOT_LEADER", "lease lost")
        cur.expires = now + duration
        return cur

    def release(self, lease: Lease) -> None:
        cur = self._leases.get(lease.scope)
        if cur is not None and cur.owner == lease.owner and cur.epoch == lease.epoch:
            cur.expires = 0.0


class FencedSink:
    """Downstream consumer contract: apply a target only with a non-decreasing fencing token."""

    HISTORY = 10000  # bounded (found by the soak/leak detector: an unbounded history grew ~0.8 KiB/decision)

    def __init__(self) -> None:
        self.applied: deque = deque(maxlen=self.HISTORY)
        self.rejected = 0
        self._high: dict[tuple, int] = {}
        self._seen_ids: OrderedDict[str, None] = OrderedDict()

    def apply(self, target: dict) -> bool:
        key = (target["tenant"], target["site"], target["workload"])
        if target["decision_id"] in self._seen_ids:
            return False  # idempotent: a re-emitted decision has no second effect
        if target["fencing_token"] < self._high.get(key, 0):
            self.rejected += 1
            raise PlaneError("E_FENCED", "stale fencing token")
        self._high[key] = target["fencing_token"]
        self._seen_ids[target["decision_id"]] = None
        while len(self._seen_ids) > self.HISTORY:
            self._seen_ids.popitem(last=False)
        self.applied.append(target)
        return True
