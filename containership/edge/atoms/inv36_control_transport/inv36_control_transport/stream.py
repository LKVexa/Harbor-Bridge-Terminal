"""PK_CTRL_STREAM/1 - length-delimited record framing over an untrusted byte stream.

Stream transports (virtio-vsock, and socketpair/fake streams in tests) carry
bytes, not messages (MC-03.007).  This module owns:

* a 6-byte version preamble exchanged by both peers before any record, so a
  legacy ``PK_CTRL_FRAME/1`` peer is rejected before payload processing
  (MC-03.016);
* 6-byte record headers ``type:u8 | reserved:u8 | length:u32`` whose length is
  validated against the hard bound *before* any payload buffer is allocated
  (MC-03.008, MC-14.013);
* a single-owner reader and a serialized writer so concurrent callers can
  neither interleave partial records nor steal bytes from each other
  (MC-03.014/.015);
* clean EOF semantics: EOF exactly on a record boundary is a graceful close
  (:class:`StreamEOF`), EOF mid-record is :class:`StreamTruncated` (MC-03.017).

Nothing in this module decrypts: records are returned only once complete and
bounded, and PK_CTRL_FRAME/2 authentication happens in :mod:`.transport`
(MC-03.011).
"""
from __future__ import annotations

import collections
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Deque, Protocol

from . import _wire
from .errors import ErrorCode, Inv36Error

PREAMBLE = _wire.STREAM_PREAMBLE
RECORD_TYPES = dict(_wire.STREAM_RECORD_TYPES)
HANDSHAKE = RECORD_TYPES["HANDSHAKE"]
FRAME = RECORD_TYPES["FRAME"]
CLOSE = RECORD_TYPES["CLOSE"]
MAX_RECORD = _wire.STREAM_MAX_RECORD
_REC = struct.Struct(">BBI")
RECORD_HEADER = _REC.size


class StreamError(Inv36Error, ConnectionError):
    code = ErrorCode.STREAM_RESET


class StreamEOF(StreamError):
    """Peer closed the stream cleanly on a record boundary."""

    code = ErrorCode.STREAM_EOF


class StreamTruncated(StreamError):
    code = ErrorCode.STREAM_TRUNCATED


class StreamLengthInvalid(StreamError):
    code = ErrorCode.STREAM_LENGTH_INVALID


class StreamTimeout(StreamError, TimeoutError):
    code = ErrorCode.STREAM_TIMEOUT


class StreamReset(StreamError):
    code = ErrorCode.STREAM_RESET


class StreamUnavailable(StreamError):
    code = ErrorCode.STREAM_UNAVAILABLE


class StreamBusy(StreamError):
    code = ErrorCode.STREAM_BUSY


class ByteStream(Protocol):
    """Minimal transport contract implemented by vsock sockets and test doubles.

    ``recv`` returns ``b""`` only on orderly EOF and raises :class:`StreamTimeout`
    when ``timeout`` elapses; ``send`` may write fewer bytes than requested.
    """

    def recv(self, max_bytes: int, timeout: float | None) -> bytes: ...

    def send(self, data: bytes, timeout: float | None) -> int: ...

    def close(self) -> None: ...


def encode_record(record_type: int, payload: bytes = b"") -> bytes:
    if record_type not in RECORD_TYPES.values():
        raise StreamLengthInvalid(f"unknown record type {record_type}")
    if len(payload) > MAX_RECORD:
        raise StreamLengthInvalid("record above protocol bound", detail={"length": len(payload)})
    if record_type == CLOSE and payload:
        raise StreamLengthInvalid("CLOSE records carry no payload")
    return _REC.pack(record_type, 0, len(payload)) + payload


def parse_record_header(header: bytes, *, limit: int = MAX_RECORD) -> tuple[int, int]:
    """Validate a record header; raise before the caller allocates ``length`` bytes."""
    if len(header) != RECORD_HEADER:
        raise StreamTruncated("short record header")
    rtype, reserved, length = _REC.unpack(header)
    if rtype not in RECORD_TYPES.values():
        raise StreamLengthInvalid("unknown record type", detail={"record_type": rtype})
    if reserved != 0:
        raise StreamLengthInvalid("reserved header byte must be zero")
    if length > min(limit, MAX_RECORD):
        raise StreamLengthInvalid("advertised record length above bound", detail={"length": length})
    if rtype == CLOSE and length != 0:
        raise StreamLengthInvalid("CLOSE with payload")
    return rtype, length


class _Deadline:
    def __init__(self, timeout: float | None) -> None:
        self.end = None if timeout is None else time.monotonic() + timeout

    def remaining(self) -> float | None:
        if self.end is None:
            return None
        left = self.end - time.monotonic()
        if left <= 0:
            raise StreamTimeout("deadline exceeded")
        return left


