"""M04 - Canonical binary value codec and byte-level frame format.

Value encoding (little-endian, deterministic, one encoding per value):

    bool            1 byte, 0x00 / 0x01 only
    u8..u64 s8..s64 fixed width two's complement, range-checked
    f32 / f64       IEEE-754; every NaN is canonicalised to the quiet NaN
                    0x7fc00000 / 0x7ff8000000000000; +/-inf allowed
    char            u32 Unicode scalar value (surrogates rejected)
    string          u32 byte length + UTF-8 (strict)
    list<T>         u32 count + elements
    option<T>       u8 tag (0 none, 1 some) + value
    result<T, E>    u8 tag (0 ok, 1 err) + payload if the side is typed
    tuple / record  fields in declaration order, no names on the wire
    enum            u32 case index

Frame format ``PK_WRPC_FRAME/2`` (12-byte header + body):

    magic "WRPC" | u8 major | u8 minor | u8 kind | u8 flags | u32 body length

The length prefix is checked against ``Limits.max_frame_bytes`` BEFORE any
body buffer is allocated.  Decoding rejects trailing bytes, unknown tags,
oversize collections, excess nesting and invalid UTF-8.  No pickle, eval or
dynamic import is used anywhere on the decode path.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Any

MAGIC = b"WRPC"
HEADER = struct.Struct("<4sBBBBI")
HEADER_SIZE = HEADER.size  # 12

KIND_REQUEST = 1
KIND_RESPONSE = 2
KIND_HELLO = 3
KIND_HELLO_ACK = 4
KIND_CANCEL = 5
KINDS = {KIND_REQUEST, KIND_RESPONSE, KIND_HELLO, KIND_HELLO_ACK, KIND_CANCEL}

_INT = {
    "u8": ("<B", 0, 2**8 - 1), "u16": ("<H", 0, 2**16 - 1),
    "u32": ("<I", 0, 2**32 - 1), "u64": ("<Q", 0, 2**64 - 1),
    "s8": ("<b", -2**7, 2**7 - 1), "s16": ("<h", -2**15, 2**15 - 1),
    "s32": ("<i", -2**31, 2**31 - 1), "s64": ("<q", -2**63, 2**63 - 1),
}
_QNAN32 = b"\x00\x00\xc0\x7f"
_QNAN64 = b"\x00\x00\x00\x00\x00\x00\xf8\x7f"


class CodecError(ValueError):
    """Stable, non-throwing-for-callers codec failure with a reason code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Limits:
    max_frame_bytes: int = 1 << 20      # 1 MiB
    max_depth: int = 16
    max_collection: int = 65_536
    max_string_bytes: int = 256 * 1024


DEFAULT_LIMITS = Limits()


# ---------------------------------------------------------------- encode
_PLAN: dict[Any, Any] = {}


def _plan(t: Any):
    """Per-type field plan for records/tuples (cached; types are hashable)."""
    p = _PLAN.get(t)
    if p is None:
        if isinstance(t, tuple) and t[0] == "record":
            p = ("record", tuple(n for n, _ in t[1]), tuple(ft for _, ft in t[1]), frozenset(n for n, _ in t[1]))
        else:
            p = False
        if len(_PLAN) < 4096:
            _PLAN[t] = p
    return p


def encode(t: Any, v: Any, limits: Limits = DEFAULT_LIMITS) -> bytes:
    out = bytearray()
    _enc(t, v, out, limits, 0)
    if len(out) > limits.max_frame_bytes:
        raise CodecError("value-too-large")
    return bytes(out)


