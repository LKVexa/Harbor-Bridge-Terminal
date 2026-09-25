"""The toolchain register: lifecycle, persistence, concurrency, integrity (MC-027..MC-030, MC-067, MC-069, MC-070).

* **Lifecycle (MC-027):** register / update / lifecycle transition / remove.  Transitions follow
  :data:`TRANSITIONS`; anything else is ``REG_ILLEGAL_TRANSITION``.  ``remove`` is allowed only
  from ``retired`` so history is never silently dropped.
* **Authorisation:** every mutation names an actor; the :class:`Authorizer` decides by capability
  (``register``, ``update``, ``lifecycle``, ``emergency``, ``remove``).  Unknown actors are refused.
* **Concurrency (MC-029):** every mutation takes ``expected_revision``; a mismatch raises
  ``REG_REVISION_CONFLICT`` (compare-and-swap).  A re-entrant lock serialises writers.
* **Integrity (MC-030):** snapshots are signed (KeyRing purpose ``registry``) and chained by
  ``prev_digest``; ``load`` refuses a bad signature, a broken chain or a revision lower than the
  one already held (rollback attack).
* **Persistence (MC-028, MC-067):** :class:`FileStore` writes snapshot files atomically
  (tmp + fsync + rename), keeps every revision, and ``reconstruct`` rebuilds the newest valid
  state from the directory, skipping tampered files and reporting them.
* **Rollback (MC-069):** ``rollback(to_revision)`` re-publishes an old snapshot's entries as a
  *new* revision - history is appended, never rewritten.
* **Emergency disable (MC-070):** ``emergency_disable`` moves a toolchain to ``disabled`` with
  capability ``emergency`` and no CAS precondition (an operator must be able to stop it now);
  disabled entries are unselectable in every environment.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .errors import Reason, RegistryError, ValidationError
from .model import ToolchainRecord, fmt_utc, sha256_hex
from .trust import KeyRing

SCHEMA = "PK_TOOLCHAIN_REGISTRY/1"
MAX_ENTRIES = 1024          # MC-078 capacity bound; see ops/CAPACITY.md
SNAPSHOT_RETENTION = 256

TRANSITIONS = {
    "candidate": {"active", "retired"},
    "active": {"deprecated", "quarantined", "disabled", "eol"},
    "deprecated": {"active", "eol", "quarantined", "disabled", "retired"},
    "eol": {"retired"},
    "quarantined": {"active", "disabled", "retired"},
    "disabled": {"active", "retired"},
    "retired": set(),
}
CAPABILITIES = ("register", "update", "lifecycle", "emergency", "remove", "rollback")


@dataclass
class Authorizer:
    grants: dict = field(default_factory=dict)     # actor -> set(capabilities)

    def check(self, actor: str, cap: str) -> None:
        if not isinstance(actor, str) or not actor.strip() or cap not in self.grants.get(actor, set()):
            raise RegistryError(Reason.REGISTRY_UNAUTHORIZED, f"actor {actor!r} lacks capability {cap!r}")

    @classmethod
    def permissive(cls, *actors: str) -> Authorizer:
        return cls({a: set(CAPABILITIES) for a in (actors or ("operator",))})


class Registry:
    def __init__(self, ring: KeyRing, authorizer: Authorizer | None = None, *, capacity: int = MAX_ENTRIES,
                 clock=None, audit=None):
        self._ring = ring
        self._auth = authorizer or Authorizer.permissive()
        self._cap = capacity
        self._clock = clock or (lambda: dt.datetime.now(dt.timezone.utc))
        self._audit = audit
        self._entries: dict[str, ToolchainRecord] = {}
        self._revision = 0
        self._prev_digest = ""
        self._head_digest = ""
        self._history: list[dict] = []
        self._snapshots: dict[int, dict] = {}
        self._lock = threading.RLock()
        self._listeners: list = []
        self._digest_memo: str | None = None

    # -- read side -------------------------------------------------------------------------------
    @property
    def revision(self) -> int:
        return self._revision

    @property
    def entries(self) -> tuple:
        with self._lock:
            return tuple(self._entries[k] for k in sorted(self._entries))

    def get(self, ref: str) -> ToolchainRecord:
        key = self._key(ref)
        with self._lock:
            if key not in self._entries:
                raise RegistryError(Reason.REGISTRY_UNKNOWN, f"{ref} is not registered")
            return self._entries[key]

    @property
    def digest(self) -> str:
        """Content digest, memoised per change notification (every mutation path calls _notify)."""
        with self._lock:
            if self._digest_memo is None:
                self._digest_memo = sha256_hex({"revision": self._revision, "state": self._state_digest(),
                                                "head": self._head_digest})
            return self._digest_memo

    @property
    def history(self) -> tuple:
        with self._lock:
            return tuple(dict(h) for h in self._history)

    def on_change(self, fn) -> None:
        """Subscribe to revision changes (cache invalidation, MC-080)."""
        self._listeners.append(fn)

    # -- write side ------------------------------------------------------------------------------
    def register(self, record: ToolchainRecord, *, actor: str, expected_revision: int) -> int:
        if not isinstance(record, ToolchainRecord):
            raise ValidationError("register takes a ToolchainRecord")
        with self._lock:
            self._auth.check(actor, "register")
            self._cas(expected_revision)
            if record.key in self._entries:
                raise RegistryError(Reason.REGISTRY_DUPLICATE, f"{record.ref} already registered")
            if len(self._entries) >= self._cap:
                raise RegistryError(Reason.REGISTRY_FULL, f"registry capacity {self._cap} reached")
            if record.lifecycle not in ("candidate", "active"):
                raise RegistryError(Reason.REGISTRY_TRANSITION, "new entries start as candidate or active")
            self._entries[record.key] = record
            return self._commit("register", record.ref, actor, record.digest)

    def update(self, record: ToolchainRecord, *, actor: str, expected_revision: int) -> int:
        """Replace attributes of an existing name@version.  Lifecycle changes go through transition()."""
        with self._lock:
            self._auth.check(actor, "update")
            self._cas(expected_revision)
            old = self._entries.get(record.key)
            if old is None:
                raise RegistryError(Reason.REGISTRY_UNKNOWN, f"{record.ref} is not registered")
            if old.lifecycle != record.lifecycle:
                raise RegistryError(Reason.REGISTRY_TRANSITION, "use transition() to change lifecycle")
            if old.integrity and record.integrity and old.integrity.artifact_sha256 != record.integrity.artifact_sha256:
                raise RegistryError(Reason.REGISTRY_TRANSITION,
                                    "artifact digest of a pinned version is immutable; register a new version")
            self._entries[record.key] = record
            return self._commit("update", record.ref, actor, record.digest, prev=old.digest)

    def transition(self, ref: str, to: str, *, actor: str, expected_revision: int, reason: str) -> int:
        with self._lock:
            self._auth.check(actor, "emergency" if to == "disabled" else "lifecycle")
            self._cas(expected_revision)
            return self._transition(ref, to, actor, reason)

    def emergency_disable(self, ref: str, *, actor: str, reason: str) -> int:
        """MC-070: no CAS precondition - stopping a toolchain must never lose a race."""
        with self._lock:
            self._auth.check(actor, "emergency")
            rec = self.get(ref)
            if rec.lifecycle == "disabled":
                return self._revision
            if rec.lifecycle == "retired":
                raise RegistryError(Reason.REGISTRY_TRANSITION, f"{ref} is retired")
            self._entries[rec.key] = rec.replace(lifecycle="disabled")
            return self._commit("emergency_disable", rec.ref, actor, self._entries[rec.key].digest, reason=reason)

    def remove(self, ref: str, *, actor: str, expected_revision: int) -> int:
        with self._lock:
            self._auth.check(actor, "remove")
            self._cas(expected_revision)
            rec = self.get(ref)
            if rec.lifecycle != "retired":
                raise RegistryError(Reason.REGISTRY_TRANSITION, "only retired entries may be removed")
            del self._entries[rec.key]
            return self._commit("remove", rec.ref, actor, rec.digest)

    def rollback(self, to_revision: int, *, actor: str, expected_revision: int, reason: str) -> int:
        with self._lock:
            self._auth.check(actor, "rollback")
            self._cas(expected_revision)
            snap = self._snapshots.get(to_revision)
            if snap is None:
                raise RegistryError(Reason.REGISTRY_UNKNOWN, f"no retained snapshot for revision {to_revision}")
            self._entries = dict(snap["entries"])
            return self._commit("rollback", f"r{to_revision}", actor, snap["digest"], reason=reason)

    # -- snapshot / integrity --------------------------------------------------------------------
    def snapshot(self) -> dict:
        with self._lock:
            body = self._payload()
            return {**body, "signature": self._ring.sign("registry", body)}

    def load(self, snap: dict, *, allow_older: bool = False) -> None:
        body = verify_snapshot(self._ring, snap)
        with self._lock:
            if not allow_older and body["revision"] < self._revision:
                raise RegistryError(Reason.REGISTRY_INTEGRITY,
                                    f"snapshot r{body['revision']} is older than held r{self._revision}")
            if body["revision"] == self._revision + 1 and self._head_digest \
                    and body.get("prev_digest") != self._head_digest:
                raise RegistryError(Reason.REGISTRY_INTEGRITY, "snapshot does not chain onto the held head")
            entries = {r.key: r for r in (ToolchainRecord.from_dict(e) for e in body["entries"])}
            self._entries = entries
            self._revision = body["revision"]
            self._prev_digest = body["prev_digest"]
            self._history = list(body["history"])
            self._head_digest = body["head_digest"]
            self._snapshots[self._revision] = {"entries": dict(entries), "digest": self._head_digest}
        self._notify()

    # -- internals -------------------------------------------------------------------------------
    def _payload(self) -> dict:
        return {"schema": SCHEMA, "revision": self._revision, "prev_digest": self._prev_digest,
                "head_digest": self._head_digest, "state_digest": self._state_digest(),
                "entries": [self._entries[k].to_dict() for k in sorted(self._entries)],
                "history": self._history[-SNAPSHOT_RETENTION:]}

    def _state_digest(self) -> str:
        return state_digest(self._entries.values())

    def _key(self, ref: str) -> str:
        if not isinstance(ref, str) or "@" not in ref:
            raise ValidationError("toolchain reference must be name@version")
        name, _, ver = ref.partition("@")
        return f"{name.strip().casefold()}@{ver.strip()}"

    def _cas(self, expected: int) -> None:
        if type(expected) is not int or expected != self._revision:
            raise RegistryError(Reason.REGISTRY_CONFLICT,
                                f"expected revision {expected!r}, registry is at {self._revision}",
                                current=self._revision)

    def _transition(self, ref, to, actor, reason):
        rec = self.get(ref)
        if to not in TRANSITIONS.get(rec.lifecycle, set()):
            raise RegistryError(Reason.REGISTRY_TRANSITION, f"{rec.lifecycle} -> {to} not allowed")
        self._entries[rec.key] = rec.replace(lifecycle=to)
        return self._commit(f"transition:{rec.lifecycle}->{to}", rec.ref, actor,
                            self._entries[rec.key].digest, reason=reason)

    def _commit(self, op, ref, actor, digest, **extra) -> int:
        self._prev_digest = self._head_digest
        self._revision += 1
        event = {"revision": self._revision, "op": op, "ref": ref, "actor": actor, "digest": digest,
                 "at": fmt_utc(self._clock()), **{k: v for k, v in extra.items() if v}}
        self._history.append(event)
        # O(entries) of short strings per commit: the head chains the previous head, the content-state
        # digest and the event; full serialisation happens only in snapshot().
        self._head_digest = chain(self._prev_digest, self._state_digest(), event)
        self._snapshots[self._revision] = {"entries": dict(self._entries), "digest": self._head_digest}
        for old in sorted(self._snapshots)[:-SNAPSHOT_RETENTION]:
            del self._snapshots[old]
        if self._audit is not None:
            self._audit.append("registry." + op.split(":")[0], {k: v for k, v in event.items()})
        self._notify()
        return self._revision

    def _notify(self):
        self._digest_memo = None
        for fn in list(self._listeners):
            fn(self._revision)


def state_digest(records) -> str:
    return sha256_hex(sorted([r.key, r.digest] for r in records))


def chain(prev: str, state: str, event: dict) -> str:
    return sha256_hex({"prev": prev, "state": state, "event": event})


def verify_snapshot(ring: KeyRing, snap: dict) -> dict:
    if not isinstance(snap, dict) or snap.get("schema") != SCHEMA:
        raise RegistryError(Reason.REGISTRY_INTEGRITY, f"snapshot schema must be {SCHEMA}")
    body = {k: v for k, v in snap.items() if k != "signature"}
    if not ring.verify("registry", body, snap.get("signature")):
        raise RegistryError(Reason.REGISTRY_INTEGRITY, "registry snapshot signature invalid or key untrusted")
    if type(body.get("revision")) is not int or not isinstance(body.get("entries"), list):
        raise RegistryError(Reason.REGISTRY_INTEGRITY, "malformed snapshot")
    if len(body["entries"]) > MAX_ENTRIES:
        raise RegistryError(Reason.REGISTRY_FULL, "snapshot exceeds capacity")
    keys = [f"{e.get('name', '').casefold()}@{e.get('version')}" for e in body["entries"]]
    if len(set(keys)) != len(keys):
        raise RegistryError(Reason.REGISTRY_DUPLICATE, "snapshot contains duplicate entries")
    try:
        records = [ToolchainRecord.from_dict(e) for e in body["entries"]]
    except ValidationError as exc:
        raise RegistryError(Reason.REGISTRY_INTEGRITY, f"invalid entry in snapshot: {exc}") from None
    if body.get("state_digest") != state_digest(records):
        raise RegistryError(Reason.REGISTRY_INTEGRITY, "state digest does not match entries")
    hist = body.get("history") or []
    if body["revision"] > 0 and (not hist or hist[-1].get("revision") != body["revision"]
                                 or body.get("head_digest") != chain(body.get("prev_digest", ""), body["state_digest"], hist[-1])):
        raise RegistryError(Reason.REGISTRY_INTEGRITY, "head digest does not chain prev_digest, state and last event")
    return body


class FileStore:
    """Durable, append-only snapshot directory: ``rev-000042.json`` per revision."""

    def __init__(self, directory):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def path(self, revision: int) -> Path:
        return self.dir / f"rev-{revision:06d}.json"

    def save(self, snap: dict) -> Path:
        dst = self.path(snap["revision"])
        if dst.exists():
            if json.loads(dst.read_text(encoding="utf-8")) == snap:
                return dst
            raise RegistryError(Reason.REGISTRY_CONFLICT, f"{dst.name} already holds a different snapshot")
        tmp = dst.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, sort_keys=True, indent=1)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, dst)
        return dst

    def revisions(self) -> list[int]:
        out = []
        for p in self.dir.glob("rev-*.json"):
            try:
                out.append(int(p.stem[4:]))
            except ValueError:
                continue
        return sorted(out)

    def reconstruct(self, ring: KeyRing) -> tuple[dict | None, list[str]]:
        """Newest snapshot that verifies; returns (snapshot, problems-with-newer-files)."""
        problems: list[str] = []
        for rev in reversed(self.revisions()):
            try:
                snap = json.loads(self.path(rev).read_text(encoding="utf-8"))
                verify_snapshot(ring, snap)
                if snap["revision"] != rev:
                    raise RegistryError(Reason.REGISTRY_INTEGRITY, "file name / revision mismatch")
                return snap, problems
            except (RegistryError, ValueError, KeyError) as exc:
                problems.append(f"rev-{rev:06d}: {exc}")
        return None, problems
