"""STUN (RFC 8489) codec, client and a minimal server (G12-A001, also used by
TURN, ICE, NAT classification and the lab).

Implemented: 20-byte header with magic cookie and 96-bit transaction id,
Binding request/success/error, XOR-MAPPED-ADDRESS (IPv4/IPv6), MAPPED-ADDRESS,
OTHER-ADDRESS / RESPONSE-ORIGIN (RFC 5780), CHANGE-REQUEST, ERROR-CODE,
USERNAME, REALM, NONCE, SOFTWARE, MESSAGE-INTEGRITY (HMAC-SHA1),
MESSAGE-INTEGRITY-SHA256, FINGERPRINT (CRC-32 xor 0x5354554E), unknown
comprehension-required attribute detection, UDP retransmission per RFC 8489
section 6.2.1 (RTO doubling, Rc=7 sends, final wait Rm*RTO), transaction-id
matching, duplicate / late / foreign response discard, and multi-server
discovery that classifies DNS failure, blocked UDP, server error, malformed
response and cross-server mapping inconsistency.

Unsupported (explicit, never silently emulated): STUN over DTLS; the
ALTERNATE-SERVER redirect is reported (reason DEP_UNAVAILABLE) but not
followed; password algorithms negotiation (PASSWORD-ALGORITHMS) is not
implemented, so only the legacy MD5 long-term key and short-term keys are
supported.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import select
import socket
import struct
import threading
import time
import zlib
from dataclasses import dataclass, field

MAGIC = 0x2112A442
FP_XOR = 0x5354554E
HEADER = struct.Struct("!HHI12s")

# message classes/methods
BINDING = 0x001
CLS_REQUEST, CLS_INDICATION, CLS_SUCCESS, CLS_ERROR = 0b00, 0b01, 0b10, 0b11

A_MAPPED_ADDRESS = 0x0001
A_CHANGE_REQUEST = 0x0003
A_USERNAME = 0x0006
A_MESSAGE_INTEGRITY = 0x0008
A_ERROR_CODE = 0x0009
A_UNKNOWN_ATTRIBUTES = 0x000A
A_REALM = 0x0014
A_NONCE = 0x0015
A_MESSAGE_INTEGRITY_SHA256 = 0x001C
A_XOR_MAPPED_ADDRESS = 0x0020
A_SOFTWARE = 0x8022
A_ALTERNATE_SERVER = 0x8023
A_FINGERPRINT = 0x8028
A_RESPONSE_ORIGIN = 0x802B
A_OTHER_ADDRESS = 0x802C

KNOWN_ATTRS = {A_MAPPED_ADDRESS, A_CHANGE_REQUEST, A_USERNAME, A_MESSAGE_INTEGRITY, A_ERROR_CODE,
               A_UNKNOWN_ATTRIBUTES, A_REALM, A_NONCE, A_MESSAGE_INTEGRITY_SHA256,
               A_XOR_MAPPED_ADDRESS, A_SOFTWARE, A_ALTERNATE_SERVER, A_FINGERPRINT,
               A_RESPONSE_ORIGIN, A_OTHER_ADDRESS}
EXTRA_KNOWN: set[int] = set()   # TURN registers its attributes here

MAX_MESSAGE = 1500
RTO_DEFAULT = 0.5
RC = 7
RM = 16


class StunError(ValueError):
    """Malformed or unacceptable STUN message."""


def msg_type(method: int, cls: int) -> int:
    return ((method & 0x0F80) << 2) | ((method & 0x0070) << 1) | (method & 0x000F) | ((cls & 2) << 7) | ((cls & 1) << 4)


def split_type(t: int) -> tuple[int, int]:
    method = (t & 0x000F) | ((t & 0x00E0) >> 1) | ((t & 0x3E00) >> 2)
    cls = ((t & 0x0100) >> 7) | ((t & 0x0010) >> 4)
    return method, cls


def new_txid() -> bytes:
    return os.urandom(12)


@dataclass
class Message:
    method: int
    cls: int
    txid: bytes = field(default_factory=new_txid)
    attrs: list[tuple[int, bytes]] = field(default_factory=list)
    raw: bytes = b""

    def get(self, atype: int) -> bytes | None:
        for t, v in self.attrs:
            if t == atype:
                return v
        return None

    def add(self, atype: int, value: bytes) -> "Message":
        self.attrs.append((atype, value))
        return self

    # --- encoding -------------------------------------------------------
    def encode(self, key: bytes | None = None, *, sha256: bool = False, fingerprint: bool = False) -> bytes:
        if len(self.txid) != 12:
            raise StunError("transaction id must be 96 bits")
        body = b"".join(_attr(t, v) for t, v in self.attrs)
        t = msg_type(self.method, self.cls)
        if key is not None:
            mi_type, mi_len = (A_MESSAGE_INTEGRITY_SHA256, 32) if sha256 else (A_MESSAGE_INTEGRITY, 20)
            hdr = HEADER.pack(t, len(body) + 4 + mi_len, MAGIC, self.txid)
            digest = hmac.new(key, hdr + body, hashlib.sha256 if sha256 else hashlib.sha1).digest()
            body += _attr(mi_type, digest)
        if fingerprint:
            hdr = HEADER.pack(t, len(body) + 8, MAGIC, self.txid)
            crc = (zlib.crc32(hdr + body) & 0xFFFFFFFF) ^ FP_XOR
            body += _attr(A_FINGERPRINT, struct.pack("!I", crc))
        return HEADER.pack(t, len(body), MAGIC, self.txid) + body


def _attr(t: int, v: bytes) -> bytes:
    if len(v) > 0xFFFF:
        raise StunError("attribute too long")
    pad = (-len(v)) % 4
    return struct.pack("!HH", t, len(v)) + v + b"\x00" * pad


def is_stun(data: bytes) -> bool:
    return len(data) >= 20 and data[0] & 0xC0 == 0 and struct.unpack_from("!I", data, 4)[0] == MAGIC


def decode(data: bytes) -> Message:
    """Strict decoder: never trusts a length field beyond the buffer."""
    if not isinstance(data, (bytes, bytearray)):
        raise StunError("not bytes")
    data = bytes(data)
    if len(data) < 20:
        raise StunError("short header")
    if len(data) > 65535 + 20:
        raise StunError("oversized")
    t, length, cookie, txid = HEADER.unpack_from(data)
    if t & 0xC000:
        raise StunError("top two bits must be zero")
    if cookie != MAGIC:
        raise StunError("bad magic cookie")
    if length % 4 or 20 + length != len(data):
        raise StunError("length mismatch")
    method, cls = split_type(t)
    attrs: list[tuple[int, bytes]] = []
    off = 20
    seen_integrity = seen_fp = False
    while off < len(data):
        if off + 4 > len(data):
            raise StunError("truncated attribute header")
        at, al = struct.unpack_from("!HH", data, off)
        start = off + 4
        end = start + al
        if end > len(data):
            raise StunError("attribute overruns message")
        if seen_fp:
            raise StunError("attribute after FINGERPRINT")
        if seen_integrity and at not in (A_FINGERPRINT, A_MESSAGE_INTEGRITY_SHA256):
            # RFC 8489 14.5: attributes after MESSAGE-INTEGRITY are ignored (except FP)
            off = end + ((-al) % 4)
            continue
        attrs.append((at, data[start:end]))
        if at in (A_MESSAGE_INTEGRITY, A_MESSAGE_INTEGRITY_SHA256):
            seen_integrity = True
        if at == A_FINGERPRINT:
            seen_fp = True
        if len(attrs) > 64:
            raise StunError("too many attributes")
        off = end + ((-al) % 4)
    if off != len(data):
        raise StunError("trailing bytes")
    return Message(method, cls, txid, attrs, data)


def unknown_required(msg: Message) -> list[int]:
    known = KNOWN_ATTRS | EXTRA_KNOWN
    return [t for t, _ in msg.attrs if t < 0x8000 and t not in known]


def check_fingerprint(msg: Message) -> bool | None:
    """True/False when a FINGERPRINT is present, None when absent."""
    raw = msg.raw
    idx = _attr_offset(raw, A_FINGERPRINT)
    if idx is None:
        return None
    hdr = bytearray(raw[:idx])
    struct.pack_into("!H", hdr, 2, idx - 20 + 8)
    crc = (zlib.crc32(bytes(hdr)) & 0xFFFFFFFF) ^ FP_XOR
    return struct.unpack_from("!I", raw, idx + 4)[0] == crc


def check_integrity(msg: Message, key: bytes) -> bool | None:
    raw = msg.raw
    for atype, algo, n in ((A_MESSAGE_INTEGRITY_SHA256, hashlib.sha256, 32), (A_MESSAGE_INTEGRITY, hashlib.sha1, 20)):
        idx = _attr_offset(raw, atype)
        if idx is None:
            continue
        hdr = bytearray(raw[:idx])
        struct.pack_into("!H", hdr, 2, idx - 20 + 4 + n)
        want = hmac.new(key, bytes(hdr), algo).digest()
        return hmac.compare_digest(want, raw[idx + 4: idx + 4 + n])
    return None


def _attr_offset(raw: bytes, atype: int) -> int | None:
    off = 20
    while off + 4 <= len(raw):
        at, al = struct.unpack_from("!HH", raw, off)
        if at == atype:
            return off
        off += 4 + al + ((-al) % 4)
    return None


def long_term_key(username: str, realm: str, password: str) -> bytes:
    return hashlib.md5(f"{username}:{realm}:{password}".encode()).digest()


# --- address attributes -------------------------------------------------------

def encode_address(ip: str, port: int, *, xor: bool, txid: bytes = b"\x00" * 12) -> bytes:
    addr = ipaddress.ip_address(ip)
    fam = 1 if addr.version == 4 else 2
    raw = addr.packed
    if xor:
        port ^= MAGIC >> 16
        mask = struct.pack("!I", MAGIC) + (txid if fam == 2 else b"")
        raw = bytes(a ^ b for a, b in zip(raw, mask))
    return struct.pack("!BBH", 0, fam, port) + raw


def decode_address(value: bytes, *, xor: bool, txid: bytes = b"\x00" * 12) -> tuple[str, int]:
    if len(value) < 4:
        raise StunError("short address attribute")
    _, fam, port = struct.unpack_from("!BBH", value)
    raw = value[4:]
    if (fam, len(raw)) not in ((1, 4), (2, 16)):
        raise StunError("bad address family/length")
    if xor:
        port ^= MAGIC >> 16
        mask = struct.pack("!I", MAGIC) + (txid if fam == 2 else b"")
        raw = bytes(a ^ b for a, b in zip(raw, mask))
    return str(ipaddress.ip_address(raw)), port


def error_code(value: bytes) -> tuple[int, str]:
    if len(value) < 4:
        raise StunError("short ERROR-CODE")
    cls, num = value[2] & 0x07, value[3]
    return cls * 100 + num, value[4:].decode("utf-8", "replace")


def encode_error(code: int, reason: str) -> bytes:
    return struct.pack("!HBB", 0, code // 100, code % 100) + reason.encode()


# --- client ---------------------------------------------------------------------

@dataclass
class BindingResult:
    ok: bool
    reason: str
    server: tuple[str, int] | None = None
    mapped: tuple[str, int] | None = None
    other: tuple[str, int] | None = None
    origin: tuple[str, int] | None = None
    local: tuple[str, int] | None = None
    rtt: float | None = None
    sends: int = 0
    discarded: int = 0
    error: int | None = None


def transact(sock: socket.socket, server: tuple[str, int], req: Message, *, key: bytes | None = None,
             rto: float = RTO_DEFAULT, rc: int = RC, rm: int = RM, deadline: float | None = None,
             fingerprint: bool = True, cancel: threading.Event | None = None,
             clock=time.monotonic, accept_any_source: bool = False) -> tuple[Message | None, BindingResult]:
    """Run one STUN transaction over an unconnected UDP socket.

    Retransmits per RFC 8489 6.2.1, matches the transaction id and source
    address, discards duplicates/foreign/late packets, honours a hard deadline
    and a cancellation event, and never leaves a pending receive behind.
    """
    wire = req.encode(key, fingerprint=fingerprint)
    start = clock()
    res = BindingResult(False, "NET_TIMEOUT", server=server)
    send_times: list[float] = []
    timeout = rto
    sends = 0
    next_send = start
    final_deadline = None
    while True:
        now = clock()
        if cancel is not None and cancel.is_set():
            res.reason = "CANCELLED_SHUTDOWN"
            return None, res
        if deadline is not None and now >= deadline:
            if res.reason not in ("DEP_MALFORMED", "AUTH_INTEGRITY"):
                res.reason = "CANCELLED_DEADLINE" if sends else "NET_TIMEOUT"
            res.sends = sends
            return None, res
        if final_deadline is None and now >= next_send:
            try:
                sock.sendto(wire, server)
            except OSError:
                res.reason = "NET_UNREACHABLE"
                res.sends = sends
                return None, res
            sends += 1
            send_times.append(now)
            if sends >= rc:
                final_deadline = now + rm * rto
            else:
                next_send = now + timeout
                timeout *= 2
        wake = final_deadline if final_deadline is not None else next_send
        if deadline is not None:
            wake = min(wake, deadline)
        if final_deadline is not None and now >= final_deadline:
            res.sends = sends
            return None, res
        wait = max(0.0, min(wake - now, 0.05 if cancel is not None else wake - now))
        r, _, _ = select.select([sock], [], [], wait)
        if not r:
            continue
        try:
            data, src = sock.recvfrom(65535)
        except OSError:
            res.reason = "NET_REFUSED"
            res.sends = sends
            return None, res
        if not is_stun(data):
            res.discarded += 1
            continue
        try:
            msg = decode(data)
        except StunError:
            res.discarded += 1
            res.reason = "DEP_MALFORMED"
            continue
        if msg.txid != req.txid or (not accept_any_source and _norm(src) != _norm(server)):
            res.discarded += 1  # foreign / late response from an older transaction
            continue
        if check_fingerprint(msg) is False:
            res.discarded += 1
            continue
        if key is not None and msg.cls in (CLS_SUCCESS,) and check_integrity(msg, key) is not True:
            res.discarded += 1
            res.reason = "AUTH_INTEGRITY"
            continue
        res.sends = sends
        res.rtt = clock() - send_times[-1] if len(send_times) == 1 else None  # Karn: ambiguous after retransmit
        res.local = sock.getsockname()[:2]
        return msg, res


def _norm(addr) -> tuple[str, int]:
    return str(ipaddress.ip_address(addr[0].split("%")[0])), int(addr[1])


def binding(sock: socket.socket, server: tuple[str, int], *, change_ip: bool = False, change_port: bool = False,
            **kw) -> BindingResult:
    req = Message(BINDING, CLS_REQUEST)
    if change_ip or change_port:
        req.add(A_CHANGE_REQUEST, struct.pack("!I", (4 if change_ip else 0) | (2 if change_port else 0)))
    # RFC 5780 4.4: answers to CHANGE-REQUEST legitimately come from another address;
    # the 96-bit transaction id is still required to match.
    msg, res = transact(sock, server, req, accept_any_source=change_ip or change_port, **kw)
    if msg is None:
        return res
    if msg.cls == CLS_ERROR:
        ec = msg.get(A_ERROR_CODE)
        res.error = error_code(ec)[0] if ec else None
        res.reason = "AUTH_FAILED" if res.error in (401, 438) else "DEP_UNAVAILABLE"
        return res
    if msg.cls != CLS_SUCCESS or msg.method != BINDING:
        res.reason = "DEP_MALFORMED"
        return res
    if unknown_required(msg):
        res.reason = "DEP_MALFORMED"
        return res
    try:
        xma = msg.get(A_XOR_MAPPED_ADDRESS)
        if xma is not None:
            res.mapped = decode_address(xma, xor=True, txid=msg.txid)
        elif msg.get(A_MAPPED_ADDRESS) is not None:
            res.mapped = decode_address(msg.get(A_MAPPED_ADDRESS), xor=False)
        else:
            res.reason = "DEP_MALFORMED"
            return res
        if msg.get(A_OTHER_ADDRESS):
            res.other = decode_address(msg.get(A_OTHER_ADDRESS), xor=False)
        if msg.get(A_RESPONSE_ORIGIN):
            res.origin = decode_address(msg.get(A_RESPONSE_ORIGIN), xor=False)
    except StunError:
        res.reason = "DEP_MALFORMED"
        return res
    res.ok = True
    res.reason = "OK"
    return res


@dataclass
class Discovery:
    reason: str
    mapped: tuple[str, int] | None
    per_server: list[dict]
    consistent: bool | None


def discover(servers: list[tuple[str, int]], *, family: int = socket.AF_INET, bind: tuple[str, int] | None = None,
             resolver=None, deadline_s: float = 3.0, rto: float = 0.1, rc: int = 4, rm: int = 4) -> Discovery:
    """Query several independent servers from ONE local socket.

    Distinguishes: DNS failure (resolver raised), blocked UDP (every server
    timed out), individual server failure, malformed response, and mapping
    inconsistency (servers disagree -> address/port-dependent mapping or an
    anycast/multi-homed middlebox; reported as DEP_INCONSISTENT, never hidden).
    """
    sock = socket.socket(family, socket.SOCK_DGRAM)
    try:
        sock.bind(bind or (("0.0.0.0" if family == socket.AF_INET else "::"), 0))
        results: list[dict] = []
        end = time.monotonic() + deadline_s
        for host, port in servers:
            entry = {"server": f"{host}:{port}"}
            try:
                addr = resolver(host) if resolver else host
                ipaddress.ip_address(addr)
            except Exception as exc:  # resolver outcome, classified not propagated
                entry.update(ok=False, reason="DNS_NXDOMAIN" if isinstance(exc, (KeyError, LookupError)) else "DNS_TIMEOUT")
                results.append(entry)
                continue
            r = binding(sock, (addr, port), rto=rto, rc=rc, rm=rm, deadline=end)
            entry.update(ok=r.ok, reason=r.reason, mapped=r.mapped, sends=r.sends, discarded=r.discarded)
            results.append(entry)
        oks = [e for e in results if e["ok"]]
        if not oks:
            if all(e["reason"].startswith("DNS_") for e in results):
                reason = "DNS_TIMEOUT"
            elif all(e["reason"] in ("NET_TIMEOUT", "CANCELLED_DEADLINE") for e in results if not e["reason"].startswith("DNS_")):
                reason = "NET_UDP_BLOCKED"
            elif any(e["reason"] == "DEP_MALFORMED" for e in results):
                reason = "DEP_MALFORMED"
            else:
                reason = "DEP_UNAVAILABLE"
            return Discovery(reason, None, results, None)
        mapped = {tuple(e["mapped"]) for e in oks}
        consistent = len(mapped) == 1 if len(oks) > 1 else None
        return Discovery("OK" if consistent is not False else "DEP_INCONSISTENT",
                         oks[0]["mapped"], results, consistent)
    finally:
        sock.close()


# --- server (lab + tests) ---------------------------------------------------------

class StunServer:
    """RFC 5780-capable Binding server.

    ``addresses`` is a list of (ip, port) sockets it listens on; with two IPs
    and two ports it can honour CHANGE-REQUEST like a full RFC 5780 server.
    Fault injection hooks: ``drop``, ``malformed``, ``wrong_mapping``,
    ``require_key`` and ``duplicate``.
    """

    def __init__(self, addresses: list[tuple[str, int]], *, drop: float = 0.0, malformed: bool = False,
                 wrong_mapping: bool = False, require_key: bytes | None = None, duplicate: bool = False,
                 software: str = "gap12-lab", fail_with: int | None = None):
        self.socks = []
        for ip, port in addresses:
            fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
            s = socket.socket(fam, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((ip, port))
            self.socks.append(s)
        self.addresses = [s.getsockname()[:2] for s in self.socks]
        self.drop, self.malformed, self.wrong_mapping = drop, malformed, wrong_mapping
        self.require_key, self.duplicate, self.software = require_key, duplicate, software
        self.fail_with = fail_with
        self.requests = 0
        self._stop = threading.Event()
        self._rng = __import__("random").Random(1)
        self._t = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self.close()

    def close(self):
        self._stop.set()
        self._t.join(timeout=2)
        for s in self.socks:
            s.close()

    def _pick(self, base: socket.socket, change_ip: bool, change_port: bool) -> socket.socket:
        bip, bport = base.getsockname()[:2]
        for s in self.socks:
            ip, port = s.getsockname()[:2]
            if (ip != bip) == change_ip and (port != bport) == change_port and s.family == base.family:
                return s
        return base

    def _other(self, base: socket.socket):
        bip, bport = base.getsockname()[:2]
        for s in self.socks:
            ip, port = s.getsockname()[:2]
            if ip != bip and port != bport and s.family == base.family:
                return ip, port
        return None

    def _run(self):
        while not self._stop.is_set():
            r, _, _ = select.select(self.socks, [], [], 0.05)
            for s in r:
                try:
                    data, src = s.recvfrom(65535)
                except OSError:
                    continue
                self.requests += 1
                if self.drop and self._rng.random() < self.drop:
                    continue
                try:
                    req = decode(data)
                except StunError:
                    continue
                if req.method != BINDING or req.cls != CLS_REQUEST:
                    continue
                if self.fail_with:
                    resp = Message(BINDING, CLS_ERROR, req.txid).add(A_ERROR_CODE, encode_error(self.fail_with, "Server Error"))
                    s.sendto(resp.encode(fingerprint=True), src)
                    continue
                if self.malformed:
                    s.sendto(data[:20] + b"\x00\x20\x00\xff", src)
                    continue
                cr = req.get(A_CHANGE_REQUEST)
                flags = struct.unpack("!I", cr)[0] if cr and len(cr) == 4 else 0
                out = self._pick(s, bool(flags & 4), bool(flags & 2))
                if self.require_key is not None and check_integrity(req, self.require_key) is not True:
                    resp = Message(BINDING, CLS_ERROR, req.txid).add(A_ERROR_CODE, encode_error(401, "Unauthorized"))
                    s.sendto(resp.encode(fingerprint=True), src)
                    continue
                mip, mport = src[0].split("%")[0], src[1]
                if self.wrong_mapping:
                    mport = (mport + 1) % 65536 or 1
                resp = Message(BINDING, CLS_SUCCESS, req.txid)
                resp.add(A_XOR_MAPPED_ADDRESS, encode_address(mip, mport, xor=True, txid=req.txid))
                oip, oport = out.getsockname()[:2]
                resp.add(A_RESPONSE_ORIGIN, encode_address(oip, oport, xor=False))
                other = self._other(s)
                if other:
                    resp.add(A_OTHER_ADDRESS, encode_address(other[0], other[1], xor=False))
                resp.add(A_SOFTWARE, self.software.encode())
                wire = resp.encode(self.require_key, fingerprint=True)
                out.sendto(wire, src)
                if self.duplicate:
                    out.sendto(wire, src)
