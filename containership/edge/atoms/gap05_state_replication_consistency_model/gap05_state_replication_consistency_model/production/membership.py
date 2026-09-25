"""MC14 atomic configuration/membership store, MC15 membership-change protocol,
MC32 split-brain fencing, MC03 trusted monotonic counters (allocation + receive guard).

Membership model
----------------
A ``MembershipConfig`` is an immutable, versioned document.  ``epoch`` increases by
exactly one per activation (compare-and-swap on the expected epoch).  Each config
records its parent digest, author and reason (provenance), so history is a hash chain.
Rollback is a *forward* activation of an older config's content under a new epoch -
epochs never decrease, so fencing tokens stay monotonic.

Replica lifecycle: ``active`` -> ``retired``.  Removal records a ``high_water`` counter
per retired replica (the drain protocol's final committed own-counter).  Historic
vector entries for retired replicas remain valid; new authorship is fenced.

Reseed: the replica is retired and re-added as a new *incarnation*
(``name~2``) with a fresh credential; counters never restart under a reused identity,
so an old and a new incarnation cannot collide in version vectors.

Fencing rule (MC32) for a write authored by ``site`` under ``epoch``:
* ``epoch`` > current epoch -> reject (future epoch / forged token)
* ``site`` unknown in every config -> reject
* ``site`` retired: accept only if its own counter <= recorded high_water (late
  delivery of pre-retirement history); otherwise reject as fenced.
* ``site`` must have been active in the stamped epoch.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field, replace
from pathlib import Path

from .durable import atomic_write
from .errors import AuthenticationError, ConfigError, CounterViolation, FencedError, IntegrityError
from .schemas import canonical_bytes, digest

CONFIG_FORMAT = "GAP05_MEMBERSHIP/1"


@dataclass(frozen=True)
class ReplicaRecord:
    name: str
    workload_id: str
    key_fingerprints: tuple[str, ...]
    public_keys: tuple[str, ...] = ()
    status: str = "active"
    high_water: dict = field(default_factory=dict)  # key -> own counter at retirement ("*" = all keys)
    active_since: int = 1
    retired_at: int | None = None

    def as_dict(self) -> dict:
        return {"name": self.name, "workload_id": self.workload_id, "key_fingerprints": list(self.key_fingerprints),
                "public_keys": list(self.public_keys), "status": self.status, "high_water": dict(self.high_water),
                "active_since": self.active_since, "retired_at": self.retired_at}

    @classmethod
    def from_dict(cls, d: dict) -> "ReplicaRecord":
        return cls(d["name"], d["workload_id"], tuple(d["key_fingerprints"]), tuple(d.get("public_keys", ())),
                   d["status"], dict(d.get("high_water", {})), d.get("active_since", 1), d.get("retired_at"))


@dataclass(frozen=True)
class MembershipConfig:
    epoch: int
    replicas: dict  # name -> ReplicaRecord
    parent: str | None
    author: str
    reason: str

    def as_dict(self) -> dict:
        return {"format": CONFIG_FORMAT, "epoch": self.epoch, "parent": self.parent, "author": self.author,
                "reason": self.reason, "replicas": {n: r.as_dict() for n, r in sorted(self.replicas.items())}}

    @property
    def digest(self) -> str:
        return digest(self.as_dict())

    @classmethod
    def from_dict(cls, d: dict) -> "MembershipConfig":
        if d.get("format") != CONFIG_FORMAT:
            raise ConfigError(f"unknown membership format {d.get('format')}")
        return cls(d["epoch"], {n: ReplicaRecord.from_dict(r) for n, r in d["replicas"].items()},
                   d["parent"], d["author"], d["reason"])

    @property
    def active(self) -> frozenset:
        return frozenset(n for n, r in self.replicas.items() if r.status == "active")

    @property
    def known(self) -> frozenset:
        return frozenset(self.replicas)

    def validate(self) -> None:
        if self.epoch < 1:
            raise ConfigError("epoch must be >= 1")
        if not self.active:
            raise ConfigError("configuration must keep at least one active replica")
        wids = {}
        for name, rec in self.replicas.items():
            if name != rec.name:
                raise ConfigError("replica map key/name mismatch")
            if rec.status not in ("active", "retired"):
                raise ConfigError(f"bad status {rec.status}")
            if rec.status == "active":
                if rec.workload_id in wids:
                    raise ConfigError(f"workload id {rec.workload_id} mapped to two active replicas")
                wids[rec.workload_id] = name
            if rec.status == "retired" and rec.retired_at is None:
                raise ConfigError("retired replica missing retired_at")


class MembershipStore:
    """Durable, CAS-activated membership history (one JSON file per epoch + CURRENT)."""

    def __init__(self, directory: Path, genesis: MembershipConfig | None = None):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._history: dict[int, MembershipConfig] = {}
        self._load()
        if not self._history:
            if genesis is None:
                raise ConfigError("empty membership store needs a genesis config")
            if genesis.epoch != 1 or genesis.parent is not None:
                raise ConfigError("genesis must be epoch 1 with no parent")
            genesis.validate()
            self._persist(genesis)

    def _load(self) -> None:
        for p in sorted(self.dir.glob("epoch-*.json")):
            cfg = MembershipConfig.from_dict(json.loads(p.read_bytes()))
            self._history[cfg.epoch] = cfg
        for epoch, cfg in self._history.items():
            if epoch > 1 and (epoch - 1 not in self._history or self._history[epoch - 1].digest != cfg.parent):
                raise IntegrityError(f"membership chain broken at epoch {epoch}", code="CORR_MEMBERSHIP_CHAIN")

    def _persist(self, cfg: MembershipConfig) -> None:
        atomic_write(self.dir / f"epoch-{cfg.epoch:08d}.json", canonical_bytes(cfg.as_dict()))
        self._history[cfg.epoch] = cfg

    @property
    def current(self) -> MembershipConfig:
        with self._lock:
            return self._history[max(self._history)]

    @property
    def epoch(self) -> int:
        return self.current.epoch

    def at(self, epoch: int) -> MembershipConfig | None:
        return self._history.get(epoch)

    def activate(self, expected_epoch: int, replicas: dict, *, author: str, reason: str) -> MembershipConfig:
        with self._lock:
            cur = self.current
            if expected_epoch != cur.epoch:
                raise ConfigError(f"CAS failed: expected epoch {expected_epoch}, current {cur.epoch}",
                                  code="CORR_CAS_CONFLICT", retryable=True)
            nxt = MembershipConfig(cur.epoch + 1, dict(replicas), cur.digest, author, reason)
            nxt.validate()
            self._persist(nxt)
            return nxt

    def rollback_to(self, epoch: int, *, expected_epoch: int, author: str, reason: str) -> MembershipConfig:
        """Forward-activate an older configuration's replica set.  Refuses to re-activate
        a replica retired since then (that would un-fence it)."""
        old = self.at(epoch)
        if old is None:
            raise ConfigError(f"no epoch {epoch}")
        cur = self.current
        replicas = dict(old.replicas)
        for name, rec in cur.replicas.items():
            if rec.status == "retired":
                replicas[name] = rec
        return self.activate(expected_epoch, replicas, author=author, reason=f"rollback to {epoch}: {reason}")

    # -- protocol (MC15) --------------------------------------------------------
    def add_replica(self, name: str, workload_id: str, fingerprints, *, public_keys=(), author: str,
                    expected_epoch: int) -> MembershipConfig:
        cur = self.current
        if name in cur.replicas:
            raise ConfigError(f"replica name {name} was already used; reseed creates a new incarnation")
        rec = ReplicaRecord(name, workload_id, tuple(fingerprints), tuple(public_keys), "active", {},
                            cur.epoch + 1, None)
        return self.activate(expected_epoch, {**cur.replicas, name: rec}, author=author, reason=f"add {name}")

    def remove_replica(self, name: str, *, high_water: dict, author: str, expected_epoch: int) -> MembershipConfig:
        cur = self.current
        rec = cur.replicas.get(name)
        if rec is None or rec.status != "active":
            raise ConfigError(f"{name} is not an active replica")
        if not isinstance(high_water, dict):
            raise ConfigError("high_water must map key -> final own counter (drain result)")
        retired = replace(rec, status="retired", high_water=dict(high_water), retired_at=cur.epoch + 1)
        return self.activate(expected_epoch, {**cur.replicas, name: retired}, author=author,
                             reason=f"remove {name}")

    def reseed_replica(self, name: str, workload_id: str, fingerprints, *, public_keys=(), high_water: dict,
                       author: str, expected_epoch: int) -> tuple[str, MembershipConfig]:
        base = name.split("~")[0]
        n = 2
        while f"{base}~{n}" in self.current.replicas:
            n += 1
        new_name = f"{base}~{n}"
        cfg = self.remove_replica(name, high_water=high_water, author=author, expected_epoch=expected_epoch)
        cfg = self.add_replica(new_name, workload_id, fingerprints, public_keys=public_keys, author=author,
                               expected_epoch=cfg.epoch)
        return new_name, cfg

    # -- identity mapping (MC01-004/005) ----------------------------------------
    def replica_for_identity(self, workload_id: str, key_fingerprint: str) -> str:
        cur = self.current
        matches = [r for r in cur.replicas.values() if r.workload_id == workload_id]
        active = [r for r in matches if r.status == "active"]
        if not matches:
            raise AuthenticationError("identity not mapped to any replica", code="SEC_UNKNOWN_IDENTITY")
        if not active:
            raise AuthenticationError("identity belongs to a retired replica", code="SEC_STALE_MEMBERSHIP")
        if len(active) > 1:
            raise AuthenticationError("identity maps to multiple replicas", code="SEC_AMBIGUOUS_IDENTITY")
        if key_fingerprint not in active[0].key_fingerprints:
            raise AuthenticationError("key not registered for this replica", code="SEC_KEY_NOT_REGISTERED")
        return active[0].name

    # -- fencing (MC32) ---------------------------------------------------------
    def check_authorship(self, site: str, epoch: int, key: str, own_counter: int) -> None:
        cur = self.current
        if epoch > cur.epoch:
            raise FencedError(f"write stamped with future epoch {epoch} > {cur.epoch}", code="SEC_FUTURE_EPOCH")
        stamped = self.at(epoch)
        if stamped is None:
            raise FencedError(f"unknown epoch {epoch}", code="SEC_UNKNOWN_EPOCH")
        rec_then = stamped.replicas.get(site)
        if rec_then is None or rec_then.status != "active":
            raise FencedError(f"{site} was not active in epoch {epoch}", code="SEC_NOT_ACTIVE_IN_EPOCH")
        rec_now = cur.replicas[site]
        if rec_now.status == "retired":
            limit = rec_now.high_water.get(key, rec_now.high_water.get("*", 0))
            if own_counter > limit:
                raise FencedError(f"{site} retired; counter {own_counter} > high-water {limit}",
                                  code="SEC_FENCED_RETIRED")


class CounterAllocator:
    """MC03 - durable per-replica monotonic counter allocation.

    Counters are reserved in blocks; the reservation ceiling is persisted (atomic write +
    fsync) *before* any counter in the block is handed out, so a crash can skip counters
    but can never re-issue one (no rollback after restart).
    """

    def __init__(self, path: Path, replica: str, *, block: int = 64):
        self.path = Path(path)
        self.replica = replica
        self.block = block
        self._lock = threading.Lock()
        self._next: dict[str, int] = {}
        self._ceiling: dict[str, int] = {}
        if self.path.exists():
            doc = json.loads(self.path.read_bytes())
            if doc.get("replica") != replica:
                raise IntegrityError("counter file belongs to another replica", code="CORR_COUNTER_OWNER")
            self._ceiling = {k: int(v) for k, v in doc["ceiling"].items()}
            self._next = {k: v + 1 for k, v in self._ceiling.items()}  # never reuse reserved range

    def _persist(self) -> None:
        atomic_write(self.path, canonical_bytes({"replica": self.replica, "ceiling": self._ceiling}))

    def observe(self, key: str, counter: int) -> None:
        """Advance past a counter observed for this replica (e.g. after restore)."""
        with self._lock:
            if counter >= self._next.get(key, 1):
                self._next[key] = counter + 1
                if self._next[key] > self._ceiling.get(key, 0):
                    self._reserve(key, counter + 1)

    def _reserve(self, key: str, at_least: int) -> None:
        """Reserve a new block under an exclusive OS file lock, re-reading the durable
        ceiling first, so two processes (or a crashed-and-restarted one) never overlap."""
        import fcntl
        lock_path = self.path.with_suffix(".lock")
        with open(lock_path, "a+") as lf:
            fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
            try:
                if self.path.exists():
                    disk = json.loads(self.path.read_bytes())
                    if disk.get("replica") != self.replica:
                        raise IntegrityError("counter file belongs to another replica", code="CORR_COUNTER_OWNER")
                    for k, v in disk["ceiling"].items():
                        self._ceiling[k] = max(self._ceiling.get(k, 0), int(v))
                start = max(at_least, self._ceiling.get(key, 0) + 1)
                self._next[key] = start
                self._ceiling[key] = start + self.block - 1
                self._persist()
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)

    def next(self, key: str) -> int:
        with self._lock:
            n = self._next.get(key, 1)
            if n > self._ceiling.get(key, 0):
                self._reserve(key, n)
                n = self._next[key]
            self._next[key] = n + 1
            return n


class CounterGuard:
    """MC03 receive side: detect counter jumps, rollback/equivocation per (key, author)."""

    def __init__(self, *, max_gap: int = 1024):
        if max_gap < 1:
            raise ConfigError("max_gap must be >= 1")
        self.max_gap = max_gap
        self.high: dict[tuple[str, str], int] = {}
        self.seen: dict[tuple[str, str, int], str] = {}
        self.evidence: list[dict] = []

    def check(self, key: str, author: str, vector: dict, op_id: str) -> None:
        own = vector[author]
        prior = self.seen.get((key, author, own))
        if prior is not None and prior != op_id:
            self.evidence.append({"kind": "equivocation", "key": key, "author": author, "counter": own,
                                  "ops": sorted([prior, op_id])})
            raise CounterViolation(f"{author} reused counter {own} on {key} for different content",
                                   code="SEC_COUNTER_EQUIVOCATION")
        for site, counter in vector.items():
            high = self.high.get((key, site), 0)
            if counter > high + self.max_gap:
                self.evidence.append({"kind": "jump", "key": key, "site": site, "counter": counter, "high": high})
                raise CounterViolation(f"counter for {site} jumps {counter - high} > max_gap {self.max_gap}",
                                       code="SEC_COUNTER_JUMP")

    def record(self, key: str, author: str, vector: dict, op_id: str) -> None:
        self.seen[(key, author, vector[author])] = op_id
        for site, counter in vector.items():
            if counter > self.high.get((key, site), 0):
                self.high[(key, site)] = counter

    def export(self) -> dict:
        return {"max_gap": self.max_gap,
                "high": [[k, s, c] for (k, s), c in sorted(self.high.items())],
                "seen": [[k, a, c, o] for (k, a, c), o in sorted(self.seen.items())]}

    @classmethod
    def restore(cls, doc: dict) -> "CounterGuard":
        g = cls(max_gap=doc["max_gap"])
        g.high = {(k, s): c for k, s, c in doc["high"]}
        g.seen = {(k, a, c): o for k, a, c, o in doc["seen"]}
        return g
