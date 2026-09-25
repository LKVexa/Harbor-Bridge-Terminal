"""Second, independently written codec (component 38 / 64 harness input).

Deliberately shares NO code with codec.py or handles.py: no struct, no Handle
class, no ErrorCode enum. It works from the normative byte layout only, using
a cursor over a memoryview, and reports failures as plain string classes. The
interop harness requires both codecs to agree byte-for-byte on every vector.
Honest limit: the same author wrote both, in the same language; this is a
cross-check, not an independent production runtime.
"""
from __future__ import annotations

KNOWN_CODES = set(range(1, 24))
REASONS = set(range(0, 11)) | {254}
ACKS = {1, 2, 3, 4}


class AltError(Exception):
    def __init__(self, kind):
        self.kind = kind  # "malformed" | "version" | "feature" | "auth"
        super().__init__(kind)


class _Cur:
    def __init__(self, b):
        self.b, self.i = memoryview(bytes(b)), 0

    def take(self, n):
        if self.i + n > len(self.b):
            raise AltError("malformed")
        out = bytes(self.b[self.i:self.i + n])
        self.i += n
        return out

    def uint(self, n):
        v = 0
        for byte in self.take(n):
            v = (v << 8) | byte
        return v

    def done(self):
        if self.i != len(self.b):
            raise AltError("malformed")


def _header(c):
    if len(c.b) < 2:
        raise AltError("malformed")
    if c.uint(1) != 1:
        raise AltError("version")
    c.uint(1)


def _handle(c):
    if len(c.b) - c.i < 2:
        raise AltError("malformed")
    ver = c.uint(1)
    if ver != 1:
        raise AltError("version")
    flags = c.uint(1)
    if flags & 0x0E:
        raise AltError("feature")
    if flags & 0x01:
        raise AltError("auth")  # alt codec is only used at unauthenticated boundaries
    epoch, slot, gen = c.uint(4), c.uint(4), c.uint(4)
    return (epoch, slot, gen, c.take(16))


def _u(v, n):
    return bytes((v >> (8 * (n - 1 - k))) & 0xFF for k in range(n))


def enc_handle(t):
    e, s, g, tok = t
    return b"\x01\x00" + _u(e, 4) + _u(s, 4) + _u(g, 4) + bytes(tok)


def decode_call_result(b):
    c = _Cur(b)
    _header(c)
    tag = c.uint(1)
    if tag == 0:
        n = c.uint(4)
        if n > (1 << 24):
            raise AltError("malformed")
        v = c.take(n)
        c.done()
        return ("value", v)
    if tag == 1:
        h = _handle(c)
        c.done()
        return ("subtask", h)
    if tag == 2:
        code, flags, n = c.uint(2), c.uint(1), c.uint(2)
        if code not in KNOWN_CODES or flags & 0xFE:
            raise AltError("malformed")
        raw = c.take(n)
        c.done()
        try:
            detail = raw.decode("utf-8")
        except UnicodeDecodeError:
            raise AltError("malformed") from None
        return ("error", (code, bool(flags & 1), detail))
    raise AltError("malformed")


def encode_call_result(kind, payload):
    if kind == "value":
        return b"\x01\x01\x00" + _u(len(payload), 4) + bytes(payload)
    if kind == "subtask":
        return b"\x01\x01\x01" + enc_handle(payload)
    code, retry, detail = payload
    d = detail.encode("utf-8")[:1024]
    return b"\x01\x01\x02" + _u(code, 2) + bytes([1 if retry else 0]) + _u(len(d), 2) + d


def decode_wait(b):
    c = _Cur(b)
    _header(c)
    n = c.uint(2)
    if n > 4096:
        raise AltError("malformed")
    out, last = [], b""
    for _ in range(n):
        start = c.i
        h = _handle(c)
        raw = bytes(c.b[start:c.i])
        if out and raw <= last:
            raise AltError("malformed")
        last = raw
        out.append(h)
    c.done()
    return out


def encode_wait(hs):
    raws = sorted({enc_handle(h) for h in hs})
    return b"\x01\x01" + _u(len(raws), 2) + b"".join(raws)


def decode_cancel(b):
    c = _Cur(b)
    _header(c)
    h = _handle(c)
    r = c.uint(1)
    c.done()
    if r not in REASONS:
        raise AltError("malformed")
    return h, r


def decode_ack(b):
    c = _Cur(b)
    _header(c)
    a = c.uint(1)
    c.done()
    if a not in ACKS:
        raise AltError("malformed")
    return a