def _enc(t: Any, v: Any, out: bytearray, lim: Limits, depth: int) -> None:
    if depth > lim.max_depth:
        raise CodecError("depth")
    if isinstance(t, str):
        if t == "bool":
            if not isinstance(v, bool):
                raise CodecError("type:bool")
            out.append(1 if v else 0)
        elif t in _INT:
            fmt, lo, hi = _INT[t]
            if isinstance(v, bool) or not isinstance(v, int):
                raise CodecError(f"type:{t}")
            if not lo <= v <= hi:
                raise CodecError(f"range:{t}")
            out += struct.pack(fmt, v)
        elif t in ("f32", "f64"):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise CodecError(f"type:{t}")
            v = float(v)
            if math.isnan(v):
                out += _QNAN32 if t == "f32" else _QNAN64
            else:
                try:
                    out += struct.pack("<f" if t == "f32" else "<d", v)
                except OverflowError:
                    raise CodecError("range:f32") from None
        elif t == "char":
            if not isinstance(v, str) or len(v) != 1 or 0xD800 <= ord(v) <= 0xDFFF:
                raise CodecError("type:char")
            out += struct.pack("<I", ord(v))
        elif t == "string":
            if not isinstance(v, str):
                raise CodecError("type:string")
            try:
                b = v.encode("utf-8", "strict")
            except UnicodeEncodeError:
                raise CodecError("utf8") from None
            if len(b) > lim.max_string_bytes:
                raise CodecError("string-limit")
            out += struct.pack("<I", len(b)) + b
        elif t == "bytes":  # internal: list<u8> fast path for envelopes
            if not isinstance(v, (bytes, bytearray)):
                raise CodecError("type:bytes")
            if len(v) > lim.max_frame_bytes:
                raise CodecError("bytes-limit")
            out += struct.pack("<I", len(v)) + bytes(v)
        else:
            raise CodecError(f"unknown-type:{t}")
        return
    kind = t[0]
    if kind == "list":
        if not isinstance(v, (list, tuple)):
            raise CodecError("type:list")
        if len(v) > lim.max_collection:
            raise CodecError("collection-limit")
        out += struct.pack("<I", len(v))
        for x in v:
            _enc(t[1], x, out, lim, depth + 1)
    elif kind == "option":
        if v is None:
            out.append(0)
        else:
            out.append(1)
            _enc(t[1], v, out, lim, depth + 1)
    elif kind == "result":
        if not (isinstance(v, tuple) and len(v) == 2 and v[0] in ("ok", "err")):
            raise CodecError("type:result")
        side = t[1] if v[0] == "ok" else t[2]
        out.append(0 if v[0] == "ok" else 1)
        if side is None:
            if v[1] is not None:
                raise CodecError("type:result-unit")
        else:
            _enc(side, v[1], out, lim, depth + 1)
    elif kind == "tuple":
        if not isinstance(v, (list, tuple)) or len(v) != len(t[1]):
            raise CodecError("type:tuple")
        for ft, x in zip(t[1], v):
            _enc(ft, x, out, lim, depth + 1)
    elif kind == "record":
        _, names, ftypes, nameset = _plan(t) or ("record", tuple(n for n, _ in t[1]),
                                                 tuple(ft for _, ft in t[1]), frozenset(n for n, _ in t[1]))
        if not isinstance(v, dict) or v.keys() != nameset:
            raise CodecError("type:record")
        for n, ft in zip(names, ftypes):
            _enc(ft, v[n], out, lim, depth + 1)
    elif kind == "enum":
        if v not in t[1]:
            raise CodecError("type:enum")
        out += struct.pack("<I", t[1].index(v))
    else:
        raise CodecError(f"unknown-type:{kind}")


# ---------------------------------------------------------------- decode
_U32 = struct.Struct("<I")


class _R:
    __slots__ = ("b", "i", "n")

    def __init__(self, b: bytes):
        self.b = b
        self.i = 0
        self.n = len(b)

    def take(self, n: int) -> bytes:
        i = self.i
        if n < 0 or i + n > self.n:
            raise CodecError("truncated")
        self.i = i + n
        return self.b[i:i + n]

    def u32(self) -> int:
        i = self.i
        if i + 4 > self.n:
            raise CodecError("truncated")
        self.i = i + 4
        return _U32.unpack_from(self.b, i)[0]


def decode(t: Any, data: bytes, limits: Limits = DEFAULT_LIMITS) -> Any:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise CodecError("not-bytes")
    if len(data) > limits.max_frame_bytes:
        raise CodecError("value-too-large")
    r = _R(bytes(data))
    v = _dec(t, r, limits, 0)
    if r.i != r.n:
        raise CodecError("trailing-bytes")
    return v


