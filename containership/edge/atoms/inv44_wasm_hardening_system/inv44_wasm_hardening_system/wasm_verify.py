"""Independent compiled-output verifier for INV-44 (missing component 9).

Replaces the caller-supplied ``output_valid`` Boolean with evidence:

1. ``parse_module`` structurally validates the Wasm binary (magic, version,
   section ids/order, LEB128 sizes, no trailing bytes, type/function/code/
   export/import cross-references, function-body framing) and
   extracts the import list that the capability layer checks.
2. ``issue_receipt`` binds the module's SHA-256, its structural summary, the
   approved toolchain identity and the declared hardening profile into a
   canonical JSON receipt authenticated with HMAC-SHA256 under a keyed id.
3. ``verify_receipt`` recomputes every bound field from the bytes presented
   at instantiation and refuses any mismatch, unknown key, unapproved
   toolchain or incomplete hardening profile.

Honest limits (recorded in RELEASE_EVIDENCE.json):
* HMAC is symmetric: whoever can verify can also mint. Asymmetric signing and
  KMS/HSM key custody are BLOCKED on an owner-provisioned key service.
* Structural validation (types, function/code agreement, body framing,
  locals, export index bounds, import type indices) is not full semantic
  validation: instruction sequences are not type-checked and does not prove that Swivel's Spectre passes were applied. That
  proof needs the real Swivel toolchain (missing component 8).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Final, Iterable, Mapping

from .errors import HardeningError
from .runtime import REQUIRED_HARDENING

WASM_MAGIC: Final[bytes] = b"\x00asm"
WASM_VERSION: Final[bytes] = b"\x01\x00\x00\x00"
MAX_MODULE_BYTES: Final[int] = 64 * 1024 * 1024
RECEIPT_SCHEMA: Final[str] = "PK_WASM_VERIFY_RECEIPT/1"

# Known section ids and the order non-custom sections must appear in
# (data-count, id 12, sits between import-related sections and code).
_SECTION_ORDER: Final[dict[int, int]] = {
    1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 13: 6, 6: 7, 7: 8, 8: 9, 9: 10, 12: 11, 10: 12, 11: 13,
}
_SECTION_NAMES: Final[dict[int, str]] = {
    0: "custom", 1: "type", 2: "import", 3: "function", 4: "table", 5: "memory",
    6: "global", 7: "export", 8: "start", 9: "element", 10: "code", 11: "data",
    12: "datacount", 13: "tag",
}
_IMPORT_KINDS: Final[dict[int, str]] = {0: "func", 1: "table", 2: "memory", 3: "global", 4: "tag"}


_VALTYPES: Final[frozenset[int]] = frozenset({0x7F, 0x7E, 0x7D, 0x7C, 0x7B, 0x70, 0x6F})


def _end(body: "_Reader", what: str) -> None:
    if body.pos != body.end:
        raise MalformedModule(f"{what} section has trailing bytes")


class MalformedModule(HardeningError):
    code = "WH-OUTPUT-MALFORMED"


class ReceiptInvalid(HardeningError):
    code = "WH-RECEIPT-INVALID"


class ToolchainUnapproved(HardeningError):
    code = "WH-TOOLCHAIN-UNAPPROVED"


class _Reader:
    __slots__ = ("buf", "pos", "end")

    def __init__(self, buf: bytes, pos: int = 0, end: int | None = None) -> None:
        self.buf, self.pos, self.end = buf, pos, len(buf) if end is None else end

    def byte(self) -> int:
        if self.pos >= self.end:
            raise MalformedModule("unexpected end of module", offset=self.pos)
        b = self.buf[self.pos]
        self.pos += 1
        return b

    def u32(self) -> int:
        result = shift = 0
        for i in range(5):
            b = self.byte()
            if i == 4 and b & 0x70:
                raise MalformedModule("LEB128 u32 overflow", offset=self.pos - 1)
            result |= (b & 0x7F) << shift
            if not b & 0x80:
                return result
            shift += 7
        raise MalformedModule("LEB128 u32 too long", offset=self.pos)

    def name(self) -> str:
        n = self.u32()
        if self.pos + n > self.end:
            raise MalformedModule("name runs past section end", offset=self.pos)
        raw = self.buf[self.pos:self.pos + n]
        self.pos += n
        try:
            return raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MalformedModule("name is not valid UTF-8", offset=self.pos - n) from exc

    def limits(self) -> tuple[int, int | None]:
        flag = self.byte()
        if flag not in (0, 1):
            raise MalformedModule("unsupported limits flag (memory64/shared refused)", offset=self.pos - 1)
        lo = self.u32()
        hi = self.u32() if flag == 1 else None
        if hi is not None and hi < lo:
            raise MalformedModule("limits max below min", offset=self.pos)
        return lo, hi


@dataclass(frozen=True, slots=True)
class ModuleSummary:
    sha256: str
    size: int
    sections: tuple[str, ...]
    imports: tuple[tuple[str, str, str], ...]   # (module, name, kind)
    memory_min_pages: int | None
    memory_max_pages: int | None

    def to_dict(self) -> dict:
        return {
            "sha256": self.sha256,
            "size": self.size,
            "sections": list(self.sections),
            "imports": [list(i) for i in self.imports],
            "memory_min_pages": self.memory_min_pages,
            "memory_max_pages": self.memory_max_pages,
        }


def parse_module(data: bytes) -> ModuleSummary:
    """Structurally validate a Wasm binary; raise :class:`MalformedModule` on any defect."""
    if not isinstance(data, (bytes, bytearray)):
        raise MalformedModule("module must be bytes")
    data = bytes(data)
    if len(data) > MAX_MODULE_BYTES:
        raise MalformedModule("module exceeds size limit", size=len(data))
    if data[:4] != WASM_MAGIC:
        raise MalformedModule("bad magic")
    if data[4:8] != WASM_VERSION:
        raise MalformedModule("unsupported binary version")
    r = _Reader(data, 8)
    last_rank = 0
    seen: set[int] = set()
    sections: list[str] = []
    imports: list[tuple[str, str, str]] = []
    mem_min = mem_max = None
    n_types = n_funcs_imported = n_mems = n_tables = n_globals = 0
    func_types: list[int] = []
    code_count: int | None = None
    exports: set[str] = set()
    while r.pos < r.end:
        sid = r.byte()
        size = r.u32()
        start = r.pos
        if start + size > r.end:
            raise MalformedModule("section runs past end of module", section=sid, offset=start)
        if sid not in _SECTION_NAMES:
            raise MalformedModule("unknown section id", section=sid, offset=start - 1)
        if sid != 0:
            if sid in seen:
                raise MalformedModule("duplicate section", section=_SECTION_NAMES[sid])
            rank = _SECTION_ORDER[sid]
            if rank <= last_rank:
                raise MalformedModule("section out of order", section=_SECTION_NAMES[sid])
            last_rank = rank
            seen.add(sid)
        body = _Reader(data, start, start + size)
        if sid == 0:
            body.name()  # custom section name must be valid
        elif sid == 1:
            n_types = body.u32()
            for _ in range(n_types):
                if body.byte() != 0x60:
                    raise MalformedModule("type entry is not a function type")
                for _ in range(2):  # params, results
                    for _ in range(body.u32()):
                        if body.byte() not in _VALTYPES:
                            raise MalformedModule("unknown value type")
            _end(body, "type")
        elif sid == 2:
            for _ in range(body.u32()):
                mod, nm = body.name(), body.name()
                kind = body.byte()
                if kind not in _IMPORT_KINDS:
                    raise MalformedModule("unknown import kind", kind=kind)
                if kind == 0:
                    if body.u32() >= n_types:
                        raise MalformedModule("import type index out of range")
                    n_funcs_imported += 1
                elif kind == 1:
                    if body.byte() not in (0x70, 0x6F):
                        raise MalformedModule("unknown table element type")
                    body.limits(); n_tables += 1
                elif kind == 2:
                    lo, hi = body.limits()
                    mem_min, mem_max = lo, hi
                    n_mems += 1
                elif kind == 3:
                    if body.byte() not in _VALTYPES or body.byte() not in (0, 1):
                        raise MalformedModule("bad global import")
                    n_globals += 1
                else:
                    body.byte(); body.u32()
                imports.append((mod, nm, _IMPORT_KINDS[kind]))
            if body.pos != body.end:
                raise MalformedModule("import section has trailing bytes")
        elif sid == 3:
            for _ in range(body.u32()):
                idx = body.u32()
                if idx >= n_types:
                    raise MalformedModule("function type index out of range")
                func_types.append(idx)
            _end(body, "function")
        elif sid == 10:
            code_count = body.u32()
            if code_count != len(func_types):
                raise MalformedModule("code count does not match function count")
            for _ in range(code_count):
                fsize = body.u32()
                fstart = body.pos
                if fsize == 0 or fstart + fsize > body.end:
                    raise MalformedModule("function body size out of range")
                if data[fstart + fsize - 1] != 0x0B:
                    raise MalformedModule("function body does not end with 'end'")
                fb = _Reader(data, fstart, fstart + fsize)
                for _ in range(fb.u32()):  # local declarations
                    fb.u32()
                    if fb.byte() not in _VALTYPES:
                        raise MalformedModule("unknown local type")
                if fb.pos > fb.end:
                    raise MalformedModule("locals overrun body")
                body.pos = fstart + fsize
            _end(body, "code")
        elif sid == 7:
            for _ in range(body.u32()):
                nm = body.name()
                if nm in exports:
                    raise MalformedModule("duplicate export name")
                exports.add(nm)
                kind, idx = body.byte(), body.u32()
                limit = {0: n_funcs_imported + len(func_types), 1: n_tables, 2: n_mems, 3: n_globals}.get(kind)
                if limit is None or idx >= limit:
                    raise MalformedModule("export index out of range", kind=kind)
            _end(body, "export")
        elif sid == 5:
            count = body.u32()
            if count + n_mems > 1:
                raise MalformedModule("multiple memories refused by hardening profile")
            for _ in range(count):
                mem_min, mem_max = body.limits()
                n_mems += 1
            if body.pos != body.end:
                raise MalformedModule("memory section has trailing bytes")
        sections.append(_SECTION_NAMES[sid])
        r.pos = start + size
    if func_types and code_count is None:
        raise MalformedModule("functions declared without a code section")
    return ModuleSummary(
        sha256=hashlib.sha256(data).hexdigest(),
        size=len(data),
        sections=tuple(sections),
        imports=tuple(imports),
        memory_min_pages=mem_min,
        memory_max_pages=mem_max,
    )


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


@dataclass(frozen=True, slots=True)
class Keyring:
    """Key id -> secret. Secrets never appear in receipts, logs or repr."""

    keys: Mapping[str, bytes]

    def __post_init__(self) -> None:
        for kid, secret in self.keys.items():
            if not isinstance(secret, bytes) or len(secret) < 32:
                raise ValueError(f"key {kid!r} must be >= 32 bytes")

    def __repr__(self) -> str:
        return f"Keyring(key_ids={sorted(self.keys)})"

    def mac(self, kid: str, payload: bytes) -> str:
        if kid not in self.keys:
            raise ReceiptInvalid("unknown key id", key_id=kid)
        return hmac.new(self.keys[kid], payload, hashlib.sha256).hexdigest()


@dataclass(frozen=True, slots=True)
class Toolchain:
    name: str
    version: str
    digest: str  # sha256 of the toolchain binary/image

    def ident(self) -> str:
        return f"{self.name}@{self.version}#{self.digest}"


def issue_receipt(data: bytes, *, toolchain: Toolchain, hardening: Iterable[str],
                  keyring: Keyring, key_id: str, issued_at: int | None = None) -> dict:
    summary = parse_module(data)
    body = {
        "schema": RECEIPT_SCHEMA,
        "module": summary.to_dict(),
        "toolchain": toolchain.ident(),
        "hardening": sorted(set(hardening)),
        "issued_at": int(time.time()) if issued_at is None else int(issued_at),
        "key_id": key_id,
    }
    return {"body": body, "mac": keyring.mac(key_id, canonical(body))}


def verify_receipt(data: bytes, receipt: Mapping, *, keyring: Keyring,
                   approved_toolchains: Iterable[str], max_age_s: int | None = None,
                   now: int | None = None) -> ModuleSummary:
    """Return the summary only when every bound field re-derives from ``data``."""
    if not isinstance(receipt, Mapping) or set(receipt) != {"body", "mac"}:
        raise ReceiptInvalid("receipt must have exactly body and mac")
    body = receipt["body"]
    if not isinstance(body, Mapping) or body.get("schema") != RECEIPT_SCHEMA:
        raise ReceiptInvalid("unsupported receipt schema")
    expected = keyring.mac(str(body.get("key_id")), canonical(dict(body)))
    if not hmac.compare_digest(expected, str(receipt["mac"])):
        raise ReceiptInvalid("receipt MAC mismatch")
    summary = parse_module(data)
    if body.get("module") != summary.to_dict():
        raise ReceiptInvalid("receipt is not bound to these module bytes", sha256=summary.sha256)
    if body.get("toolchain") not in set(approved_toolchains):
        raise ToolchainUnapproved("toolchain not approved", toolchain=body.get("toolchain"))
    missing = REQUIRED_HARDENING - set(body.get("hardening", ()))
    if missing:
        raise ReceiptInvalid("receipt hardening profile incomplete", missing=sorted(missing))
    if max_age_s is not None:
        current = int(time.time()) if now is None else now
        issued = body.get("issued_at")
        if not isinstance(issued, int) or issued > current or current - issued > max_age_s:
            raise ReceiptInvalid("receipt outside freshness window")
    return summary
