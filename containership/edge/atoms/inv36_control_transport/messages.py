"""PK_CTRL_MSG/1 - typed, canonical control-message envelope carried inside PK_CTRL_FRAME/2.

The envelope is authenticated as part of the AEAD plaintext, so tenant,
message type and operation ID cannot be rewritten by a relay (MC-07.014).
Encoding is canonical: exactly one byte representation per value, strict
field order, no optional padding, and the decoder must consume every byte
(MC-06.007, MC-06.019).
"""
from __future__ import annotations

import re
import secrets
import struct
from dataclasses import dataclass, field

from . import _wire
from .errors import ErrorCode, Inv36Error

MSG_VERSION = _wire.MSG_VERSION
MESSAGE_TYPES: dict[str, int] = dict(_wire.MESSAGE_TYPES)
TYPE_NAMES: dict[int, str] = {v: k for k, v in MESSAGE_TYPES.items()}
TENANT_MAX = _wire.MSG_TENANT_MAX
BODY_MAX = _wire.MSG_BODY_MAX
OP_ID_SIZE = 16
_FIXED = struct.Struct(">BBHH")
_TENANT_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}\Z")
_TRACEPARENT_RE = re.compile(r"00-[0-9a-f]{32}-[0-9a-f]{16}-[0-9a-f]{2}\Z")
MIN_ENCODED = _FIXED.size + OP_ID_SIZE + 1 + 1 + 1 + 4 + 1  # tenant >= 1 byte

if len(set(MESSAGE_TYPES.values())) != len(MESSAGE_TYPES):  # pragma: no cover
    raise ImportError("message-type registry collision")


class MessageFormatError(Inv36Error, ValueError):
    code = ErrorCode.MESSAGE_FORMAT


class UnknownMessageType(Inv36Error, ValueError):
    code = ErrorCode.UNKNOWN_MESSAGE_TYPE


def new_op_id() -> bytes:
    return secrets.token_bytes(OP_ID_SIZE)


def validate_tenant(tenant: str) -> str:
    if not isinstance(tenant, str) or not _TENANT_RE.match(tenant):
        raise MessageFormatError("invalid tenant identifier", detail={"field": "tenant"})
    return tenant


@dataclass(frozen=True)
class ControlMessage:
    msg_type: int
    tenant: str
    body: bytes = b""
    op_id: bytes = field(default_factory=new_op_id)
    traceparent: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.msg_type, int) or self.msg_type not in TYPE_NAMES:
            raise UnknownMessageType(f"message type {self.msg_type!r} is not registered")
        validate_tenant(self.tenant)
        if not isinstance(self.body, (bytes, bytearray)) or len(self.body) > BODY_MAX:
            raise MessageFormatError("body missing or above bound", detail={"max": BODY_MAX})
        if not isinstance(self.op_id, (bytes, bytearray)) or len(self.op_id) != OP_ID_SIZE:
            raise MessageFormatError("op_id must be 16 bytes")
        if self.traceparent and not _TRACEPARENT_RE.match(self.traceparent):
            raise MessageFormatError("invalid traceparent")

    @property
    def type_name(self) -> str:
        return TYPE_NAMES[self.msg_type]

    @classmethod
    def of(cls, type_name: str, tenant: str, body: bytes = b"", **kw) -> "ControlMessage":
        if type_name not in MESSAGE_TYPES:
            raise UnknownMessageType(f"unknown message type {type_name!r}")
        return cls(MESSAGE_TYPES[type_name], tenant, bytes(body), **kw)

    def encode(self) -> bytes:
        t = self.tenant.encode("ascii")
        tp = self.traceparent.encode("ascii")
        return b"".join((
            _FIXED.pack(MSG_VERSION, 0, self.msg_type, 0),
            bytes(self.op_id),
            bytes([len(t)]), t,
            bytes([len(tp)]), tp,
            len(self.body).to_bytes(4, "big"), bytes(self.body),
        ))


def decode(data: bytes | bytearray | memoryview) -> ControlMessage:
    """Strict canonical decode. Every length is bounds-checked before slicing."""
    buf = memoryview(bytes(data))
    n = len(buf)
    if n < MIN_ENCODED:
        raise MessageFormatError("message shorter than minimum envelope")
    version, flags, msg_type, ext_count = _FIXED.unpack_from(buf, 0)
    if version != MSG_VERSION:
        raise MessageFormatError(f"unsupported message version {version}")
    if flags != 0:
        raise MessageFormatError("reserved flags must be zero")
    if ext_count != 0:
        raise MessageFormatError("extensions are not supported in PK_CTRL_MSG/1")
    if msg_type not in TYPE_NAMES:
        raise UnknownMessageType(f"message type {msg_type} is not registered", detail={"msg_type": msg_type})
    pos = _FIXED.size
    op_id = bytes(buf[pos:pos + OP_ID_SIZE])
    pos += OP_ID_SIZE
    tlen = buf[pos]
    pos += 1
    if not 1 <= tlen <= TENANT_MAX or pos + tlen > n:
        raise MessageFormatError("tenant length invalid")
    try:
        tenant = bytes(buf[pos:pos + tlen]).decode("ascii")
    except UnicodeDecodeError as exc:
        raise MessageFormatError("tenant is not ascii") from exc
    pos += tlen
    if pos >= n:
        raise MessageFormatError("truncated before traceparent")
    tplen = buf[pos]
    pos += 1
    if tplen not in (0, 55) or pos + tplen > n:
        raise MessageFormatError("traceparent length invalid")
    try:
        traceparent = bytes(buf[pos:pos + tplen]).decode("ascii")
    except UnicodeDecodeError as exc:
        raise MessageFormatError("traceparent is not ascii") from exc
    pos += tplen
    if pos + 4 > n:
        raise MessageFormatError("truncated before body length")
    blen = int.from_bytes(buf[pos:pos + 4], "big")
    pos += 4
    if blen > BODY_MAX or pos + blen != n:
        raise MessageFormatError("body length invalid or trailing bytes present")
    body = bytes(buf[pos:pos + blen])
    return ControlMessage(msg_type, tenant, body, op_id, traceparent)