@dataclass
class Connection:
    """Owns framing for one byte stream: one reader, serialized writers.

    ``read_timeout``/``write_timeout`` are per-record deadlines.  Every failure
    path closes the underlying stream exactly once (MC-03.010).
    """

    stream: ByteStream
    read_timeout: float | None = 30.0
    write_timeout: float | None = 30.0
    max_record: int = MAX_RECORD
    on_close: Callable[[], None] | None = None
    bytes_in: int = field(default=0, init=False)
    bytes_out: int = field(default=0, init=False)
    records_in: int = field(default=0, init=False)
    records_out: int = field(default=0, init=False)
    closed: bool = field(default=False, init=False)
    _rlock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _wlock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _close_lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _buf: bytearray = field(default_factory=bytearray, init=False, repr=False)

    # -- low level -----------------------------------------------------------------
    def _read_exact(self, n: int, deadline: _Deadline, *, at_boundary: bool) -> bytes:
        while len(self._buf) < n:
            want = max(n - len(self._buf), 1)
            try:
                chunk = self.stream.recv(min(want, 65536), deadline.remaining())
            except StreamError:
                raise
            except TimeoutError as exc:
                raise StreamTimeout("read deadline exceeded") from exc
            except (ConnectionResetError, BrokenPipeError) as exc:
                raise StreamReset("connection reset by peer") from exc
            except OSError as exc:
                raise StreamReset(f"stream error: {type(exc).__name__}") from exc
            if not chunk:
                if at_boundary and not self._buf:
                    raise StreamEOF("peer closed stream")
                raise StreamTruncated("EOF inside record")
            self._buf += chunk
            self.bytes_in += len(chunk)
        out = bytes(self._buf[:n])
        del self._buf[:n]
        return out

    def _write_all(self, data: bytes, deadline: _Deadline) -> None:
        view = memoryview(data)
        while view:
            try:
                sent = self.stream.send(bytes(view), deadline.remaining())
            except StreamError:
                raise
            except TimeoutError as exc:
                raise StreamTimeout("write deadline exceeded") from exc
            except (ConnectionResetError, BrokenPipeError) as exc:
                raise StreamReset("connection reset by peer") from exc
            except OSError as exc:
                raise StreamReset(f"stream error: {type(exc).__name__}") from exc
            if sent <= 0:
                raise StreamReset("stream accepted no bytes")
            view = view[sent:]
            self.bytes_out += sent

    def _fail(self) -> None:
        self.close()

    # -- public ----------------------------------------------------------------------
    def exchange_preamble(self, timeout: float | None = None) -> None:
        """Send our preamble and require the peer's to match exactly."""
        try:
            with self._wlock:
                self._write_all(PREAMBLE, _Deadline(timeout if timeout is not None else self.write_timeout))
            with self._rlock:
                got = self._read_exact(len(PREAMBLE), _Deadline(timeout if timeout is not None else self.read_timeout),
                                       at_boundary=True)
        except StreamError:
            self._fail()
            raise
        if got != PREAMBLE:
            self._fail()
            raise StreamLengthInvalid("peer preamble is not PK_CTRL_STREAM/1 (legacy or foreign peer)")

    def send_record(self, record_type: int, payload: bytes = b"") -> None:
        if self.closed:
            raise StreamReset("connection closed")
        data = encode_record(record_type, payload)
        if len(payload) > self.max_record:
            raise StreamLengthInvalid("record above configured bound")
        if not self._wlock.acquire(timeout=self.write_timeout if self.write_timeout is not None else -1):
            raise StreamTimeout("writer lock wait exceeded")
        try:
            self._write_all(data, _Deadline(self.write_timeout))
            self.records_out += 1
        except StreamError:
            self._fail()
            raise
        finally:
            self._wlock.release()

    def recv_record(self) -> tuple[int, bytes]:
        if self.closed:
            raise StreamReset("connection closed")
        if not self._rlock.acquire(blocking=False):
            raise StreamBusy("another reader owns this stream")
        try:
            deadline = _Deadline(self.read_timeout)
            header = self._read_exact(RECORD_HEADER, deadline, at_boundary=True)
            rtype, length = parse_record_header(header, limit=self.max_record)
            payload = self._read_exact(length, deadline, at_boundary=False) if length else b""
            self.records_in += 1
            if rtype == CLOSE:
                raise StreamEOF("peer sent CLOSE")
            return rtype, payload
        except StreamError:
            self._fail()
            raise
        finally:
            self._rlock.release()

    def close(self, *, graceful: bool = False) -> None:
        with self._close_lock:
            if self.closed:
                return
            if graceful:
                try:
                    if self._wlock.acquire(timeout=1.0):
                        try:
                            self._write_all(encode_record(CLOSE), _Deadline(1.0))
                        finally:
                            self._wlock.release()
                except (StreamError, OSError):
                    pass
            self.closed = True
            self._buf.clear()  # discard unauthenticated buffered bytes (MC-10.008)
            try:
                self.stream.close()
            finally:
                if self.on_close:
                    self.on_close()


# ---------------------------------------------------------------------------------
# Deterministic fake byte stream (MC-03.034, MC-14.004, MC-03.039)
# ---------------------------------------------------------------------------------
@dataclass
class FaultPlan:
    """Scripted faults for :class:`FakeStream`.

    ``max_chunk`` fragments every read/write; ``reset_after_bytes`` raises a
    reset once that many bytes have been *sent*; ``stall_reads`` makes reads
    time out; ``short_write`` caps each send call.
    """

    max_chunk: int = 0
    short_write: int = 0
    reset_after_bytes: int = -1
    stall_reads: bool = False
    drop_after_bytes: int = -1


