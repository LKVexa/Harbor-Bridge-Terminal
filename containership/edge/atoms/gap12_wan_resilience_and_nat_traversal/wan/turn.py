"""TURN (RFC 8656) client and a minimal UDP relay server (G12-A002, G12-C040,
G12-D047, G12-D048).

Client: Allocate with the 401 -> REALM/NONCE long-term credential exchange,
438 Stale Nonce retry, Refresh (lifetime renewal and lifetime=0 teardown),
CreatePermission (300 s permission lifetime, refreshed at 240 s),
ChannelBind (600 s binding, refreshed at 540 s, channel numbers
0x4000-0x4FFF), Send / Data indications and ChannelData framing, allocation
expiry tracking and deterministic teardown.  Bytes are counted automatically
at the relay data-plane boundary (payload vs. framing overhead separated, a
retransmitted control request is never counted as payload).

Server: UDP-transport relay for lab/integration use with per-username tenant
isolation, quota (bytes) enforcement, allocation expiry and a usage report the
client counters are reconciled against.

Unsupported (explicit): TURN over TCP/TLS/DTLS transports (RFC 6062 TCP
allocations), EVEN-PORT / RESERVATION-TOKEN, DONT-FRAGMENT, ADDITIONAL-ADDRESS-
FAMILY dual allocations, and third-party authorization (RFC 7635 OAuth).
"""
from __future__ import annotations

import os
import secrets
import select
import socket
import struct
import threading
import time
from dataclasses import dataclass, field

from . import stun
from .stun import (A_ERROR_CODE, A_NONCE, A_REALM, A_USERNAME, CLS_ERROR, CLS_INDICATION,
                   CLS_REQUEST, CLS_SUCCESS, Message, decode, encode_address, decode_address,
                   encode_error, error_code, long_term_key)

ALLOCATE, REFRESH, SEND, DATA, CREATE_PERMISSION, CHANNEL_BIND = 0x003, 0x004, 0x006, 0x007, 0x008, 0x009
A_CHANNEL_NUMBER = 0x000C
A_LIFETIME = 0x000D
A_XOR_PEER_ADDRESS = 0x0012
A_DATA = 0x0013
A_XOR_RELAYED_ADDRESS = 0x0016
A_REQUESTED_TRANSPORT = 0x0019
stun.EXTRA_KNOWN.update({A_CHANNEL_NUMBER, A_LIFETIME, A_XOR_PEER_ADDRESS, A_DATA,
                         A_XOR_RELAYED_ADDRESS, A_REQUESTED_TRANSPORT})

UDP_PROTO = 17
PERMISSION_LIFETIME = 300
CHANNEL_LIFETIME = 600
DEFAULT_LIFETIME = 600
CHANNEL_MIN, CHANNEL_MAX = 0x4000, 0x4FFF


class TurnError(RuntimeError):
    def __init__(self, reason: str, code: int | None = None):
        super().__init__(reason if code is None else f"{reason} ({code})")
        self.reason, self.code = reason, code


def channel_data(channel: int, payload: bytes) -> bytes:
    if not CHANNEL_MIN <= channel <= CHANNEL_MAX:
        raise ValueError("channel number out of range")
    if len(payload) > 0xFFFF:
        raise ValueError("payload too large")
    return struct.pack("!HH", channel, len(payload)) + payload + b"\x00" * ((-len(payload)) % 4)


def parse_channel_data(data: bytes) -> tuple[int, bytes]:
    if len(data) < 4:
        raise ValueError("short ChannelData")
    ch, ln = struct.unpack_from("!HH", data)
    if not CHANNEL_MIN <= ch <= CHANNEL_MAX:
        raise ValueError("not ChannelData")
    if 4 + ln > len(data):
        raise ValueError("ChannelData length overruns datagram")
    return ch, data[4:4 + ln]


@dataclass
class Counters:
    payload_out: int = 0
    payload_in: int = 0
    overhead_out: int = 0
    overhead_in: int = 0
    control_out: int = 0

    def as_dict(self):
        return dict(self.__dict__)


