"""Durable, crash-consistent INV-53 queue (components 44, 45-partial, 48, 49, 83).

Design (see docs/architecture/DURABILITY.md):

* **Write-ahead journal.** Every state transition is first written as one JSON line
  ``{seq, epoch, op, a, h}`` to ``journal.jsonl`` and fsynced; only then is it
  applied to memory.  ``h`` chains ``sha256(prev_h || canonical(body))`` so edits,
  reordering and mid-file deletion are detected on open.
* **Recovery.** ``open`` loads ``snapshot.json`` (if any) and replays the journal.
  A torn *final* line (crash mid-write) is truncated and reported; damage anywhere
  else raises :class:`CorruptStoreError` and the store refuses to open.
* **Ownership / fencing.** An OS advisory lock (``flock``/``msvcrt``) admits one
  writer per store on a host, and a monotonically increasing ``EPOCH`` file fences
  a writer that lost ownership (e.g. on shared storage where locks are unreliable):
  every append re-reads the epoch and refuses with :class:`EpochFencedError` if a
  newer owner exists.  Cross-host consensus is *not* provided here.
* **Compaction** writes an atomic snapshot and resets the journal.
* **Backup/restore** copy snapshot + journal with a sha256 manifest; restore
  verifies the manifest and replays before accepting.

Leases survive restarts: a lease granted before a crash keeps its deadline and is
redelivered only after it expires, never earlier.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from collections import deque
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping
from uuid import uuid4

from .reliability import (
    DeadLetter,
    Delivery,
    DuplicateMessageError,
    QueueCapacityError,
    ReliabilityError,
    ReliableQueue,
)

STORE_SCHEMA = "inv53.store/1"
GENESIS = "0" * 64


class StorageError(ReliabilityError):
    """A durable write failed; the transition was NOT applied."""


class CorruptStoreError(ReliabilityError):
    """Durable state failed integrity verification."""


class EpochFencedError(ReliabilityError):
    """This writer's epoch is older than the store's; it no longer owns the store."""


class OwnershipError(ReliabilityError):
    """Another live writer holds the store lock."""


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _atomic_write(path: Path, data: bytes) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix="." + path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


class _Lock:
    def __init__(self, path: Path) -> None:
        self.fh = open(path, "a+b")
        try:
            if os.name == "nt":  # pragma: no cover - exercised on Windows only
                import msvcrt
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            self.fh.close()
            raise OwnershipError("store is locked by another live writer") from exc

    def release(self) -> None:
        try:
            if os.name == "nt":  # pragma: no cover
                import msvcrt
                self.fh.seek(0)
                msvcrt.locking(self.fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
        finally:
            self.fh.close()


class _State:
    """Deterministic state machine; the journal is its input tape."""

    def __init__(self) -> None:
        self.ready: deque[str] = deque()
        self.msgs: dict[str, dict] = {}
        self.attempts: dict[str, int] = {}
        self.inflight: dict[str, dict] = {}
        self.dlq: list[dict] = []
        self.c = {"redeliveries": 0, "acks": 0, "nacks": 0, "redrives": 0, "purges": 0}

    def apply(self, op: str, a: dict) -> None:
        if op == "put":
            mid = a["msg"]["id"]
            if mid in self.msgs:
                raise CorruptStoreError(f"replayed put for active id {mid!r}")
            self.msgs[mid] = a["msg"]
            self.ready.append(mid)
        elif op == "lease":
            mid = a["id"]
            if not self.ready or self.ready[0] != mid:
                raise CorruptStoreError("lease does not match ready-queue head")
            self.ready.popleft()
            self.attempts[mid] = a["attempt"]
            self.inflight[mid] = {"lease": a["lease"], "deadline": a["deadline"], "attempt": a["attempt"]}
        elif op == "ack":
            self.inflight.pop(a["id"])
            self.msgs.pop(a["id"])
            self.attempts.pop(a["id"], None)
            self.c["acks"] += 1
        elif op == "requeue":
            self.inflight.pop(a["id"])
            self.ready.append(a["id"])
            self.c["redeliveries"] += 1
            if a.get("nack"):
                self.c["nacks"] += 1
        elif op == "dead":
            rec = self.inflight.pop(a["id"])
            msg = self.msgs.pop(a["id"])
            self.attempts.pop(a["id"], None)
            self.dlq.append({"msg": msg, "attempts": rec["attempt"], "reason": a["reason"], "lease": rec["lease"]})
            if a.get("nack"):
                self.c["nacks"] += 1
        elif op == "extend":
            self.inflight[a["id"]]["deadline"] = a["deadline"]
        elif op == "redrive":
            item = self.dlq.pop(a["index"])
            mid = item["msg"]["id"]
            if mid in self.msgs:
                raise CorruptStoreError("redrive of an id that is active again")
            self.msgs[mid] = item["msg"]
            self.attempts.pop(mid, None)
            self.ready.append(mid)
            self.c["redrives"] += 1
        elif op == "purge":
            self.dlq.pop(a["index"])
            self.c["purges"] += 1
        elif op == "epoch":
            pass
        else:
            raise CorruptStoreError(f"unknown journal op {op!r}")

    def dump(self) -> dict:
        return {"ready": list(self.ready), "msgs": self.msgs, "attempts": self.attempts,
                "inflight": self.inflight, "dlq": self.dlq, "c": self.c}

    @classmethod
    def load(cls, d: dict) -> "_State":
        s = cls()
        s.ready = deque(d["ready"])
        s.msgs, s.attempts, s.inflight, s.dlq, s.c = d["msgs"], d["attempts"], d["inflight"], d["dlq"], d["c"]
        return s


class DurableQueue:
    """Journaled equivalent of :class:`ReliableQueue` with the same safety rules."""

    def __init__(self, directory: str | os.PathLike, *, visibility: float = 30.0, max_attempts: int = 5,
                 max_ready: int | None = None, max_in_flight: int | None = None,
                 max_dead_letters: int | None = None, max_message_bytes: int = 262_144,
                 fsync: bool = True, compact_every: int = 10_000,
                 fault: Callable[[str, str], None] | None = None,
                 anchored_head: Mapping[str, Any] | None = None) -> None:
        # Reuse the reference queue's validators so both layers accept identical input.
        ref = ReliableQueue(visibility=visibility, max_attempts=max_attempts, max_ready=max_ready,
                            max_in_flight=max_in_flight, max_dead_letters=max_dead_letters)
        self.visibility, self.max_attempts = ref.visibility, ref.max_attempts
        self.max_ready, self.max_in_flight, self.max_dead_letters = ref.max_ready, ref.max_in_flight, ref.max_dead_letters
        self.max_message_bytes = max_message_bytes
        self.fsync = fsync
        self.compact_every = compact_every
        self._fault = fault or (lambda point, op: None)
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._oslock = _Lock(self.dir / "LOCK")
        self.recovery_notes: list[str] = []
        self.ack_rejections = 0
        self._closed = False
        self._failed = False
        self._jfh = None
        self._anchor = dict(anchored_head) if anchored_head is not None else None
        try:
            self._recover()
            self.epoch = self._read_epoch() + 1
            _atomic_write(self.dir / "EPOCH", str(self.epoch).encode())
            _atomic_write(self.dir / "CLEAN", json.dumps({"state": "open", "epoch": self.epoch}).encode())
            self._jfh = open(self.dir / "journal.jsonl", "ab", buffering=0)
            self._append("epoch", {"epoch": self.epoch})
        except BaseException:
            if getattr(self, "_jfh", None) is not None:
                self._jfh.close()
            self._oslock.release()
            raise

    # ------------------------------------------------------------------ storage
    def _read_epoch(self) -> int:
        p = self.dir / "EPOCH"
        return int(p.read_text().strip() or 0) if p.exists() else 0

    def _epoch_now(self) -> int:
        """Current store epoch, read from disk on every append.

        5.1.0-dev cached this behind a ``stat`` identity check; an adversarial review
        reproduced a bypass (inode reuse + equal mtime, which coarse-mtime or network
        storage can produce naturally), so the fast path was withdrawn: fencing
        correctness outranks the ~30 % throughput it bought.
        """
        return self._read_epoch()

    def _recover(self) -> None:
        snap = self.dir / "snapshot.json"
        self._state, self._seq, self._head = _State(), 0, GENESIS
        if snap.exists():
            doc = json.loads(snap.read_text(encoding="utf-8"))
            body = {k: doc[k] for k in ("schema", "seq", "head", "state")}
            if doc.get("digest") != hashlib.sha256(_canon(body)).hexdigest():
                raise CorruptStoreError("snapshot digest mismatch")
            doc = self._migrate(doc)
            self._state, self._seq, self._head = _State.load(doc["state"]), doc["seq"], doc["head"]
        snap_seq = self._seq
        heads = {self._seq: self._head}
        clean = self._read_clean()
        jpath = self.dir / "journal.jsonl"
        if not jpath.exists():
            jpath.touch()
        raw = jpath.read_bytes()
        offset = 0
        truncated = False
        while offset < len(raw):
            nl = raw.find(b"\n", offset)
            complete = nl != -1
            line = raw[offset: nl if complete else len(raw)]
            rec = None
            try:
                rec = json.loads(line)
                body = {k: rec[k] for k in ("seq", "epoch", "op", "a")}
                if not isinstance(rec["seq"], int) or isinstance(rec["seq"], bool):
                    raise TypeError("seq")
            except (ValueError, KeyError, TypeError):
                rec = None
            if rec is not None and rec["seq"] <= snap_seq:
                # Folded into the snapshot already; left behind by a crash between the snapshot
                # write and the journal reset during compaction.  Its chain base is older than
                # the snapshot, so it is skipped rather than chain-checked.
                offset = (nl + 1) if complete else len(raw)
                if not heads.get("_stale_note"):
                    self.recovery_notes.append("skipped journal records already folded into the snapshot")
                    heads["_stale_note"] = True
                continue
            ok = rec is not None and rec["h"] == hashlib.sha256(self._head.encode() + _canon(body)).hexdigest()
            if not ok:
                if not complete and not (clean and clean.get("state") == "closed"):
                    # A crash mid-append leaves a final record without its newline.
                    self.recovery_notes.append(f"truncated torn final journal record at byte {offset}")
                    with open(jpath, "r+b") as fh:
                        fh.truncate(offset)
                        fh.flush()
                        os.fsync(fh.fileno())
                    truncated = True
                    break
                raise CorruptStoreError(f"journal record at byte {offset} failed integrity verification")
            if not complete:
                with open(jpath, "ab") as fh:
                    fh.write(b"\n")
                    fh.flush()
                    os.fsync(fh.fileno())
                self.recovery_notes.append("terminated a complete final record that lacked its newline")
            offset = (nl + 1) if complete else len(raw)
            if rec["seq"] != self._seq + 1:
                raise CorruptStoreError(f"journal gap before seq {rec['seq']}")
            try:
                self._state.apply(rec["op"], rec["a"])
            except (KeyError, IndexError, TypeError) as exc:
                raise CorruptStoreError(f"journal seq {rec['seq']} is not applicable: {exc!r}") from None
            self._seq, self._head = rec["seq"], rec["h"]
            heads[self._seq] = self._head
        # Tail completeness.  After a clean close the recorded head must be reached exactly;
        # after a crash, only an external anchor can prove that no complete record was removed.
        if clean and clean.get("state") == "closed":
            if (clean.get("seq"), clean.get("head")) != (self._seq, self._head) or truncated:
                raise CorruptStoreError("journal does not end at the head recorded at the last clean shutdown")
        elif clean is not None or self._seq > 0:
            self.recovery_notes.append("unclean shutdown: tail completeness is proven only by an external anchor")
        if self._anchor is not None:
            aseq, ahead = self._anchor.get("seq"), self._anchor.get("head")
            if not isinstance(aseq, int) or not isinstance(ahead, str) or heads.get(aseq) != ahead:
                raise CorruptStoreError("store does not contain the externally anchored head")

    def _read_clean(self) -> dict | None:
        p = self.dir / "CLEAN"
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            raise CorruptStoreError("CLEAN marker is unreadable") from None

    def head(self) -> dict[str, Any]:
        """``{seq, head}`` of the journal, for external anchoring (pass back as ``anchored_head``)."""
        with self._lock:
            return {"seq": self._seq, "head": self._head}

    @staticmethod
    def _migrate(doc: dict) -> dict:
        if doc["schema"] == STORE_SCHEMA:
            return doc
        raise CorruptStoreError(f"unsupported store schema {doc['schema']!r}; no migration registered")

    def _append(self, op: str, a: dict) -> None:
        self._writable()
        body = {"seq": self._seq + 1, "epoch": self.epoch, "op": op, "a": a}
        h = hashlib.sha256(self._head.encode() + _canon(body)).hexdigest()
        line = json.dumps({**body, "h": h}, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        try:
            self._fault("before_write", op)
            fh = self._jfh
            fh.write(line)
            fh.flush()
            if self.fsync:
                os.fsync(fh.fileno())
            self._fault("after_write", op)
        except OSError as exc:
            # The record may or may not be durable.  Fail-stop: memory is no longer
            # trusted and only recovery (reopen + replay) decides what happened.
            self._failed = True
            raise StorageError(f"journal write failed for {op}; outcome indeterminate, store fail-stopped") from exc
        # Callers have already checked every precondition, so apply cannot fail here.
        self._state.apply(op, a)
        self._seq, self._head = body["seq"], h
        if self.compact_every and self._seq % self.compact_every == 0:
            self.compact()          # raises StorageError and fail-stops on failure

    def _writable(self) -> None:
        """The guard shared by every path that writes store files."""
        if self._closed:
            raise StorageError("store is closed")
        if self._failed:
            raise StorageError("store fail-stopped after a write failure; reopen to recover")
        if self._epoch_now() != self.epoch:
            raise EpochFencedError(f"store epoch advanced beyond {self.epoch}; this writer is fenced")

    def compact(self) -> None:
        with self._lock:
            self._writable()        # a closed, fail-stopped or fenced writer must never rewrite the store
            body = {"schema": STORE_SCHEMA, "seq": self._seq, "head": self._head, "state": self._state.dump()}
            doc = {**body, "digest": hashlib.sha256(_canon(body)).hexdigest()}
            try:
                _atomic_write(self.dir / "snapshot.json", json.dumps(doc, sort_keys=True).encode())
                self._jfh.close()
                _atomic_write(self.dir / "journal.jsonl", b"")
                self._jfh = open(self.dir / "journal.jsonl", "ab", buffering=0)
            except OSError as exc:
                # State is durable (snapshot and/or journal); the writer is not.  Fail-stop so that
                # recovery -- which tolerates a crash at any point of this sequence -- decides.
                self._failed = True
                raise StorageError("compaction failed; store fail-stopped, reopen to recover") from exc

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._closed = True
                try:
                    self._jfh.close()
                    if not self._failed and self._read_epoch() == self.epoch:
                        _atomic_write(self.dir / "CLEAN", json.dumps(
                            {"state": "closed", "seq": self._seq, "head": self._head}).encode())
                finally:
                    self._oslock.release()

    def __enter__(self) -> "DurableQueue":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -------------------------------------------------------------- operations
    @staticmethod
    def _now(v: float) -> float:
        return ReliableQueue._time(v)

    def _limit(self, current: int, limit: int | None, name: str) -> None:
        if limit is not None and current >= limit:
            raise QueueCapacityError(f"{name} capacity reached ({limit})")

    def put(self, message: Mapping[str, Any]) -> bool:
        """Durably accept a message.  Returns ``True`` when newly accepted and ``False``
        for an idempotent retry of an identical active message (e.g. after an
        indeterminate :class:`StorageError`).  A *different* message with an active id
        raises :class:`DuplicateMessageError`."""
        msg = ReliableQueue._copy_message(message)
        encoded = _canon(msg)
        if len(encoded) > self.max_message_bytes:
            raise QueueCapacityError(f"message is {len(encoded)} bytes, limit {self.max_message_bytes}")
        with self._lock:
            s = self._state
            self._limit(len(s.ready), self.max_ready, "ready queue")
            if msg["id"] in s.msgs:
                if _canon(s.msgs[msg["id"]]) == encoded:
                    return False
                raise DuplicateMessageError(f"message id already active: {msg['id']!r}")
            self._append("put", {"msg": json.loads(encoded)})
            return True

    def _expire(self, now: float) -> None:
        for mid in sorted(k for k, r in self._state.inflight.items() if now >= r["deadline"]):
            r = self._state.inflight[mid]
            if r["attempt"] >= self.max_attempts:
                self._limit(len(self._state.dlq), self.max_dead_letters, "dead-letter queue")
                self._append("dead", {"id": mid, "reason": "visibility_timeout"})
            else:
                self._limit(len(self._state.ready), self.max_ready, "ready queue")
                self._append("requeue", {"id": mid})

    def expire(self, *, now: float) -> None:
        with self._lock:
            self._expire(self._now(now))

    def receive(self, *, now: float) -> Delivery | None:
        t = self._now(now)
        with self._lock:
            self._expire(t)
            s = self._state
            if not s.ready:
                return None
            self._limit(len(s.inflight), self.max_in_flight, "in-flight")
            mid = s.ready[0]
            attempt = s.attempts.get(mid, 0) + 1
            if attempt > self.max_attempts:
                raise ReliabilityError("attempt counter exceeded cap before leasing")
            lease = uuid4().hex
            self._append("lease", {"id": mid, "lease": lease, "deadline": t + self.visibility, "attempt": attempt})
            return Delivery(deepcopy(s.msgs[mid]), lease, t + self.visibility, attempt)

    def _match(self, delivery: Delivery | str, lease_id: str | None) -> tuple[str, dict | None]:
        mid, token = ReliableQueue._lease_parts(delivery, lease_id)
        rec = self._state.inflight.get(mid)
        if rec is None or token is None or token != rec["lease"]:
            return mid, None
        return mid, rec

    def ack(self, delivery: Delivery | str, lease_id: str | None = None, *, now: float) -> bool:
        t = self._now(now)
        with self._lock:
            self._expire(t)
            mid, rec = self._match(delivery, lease_id)
            if rec is None:
                self.ack_rejections += 1
                return False
            self._append("ack", {"id": mid})
            return True

    def nack(self, delivery: Delivery | str, *, now: float, lease_id: str | None = None,
             requeue: bool = True, reason: str = "negative_acknowledgement") -> bool:
        t = self._now(now)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason must be a non-empty string")
        with self._lock:
            self._expire(t)
            mid, rec = self._match(delivery, lease_id)
            if rec is None:
                return False
            if (not requeue) or rec["attempt"] >= self.max_attempts:
                self._limit(len(self._state.dlq), self.max_dead_letters, "dead-letter queue")
                self._append("dead", {"id": mid, "reason": reason.strip(), "nack": True})
            else:
                self._limit(len(self._state.ready), self.max_ready, "ready queue")
                self._append("requeue", {"id": mid, "nack": True})
            return True

    def extend_visibility(self, delivery: Delivery | str, *, now: float, extension: float,
                          lease_id: str | None = None) -> Delivery | None:
        t = self._now(now)
        extra = ReliableQueue._positive_number(extension, "extension")
        with self._lock:
            self._expire(t)
            mid, rec = self._match(delivery, lease_id)
            if rec is None:
                return None
            self._append("extend", {"id": mid, "deadline": t + extra})
            r = self._state.inflight[mid]
            return Delivery(deepcopy(self._state.msgs[mid]), r["lease"], r["deadline"], r["attempt"])

    # ---------------------------------------------------------- DLQ operations
    @property
    def dlq(self) -> tuple[DeadLetter, ...]:
        with self._lock:
            return tuple(DeadLetter(deepcopy(d["msg"]), d["attempts"], d["reason"], d["lease"]) for d in self._state.dlq)

    def redrive(self, message_id: str, *, now: float) -> bool:
        """Move the oldest dead letter with ``message_id`` back to ready with a fresh attempt budget."""
        self._now(now)
        with self._lock:
            for i, d in enumerate(self._state.dlq):
                if d["msg"]["id"] == message_id:
                    if message_id in self._state.msgs:
                        raise DuplicateMessageError("id is active again; redrive would duplicate it")
                    self._limit(len(self._state.ready), self.max_ready, "ready queue")
                    self._append("redrive", {"index": i})
                    return True
            return False

    def purge_dead_letter(self, message_id: str) -> bool:
        with self._lock:
            for i, d in enumerate(self._state.dlq):
                if d["msg"]["id"] == message_id:
                    self._append("purge", {"index": i})
                    return True
            return False

    # ------------------------------------------------------------- inspection
    def snapshot(self) -> dict[str, int]:
        with self._lock:
            s = self._state
            return {"ready": len(s.ready), "in_flight": len(s.inflight), "dead_lettered": len(s.dlq),
                    "redeliveries": s.c["redeliveries"], "acks": s.c["acks"], "ack_rejections": self.ack_rejections,
                    "nacks": s.c["nacks"], "tracked_attempts": len(s.attempts), "redrives": s.c["redrives"],
                    "purges": s.c["purges"], "journal_seq": self._seq, "epoch": self.epoch}

    def state_digest(self) -> str:
        with self._lock:
            return hashlib.sha256(_canon(self._state.dump())).hexdigest()

    def explain(self, message_id: str) -> dict[str, Any]:
        """Operator view of one message: where it is and why (component 66)."""
        with self._lock:
            s = self._state
            if message_id in s.inflight:
                r = s.inflight[message_id]
                return {"id": message_id, "state": "in_flight", "attempt": r["attempt"], "deadline": r["deadline"],
                        "max_attempts": self.max_attempts}
            if message_id in s.msgs:
                return {"id": message_id, "state": "ready", "position": list(s.ready).index(message_id),
                        "attempts_so_far": s.attempts.get(message_id, 0), "max_attempts": self.max_attempts}
            dead = [d for d in s.dlq if d["msg"]["id"] == message_id]
            if dead:
                return {"id": message_id, "state": "dead_lettered", "reason": dead[0]["reason"],
                        "attempts": dead[0]["attempts"]}
            return {"id": message_id, "state": "unknown_or_settled"}

    # ------------------------------------------------------------ backup/restore
    def backup(self, dest: str | os.PathLike) -> dict[str, Any]:
        with self._lock:
            self.compact()
            out = Path(dest)
            out.mkdir(parents=True, exist_ok=False)
            files = {}
            for name in ("snapshot.json", "journal.jsonl"):
                shutil.copyfile(self.dir / name, out / name)
                files[name] = hashlib.sha256((out / name).read_bytes()).hexdigest()
            manifest = {"schema": "inv53.backup/1", "store_schema": STORE_SCHEMA, "seq": self._seq,
                        "head": self._head, "state_digest": self.state_digest(), "files": files}
            (out / "MANIFEST.json").write_text(json.dumps(manifest, sort_keys=True, indent=1))
            return manifest


def restore(backup_dir: str | os.PathLike, target_dir: str | os.PathLike, **queue_kwargs: Any) -> DurableQueue:
    """Verify a backup and materialise it into an *empty* target directory."""
    src, dst = Path(backup_dir), Path(target_dir)
    manifest = json.loads((src / "MANIFEST.json").read_text())
    for name, digest in manifest["files"].items():
        if hashlib.sha256((src / name).read_bytes()).hexdigest() != digest:
            raise CorruptStoreError(f"backup file {name} does not match its manifest")
    if dst.exists() and any(p.name != "LOCK" for p in dst.iterdir()):
        raise ReliabilityError("restore target must be empty")
    dst.mkdir(parents=True, exist_ok=True)
    for name in manifest["files"]:
        shutil.copyfile(src / name, dst / name)
    q = DurableQueue(dst, **queue_kwargs)
    # The restored store appends one epoch record; state itself must be identical.
    if q.state_digest() != manifest["state_digest"]:
        q.close()
        raise CorruptStoreError("restored state digest differs from the backup manifest")
    return q

