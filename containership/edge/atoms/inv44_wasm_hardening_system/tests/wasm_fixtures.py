"""Hand-assembled Wasm binaries for INV-44 tests (no toolchain required)."""
from __future__ import annotations


def leb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def name(s: str) -> bytes:
    raw = s.encode()
    return leb(len(raw)) + raw


def section(sid: int, body: bytes) -> bytes:
    return bytes([sid]) + leb(len(body)) + body


def module(*, imports: tuple[tuple[str, str], ...] = (), mem: tuple[int, int | None] | None = (1, 4),
           extra: bytes = b"") -> bytes:
    """A valid module: one type ()->(), optional func imports, one local func, a memory."""
    out = b"\x00asm\x01\x00\x00\x00"
    out += section(1, leb(1) + b"\x60\x00\x00")                     # type: () -> ()
    if imports:
        body = leb(len(imports)) + b"".join(name(m) + name(n) + b"\x00" + leb(0) for m, n in imports)
        out += section(2, body)
    out += section(3, leb(1) + leb(0))                              # one function of type 0
    if mem is not None:
        lo, hi = mem
        lim = (b"\x01" + leb(lo) + leb(hi)) if hi is not None else (b"\x00" + leb(lo))
        out += section(5, leb(1) + lim)
    out += section(7, leb(1) + name("run") + b"\x00" + leb(len(imports)))  # export func
    out += section(10, leb(1) + leb(2) + b"\x00\x0b")               # body: no locals, end
    return out + extra
