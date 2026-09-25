"""MC18 replication transport adapter and MC43 zero-copy/binary encoding path.

The model stays transport-agnostic: this module only frames, carries and retries
``PK_REPLICATED_WRITE/1`` documents between authenticated sessions.

Frames: ``b"G5FR" | kind(u8) | length(u32) | crc32(u32) | payload``.  Receivers reject
bad magic, oversize frames (> limits.max_frame_bytes) and CRC mismatches.

Binary write encoding (``encode_write_bin``/``decode_write_bin``): a length-prefixed
field layout decoded through ``memoryview`` slices, so large values are not copied until
materialised.  It is a lossless alternative encoding of the same schema: the decoder
re-validates the reconstructed document (including its content-addressed op_id).

``Link`` is a deterministic fault-injecting channel (seeded drop / duplicate / reorder /
delay) used by partition tests.  ``ReliableSender`` gives at-least-once delivery with a
bounded in-flight window (flow control / backpressure), per-frame ack, retransmit on
timeout ticks, and a bounded retry budget; receiver idempotency comes from op_id dedupe
in the node, so at-least-once never becomes double application.
"""
from __future__ import annotations

import json
import random
import struct
import zlib
from collections import deque

from .errors import CapacityError, SchemaError
from .limits import DEFAULT_LIMITS, Limits
from .schemas import canonical_bytes, strict_loads, validate_write_doc

FRAME = struct.Struct("<4sBII")
FRAME_MAGIC = b"G5FR"
KIND_WRITE, KIND_ACK, KIND_HELLO, KIND_BIN_WRITE = 1, 2, 3, 4


def encode_frame(kind: int, payload: bytes) -> bytes:
    return FRAME.pack(FRAME_MAGIC, kind, len(payload), zlib.crc32(payload)) + payload


def decode_frame(buf: bytes | memoryview, limits: Limits = DEFAULT_LIMITS) -> tuple[int, memoryview, int]:
    mv = memoryview(buf)
    if len(mv) < FRAME.size:
        raise SchemaError("short frame header", code="CORR_FRAME_SHORT")
    magic, kind, length, crc = FRAME.unpack_from(mv)
    if magic != FRAME_MAGIC:
        raise SchemaError("bad frame magic", code="CORR_FRAME_MAGIC")
    if length > limits.max_frame_bytes:
        raise SchemaError("frame too large", code="CAP_FRAME_SIZE")
    end = FRAME.size + length
    if len(mv) < end:
        raise SchemaError("truncated frame", code="CORR_FRAME_SHORT")
    payload = mv[FRAME.size:end]
    if zlib.crc32(payload) != crc:
        raise SchemaError("frame CRC mismatch", code="CORR_FRAME_CRC")
    return kind, payload, end


# ---------------------------------------------------------------- binary codec (MC43)
_U16 = struct.Struct("<H")
_U32 = struct.Struct("<I")
_U64 = struct.Struct("<Q")
_STR_FIELDS = ("tenant", "environment", "key", "site", "op_id")


def _put(out: bytearray, data: bytes, wide=False):
    out += (_U32 if wide else _U16).pack(len(data))
    out += data


def encode_write_bin(doc: dict) -> bytes:
    out = bytearray(b"G5W1")
    for f in _STR_FIELDS:
        _put(out, doc[f].encode("utf-8"))
    _put(out, doc["value"].encode("utf-8"), wide=True)
    out += _U64.pack(doc["epoch"])
    flags = (1 if doc.get("deleted") else 0) | (2 if "value_type" in doc else 0) | (4 if "provenance" in doc else 0)
    out.append(flags)
    if flags & 2:
        _put(out, doc["value_type"].encode("utf-8"))
    if flags & 4:
        _put(out, canonical_bytes(doc["provenance"]))
    out += _U16.pack(len(doc["vector"]))
    for site, counter in doc["vector"]:
        _put(out, site.encode("utf-8"))
        out += _U64.pack(counter)
    return bytes(out)


class _Reader:
    def __init__(self, mv: memoryview):
        self.mv, self.pos = mv, 0

    def take(self, n) -> memoryview:
        if self.pos + n > len(self.mv):
            raise SchemaError("truncated binary write", code="CORR_BIN_TRUNCATED")
        v = self.mv[self.pos:self.pos + n]
        self.pos += n
        return v

    def u(self, st):
        return st.unpack(self.take(st.size))[0]

    def blob(self, wide=False) -> memoryview:
        return self.take(self.u(_U32 if wide else _U16))