@dataclass
class TurnClient:
    server: tuple[str, int]
    username: str
    password: str
    sock: socket.socket | None = None
    clock: object = time.monotonic
    rto: float = 0.1
    rc: int = 4
    rm: int = 4
    realm: str | None = None
    nonce: bytes | None = None
    relayed: tuple[str, int] | None = None
    mapped: tuple[str, int] | None = None
    expires_at: float | None = None
    permissions: dict[str, float] = field(default_factory=dict)
    channels: dict[tuple[str, int], tuple[int, float]] = field(default_factory=dict)
    counters: Counters = field(default_factory=Counters)
    closed: bool = False

    def __post_init__(self):
        if self.sock is None:
            fam = socket.AF_INET6 if ":" in self.server[0] else socket.AF_INET
            self.sock = socket.socket(fam, socket.SOCK_DGRAM)
            self.sock.bind(("::" if fam == socket.AF_INET6 else "0.0.0.0", 0))
        self._next_channel = CHANNEL_MIN

    # -- control transactions ------------------------------------------------
    def _key(self) -> bytes:
        return long_term_key(self.username, self.realm or "", self.password)

    def _request(self, method: int, attrs: list[tuple[int, bytes]], *, authenticated: bool = True,
                 _retry: int = 0) -> Message:
        req = Message(method, CLS_REQUEST)
        for atype, value in attrs:
            req.add(atype, value(req.txid) if callable(value) else value)
        key = None
        if authenticated and self.realm is not None:
            req.add(A_USERNAME, self.username.encode()).add(A_REALM, self.realm.encode()).add(A_NONCE, self.nonce or b"")
            key = self._key()
        msg, res = stun.transact(self.sock, self.server, req, key=key, rto=self.rto, rc=self.rc, rm=self.rm,
                                 clock=self.clock)
        self.counters.control_out += len(req.encode(key, fingerprint=True))
        if msg is None:
            raise TurnError(res.reason)
        if msg.cls == CLS_ERROR:
            code, _ = error_code(msg.get(A_ERROR_CODE) or b"\x00\x00\x05\x00")
            if code in (401, 438) and _retry < 2:
                realm, nonce = msg.get(A_REALM), msg.get(A_NONCE)
                if realm is None or nonce is None:
                    raise TurnError("AUTH_FAILED", code)
                if code == 401 and self.realm is not None and _retry:
                    raise TurnError("AUTH_FAILED", code)
                self.realm, self.nonce = realm.decode(), nonce
                return self._request(method, attrs, authenticated=True, _retry=_retry + 1)
            reason = {401: "AUTH_FAILED", 403: "POLICY_EGRESS_DENIED", 437: "DEFECT_PROTOCOL",
                      486: "BUDGET_QUOTA_EXHAUSTED", 508: "BUDGET_QUOTA_EXHAUSTED"}.get(code, "DEP_UNAVAILABLE")
            raise TurnError(reason, code)
        if self.realm is not None and stun.check_integrity(msg, self._key()) is not True:
            raise TurnError("AUTH_INTEGRITY")
        return msg

    def allocate(self, lifetime: int = DEFAULT_LIFETIME) -> tuple[str, int]:
        msg = self._request(ALLOCATE, [(A_REQUESTED_TRANSPORT, struct.pack("!B3x", UDP_PROTO)),
                                       (A_LIFETIME, struct.pack("!I", lifetime))], authenticated=self.realm is not None)
        self.relayed = decode_address(msg.get(A_XOR_RELAYED_ADDRESS), xor=True, txid=msg.txid)
        xm = msg.get(stun.A_XOR_MAPPED_ADDRESS)
        self.mapped = decode_address(xm, xor=True, txid=msg.txid) if xm else None
        granted = struct.unpack("!I", msg.get(A_LIFETIME))[0]
        self.expires_at = self.clock() + granted
        return self.relayed

    def refresh(self, lifetime: int = DEFAULT_LIFETIME) -> int:
        msg = self._request(REFRESH, [(A_LIFETIME, struct.pack("!I", lifetime))])
        granted = struct.unpack("!I", msg.get(A_LIFETIME))[0]
        self.expires_at = self.clock() + granted if granted else None
        return granted

    def create_permission(self, peer_ip: str) -> None:
        self._request(CREATE_PERMISSION, [(A_XOR_PEER_ADDRESS, lambda tx: encode_address(peer_ip, 0, xor=True, txid=tx))])
        self.permissions[peer_ip] = self.clock() + PERMISSION_LIFETIME

    def channel_bind(self, peer: tuple[str, int]) -> int:
        if peer in self.channels:
            ch = self.channels[peer][0]
        else:
            if self._next_channel > CHANNEL_MAX:
                raise TurnError("BUDGET_QUOTA_EXHAUSTED")
            ch = self._next_channel
            self._next_channel += 1
        self._request(CHANNEL_BIND, [(A_CHANNEL_NUMBER, struct.pack("!H2x", ch)),
                                     (A_XOR_PEER_ADDRESS, lambda tx: encode_address(peer[0], peer[1], xor=True, txid=tx))])
        self.channels[peer] = (ch, self.clock() + CHANNEL_LIFETIME)
        self.permissions[peer[0]] = self.clock() + PERMISSION_LIFETIME
        return ch

    def due_refreshes(self) -> dict[str, list]:
        """What must be refreshed now (allocation at 80 %, permission at 240 s, channel at 540 s)."""
        now = self.clock()
        out: dict[str, list] = {"allocation": [], "permissions": [], "channels": []}
        if self.expires_at is not None and self.expires_at - now < 0.2 * DEFAULT_LIFETIME:
            out["allocation"].append(self.relayed)
        out["permissions"] = [p for p, exp in self.permissions.items() if exp - now < 60]
        out["channels"] = [p for p, (_, exp) in self.channels.items() if exp - now < 60]
        return out

    def maintain(self) -> dict[str, int]:
        due = self.due_refreshes()
        if due["allocation"]:
            self.refresh()
        for p in due["permissions"]:
            self.create_permission(p)
        for p in due["channels"]:
            self.channel_bind(p)
        return {k: len(v) for k, v in due.items()}

    # -- data plane ------------------------------------------------------------
    def send(self, peer: tuple[str, int], payload: bytes) -> None:
        if self.closed:
            raise TurnError("DEFECT_PROTOCOL")
        if peer[0] not in self.permissions:
            raise TurnError("POLICY_EGRESS_DENIED")
        if peer in self.channels:
            wire = channel_data(self.channels[peer][0], payload)
        else:
            ind = Message(SEND, CLS_INDICATION)
            ind.add(A_XOR_PEER_ADDRESS, encode_address(peer[0], peer[1], xor=True, txid=ind.txid))
            ind.add(A_DATA, payload)
            wire = ind.encode()
        self.sock.sendto(wire, self.server)
        self.counters.payload_out += len(payload)
        self.counters.overhead_out += len(wire) - len(payload)

    def recv(self, timeout: float = 1.0) -> tuple[tuple[str, int], bytes] | None:
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            r, _, _ = select.select([self.sock], [], [], max(0.0, end - time.monotonic()))
            if not r:
                return None
            data, src = self.sock.recvfrom(65535)
            if tuple(src[:2]) != tuple(self.server):
                continue  # never accept relay data from anything but the server
            if data and CHANNEL_MIN >> 8 <= data[0] <= CHANNEL_MAX >> 8:
                ch, payload = parse_channel_data(data)
                peer = next((p for p, (c, _) in self.channels.items() if c == ch), None)
                if peer is None:
                    continue
            else:
                try:
                    msg = decode(data)
                except stun.StunError:
                    continue
                if msg.method != DATA or msg.cls != CLS_INDICATION:
                    continue
                peer = decode_address(msg.get(A_XOR_PEER_ADDRESS), xor=True, txid=msg.txid)
                payload = msg.get(A_DATA) or b""
            self.counters.payload_in += len(payload)
            self.counters.overhead_in += len(data) - len(payload)
            return peer, payload
        return None

    def close(self) -> None:
        """Deterministic teardown: lifetime=0 Refresh, then socket close; idempotent."""
        if self.closed:
            return
        try:
            if self.relayed is not None:
                try:
                    self.refresh(0)
                except TurnError:
                    pass
        finally:
            self.closed = True
            self.relayed = None
            self.permissions.clear()
            self.channels.clear()
            self.sock.close()