def _dec(t: Any, r: _R, lim: Limits, depth: int) -> Any:
    if depth > lim.max_depth:
        raise CodecError("depth")
    if isinstance(t, str):
        if t == "bool":
            b = r.take(1)[0]
            if b > 1:
                raise CodecError("bool-tag")
            return b == 1
        if t in _INT:
            fmt = _INT[t][0]
            return struct.unpack(fmt, r.take(struct.calcsize(fmt)))[0]
        if t == "f32":
            return struct.unpack("<f", r.take(4))[0]
        if t == "f64":
            return struct.unpack("<d", r.take(8))[0]
        if t == "char":
            cp = r.u32()
            if cp > 0x10FFFF or 0xD800 <= cp <= 0xDFFF:
                raise CodecError("char")
            return chr(cp)
        if t == "string":
            n = r.u32()
            if n > lim.max_string_bytes:
                raise CodecError("string-limit")
            try:
                return r.take(n).decode("utf-8", "strict")
            except UnicodeDecodeError:
                raise CodecError("utf8") from None
        if t == "bytes":
            n = r.u32()
            if n > lim.max_frame_bytes:
                raise CodecError("bytes-limit")
            return r.take(n)
        raise CodecError(f"unknown-type:{t}")
    kind = t[0]
    if kind == "list":
        n = r.u32()
        if n > lim.max_collection:
            raise CodecError("collection-limit")
        # each element needs >= 1 byte except zero-size types; bound by remaining input
        if n > (r.n - r.i) and not _zero_size(t[1]):
            raise CodecError("truncated")
        return [_dec(t[1], r, lim, depth + 1) for _ in range(n)]
    if kind == "option":
        tag = r.take(1)[0]
        if tag == 0:
            return None
        if tag == 1:
            return _dec(t[1], r, lim, depth + 1)
        raise CodecError("option-tag")
    if kind == "result":
        tag = r.take(1)[0]
        if tag not in (0, 1):
            raise CodecError("result-tag")
        side = t[1] if tag == 0 else t[2]
        return ("ok" if tag == 0 else "err", None if side is None else _dec(side, r, lim, depth + 1))
    if kind == "tuple":
        return tuple(_dec(ft, r, lim, depth + 1) for ft in t[1])
    if kind == "record":
        plan = _plan(t)
        if plan:
            return {n: _dec(ft, r, lim, depth + 1) for n, ft in zip(plan[1], plan[2])}
        return {n: _dec(ft, r, lim, depth + 1) for n, ft in t[1]}
    if kind == "enum":
        idx = r.u32()
        if idx >= len(t[1]):
            raise CodecError("enum-index")
        return t[1][idx]
    raise CodecError(f"unknown-type:{kind}")


def _zero_size(t: Any) -> bool:
    return (isinstance(t, tuple) and t[0] in ("tuple", "record") and len(t[1]) == 0)


# ---------------------------------------------------------------- frames
def pack_frame(kind: int, body: bytes, major: int, minor: int,
               flags: int = 0, limits: Limits = DEFAULT_LIMITS) -> bytes:
    if kind not in KINDS:
        raise CodecError("frame-kind")
    if len(body) > limits.max_frame_bytes:
        raise CodecError("frame-too-large")
    return HEADER.pack(MAGIC, major, minor, kind, flags, len(body)) + body


def parse_header(head: bytes, limits: Limits = DEFAULT_LIMITS) -> tuple[int, int, int, int, int]:
    """Validate a 12-byte header; return (major, minor, kind, flags, length).

    Called before the body is read so an oversize length prefix is refused
    without allocating a buffer for it.
    """
    if len(head) != HEADER_SIZE:
        raise CodecError("truncated-header")
    magic, major, minor, kind, flags, length = HEADER.unpack(head)
    if magic != MAGIC:
        raise CodecError("bad-magic")
    if kind not in KINDS:
        raise CodecError("frame-kind")
    if flags != 0:
        raise CodecError("flags")
    if length > limits.max_frame_bytes:
        raise CodecError("frame-too-large")
    return major, minor, kind, flags, length


def unpack_frame(data: bytes, limits: Limits = DEFAULT_LIMITS) -> tuple[int, int, int, bytes]:
    major, minor, kind, _flags, length = parse_header(bytes(data[:HEADER_SIZE]), limits)
    body = bytes(data[HEADER_SIZE:])
    if len(body) != length:
        raise CodecError("length-mismatch")
    return major, minor, kind, body


# Envelope types (themselves canonical codec types) ---------------------------
REQUEST_ENVELOPE = ("record", (
    ("request_id", "string"),
    ("sender", "string"),
    ("tenant", "string"),
    ("nonce", "string"),
    ("issued_ms", "u64"),
    ("deadline_ms", "u64"),
    ("interface", "string"),
    ("version", "string"),
    ("function", "string"),
    ("fp", "string"),
    ("idempotency_key", ("option", "string")),
    ("traceparent", ("option", "string")),
    ("args", "bytes"),
    ("key_id", "string"),
    ("mac", "bytes"),
))
RESPONSE_ENVELOPE = ("record", (
    ("request_id", "string"),
    ("status", "string"),
    ("detail", ("option", "string")),
    ("result", ("option", "bytes")),
    ("retryable", "bool"),
))
HELLO = ("record", (
    ("peer", "string"),
    ("offered", ("list", ("tuple", ("u8", "u8")))),
    ("min_accepted", ("tuple", ("u8", "u8"))),
    ("client_nonce", "string"),
))
HELLO_ACK = ("record", (
    ("peer", "string"),
    ("chosen", ("tuple", ("u8", "u8"))),
    ("server_nonce", "string"),
    ("transcript_mac", "bytes"),
))
CANCEL = ("record", (("request_id", "string"),))
