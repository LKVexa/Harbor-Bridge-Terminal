"""MC-002 (load-time half) -- Wasm binary validation and world enforcement.

Parses the preamble and import/export sections of a Wasm binary *before* any
engine sees it: magic, version/layer (core module vs component), size ceiling,
section ordering/length sanity, LEB128 bounds, UTF-8 names.  Every import is
mapped to a capability through ``IMPORT_CAPABILITY``; an import with no
mapping, or one whose capability the world does not grant, rejects the
module (no fallback/ambient binding).  Also contains a minimal encoder used
by tests and fixtures to build real binaries.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable

from .errors import ErrorCode, Inv13Error

MAGIC = b"\0asm"
CORE_VERSION = b"\x01\x00\x00\x00"
COMPONENT_VERSION = b"\x0d\x00\x01\x00"   # component-model binary, layer 1 (pre-standard)
MAX_MODULE_BYTES = 64 << 20
MAX_IMPORTS = 1024

# core-ABI namespace used by the INV-13 adapter (mirrors wit/inv13-system-interface.wit)
IMPORT_CAPABILITY: dict[tuple[str, str], str] = {
    ("inv13:filesystem@4.3.0", "open-at"): "filesystem",
    ("inv13:filesystem@4.3.0", "read"): "filesystem",
    ("inv13:filesystem@4.3.0", "write"): "filesystem",
    ("inv13:filesystem@4.3.0", "drop"): "filesystem",
    ("inv13:clocks@4.3.0", "wall-now"): "wall-clock",
    ("inv13:clocks@4.3.0", "monotonic-now"): "monotonic-clock",
    ("inv13:random@4.3.0", "get-random-bytes"): "random",
    ("inv13:stdio@4.3.0", "stdout-write"): "stdio",
    ("inv13:stdio@4.3.0", "stderr-write"): "stdio",
    ("inv13:environment@4.3.0", "get-env"): "environment",
    ("inv13:environment@4.3.0", "get-args"): "environment",
    ("inv13:sockets@4.3.0", "connect"): "sockets",
    ("inv13:http-outgoing@4.3.0", "handle"): "http-outgoing",
}
EXTERN_KIND = {0: "func", 1: "table", 2: "memory", 3: "global", 4: "tag"}


@dataclass(frozen=True)
class ModuleInfo:
    kind: str                     # "core" | "component"
    digest: str
    imports: tuple[tuple[str, str, str], ...]
    exports: tuple[tuple[str, str], ...]
    size: int


class _R:
    def __init__(self, b: bytes, pos: int = 0, end: int | None = None) -> None:
        self.b, self.p, self.end = b, pos, len(b) if end is None else end

    def byte(self) -> int:
        if self.p >= self.end:
            raise Inv13Error(ErrorCode.MALFORMED_MODULE, "eof")
        v = self.b[self.p]
        self.p += 1
        return v

    def u32(self) -> int:
        result = shift = 0
        for _ in range(5):
            byte = self.byte()
            result |= (byte & 0x7F) << shift
            if not byte & 0x80:
                if result > 0xFFFFFFFF:
                    raise Inv13Error(ErrorCode.MALFORMED_MODULE, "leb overflow")
                return result
            shift += 7
        raise Inv13Error(ErrorCode.MALFORMED_MODULE, "leb too long")

    def name(self) -> str:
        n = self.u32()
        if self.p + n > self.end:
            raise Inv13Error(ErrorCode.MALFORMED_MODULE, "name overrun")
        raw = self.b[self.p:self.p + n]
        self.p += n
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError:
            raise Inv13Error(ErrorCode.MALFORMED_MODULE, "bad utf-8 name") from None

    def limits(self) -> None:
        flag = self.byte()
        self.u32()
        if flag & 1:
            self.u32()


def parse(binary: bytes) -> ModuleInfo:
    if not isinstance(binary, (bytes, bytearray)):
        raise Inv13Error(ErrorCode.INVALID_ARGUMENT)
    if len(binary) > MAX_MODULE_BYTES:
        raise Inv13Error(ErrorCode.QUOTA_EXCEEDED, "module size")
    if len(binary) < 8 or binary[:4] != MAGIC:
        raise Inv13Error(ErrorCode.MALFORMED_MODULE, "magic")
    ver = bytes(binary[4:8])
    digest = hashlib.sha256(binary).hexdigest()
    if ver == COMPONENT_VERSION:
        # Component binaries need a component-model engine (MC-002 external gap).
        return ModuleInfo("component", digest, (), (), len(binary))
    if ver != CORE_VERSION:
        raise Inv13Error(ErrorCode.UNSUPPORTED_VERSION, ver.hex())
    r = _R(bytes(binary), 8)
    imports: list[tuple[str, str, str]] = []
    exports: list[tuple[str, str]] = []
    last_id = 0
    while r.p < r.end:
        sid = r.byte()
        size = r.u32()
        start = r.p
        if start + size > r.end:
            raise Inv13Error(ErrorCode.MALFORMED_MODULE, "section overrun")
        if sid != 0:
            if sid > 12 or (sid != 12 and sid <= last_id and last_id != 12):
                raise Inv13Error(ErrorCode.MALFORMED_MODULE, f"section order {sid}")
            last_id = sid
        s = _R(r.b, start, start + size)
        if sid == 2:
            n = s.u32()
            if n > MAX_IMPORTS:
                raise Inv13Error(ErrorCode.QUOTA_EXCEEDED, "imports")
            for _ in range(n):
                mod, fld = s.name(), s.name()
                kind = s.byte()
                if kind == 0:
                    s.u32()
                elif kind == 1:
                    s.byte(); s.limits()
                elif kind == 2:
                    s.limits()
                elif kind == 3:
                    s.byte(); s.byte()
                else:
                    raise Inv13Error(ErrorCode.MALFORMED_MODULE, "import kind")
                imports.append((mod, fld, EXTERN_KIND[kind]))
        elif sid == 7:
            for _ in range(s.u32()):
                nm = s.name()
                kind = s.byte()
                s.u32()
                if kind not in EXTERN_KIND:
                    raise Inv13Error(ErrorCode.MALFORMED_MODULE, "export kind")
                exports.append((nm, EXTERN_KIND[kind]))
        r.p = start + size
    return ModuleInfo("core", digest, tuple(imports), tuple(exports), len(binary))


def required_capabilities(info: ModuleInfo) -> set[str]:
    caps = set()
    for mod, fld, kind in info.imports:
        cap = IMPORT_CAPABILITY.get((mod, fld))
        if cap is None or kind != "func":
            raise Inv13Error(ErrorCode.CAP_NOT_GRANTED, f"unmapped import {mod}.{fld}")
        caps.add(cap)
    return caps


def admit(binary: bytes, granted: Iterable[str], *, allowed_digests: set[str] | None = None) -> ModuleInfo:
    info = parse(binary)
    if allowed_digests is not None and info.digest not in allowed_digests:
        raise Inv13Error(ErrorCode.POLICY_DENIED, "digest not approved")
    if info.kind != "core":
        raise Inv13Error(ErrorCode.UNSUPPORTED_VERSION, "component binaries require a component-model engine")
    extra = required_capabilities(info) - set(granted)
    if extra:
        raise Inv13Error(ErrorCode.CAP_NOT_GRANTED, sorted(extra))
    return info


# ---------------------------------------------------------------- encoder --
def leb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def sleb(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        done = (n == 0 and not b & 0x40) or (n == -1 and b & 0x40)
        out.append(b if done else b | 0x80)
        if done:
            return bytes(out)


def _vec(items: list[bytes]) -> bytes:
    return leb(len(items)) + b"".join(items)


def _name(s: str) -> bytes:
    b = s.encode()
    return leb(len(b)) + b


def _sec(i: int, body: bytes) -> bytes:
    return bytes([i]) + leb(len(body)) + body


I32, I64 = 0x7F, 0x7E


def build_module(types: list[tuple[list[int], list[int]]], imports: list[tuple[str, str, int]],
                 funcs: list[tuple[int, list[tuple[int, int]], bytes]], exports: list[tuple[str, int, int]],
                 memory_pages: int | None = 1, data: list[tuple[int, bytes]] | None = None) -> bytes:
    """types: (params, results); imports: (mod, name, typeidx); funcs: (typeidx, locals[(n,type)], body)."""
    out = MAGIC + CORE_VERSION
    out += _sec(1, _vec([b"\x60" + _vec([bytes([p]) for p in ps]) + _vec([bytes([r]) for r in rs]) for ps, rs in types]))
    if imports:
        out += _sec(2, _vec([_name(m) + _name(n) + b"\x00" + leb(t) for m, n, t in imports]))
    if funcs:
        out += _sec(3, _vec([leb(t) for t, _, _ in funcs]))
    if memory_pages is not None:
        out += _sec(5, _vec([b"\x00" + leb(memory_pages)]))
    if exports:
        out += _sec(7, _vec([_name(n) + bytes([k]) + leb(i) for n, k, i in exports]))
    if funcs:
        bodies = []
        for _, locs, body in funcs:
            fb = _vec([leb(n) + bytes([t]) for n, t in locs]) + body + b"\x0b"
            bodies.append(leb(len(fb)) + fb)
        out += _sec(10, _vec(bodies))
    if data:
        out += _sec(11, _vec([b"\x00\x41" + sleb(off) + b"\x0b" + leb(len(d)) + d for off, d in data]))
    return out
