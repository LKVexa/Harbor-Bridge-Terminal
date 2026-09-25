"""Durable storage path: write-ahead log, atomic snapshots, crash recovery (MC-006),
at-rest encryption with key rotation (MC-024/MC-025).

Durability classes (MC-006-01, returned as ``TxnResult.durability``):

* ``fsync``  -- (default) the record is written *and* ``fsync``-ed before the
  engine applies it and before success is returned.  Data-loss envelope under
  power failure: zero acknowledged writes (assuming honest device flush).
* ``group``  -- records are flushed to the OS on every append and fsync-ed every
  ``group_commit`` records or on :meth:`WriteAheadLog.sync`.  Envelope: at most
  ``group_commit - 1`` acknowledged writes.  Must be explicitly opted into.
* ``none``   -- test-only; refused unless ``allow_unsafe=True``.

On-disk layout inside ``data_dir``::

    snap-<gen>.bin   sealed snapshot (atomic tmp+fsync+rename+dirfsync)
    wal-<gen>.log    frames appended after snapshot <gen>

Frame format: ``b"CSW1" | u32 length | u32 crc32(payload) | payload``.  The payload
is the (optionally AES-256-GCM sealed) canonical JSON record.

Recovery rules (MC-006-06 -- never continue with ambiguous state):

* a frame whose header or body is *incomplete* at the very end of the newest WAL
  is a torn write that was never acknowledged; it is truncated and reported;
* any complete frame with a bad magic/CRC/authentication tag, or any damage
  that is not at the tail, raises :class:`CorruptionError` -- the operator must
  restore from backup or explicitly pass ``allow_tail_truncation=True`` after
  review (recorded in the recovery report);
* snapshots carry a SHA-256 and generation; a corrupt newest snapshot is an
  error, never silently skipped.
"""
from __future__ import annotations

import json
import os
import struct
import threading
import zlib
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from .errors import CorruptionError, InvalidArgument
from .limits import Limits
from .store import ControlStore

MAGIC = b"CSW1"
HDR = struct.Struct(">4sII")
MAX_FRAME = 64 * 1024 * 1024


class SimulatedCrash(BaseException):
    """Raised by fault hooks to emulate process death at a persistence boundary."""


FaultHook = Callable[[str], None]


def _noop(_: str) -> None:
    return None


# --------------------------------------------------------------------------- sealing

class Keyring:
    """Envelope keyring: ``key_id -> 32-byte data key``; one active key.

    Data keys should be unwrapped from a KMS/HSM by a :class:`KeyProvider`
    (see ``security.py``); this class never reads plaintext keys from config.
    """

    def __init__(self, keys: dict[str, bytes], active: str) -> None:
        if active not in keys:
            raise InvalidArgument("active key id not in keyring", field="active")
        for kid, k in keys.items():
            if len(k) != 32 or not kid or len(kid.encode()) > 64:
                raise InvalidArgument("keys must be 32 bytes with a short id", field="keys")
        self._keys = dict(keys)
        self.active = active

    def rotate(self, new_id: str, key: bytes) -> None:
        if len(key) != 32:
            raise InvalidArgument("key must be 32 bytes", field="key")
        self._keys[new_id] = key
        self.active = new_id

    def get(self, kid: str) -> bytes:
        try:
            return self._keys[kid]
        except KeyError:
            raise CorruptionError("unknown data-key id in sealed payload", reason="unknown_key") from None

    @property
    def key_ids(self) -> list[str]:
        return sorted(self._keys)


class Sealer:
    """AES-256-GCM sealing with AAD binding the payload to its file/purpose."""

    def __init__(self, keyring: Keyring) -> None:
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # noqa: F401
        except ImportError as exc:  # fail closed: never write plaintext when encryption was requested
            raise RuntimeError("encryption at rest requested but 'cryptography' is unavailable") from exc
        self.keyring = keyring

    def seal(self, plaintext: bytes, aad: bytes) -> bytes:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        kid = self.keyring.active.encode()
        nonce = os.urandom(12)
        ct = AESGCM(self.keyring.get(self.keyring.active)).encrypt(nonce, plaintext, aad + b"|" + kid)
        return b"E1" + bytes([len(kid)]) + kid + nonce + ct

    def open(self, blob: bytes, aad: bytes) -> bytes:
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        if blob[:2] != b"E1":
            raise CorruptionError("payload is not sealed but encryption is required", reason="plaintext")
        n = blob[2]
        kid = blob[3:3 + n]
        nonce = blob[3 + n:15 + n]
        try:
            return AESGCM(self.keyring.get(kid.decode())).decrypt(nonce, blob[15 + n:], aad + b"|" + kid)
        except InvalidTag as exc:
            raise CorruptionError("authentication tag mismatch", reason="bad_tag") from exc


# --------------------------------------------------------------------------- WAL

@dataclass
class RecoveryReport:
    generation: int = 0
    snapshot_revision: int = 0
    records_replayed: int = 0
    torn_tail_bytes: int = 0
    tail_truncated_by_operator: bool = False
    final_revision: int = 0
    invariant_violations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _fsync_dir(path: str) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