def decode_write_bin(data, limits: Limits = DEFAULT_LIMITS, *, lazy_value=False):
    r = _Reader(memoryview(data))
    if bytes(r.take(4)) != b"G5W1":
        raise SchemaError("bad binary write magic", code="CORR_BIN_MAGIC")
    try:
        doc = {f: str(r.blob(), "utf-8") for f in _STR_FIELDS}
        value_view = r.blob(wide=True)
        doc["epoch"] = r.u(_U64)
        flags = r.take(1)[0]
        if flags & ~7:
            raise SchemaError("unknown binary flags", code="CORR_BIN_FLAGS")
        if flags & 1:
            doc["deleted"] = True
        if flags & 2:
            doc["value_type"] = str(r.blob(), "utf-8")
        if flags & 4:
            doc["provenance"] = strict_loads(bytes(r.blob()), limits)
        n = r.u(_U16)
        if n > limits.max_vector_entries:
            raise SchemaError("vector too large", code="CAP_VECTOR_SIZE")
        doc["vector"] = [[str(r.blob(), "utf-8"), r.u(_U64)] for _ in range(n)]
    except UnicodeDecodeError as exc:
        raise SchemaError("invalid UTF-8 in binary write", code="CORR_SCHEMA_ENCODING") from exc
    if r.pos != len(r.mv):
        raise SchemaError("trailing bytes after binary write", code="CORR_BIN_TRAILING")
    if lazy_value:
        return doc, value_view
    doc["value"] = str(value_view, "utf-8")
    doc["schema"] = "PK_REPLICATED_WRITE/1"
    return validate_write_doc(doc, limits)


# ---------------------------------------------------------------- fault-injecting link
class Link:
    def __init__(self, *, seed=0, drop=0.0, dup=0.0, reorder=0.0, delay_max=0, capacity=10_000):
        self.rng = random.Random(seed)
        self.drop, self.dup, self.reorder, self.delay_max = drop, dup, reorder, delay_max
        self.capacity = capacity
        self.queue: list[tuple[int, bytes]] = []
        self.tick = 0
        self.partitioned = False
        self.stats = {"sent": 0, "dropped": 0, "duplicated": 0, "delivered": 0, "refused": 0}

    def send(self, frame: bytes):
        if len(self.queue) >= self.capacity:
            self.stats["refused"] += 1
            raise CapacityError("link queue full", code="CAP_LINK_FULL")
        self.stats["sent"] += 1
        if self.partitioned or self.rng.random() < self.drop:
            self.stats["dropped"] += 1
            return
        copies = 2 if self.rng.random() < self.dup else 1
        self.stats["duplicated"] += copies - 1
        for _ in range(copies):
            due = self.tick + (self.rng.randint(0, self.delay_max) if self.delay_max else 0)
            self.queue.append((due, frame))
        if self.rng.random() < self.reorder and len(self.queue) > 1:
            i, j = self.rng.randrange(len(self.queue)), self.rng.randrange(len(self.queue))
            self.queue[i], self.queue[j] = self.queue[j], self.queue[i]

    def advance(self) -> list[bytes]:
        self.tick += 1
        ready = [f for due, f in self.queue if due <= self.tick]
        self.queue = [(d, f) for d, f in self.queue if d > self.tick]
        self.stats["delivered"] += len(ready)
        return ready


class ReliableSender:
    """At-least-once sender with bounded window and retry budget."""

    def __init__(self, link: Link, *, window=64, timeout_ticks=3, max_retries=50, max_pending=100_000):
        self.link, self.window, self.timeout, self.max_retries = link, window, timeout_ticks, max_retries
        self.max_pending = max_pending
        self.pending: deque[tuple[str, bytes]] = deque()
        self.inflight: dict[str, list] = {}
        self.acked: set[str] = set()
        self.failed: list[str] = []

    def enqueue(self, doc: dict):
        if len(self.pending) + len(self.inflight) >= self.max_pending:
            raise CapacityError("sender backlog full (backpressure)", code="CAP_SENDER_BACKLOG")
        self.pending.append((doc["op_id"], encode_frame(KIND_WRITE, canonical_bytes(doc))))

    @property
    def backlog(self) -> int:
        return len(self.pending) + len(self.inflight)

    def pump(self, tick: int):
        for op, entry in list(self.inflight.items()):
            if tick - entry[1] >= self.timeout:
                if entry[2] >= self.max_retries:
                    self.failed.append(op)
                    del self.inflight[op]
                    continue
                entry[1], entry[2] = tick, entry[2] + 1
                self.link.send(entry[0])
        while self.pending and len(self.inflight) < self.window:
            op, frame = self.pending.popleft()
            self.inflight[op] = [frame, tick, 0]
            self.link.send(frame)

    def on_ack(self, op_id: str):
        self.inflight.pop(op_id, None)
        self.acked.add(op_id)


def ack_frame(op_id: str) -> bytes:
    return encode_frame(KIND_ACK, op_id.encode("ascii"))


def parse_write_frame(payload: memoryview, limits: Limits = DEFAULT_LIMITS) -> dict:
    return validate_write_doc(strict_loads(bytes(payload), limits), limits)
