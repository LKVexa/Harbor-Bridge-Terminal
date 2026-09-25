"""Canonical return-value transport for PK_ASYNC_INVOKE/1 (closure item #9).

Values crossing the async-completion boundary are lowered to a canonical,
bounded, versioned byte envelope bound to exactly one ``call_id`` and lifted
back into fresh objects, so no Python object identity ever crosses the ABI.

Envelope:  b"PKV" | u8 schema | u64le call_id | u32le body_len | body
Body TLV (all integers little-endian):

====  ==========  ==============================================
tag   type        encoding
====  ==========  ==============================================
0x00  none        -
0x01  false       -
0x02  true        -
0x03  s64         8 bytes two's complement
0x04  f64         8 bytes IEEE-754 (NaN canonicalised to 0x7ff8...)
0x05  string      u32 len + UTF-8 (strict, no surrogates)
0x06  bytes       u32 len + raw
0x07  list        u32 count + items
0x08  record      u32 count + (string key, value)*, keys strictly ascending
0x09  variant     string case + value
0x0A  error       string code + string message
====  ==========  ==============================================

Resource/handle values are owned by INV-15 and are rejected here (see the
closure ledger: that portion is BLOCKED on the real INV-15 fixture).
"""
from __future__ import annotations

import math
import struct
from dataclasses import dataclass

SCHEMA_VERSION = 1
SUPPORTED_SCHEMAS = frozenset({1})
MAGIC = b"PKV"
_HDR = struct.Struct("<3sBQI")


class AbiError(ValueError):
    """Malformed, oversized, non-canonical or foreign payload."""


class AbiTypeError(TypeError):
    """Value category not representable in the canonical ABI."""


@dataclass(frozen=True, slots=True)
class Variant:
    case: str
    value: object = None


@dataclass(frozen=True, slots=True)
class ErrorValue:
    code: str
    message: str = ""


@dataclass(frozen=True, slots=True)
class Limits:
    max_bytes: int = 1 << 20
    max_depth: int = 32
    max_items: int = 65_536


_NAN = struct.pack("<d", float("nan"))


