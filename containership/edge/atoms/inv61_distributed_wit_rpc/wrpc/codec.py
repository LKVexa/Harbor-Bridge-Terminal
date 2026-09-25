"""M04 - Canonical wire serialization for WIT values and the PK_WRPC_FRAME/2 envelope.

Encoding rules (normative, see REQUIREMENTS.md R-CODEC-*):
  * unsigned ints: unsigned LEB128, minimal length, range-checked for the declared width
  * signed ints:   zigzag + LEB128
  * f32/f64:       IEEE-754 big-endian; every NaN is canonicalised to one bit pattern
  * bool:          one byte 0x00/0x01 (anything else is rejected)
  * char:          UTF-8 of exactly one Unicode scalar value (no surrogates)
  * string:        LEB128 byte length + UTF-8 (strict)
  * list:          LEB128 count + elements;   option: 0x00 | 0x01 value
  * result:        0x00 ok-payload | 0x01 err-payload
  * tuple/record:  members in declaration order;  enum: LEB128 case index
  * variant:       LEB128 case index + payload (if the case has one)

Every decode is bounded: byte budget, element count, nesting depth. Trailing
bytes are an error, so an encoding is canonical iff ``encode(decode(b)) == b``.
"""
from __future__ import annotations

import math
import struct

from .wit import T, WitError

MAX_FRAME_BYTES = 1 << 20
MAX_ELEMENTS = 1 << 16
MAX_DEPTH = 32
MAGIC = b"WR"
WIRE_MAJOR = 2

_UBITS = {"u8": 8, "u16": 16, "u32": 32, "u64": 64}
_SBITS = {"s8": 8, "s16": 16, "s32": 32, "s64": 64}
_NAN32 = struct.pack(">I", 0x7FC00000)
_NAN64 = struct.pack(">Q", 0x7FF8000000000000)


