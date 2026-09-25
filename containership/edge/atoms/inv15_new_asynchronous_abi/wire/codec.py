"""Primary canonical codec (components 1-4, 8). struct-based.

Every message starts with a 2-byte header: interface major, interface minor.
Supported: major 1, minor 0..1. Unknown major -> UNSUPPORTED_VERSION.
Minor > supported maximum is accepted only if the message carries no fields the
decoder does not understand (version 1.x messages never append fields, so
trailing bytes are always MALFORMED).

Call result (PK_ASYNC_CALL/1)   tag u8: 0 value | 1 subtask | 2 error
  value   : u32 len, payload bytes
  subtask : handle (30 or 46 bytes, see handles.py; length implied by flag)
  error   : u16 code, u8 flags (bit0 retryable), u16 detail len, UTF-8 detail
Wait request (PK_WAITABLE_SET/1): u16 count, count x 30-byte handle, strictly
  ascending by bytes (canonical set; duplicates and unsorted input MALFORMED)
Wait result: u16 count, handles, same canonical rule
Cancel request (PK_SUBTASK_CANCEL/1): 30-byte handle, u8 reason code
Cancel ack: u8 ack code
"""
from __future__ import annotations

import struct

from .. import handles as H
from ..errors import (AbiError, CancelAck, CancelReason, ErrorCode, Malformed,
                      UnsupportedVersion, InvalidArgument)

MAJOR, MINOR_MAX = 1, 1
MAX_WAIT = 4096
MAX_VALUE = 1 << 24
TAG_VALUE, TAG_SUBTASK, TAG_ERROR = 0, 1, 2


def negotiate(peer: list[tuple[int, int]]) -> tuple[int, int]:
    """Pick (major, minor): highest shared minor under major 1, else hard-fail."""
    minors = [mi for ma, mi in peer if ma == MAJOR]
    if not minors:
        raise UnsupportedVersion(f"no shared major; peer offers {sorted(set(ma for ma, _ in peer))}")
    return MAJOR, min(max(minors), MINOR_MAX)


def _hdr(minor=MINOR_MAX):
    return struct.pack(">BB", MAJOR, minor)


def _check_hdr(b: bytes) -> bytes:
    if len(b) < 2:
        raise Malformed("truncated header")
    major, _minor = struct.unpack(">BB", b[:2])
    if major != MAJOR:
        raise UnsupportedVersion(f"interface major {major}")
    return b[2:]


def encode_call_result(kind: str, payload) -> bytes:
    if kind == "value":
        if not isinstance(payload, (bytes, bytearray)) or len(payload) > MAX_VALUE:
            raise InvalidArgument("value payload must be bytes <= 16 MiB")
        return _hdr() + struct.pack(">BI", TAG_VALUE, len(payload)) + bytes(payload)
    if kind == "subtask":
        return _hdr() + bytes([TAG_SUBTASK]) + H.encode(payload)
    if kind == "error":
        env = payload.envelope() if isinstance(payload, AbiError) else payload
        detail = str(env.get("detail", "")).encode("utf-8")[:1024]
        return _hdr() + struct.pack(">BHBH", TAG_ERROR, int(env["code"]), 1 if env.get("retryable") else 0,
                                    len(detail)) + detail
    raise InvalidArgument(f"unknown call-result kind {kind!r}")


def decode_call_result(b: bytes):
    body = _check_hdr(bytes(b))
    if not body:
        raise Malformed("missing tag")
    tag, rest = body[0], body[1:]
    if tag == TAG_VALUE:
        if len(rest) < 4:
            raise Malformed("truncated value length")
        (n,) = struct.unpack(">I", rest[:4])
        if n > MAX_VALUE or len(rest) != 4 + n:
            raise Malformed("value length mismatch")
        return ("value", rest[4:])
    if tag == TAG_SUBTASK:
        return ("subtask", H.decode(rest))
    if tag == TAG_ERROR:
        if len(rest) < 5:
            raise Malformed("truncated error envelope")
        code, flags, n = struct.unpack(">HBH", rest[:5])
        if len(rest) != 5 + n or flags & 0xFE:
            raise Malformed("error envelope length/flags")
        try:
            ec = ErrorCode(code)
        except ValueError:
            raise Malformed(f"unknown error code {code}") from None
        if ec is ErrorCode.OK:
            raise Malformed("error envelope may not carry OK")
        try:
            detail = rest[5:].decode("utf-8")
        except UnicodeDecodeError:
            raise Malformed("detail not UTF-8") from None
        return ("error", {"code": int(ec), "name": ec.name, "retryable": bool(flags & 1), "detail": detail})
    raise Malformed(f"unknown call-result tag {tag}")


def encode_wait(handles) -> bytes:
    encs = sorted({H.encode(h) for h in handles})
    if len(encs) > MAX_WAIT:
        raise InvalidArgument("wait set too large")
    return _hdr() + struct.pack(">H", len(encs)) + b"".join(encs)


def decode_wait(b: bytes):
    body = _check_hdr(bytes(b))
    if len(body) < 2:
        raise Malformed("truncated wait count")
    (n,) = struct.unpack(">H", body[:2])
    if n > MAX_WAIT or len(body) != 2 + n * H.BASE_LEN:
        raise Malformed("wait length mismatch")
    out, prev = [], None
    for i in range(n):
        chunk = body[2 + i * H.BASE_LEN: 2 + (i + 1) * H.BASE_LEN]
        if prev is not None and chunk <= prev:
            raise Malformed("wait set not canonical (unsorted or duplicate)")
        prev = chunk
        out.append(H.decode(chunk))
    return out


def encode_cancel(h, reason: CancelReason) -> bytes:
    return _hdr() + H.encode(h) + bytes([int(CancelReason(reason))])


def decode_cancel(b: bytes):
    body = _check_hdr(bytes(b))
    if len(body) != H.BASE_LEN + 1:
        raise Malformed("cancel length")
    try:
        reason = CancelReason(body[-1])
    except ValueError:
        raise Malformed("unknown cancel reason") from None
    return H.decode(body[:-1]), reason


def encode_ack(ack: CancelAck) -> bytes:
    return _hdr() + bytes([int(CancelAck(ack))])


def decode_ack(b: bytes) -> CancelAck:
    body = _check_hdr(bytes(b))
    if len(body) != 1:
        raise Malformed("ack length")
    try:
        return CancelAck(body[0])
    except ValueError:
        raise Malformed("unknown ack code") from None