class Codec:
    """Stateless canonical lowering/lifting codec with explicit limits."""

    def __init__(self, limits: Limits = Limits(), schema: int = SCHEMA_VERSION):
        if schema not in SUPPORTED_SCHEMAS:
            raise AbiError(f"unsupported schema {schema}")
        self.limits = limits
        self.schema = schema

    # ---------------------------------------------------------------- lower
    def lower(self, value: object, call_id: int) -> bytes:
        if isinstance(call_id, bool) or not isinstance(call_id, int) or not 1 <= call_id < 1 << 64:
            raise AbiError("call_id out of u64 range")
        out = bytearray()
        self._lower(value, out, 0, [0])
        if len(out) + _HDR.size > self.limits.max_bytes:
            raise AbiError("payload exceeds max_bytes")
        return _HDR.pack(MAGIC, self.schema, call_id, len(out)) + bytes(out)

    def _count(self, ctx: list) -> None:
        ctx[0] += 1
        if ctx[0] > self.limits.max_items:
            raise AbiError("payload exceeds max_items")

    def _str(self, s: str, out: bytearray) -> None:
        try:
            b = s.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise AbiError("string is not valid UTF-8 (lone surrogate)") from exc
        out += struct.pack("<I", len(b)) + b
        if len(out) > self.limits.max_bytes:
            raise AbiError("payload exceeds max_bytes")

    def _lower(self, v: object, out: bytearray, depth: int, ctx: list) -> None:
        if depth > self.limits.max_depth:
            raise AbiError("payload exceeds max_depth")
        self._count(ctx)
        if v is None:
            out.append(0x00)
        elif v is False:
            out.append(0x01)
        elif v is True:
            out.append(0x02)
        elif type(v) is int:
            if not -(1 << 63) <= v < 1 << 63:
                raise AbiError("integer outside s64")
            out.append(0x03)
            out += struct.pack("<q", v)
        elif type(v) is float:
            out.append(0x04)
            out += _NAN if math.isnan(v) else struct.pack("<d", v)
        elif type(v) is str:
            out.append(0x05)
            self._str(v, out)
        elif type(v) in (bytes, bytearray, memoryview):
            b = bytes(v)
            out.append(0x06)
            out += struct.pack("<I", len(b)) + b
        elif type(v) in (list, tuple):
            out.append(0x07)
            out += struct.pack("<I", len(v))
            for item in v:
                self._lower(item, out, depth + 1, ctx)
        elif type(v) is dict:
            keys = list(v)
            if not all(type(k) is str for k in keys):
                raise AbiTypeError("record keys must be str")
            out.append(0x08)
            out += struct.pack("<I", len(keys))
            for k in sorted(keys, key=lambda s: s.encode("utf-8", "surrogatepass")):
                self._str(k, out)
                self._lower(v[k], out, depth + 1, ctx)
        elif type(v) is Variant:
            out.append(0x09)
            self._str(v.case, out)
            self._lower(v.value, out, depth + 1, ctx)
        elif type(v) is ErrorValue:
            out.append(0x0A)
            self._str(v.code, out)
            self._str(v.message, out)
        else:
            raise AbiTypeError(f"{type(v).__name__} is not an ABI value (handles belong to INV-15)")
        if len(out) > self.limits.max_bytes:
            raise AbiError("payload exceeds max_bytes")

    # ---------------------------------------------------------------- lift
    def lift(self, payload: bytes, call_id: int) -> object:
        if not isinstance(payload, (bytes, bytearray)):
            raise AbiError("payload must be bytes")
        if len(payload) > self.limits.max_bytes:
            raise AbiError("payload exceeds max_bytes")
        if len(payload) < _HDR.size:
            raise AbiError("truncated header")
        magic, schema, cid, body_len = _HDR.unpack_from(payload, 0)
        if magic != MAGIC:
            raise AbiError("bad magic")
        if schema not in SUPPORTED_SCHEMAS:
            raise AbiError(f"unsupported schema {schema}")
        if cid != call_id:
            raise AbiError(f"payload bound to call {cid}, not {call_id}")
        if body_len != len(payload) - _HDR.size:
            raise AbiError("length mismatch")
        value, pos = self._lift(memoryview(payload), _HDR.size, 0, [0])
        if pos != len(payload):
            raise AbiError("trailing bytes")
        return value

    def _need(self, buf, pos: int, n: int) -> None:
        if pos + n > len(buf):
            raise AbiError("truncated body")

    def _u32(self, buf, pos: int) -> tuple[int, int]:
        self._need(buf, pos, 4)
        return struct.unpack_from("<I", buf, pos)[0], pos + 4

    def _lstr(self, buf, pos: int) -> tuple[str, int]:
        n, pos = self._u32(buf, pos)
        self._need(buf, pos, n)
        try:
            return bytes(buf[pos:pos + n]).decode("utf-8", "strict"), pos + n
        except UnicodeDecodeError as exc:
            raise AbiError("invalid UTF-8") from exc

    def _lift(self, buf, pos: int, depth: int, ctx: list):
        if depth > self.limits.max_depth:
            raise AbiError("payload exceeds max_depth")
        self._count(ctx)
        self._need(buf, pos, 1)
        tag = buf[pos]
        pos += 1
        if tag == 0x00:
            return None, pos
        if tag == 0x01:
            return False, pos
        if tag == 0x02:
            return True, pos
        if tag == 0x03:
            self._need(buf, pos, 8)
            return struct.unpack_from("<q", buf, pos)[0], pos + 8
        if tag == 0x04:
            self._need(buf, pos, 8)
            raw = bytes(buf[pos:pos + 8])
            f = struct.unpack("<d", raw)[0]
            if math.isnan(f) and raw != _NAN:
                raise AbiError("non-canonical NaN")
            return f, pos + 8
        if tag == 0x05:
            return self._lstr(buf, pos)
        if tag == 0x06:
            n, pos = self._u32(buf, pos)
            self._need(buf, pos, n)
            return bytes(buf[pos:pos + n]), pos + n
        if tag == 0x07:
            n, pos = self._u32(buf, pos)
            if n > self.limits.max_items:
                raise AbiError("list count exceeds max_items")
            items = []
            for _ in range(n):
                item, pos = self._lift(buf, pos, depth + 1, ctx)
                items.append(item)
            return items, pos
        if tag == 0x08:
            n, pos = self._u32(buf, pos)
            if n > self.limits.max_items:
                raise AbiError("record count exceeds max_items")
            rec: dict = {}
            prev: bytes | None = None
            for _ in range(n):
                k, pos = self._lstr(buf, pos)
                kb = k.encode("utf-8")
                if prev is not None and kb <= prev:
                    raise AbiError("record keys not strictly ascending (non-canonical)")
                prev = kb
                rec[k], pos = self._lift(buf, pos, depth + 1, ctx)
            return rec, pos
        if tag == 0x09:
            case, pos = self._lstr(buf, pos)
            val, pos = self._lift(buf, pos, depth + 1, ctx)
            return Variant(case, val), pos
        if tag == 0x0A:
            code, pos = self._lstr(buf, pos)
            msg, pos = self._lstr(buf, pos)
            return ErrorValue(code, msg), pos
        raise AbiError(f"unknown tag 0x{tag:02x}")