class CodecError(ValueError):
    """Stable decode/encode failure; ``code`` is wire-safe."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _uleb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


class Reader:
    def __init__(self, data: bytes, limit: int = MAX_FRAME_BYTES):
        if len(data) > limit:
            raise CodecError("frame-too-large")
        self.b = memoryview(data)
        self.i = 0

    def need(self, n: int) -> memoryview:
        if n < 0 or self.i + n > len(self.b):
            raise CodecError("truncated")
        v = self.b[self.i:self.i + n]
        self.i += n
        return v

    def uleb(self, bits: int = 64) -> int:
        result = shift = 0
        start = self.i
        while True:
            byte = self.need(1)[0]
            result |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                break
            if shift > bits + 6:
                raise CodecError("varint-overlong")
        if self.i - start > 1 and self.b[self.i - 1] == 0:
            raise CodecError("varint-noncanonical")
        if result >> bits:
            raise CodecError("int-range")
        return result

    def done(self) -> None:
        if self.i != len(self.b):
            raise CodecError("trailing-bytes")


def encode_value(t: T, v, out: bytearray, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise CodecError("too-deep")
    k = t.kind
    if k == "bool":
        if not isinstance(v, bool):
            raise CodecError("type:bool")
        out.append(1 if v else 0)
    elif k in _UBITS:
        if not isinstance(v, int) or isinstance(v, bool) or v < 0 or v >> _UBITS[k]:
            raise CodecError(f"type:{k}")
        out += _uleb(v)
    elif k in _SBITS:
        bits = _SBITS[k]
        if not isinstance(v, int) or isinstance(v, bool) or not -(1 << (bits - 1)) <= v < (1 << (bits - 1)):
            raise CodecError(f"type:{k}")
        out += _uleb((v << 1) ^ (v >> (bits - 1)))
    elif k in ("f32", "f64"):
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            raise CodecError(f"type:{k}")
        v = float(v)
        if math.isnan(v):
            out += _NAN32 if k == "f32" else _NAN64
        else:
            try:
                out += struct.pack(">f" if k == "f32" else ">d", v)
            except OverflowError:
                raise CodecError("type:f32") from None
    elif k == "char":
        if not isinstance(v, str) or len(v) != 1 or 0xD800 <= ord(v) <= 0xDFFF:
            raise CodecError("type:char")
        out += v.encode("utf-8")
    elif k == "string":
        if not isinstance(v, str):
            raise CodecError("type:string")
        try:
            raw = v.encode("utf-8")
        except UnicodeEncodeError:
            raise CodecError("type:string") from None
        out += _uleb(len(raw)) + raw
    elif k == "list":
        if not isinstance(v, (list, tuple)) or len(v) > MAX_ELEMENTS:
            raise CodecError("type:list")
        out += _uleb(len(v))
        for item in v:
            encode_value(t.args[0], item, out, depth + 1)
    elif k == "option":
        if v is None:
            out.append(0)
        else:
            out.append(1)
            encode_value(t.args[0], v, out, depth + 1)
    elif k == "result":
        if not isinstance(v, dict) or len(v) != 1 or not ({"ok"} >= v.keys() or {"err"} >= v.keys()):
            raise CodecError("type:result")
        tag = "ok" if "ok" in v else "err"
        out.append(0 if tag == "ok" else 1)
        inner = t.args[0 if tag == "ok" else 1]
        if inner is None:
            if v[tag] is not None:
                raise CodecError("type:result")
        else:
            encode_value(inner, v[tag], out, depth + 1)
    elif k == "tuple":
        if not isinstance(v, (list, tuple)) or len(v) != len(t.args):
            raise CodecError("type:tuple")
        for mt, mv in zip(t.args, v):
            encode_value(mt, mv, out, depth + 1)
    elif k == "record":
        if not isinstance(v, dict) or set(v) != {n for n, _ in t.fields}:
            raise CodecError("type:record")
        for n, ft in t.fields:
            encode_value(ft, v[n], out, depth + 1)
    elif k == "enum":
        names = [n for n, _ in t.fields]
        if v not in names:
            raise CodecError("type:enum")
        out += _uleb(names.index(v))
    elif k == "variant":
        if not isinstance(v, dict) or len(v) != 1:
            raise CodecError("type:variant")
        (case, payload), = v.items()
        names = [n for n, _ in t.fields]
        if case not in names:
            raise CodecError("type:variant")
        idx = names.index(case)
        out += _uleb(idx)
        pt = t.fields[idx][1]
        if pt is None:
            if payload is not None:
                raise CodecError("type:variant")
        else:
            encode_value(pt, payload, out, depth + 1)
    else:
        raise CodecError(f"unsupported:{k}")


def _min_size(t: T) -> int:
    if t.kind in ("tuple",):
        return sum(_min_size(a) for a in t.args)
    if t.kind == "record":
        return sum(_min_size(ft) for _, ft in t.fields)
    return 1


def decode_value(t: T, r: Reader, depth: int = 0):
    if depth > MAX_DEPTH:
        raise CodecError("too-deep")
    k = t.kind
    if k == "bool":
        b = r.need(1)[0]
        if b > 1:
            raise CodecError("bool-range")
        return b == 1
    if k in _UBITS:
        return r.uleb(_UBITS[k])
    if k in _SBITS:
        bits = _SBITS[k]
        z = r.uleb(bits)
        return (z >> 1) ^ -(z & 1)
    if k == "f32":
        raw = bytes(r.need(4))
        v = struct.unpack(">f", raw)[0]
        if math.isnan(v) and raw != _NAN32:
            raise CodecError("nan-noncanonical")
        return v
    if k == "f64":
        raw = bytes(r.need(8))
        v = struct.unpack(">d", raw)[0]
        if math.isnan(v) and raw != _NAN64:
            raise CodecError("nan-noncanonical")
        return v
    if k == "char":
        first = r.b[r.i] if r.i < len(r.b) else None
        if first is None:
            raise CodecError("truncated")
        n = 1 if first < 0x80 else 2 if first >> 5 == 6 else 3 if first >> 4 == 14 else 4 if first >> 3 == 30 else 0
        if not n:
            raise CodecError("utf8")
        try:
            return bytes(r.need(n)).decode("utf-8")
        except UnicodeDecodeError:
            raise CodecError("utf8") from None
    if k == "string":
        n = r.uleb(32)
        try:
            return bytes(r.need(n)).decode("utf-8")
        except UnicodeDecodeError:
            raise CodecError("utf8") from None
    if k == "list":
        n = r.uleb(32)
        # a non-empty element type costs >= 1 byte, so n is also bounded by remaining input
        # (zero-size elements - empty record/tuple - are bounded by MAX_ELEMENTS only)
        if n > MAX_ELEMENTS or (_min_size(t.args[0]) > 0 and n > len(r.b) - r.i):
            raise CodecError("list-limit")
        return [decode_value(t.args[0], r, depth + 1) for _ in range(n)]
    if k == "option":
        tag = r.need(1)[0]
        if tag > 1:
            raise CodecError("option-tag")
        return None if tag == 0 else decode_value(t.args[0], r, depth + 1)
    if k == "result":
        tag = r.need(1)[0]
        if tag > 1:
            raise CodecError("result-tag")
        inner = t.args[tag]
        key = "ok" if tag == 0 else "err"
        return {key: None if inner is None else decode_value(inner, r, depth + 1)}
    if k == "tuple":
        return [decode_value(m, r, depth + 1) for m in t.args]
    if k == "record":
        return {n: decode_value(ft, r, depth + 1) for n, ft in t.fields}
    if k == "enum":
        idx = r.uleb(32)
        if idx >= len(t.fields):
            raise CodecError("enum-range")
        return t.fields[idx][0]
    if k == "variant":
        idx = r.uleb(32)
        if idx >= len(t.fields):
            raise CodecError("variant-range")
        name, pt = t.fields[idx]
        return {name: None if pt is None else decode_value(pt, r, depth + 1)}
    raise CodecError(f"unsupported:{k}")


def encode_args(types: list[T], values: list) -> bytes:
    if len(types) != len(values):
        raise CodecError("arity")
    out = bytearray()
    for t, v in zip(types, values):
        encode_value(t, v, out)
    return bytes(out)


def decode_args(types: list[T], data: bytes) -> list:
    r = Reader(data)
    vals = [decode_value(t, r) for t in types]
    r.done()
    return vals


# ---------------------------------------------------------------- envelope
def _put_str(out: bytearray, s: str, limit: int = 255) -> None:
    raw = s.encode("utf-8")
    if not raw or len(raw) > limit:
        raise CodecError("header-field")
    out += _uleb(len(raw)) + raw


def _get_str(r: Reader, limit: int = 255, allow_empty: bool = False) -> str:
    n = r.uleb(16)
    if n > limit or (n == 0 and not allow_empty):
        raise CodecError("header-field")
    try:
        return bytes(r.need(n)).decode("utf-8")
    except UnicodeDecodeError:
        raise CodecError("utf8") from None


def encode_frame(h: dict, payload: bytes) -> bytes:
    """Encode a PK_WRPC_FRAME/2 envelope. ``h`` keys: interface, version, function,
    fp (16 hex), deadline (float seconds), request_id (32 hex), traceparent (str, may be '')."""
    out = bytearray(MAGIC)
    out.append(WIRE_MAJOR)
    _put_str(out, h["interface"])
    _put_str(out, h["version"], 64)
    _put_str(out, h["function"])
    try:
        fp = bytes.fromhex(h["fp"])
        rid = bytes.fromhex(h["request_id"])
    except (ValueError, TypeError):
        raise CodecError("header-field") from None
    if len(fp) != 8 or len(rid) != 16:
        raise CodecError("header-field")
    d = h["deadline"]
    if not isinstance(d, (int, float)) or isinstance(d, bool) or not math.isfinite(d):
        raise CodecError("deadline")
    out += fp + struct.pack(">d", float(d)) + rid
    tp = h.get("traceparent", "") or ""
    raw_tp = tp.encode("ascii", "strict") if tp else b""
    if len(raw_tp) > 128:
        raise CodecError("traceparent")
    out += _uleb(len(raw_tp)) + raw_tp
    out += _uleb(len(payload)) + payload
    if len(out) > MAX_FRAME_BYTES:
        raise CodecError("frame-too-large")
    return bytes(out)


def decode_header(data: bytes) -> tuple[dict, bytes]:
    """Decode the envelope header ONLY; argument bytes are returned undecoded so
    the receiver can check the fingerprint before touching a single argument byte."""
    r = Reader(data)
    if bytes(r.need(2)) != MAGIC:
        raise CodecError("magic")
    major = r.need(1)[0]
    if major != WIRE_MAJOR:
        raise CodecError("wire-version")
    h = {"interface": _get_str(r), "version": _get_str(r, 64), "function": _get_str(r)}
    h["fp"] = bytes(r.need(8)).hex()
    h["deadline"] = struct.unpack(">d", bytes(r.need(8)))[0]
    if not math.isfinite(h["deadline"]):
        raise CodecError("deadline")
    h["request_id"] = bytes(r.need(16)).hex()
    n = r.uleb(8)
    if n > 128:
        raise CodecError("traceparent")
    try:
        h["traceparent"] = bytes(r.need(n)).decode("ascii")
    except UnicodeDecodeError:
        h["traceparent"] = ""        # bad trace context is dropped (new trace), never fatal to the call
    plen = r.uleb(32)
    payload = bytes(r.need(plen))
    r.done()
    return h, payload


__all__ = ["CodecError", "encode_value", "decode_value", "encode_args", "decode_args",
           "encode_frame", "decode_header", "MAX_FRAME_BYTES", "WitError"]