# --------------------------------------------------------------------------------
@dataclass
class _Alloc:
    client: tuple[str, int]
    user: str
    relay: socket.socket
    expires: float
    perms: dict[str, float] = field(default_factory=dict)
    chans: dict[int, tuple[str, int]] = field(default_factory=dict)
    bytes_relayed: int = 0


class TurnServer:
    """Minimal UDP TURN server for lab/integration use (not a production relay)."""

    def __init__(self, listen: tuple[str, int], users: dict[str, str], *, realm: str = "gap12.lab",
                 relay_ip: str | None = None, quota_bytes: dict[str, int] | None = None,
                 max_lifetime: int = 3600, clock=time.monotonic):
        fam = socket.AF_INET6 if ":" in listen[0] else socket.AF_INET
        self.sock = socket.socket(fam, socket.SOCK_DGRAM)
        self.sock.bind(listen)
        self.address = self.sock.getsockname()[:2]
        self.users, self.realm = users, realm
        self.relay_ip = relay_ip or self.address[0]
        self.quota = quota_bytes or {}
        self.usage: dict[str, int] = {}
        self.max_lifetime = max_lifetime
        self.clock = clock
        self.nonces: dict[bytes, float] = {}
        self.allocs: dict[tuple[str, int], _Alloc] = {}
        self._stop = threading.Event()
        self._t = threading.Thread(target=self._run, daemon=True)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self.close()

    def close(self):
        self._stop.set()
        self._t.join(timeout=2)
        for a in self.allocs.values():
            a.relay.close()
        self.allocs.clear()
        self.sock.close()

    def rotate_nonces(self):
        self.nonces.clear()

    def _err(self, req, code, reason, src, with_nonce=False):
        m = Message(req.method, CLS_ERROR, req.txid).add(A_ERROR_CODE, encode_error(code, reason))
        if with_nonce:
            n = secrets.token_hex(8).encode()
            self.nonces[n] = self.clock() + 600
            m.add(A_REALM, self.realm.encode()).add(A_NONCE, n)
        self.sock.sendto(m.encode(fingerprint=True), src)

    def _run(self):
        while not self._stop.is_set():
            socks = [self.sock] + [a.relay for a in self.allocs.values()]
            try:
                r, _, _ = select.select(socks, [], [], 0.05)
            except (OSError, ValueError):
                continue
            now = self.clock()
            for key in [k for k, a in self.allocs.items() if a.expires <= now]:
                self.allocs.pop(key).relay.close()
            for s in r:
                try:
                    data, src = s.recvfrom(65535)
                except OSError:
                    continue
                src = tuple(src[:2])
                if s is self.sock:
                    self._client_packet(data, src)
                else:
                    self._peer_packet(s, data, src)

    def _peer_packet(self, relay, data, src):
        alloc = next((a for a in self.allocs.values() if a.relay is relay), None)
        if alloc is None or src[0] not in alloc.perms or alloc.perms[src[0]] < self.clock():
            return  # no permission: silently dropped (RFC 8656 filtering)
        ch = next((c for c, p in alloc.chans.items() if p == src), None)
        if ch is not None:
            wire = channel_data(ch, data)
        else:
            ind = Message(DATA, CLS_INDICATION)
            ind.add(A_XOR_PEER_ADDRESS, encode_address(src[0], src[1], xor=True, txid=ind.txid))
            ind.add(A_DATA, data)
            wire = ind.encode()
        if self._charge(alloc, len(data)):
            self.sock.sendto(wire, alloc.client)

    def _client_packet(self, data, src):
        alloc = self.allocs.get(src)
        if data and 0x40 <= data[0] <= 0x4F:
            if alloc is None:
                return
            try:
                ch, payload = parse_channel_data(data)
            except ValueError:
                return
            peer = alloc.chans.get(ch)
            if peer is not None and self._charge(alloc, len(payload)):
                alloc.relay.sendto(payload, peer)
            return
        try:
            req = decode(data)
        except stun.StunError:
            return
        if req.cls == CLS_INDICATION and req.method == SEND:
            if alloc is None:
                return
            peer = decode_address(req.get(A_XOR_PEER_ADDRESS), xor=True, txid=req.txid)
            payload = req.get(A_DATA) or b""
            if peer[0] in alloc.perms and self._charge(alloc, len(payload)):
                alloc.relay.sendto(payload, peer)
            return
        if req.cls != CLS_REQUEST:
            return
        user, nonce = req.get(A_USERNAME), req.get(A_NONCE)
        if user is None:
            return self._err(req, 401, "Unauthorized", src, with_nonce=True)
        user = user.decode()
        if nonce not in self.nonces or self.nonces[nonce] < self.clock():
            return self._err(req, 438, "Stale Nonce", src, with_nonce=True)
        pw = self.users.get(user)
        key = long_term_key(user, self.realm, pw or "")
        if pw is None or stun.check_integrity(req, key) is not True:
            return self._err(req, 401, "Unauthorized", src, with_nonce=True)
        ok = Message(req.method, CLS_SUCCESS, req.txid)
        if req.method == ALLOCATE:
            if alloc is not None:
                return self._err(req, 437, "Allocation Mismatch", src)
            limit = self.quota.get(user)
            if limit is not None and self.usage.get(user, 0) >= limit:
                return self._err(req, 486, "Allocation Quota Reached", src)
            relay = socket.socket(self.sock.family, socket.SOCK_DGRAM)
            relay.bind((self.relay_ip, 0))
            lt = req.get(A_LIFETIME)
            life = min(struct.unpack("!I", lt)[0] if lt else DEFAULT_LIFETIME, self.max_lifetime)
            self.allocs[src] = _Alloc(src, user, relay, self.clock() + life)
            rip, rport = relay.getsockname()[:2]
            ok.add(A_XOR_RELAYED_ADDRESS, encode_address(rip, rport, xor=True, txid=req.txid))
            ok.add(stun.A_XOR_MAPPED_ADDRESS, encode_address(src[0], src[1], xor=True, txid=req.txid))
            ok.add(A_LIFETIME, struct.pack("!I", life))
        elif alloc is None or alloc.user != user:
            return self._err(req, 437, "Allocation Mismatch", src)
        elif req.method == REFRESH:
            lt = req.get(A_LIFETIME)
            life = min(struct.unpack("!I", lt)[0] if lt else DEFAULT_LIFETIME, self.max_lifetime)
            if life == 0:
                self.allocs.pop(src).relay.close()
            else:
                alloc.expires = self.clock() + life
            ok.add(A_LIFETIME, struct.pack("!I", life))
        elif req.method == CREATE_PERMISSION:
            ip, _ = decode_address(req.get(A_XOR_PEER_ADDRESS), xor=True, txid=req.txid)
            alloc.perms[ip] = self.clock() + PERMISSION_LIFETIME
        elif req.method == CHANNEL_BIND:
            ch = struct.unpack("!H", req.get(A_CHANNEL_NUMBER)[:2])[0]
            peer = decode_address(req.get(A_XOR_PEER_ADDRESS), xor=True, txid=req.txid)
            if not CHANNEL_MIN <= ch <= CHANNEL_MAX or any(p == peer and c != ch for c, p in alloc.chans.items()):
                return self._err(req, 400, "Bad Request", src)
            alloc.chans[ch] = peer
            alloc.perms[peer[0]] = self.clock() + PERMISSION_LIFETIME
        else:
            return self._err(req, 400, "Bad Request", src)
        self.sock.sendto(ok.encode(key, fingerprint=True), src)

    def _charge(self, alloc: _Alloc, n: int) -> bool:
        limit = self.quota.get(alloc.user)
        used = self.usage.get(alloc.user, 0)
        if limit is not None and used + n > limit:
            return False
        self.usage[alloc.user] = used + n
        alloc.bytes_relayed += n
        return True