class WriteAheadLog:
    """Append-only journal implementing the ``store.Journal`` protocol."""

    def __init__(self, data_dir: str, generation: int, *, durability: str = "fsync", group_commit: int = 32,
                 sealer: Sealer | None = None, fault: FaultHook = _noop, allow_unsafe: bool = False) -> None:
        if durability not in ("fsync", "group", "none"):
            raise InvalidArgument("durability must be fsync|group|none", field="durability")
        if durability == "none" and not allow_unsafe:
            raise InvalidArgument("durability=none requires allow_unsafe=True", field="durability")
        self.dir = data_dir
        self.generation = generation
        self.durability = durability
        self.group_commit = max(1, group_commit)
        self.sealer = sealer
        self.fault = fault
        self._pending = 0
        self._lock = threading.Lock()
        self.path = os.path.join(data_dir, f"wal-{generation:016d}.log")
        self._fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        self.bytes_written = os.fstat(self._fd).st_size
        self.appends = 0

    def _frame(self, record: dict[str, Any]) -> bytes:
        payload = json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
        if self.sealer:
            payload = self.sealer.seal(payload, f"wal:{self.generation}".encode())
        if len(payload) > MAX_FRAME:
            raise InvalidArgument("record too large for WAL frame", field="record")
        return HDR.pack(MAGIC, len(payload), zlib.crc32(payload)) + payload

    def append(self, record: dict[str, Any]) -> None:
        frame = self._frame(record)
        with self._lock:
            self.fault("wal.before_write")
            half = len(frame) // 2
            os.write(self._fd, frame[:half])
            self.fault("wal.mid_write")
            os.write(self._fd, frame[half:])
            self.fault("wal.before_fsync")
            self._pending += 1
            if self.durability == "fsync" or (self.durability == "group" and self._pending >= self.group_commit):
                os.fsync(self._fd)
                self._pending = 0
            self.fault("wal.after_fsync")
            self.bytes_written += len(frame)
            self.appends += 1

    def sync(self) -> None:
        with self._lock:
            os.fsync(self._fd)
            self._pending = 0

    def close(self) -> None:
        with self._lock:
            if self._fd >= 0:
                try:
                    os.fsync(self._fd)
                finally:
                    os.close(self._fd)
                    self._fd = -1


def read_frames(path: str, sealer: Sealer | None, generation: int, *, is_tail_file: bool,
                allow_tail_truncation: bool = False) -> tuple[list[dict[str, Any]], int, bool]:
    """Return ``(records, torn_bytes, operator_truncated)``; raise on ambiguous damage."""
    with open(path, "rb") as fh:
        data = fh.read()
    out: list[dict[str, Any]] = []
    off = 0
    while off < len(data):
        rest = len(data) - off
        if rest < HDR.size:
            if is_tail_file:
                return out, rest, False
            raise CorruptionError(f"truncated frame header in non-tail WAL {os.path.basename(path)}")
        magic, n, crc = HDR.unpack_from(data, off)
        if magic != MAGIC or n > MAX_FRAME:
            if is_tail_file and allow_tail_truncation:
                return out, rest, True
            raise CorruptionError(f"bad frame header at offset {off} in {os.path.basename(path)}")
        if rest < HDR.size + n:
            if is_tail_file:
                return out, rest, False  # torn, never acknowledged
            raise CorruptionError(f"truncated frame in non-tail WAL {os.path.basename(path)}")
        payload = data[off + HDR.size: off + HDR.size + n]
        last = off + HDR.size + n == len(data)
        if zlib.crc32(payload) != crc:
            if is_tail_file and last and allow_tail_truncation:
                return out, HDR.size + n, True
            raise CorruptionError(f"CRC mismatch at offset {off} in {os.path.basename(path)}")
        if sealer:
            payload = sealer.open(payload, f"wal:{generation}".encode())
        elif payload[:2] == b"E1":
            raise CorruptionError("WAL is encrypted but no keyring was supplied")
        out.append(json.loads(payload))
        off += HDR.size + n
    return out, 0, False


def _generations(data_dir: str) -> tuple[list[int], list[int]]:
    snaps, wals = [], []
    for name in os.listdir(data_dir):
        if name.startswith("snap-") and name.endswith(".bin"):
            snaps.append(int(name[5:-4]))
        elif name.startswith("wal-") and name.endswith(".log"):
            wals.append(int(name[4:-4]))
    return sorted(snaps), sorted(wals)


def write_snapshot(data_dir: str, generation: int, state: dict[str, Any], sealer: Sealer | None,
                   fault: FaultHook = _noop) -> str:
    import hashlib
    body = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    meta = {"schema": "cstate.snapfile/1", "generation": generation, "revision": state["revision"],
            "sha256": hashlib.sha256(body).hexdigest(), "sealed": bool(sealer)}
    if sealer:
        body = sealer.seal(body, f"snap:{generation}".encode())
    blob = json.dumps(meta, sort_keys=True).encode() + b"\n" + body
    final = os.path.join(data_dir, f"snap-{generation:016d}.bin")
    tmp = final + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(blob)
        fh.flush()
        os.fsync(fh.fileno())
    fault("snap.before_rename")
    os.replace(tmp, final)
    _fsync_dir(data_dir)
    fault("snap.after_rename")
    return final


