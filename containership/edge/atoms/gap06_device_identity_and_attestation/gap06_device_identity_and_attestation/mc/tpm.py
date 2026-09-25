"""MC-01 / MC-32: bounds-checked TPM 2.0 quote parsing and verification.

Parses TPMS_ATTEST (TPM 2.0 Library Part 2 §10.12.12) and TPMT_SIGNATURE,
recomputes the PCR composite digest, replays a crypto-agile TCG event log
(TCG_PCR_EVENT2) and checks clockInfo monotonicity.  Every parse error raises a
Gap06Error; there is no lenient mode.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass, field

from . import algorithms as alg
from .errors import Gap06Error, fail

TPM_GENERATED_VALUE = 0xFF544347
TPM_ST_ATTEST_QUOTE = 0x8018
TPM_ALG_RSASSA, TPM_ALG_RSAPSS, TPM_ALG_ECDSA = 0x0014, 0x0016, 0x0018
MAX_QUOTE = 4096
MAX_EVENTLOG = 4 * 1024 * 1024
MAX_EVENTS = 20_000
MAX_EVENT_DATA = 64 * 1024
EV_NO_ACTION = 0x00000003


class _Reader:
    def __init__(self, data: bytes):
        if not isinstance(data, (bytes, bytearray)):
            raise fail("E_MALFORMED_EVIDENCE", "bytes required")
        self.b, self.i = bytes(data), 0

    def take(self, n: int) -> bytes:
        if n < 0 or self.i + n > len(self.b):
            raise fail("E_MALFORMED_EVIDENCE", f"truncated at offset {self.i} (+{n})")
        out = self.b[self.i:self.i + n]
        self.i += n
        return out

    def u8(self): return self.take(1)[0]
    def u16(self): return struct.unpack(">H", self.take(2))[0]
    def u32(self): return struct.unpack(">I", self.take(4))[0]
    def u64(self): return struct.unpack(">Q", self.take(8))[0]
    def le32(self): return struct.unpack("<I", self.take(4))[0]
    def le16(self): return struct.unpack("<H", self.take(2))[0]

    def tpm2b(self, maximum: int) -> bytes:
        n = self.u16()
        if n > maximum:
            raise fail("E_MALFORMED_EVIDENCE", f"TPM2B length {n} exceeds {maximum}")
        return self.take(n)

    def done(self):
        if self.i != len(self.b):
            raise fail("E_TRAILING_BYTES", f"{len(self.b) - self.i} trailing bytes")


@dataclass(frozen=True)
class ClockInfo:
    clock: int
    reset_count: int
    restart_count: int
    safe: bool


@dataclass(frozen=True)
class Quote:
    qualified_signer: bytes
    extra_data: bytes
    clock_info: ClockInfo
    firmware_version: int
    pcr_selection: tuple  # ((alg_name, (pcr indices...)), ...)
    pcr_digest: bytes
    raw: bytes


def parse_attest(data: bytes) -> Quote:
    if len(data) > MAX_QUOTE:
        raise fail("E_MALFORMED_EVIDENCE", "quote too large")
    r = _Reader(data)
    if r.u32() != TPM_GENERATED_VALUE:
        raise fail("E_BAD_MAGIC", "not TPM_GENERATED_VALUE")
    if r.u16() != TPM_ST_ATTEST_QUOTE:
        raise fail("E_MALFORMED_EVIDENCE", "attest type is not TPM_ST_ATTEST_QUOTE")
    signer = r.tpm2b(68)
    extra = r.tpm2b(64)
    ci = ClockInfo(r.u64(), r.u32(), r.u32(), None)
    safe = r.u8()
    if safe not in (0, 1):
        raise fail("E_MALFORMED_EVIDENCE", "clockInfo.safe must be 0 or 1")
    ci = ClockInfo(ci.clock, ci.reset_count, ci.restart_count, bool(safe))
    fw = r.u64()
    count = r.u32()
    if count == 0 or count > 16:
        raise fail("E_MALFORMED_EVIDENCE", f"illegal pcrSelect count {count}")
    sel, seen = [], set()
    for _ in range(count):
        hid = r.u16()
        if hid not in alg.TPM_ALG:
            raise fail("E_UNSUPPORTED_ALG", f"unknown PCR bank 0x{hid:04x}")
        if hid in seen:
            raise fail("E_MALFORMED_EVIDENCE", "duplicate PCR bank in selection")
        seen.add(hid)
        size = r.u8()
        if size < 3 or size > 4:
            raise fail("E_MALFORMED_EVIDENCE", f"illegal sizeofSelect {size}")
        bitmap = r.take(size)
        pcrs = tuple(i for i in range(size * 8) if bitmap[i // 8] >> (i % 8) & 1)
        if not pcrs:
            raise fail("E_MALFORMED_EVIDENCE", "empty PCR bitmap")
        sel.append((alg.TPM_ALG[hid], pcrs))
    pcr_digest = r.tpm2b(64)
    r.done()
    return Quote(signer, extra, ci, fw, tuple(sel), pcr_digest, bytes(data))


def build_attest(*, nonce: bytes, signer: bytes, clock: ClockInfo, firmware: int,
                 selection, pcr_digest: bytes) -> bytes:
    """Serialiser used by the simulator/test vectors (inverse of parse_attest)."""
    out = struct.pack(">IH", TPM_GENERATED_VALUE, TPM_ST_ATTEST_QUOTE)
    out += struct.pack(">H", len(signer)) + signer + struct.pack(">H", len(nonce)) + nonce
    out += struct.pack(">QIIB", clock.clock, clock.reset_count, clock.restart_count, int(clock.safe))
    out += struct.pack(">Q", firmware) + struct.pack(">I", len(selection))
    for name, pcrs in selection:
        bm = bytearray(3)
        for p in pcrs:
            bm[p // 8] |= 1 << (p % 8)
        out += struct.pack(">HB", alg.TPM_ALG_ID[name], 3) + bytes(bm)
    return out + struct.pack(">H", len(pcr_digest)) + pcr_digest


def parse_signature(data: bytes) -> tuple[str, bytes]:
    """TPMT_SIGNATURE -> (profile, signature bytes in cryptography's format)."""
    r = _Reader(data)
    sig_alg, hash_alg = r.u16(), r.u16()
    hname = alg.TPM_ALG.get(hash_alg)
    if sig_alg == TPM_ALG_ECDSA:
        rr, ss = r.tpm2b(66), r.tpm2b(66)
        r.done()
        prof = {"sha256": "ecdsa-p256-sha256", "sha384": "ecdsa-p384-sha384"}.get(hname)
        if not prof:
            raise fail("E_UNSUPPORTED_ALG", "ECDSA hash not allowed")
        return prof, alg.ecdsa_raw_to_der(rr, ss)
    if sig_alg in (TPM_ALG_RSASSA, TPM_ALG_RSAPSS):
        sig = r.tpm2b(1024)
        r.done()
        if hname != "sha256":
            raise fail("E_UNSUPPORTED_ALG", "RSA hash not allowed")
        return ("rsassa-pkcs1v15-sha256" if sig_alg == TPM_ALG_RSASSA else "rsassa-pss-sha256"), sig
    raise fail("E_UNSUPPORTED_ALG", f"signature scheme 0x{sig_alg:04x}")


def pcr_composite(selection, pcr_values: dict, digest_alg: str = "sha256") -> bytes:
    """Digest of concatenated PCR values in selection order (TPM2_Quote semantics)."""
    h = hashlib.new(digest_alg)
    for bank, pcrs in selection:
        for p in pcrs:
            v = pcr_values.get((bank, p))
            if v is None or len(v) != alg.DIGEST_SIZE[bank]:
                raise fail("E_PCR_MISMATCH", f"missing/illegal value for {bank}:{p}")
            h.update(v)
    return h.digest()


@dataclass(frozen=True)
class Event:
    pcr: int
    event_type: int
    digests: dict
    data_sha256: str
    data_verified: bool = False


@dataclass
class ReplayResult:
    pcrs: dict = field(default_factory=dict)
    events: int = 0
    log_sha256: str = ""


# Event types whose TCG-defined digest is the hash of the event data itself.
# For these the parser REQUIRES digest == H(data); data of other types is not
# bound by the PCR and is surfaced as unverified (never usable by policy).
DATA_BOUND_TYPES = {0x00000008, 0x0000000D}  # EV_S_CRTM_VERSION, EV_IPL
# TCG PC Client PFP event types (1.05).  Unknown types are rejected: the PCR
# binds only digests, so an unregistered type code is either corruption or an
# attempt to relabel an event.
KNOWN_EVENT_TYPES = set(range(0x00000000, 0x00000013)) | {
    0x80000001, 0x80000002, 0x80000003, 0x80000004, 0x80000005, 0x80000006, 0x80000007, 0x80000008,
    0x80000009, 0x8000000A, 0x8000000B, 0x8000000C, 0x800000E0, 0x800000E1}


def _parse_spec_id(spec: bytes) -> dict:
    r = _Reader(spec)
    if r.take(16) != b"Spec ID Event03\0":
        raise fail("E_MALFORMED_EVIDENCE", "unsupported Spec ID signature")
    platform_class = r.le32()
    minor, major, errata, uintn = r.take(4)
    if major != 2 or uintn not in (1, 2):
        raise fail("E_MALFORMED_EVIDENCE", "Spec ID version/uintnSize not supported")
    n = r.le32()
    if n == 0 or n > 5:
        raise fail("E_MALFORMED_EVIDENCE", "Spec ID algorithm count")
    algs = {}
    for _ in range(n):
        aid, size = r.le16(), r.le16()
        name = alg.TPM_ALG.get(aid)
        if name is None or alg.DIGEST_SIZE[name] != size or name in algs:
            raise fail("E_MALFORMED_EVIDENCE", "Spec ID algorithm table")
        algs[name] = size
    vendor = r.u8()
    r.take(vendor)
    r.done()
    return {"platform_class": platform_class, "algs": algs}


def parse_event_log(data: bytes) -> list[Event]:
    """Crypto-agile TCG log: legacy TCG_PCR_EVENT header carrying a fully
    parsed TCG_EfiSpecIDEvent (EV_NO_ACTION, zero digest), followed by
    TCG_PCR_EVENT2 entries whose digest set must equal the declared algorithms.
    Little-endian per the TCG PC Client PFP specification."""
    if len(data) > MAX_EVENTLOG:
        raise fail("E_MALFORMED_EVIDENCE", "event log too large")
    r = _Reader(data)
    pcr, etype = r.le32(), r.le32()
    if r.take(20) != b"\0" * 20:
        raise fail("E_MALFORMED_EVIDENCE", "Spec ID header digest must be zero")
    size = r.le32()
    if etype != EV_NO_ACTION or pcr != 0 or size > MAX_EVENT_DATA:
        raise fail("E_MALFORMED_EVIDENCE", "event log must start with a Spec ID EV_NO_ACTION header")
    declared = _parse_spec_id(r.take(size))["algs"]
    events = []
    while r.i < len(r.b):
        if len(events) >= MAX_EVENTS:
            raise fail("E_MALFORMED_EVIDENCE", "too many events")
        pcr, etype, n = r.le32(), r.le32(), r.le32()
        if etype not in KNOWN_EVENT_TYPES:
            raise fail("E_MALFORMED_EVIDENCE", f"unknown event type 0x{etype:08x}")
        if pcr > 23 or n != len(declared):
            raise fail("E_MALFORMED_EVIDENCE", "illegal PCR index or digest count")
        ds = {}
        for _ in range(n):
            aid = r.le16()
            name = alg.TPM_ALG.get(aid)
            if name not in declared:
                raise fail("E_MALFORMED_EVIDENCE", f"event digest alg 0x{aid:04x} not declared")
            if name in ds:
                raise fail("E_MALFORMED_EVIDENCE", "duplicate digest alg in event")
            ds[name] = r.take(alg.DIGEST_SIZE[name])
        size = r.le32()
        if size > MAX_EVENT_DATA:
            raise fail("E_MALFORMED_EVIDENCE", "event data too large")
        body = r.take(size)
        if etype in DATA_BOUND_TYPES:
            for name, d in ds.items():
                if hashlib.new(name, body).digest() != d:
                    raise fail("E_EVENTLOG_MISMATCH", f"event {len(events)} data does not match its digest")
        events.append(Event(pcr, etype, ds, hashlib.sha256(body).hexdigest(), etype in DATA_BOUND_TYPES))
    return events


def build_event_log(entries, algs=("sha256",)) -> bytes:
    """entries: iterable of (pcr, type, {alg: digest}, data)."""
    spec = b"Spec ID Event03\0" + struct.pack("<I", 0) + bytes([0, 2, 0, 2]) + struct.pack("<I", len(algs))
    for a in algs:
        spec += struct.pack("<HH", alg.TPM_ALG_ID[a], alg.DIGEST_SIZE[a])
    spec += b"\0"
    out = struct.pack("<II", 0, EV_NO_ACTION) + b"\0" * 20 + struct.pack("<I", len(spec)) + spec
    for pcr, et, ds, body in entries:
        out += struct.pack("<III", pcr, et, len(ds))
        for name, d in ds.items():
            out += struct.pack("<H", alg.TPM_ALG_ID[name]) + d
        out += struct.pack("<I", len(body)) + body
    return out


def replay(events: list[Event], bank: str) -> dict:
    pcrs: dict = {}
    for e in events:
        if e.event_type == EV_NO_ACTION:
            continue
        if bank not in e.digests:
            raise fail("E_EVENTLOG_MISMATCH", f"event lacks {bank} digest")
        cur = pcrs.get(e.pcr, b"\0" * alg.DIGEST_SIZE[bank])
        pcrs[e.pcr] = hashlib.new(bank, cur + e.digests[bank]).digest()
    return pcrs


def first_divergence(events: list[Event], bank: str, quoted: dict) -> int | None:
    """Index of the last event of the first PCR whose replay differs from the
    quoted value; None when the log matches."""
    final = replay(events, bank)
    for pcr, value in sorted(quoted.items()):
        if final.get(pcr, b"\0" * alg.DIGEST_SIZE[bank]) != value:
            idx = [i for i, e in enumerate(events) if e.pcr == pcr and e.event_type != EV_NO_ACTION]
            return idx[-1] if idx else -1
    return None


@dataclass
class ClockTracker:
    """01.09: per-AK monotonic clockInfo tracking."""
    last: dict = field(default_factory=dict)

    def check(self, ak_id: str, ci: ClockInfo) -> None:
        if not ci.safe:
            raise fail("E_TPM_CLOCK_UNSAFE", "clockInfo.safe is NO")
        prev = self.last.get(ak_id)
        if prev is not None:
            if ci.reset_count < prev.reset_count or (
                    ci.reset_count == prev.reset_count and ci.restart_count < prev.restart_count) or (
                    (ci.reset_count, ci.restart_count) == (prev.reset_count, prev.restart_count) and ci.clock <= prev.clock):
                raise fail("E_CLOCK_ROLLBACK", "TPM clock/reset/restart counters went backwards")
        self.last[ak_id] = ci