class _Pipe:
    def __init__(self, capacity: int) -> None:
        self.data: Deque[bytes] = collections.deque()
        self.size = 0
        self.capacity = capacity
        self.eof = False
        self.reset = False
        self.cv = threading.Condition()


class FakeStream:
    """In-memory duplex stream pair with bounded buffers and fault injection."""

    def __init__(self, rx: _Pipe, tx: _Pipe, plan: FaultPlan | None = None) -> None:
        self._rx, self._tx = rx, tx
        self.plan = plan or FaultPlan()
        self.sent = 0
        self.closed = False

    @classmethod
    def pair(cls, capacity: int = 1 << 20, a_plan: FaultPlan | None = None,
             b_plan: FaultPlan | None = None) -> tuple["FakeStream", "FakeStream"]:
        p1, p2 = _Pipe(capacity), _Pipe(capacity)
        return cls(p1, p2, a_plan), cls(p2, p1, b_plan)

    def recv(self, max_bytes: int, timeout: float | None) -> bytes:
        if self.plan.stall_reads:
            if timeout is not None:
                time.sleep(min(timeout, 0.01))
            raise StreamTimeout("stalled")
        limit = max_bytes if not self.plan.max_chunk else min(max_bytes, self.plan.max_chunk)
        with self._rx.cv:
            end = None if timeout is None else time.monotonic() + timeout
            while not self._rx.data and not self._rx.eof and not self._rx.reset:
                left = None if end is None else end - time.monotonic()
                if left is not None and left <= 0:
                    raise StreamTimeout("recv timeout")
                self._rx.cv.wait(left)
            if self._rx.reset:
                raise ConnectionResetError("reset")
            if not self._rx.data:
                return b""
            head = self._rx.data[0]
            out, rest = head[:limit], head[limit:]
            if rest:
                self._rx.data[0] = rest
            else:
                self._rx.data.popleft()
            self._rx.size -= len(out)
            self._rx.cv.notify_all()
            return out

    def send(self, data: bytes, timeout: float | None) -> int:
        if self.closed:
            raise BrokenPipeError("closed")
        n = len(data)
        if self.plan.short_write:
            n = min(n, self.plan.short_write)
        if self.plan.max_chunk:
            n = min(n, self.plan.max_chunk)
        if self.plan.reset_after_bytes >= 0 and self.sent + n > self.plan.reset_after_bytes:
            n = self.plan.reset_after_bytes - self.sent
            if n <= 0:
                with self._tx.cv:
                    self._tx.reset = True
                    self._tx.cv.notify_all()
                raise ConnectionResetError("injected reset")
        if self.plan.drop_after_bytes >= 0 and self.sent + n > self.plan.drop_after_bytes:
            # Silently black-hole bytes (models a stalled peer / dropped path).
            self.sent += n
            return n
        with self._tx.cv:
            end = None if timeout is None else time.monotonic() + timeout
            while self._tx.size + n > self._tx.capacity:
                left = None if end is None else end - time.monotonic()
                if left is not None and left <= 0:
                    raise StreamTimeout("send buffer full")
                self._tx.cv.wait(left)
            if self._tx.reset or self._tx.eof:
                raise BrokenPipeError("peer gone")
            self._tx.data.append(bytes(data[:n]))
            self._tx.size += n
            self._tx.cv.notify_all()
        self.sent += n
        return n

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        with self._tx.cv:
            self._tx.eof = True
            self._tx.cv.notify_all()

    def reset(self) -> None:
        """Abortive close visible to the peer as a reset."""
        self.closed = True
        for p in (self._tx, self._rx):
            with p.cv:
                p.reset = True
                p.cv.notify_all()


class SocketStream:
    """Adapts a connected stream socket (AF_VSOCK, AF_UNIX) to :class:`ByteStream`."""

    def __init__(self, sock) -> None:  # socket.socket
        self.sock = sock
        self._closed = False

    def recv(self, max_bytes: int, timeout: float | None) -> bytes:
        self.sock.settimeout(timeout)
        try:
            return self.sock.recv(max_bytes)
        except TimeoutError as exc:
            raise StreamTimeout("socket read timeout") from exc
        except InterruptedError:  # pragma: no cover - PEP 475 retries EINTR
            return self.recv(max_bytes, timeout)
        except BlockingIOError as exc:  # EAGAIN on a nonblocking socket
            raise StreamTimeout("socket would block") from exc

    def send(self, data: bytes, timeout: float | None) -> int:
        self.sock.settimeout(timeout)
        try:
            return self.sock.send(data)
        except TimeoutError as exc:
            raise StreamTimeout("socket write timeout") from exc
        except BlockingIOError as exc:
            raise StreamTimeout("socket would block") from exc

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            import socket as _s
            self.sock.shutdown(_s.SHUT_RDWR)
        except OSError:
            pass
        self.sock.close()