def read_snapshot(path: str, sealer: Sealer | None) -> dict[str, Any]:
    import hashlib
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        head, body = raw.split(b"\n", 1)
        meta = json.loads(head)
    except ValueError as exc:
        raise CorruptionError(f"unreadable snapshot header {os.path.basename(path)}") from exc
    if meta.get("sealed"):
        if not sealer:
            raise CorruptionError("snapshot is encrypted but no keyring was supplied")
        body = sealer.open(body, f"snap:{meta['generation']}".encode())
    elif sealer:
        raise CorruptionError("plaintext snapshot found while encryption at rest is required")
    if hashlib.sha256(body).hexdigest() != meta.get("sha256"):
        raise CorruptionError(f"snapshot checksum mismatch {os.path.basename(path)}")
    state = json.loads(body)
    if state.get("revision") != meta.get("revision"):
        raise CorruptionError("snapshot revision does not match header")
    return state


class DurableStore:
    """Owns a :class:`ControlStore` plus its WAL/snapshot directory."""

    def __init__(self, store: ControlStore, wal: WriteAheadLog, report: RecoveryReport, *,
                 sealer: Sealer | None, fault: FaultHook) -> None:
        self.store, self.wal, self.report, self.sealer, self.fault = store, wal, report, sealer, fault
        self._ckpt_lock = threading.Lock()

    @classmethod
    def open(cls, data_dir: str, *, limits: Limits | None = None, durability: str = "fsync",
             group_commit: int = 32, sealer: Sealer | None = None, fault: FaultHook = _noop,
             allow_tail_truncation: bool = False, allow_unsafe: bool = False, clock=None) -> "DurableStore":
        os.makedirs(data_dir, mode=0o700, exist_ok=True)
        for name in os.listdir(data_dir):  # an interrupted snapshot never became authoritative
            if name.endswith(".tmp"):
                os.remove(os.path.join(data_dir, name))
        snaps, wals = _generations(data_dir)
        kw = {"clock": clock} if clock else {}
        store = ControlStore(limits, **kw)
        rep = RecoveryReport()
        gen = 0
        if snaps:
            gen = snaps[-1]
            store.load_state(read_snapshot(os.path.join(data_dir, f"snap-{gen:016d}.bin"), sealer))
            rep.snapshot_revision = store.revision
        replay = [g for g in wals if g >= gen]
        if wals and not snaps and wals[0] != 0:
            raise CorruptionError("WAL generations present without their base snapshot")
        for g in replay:
            path = os.path.join(data_dir, f"wal-{g:016d}.log")
            recs, torn, op_trunc = read_frames(path, sealer, g, is_tail_file=(g == replay[-1]),
                                               allow_tail_truncation=allow_tail_truncation)
            for r in recs:
                try:
                    store.apply_record(r)
                except (ValueError, KeyError) as exc:
                    raise CorruptionError(f"WAL record failed to apply: {exc}") from exc
                rep.records_replayed += 1
            if torn:
                with open(path, "r+b") as fh:
                    fh.truncate(os.path.getsize(path) - torn)
                    os.fsync(fh.fileno())
                rep.torn_tail_bytes = torn
                rep.tail_truncated_by_operator = op_trunc
        gen = max([gen] + replay)
        rep.generation = gen
        rep.final_revision = store.revision
        rep.invariant_violations = store.check_invariants()
        if rep.invariant_violations:
            raise CorruptionError("recovered state violates invariants: " + "; ".join(rep.invariant_violations))
        wal = WriteAheadLog(data_dir, gen, durability=durability, group_commit=group_commit, sealer=sealer,
                            fault=fault, allow_unsafe=allow_unsafe)
        store.journal = wal
        return cls(store, wal, rep, sealer=sealer, fault=fault)

    def checkpoint(self) -> int:
        """Write snapshot gen+1 atomically, switch to a fresh WAL, prune old files."""
        with self._ckpt_lock, self.store.lock:
            state = self.store.export_state()
            new_gen = self.wal.generation + 1
            write_snapshot(self.wal.dir, new_gen, state, self.sealer, self.fault)
            old = self.wal
            self.wal = WriteAheadLog(old.dir, new_gen, durability=old.durability, group_commit=old.group_commit,
                                     sealer=self.sealer, fault=self.fault, allow_unsafe=True)
            self.store.journal = self.wal
            old.close()
            _fsync_dir(old.dir)
            for name in os.listdir(old.dir):  # keep current and previous generation
                for pre, suf in (("snap-", ".bin"), ("wal-", ".log")):
                    if name.startswith(pre) and name.endswith(suf) and int(name[len(pre):-len(suf)]) < new_gen - 1:
                        os.remove(os.path.join(old.dir, name))
            return new_gen

    def close(self) -> None:
        self.wal.close()
