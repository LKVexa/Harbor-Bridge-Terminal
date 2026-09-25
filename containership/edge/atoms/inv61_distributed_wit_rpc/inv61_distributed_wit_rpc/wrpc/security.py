"""M05/M06/M08/M09 - negotiation, peer authentication, channel encryption, anti-replay.

Handshake (PK_WRPC_HELLO/1), pre-shared-key mutual authentication:

  C -> S  HELLO   {peer, key_id, versions[], nonce_c}
  S -> C  ACCEPT  {peer, version, nonce_s, mac_s}
  C -> S  FINISH  {mac_c}

  transcript = canonical JSON of (HELLO, ACCEPT-without-mac)
  prk        = HKDF-SHA256(salt=nonce_c||nonce_s, ikm=PSK[key_id])
  mac_s      = HMAC(prk, "server"||transcript)   mac_c = HMAC(prk, "client"||transcript)
  session keys c2s / s2c = HKDF-Expand(prk, "c2s"/"s2c")

Because the client's offered version list is inside the MAC'd transcript, a
man-in-the-middle that strips versions to force a downgrade breaks mac_s
(downgrade protection, M05). Records are AES-256-GCM with a 96-bit nonce made
from a direction byte and a strictly increasing 64-bit sequence number; a
repeated or reordered sequence is rejected (anti-replay, M09) and the nonce is
never reused under one key (M08). ``cryptography`` is the only third-party
dependency; without it the channel refuses to start (fail closed).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac
import json
import os
import struct
import threading
import time

try:  # optional, pinned in pyproject.toml; absent => fail closed
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except ImportError:  # pragma: no cover
    AESGCM = None

SUPPORTED_VERSIONS = ("wrpc/2",)          # ordered most-preferred first
DEPRECATED_VERSIONS: tuple = ()           # none yet; a deprecation mechanism is OPEN
MAX_RECORD = 1 << 20


class SecurityError(Exception):
    """Wire-safe security failure; ``code`` never includes secret material."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _hkdf_extract(salt: bytes, ikm: bytes) -> bytes:
    return hmac.new(salt, ikm, hashlib.sha256).digest()


def _hkdf_expand(prk: bytes, info: bytes, n: int = 32) -> bytes:
    out, t, i = b"", b"", 1
    while len(out) < n:
        t = hmac.new(prk, t + info + bytes([i]), hashlib.sha256).digest()
        out += t
        i += 1
    return out[:n]


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


@dataclass
class KeyEntry:
    key_id: str
    peer: str
    secret: bytes
    not_after: float
    revoked: bool = False


@dataclass
class Keyring:
    """M06 credential store: per-peer PSKs with ids, expiry, rotation and revocation."""

    entries: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def add(self, peer: str, secret: bytes, ttl_s: float, key_id: str | None = None, now: float | None = None) -> str:
        if len(secret) < 32:
            raise SecurityError("weak-key")
        kid = key_id or os.urandom(8).hex()
        with self._lock:
            if kid in self.entries:
                raise SecurityError("duplicate-key-id")
            self.entries[kid] = KeyEntry(kid, peer, bytes(secret), (time.time() if now is None else now) + ttl_s)
        return kid

    def rotate(self, peer: str, secret: bytes, ttl_s: float, overlap_s: float, now: float | None = None) -> str:
        """Add a new key and shorten every older live key of ``peer`` to ``overlap_s``."""
        now = time.time() if now is None else now
        with self._lock:
            for e in self.entries.values():
                if e.peer == peer and not e.revoked:
                    e.not_after = min(e.not_after, now + overlap_s)
        return self.add(peer, secret, ttl_s, now=now)

    def revoke(self, key_id: str) -> None:
        with self._lock:
            if key_id in self.entries:
                self.entries[key_id].revoked = True

    def lookup(self, key_id: str, peer: str, now: float | None = None) -> bytes:
        now = time.time() if now is None else now
        with self._lock:
            e = self.entries.get(key_id)
            # one generic code for every failure: no oracle for which part was wrong
            if e is None or e.revoked or e.peer != peer or now >= e.not_after:
                raise SecurityError("authentication-failed")
            return e.secret

    def current(self, peer: str, now: float | None = None) -> str:
        now = time.time() if now is None else now
        with self._lock:
            live = [e for e in self.entries.values() if e.peer == peer and not e.revoked and now < e.not_after]
        if not live:
            raise SecurityError("no-credential")
        return max(live, key=lambda e: e.not_after).key_id


def negotiate(offered: list, supported=SUPPORTED_VERSIONS) -> str:
    """M05: pick the most-preferred locally supported version the peer offered."""
    if not isinstance(offered, list) or not offered or len(offered) > 16:
        raise SecurityError("bad-offer")
    for v in supported:
        if v in offered:
            return v
    raise SecurityError("no-common-version")


class ReplayWindow:
    """M09: sliding window over record sequence numbers, plus an optional strict
    request-id rejector (``check_request``) for callers that need at-most-once *rejection*.
    ``Node`` does not use ``check_request``: it answers duplicate request ids from the
    idempotency cache instead (THREAT_MODEL.md T-04)."""

    def __init__(self, request_ttl_s: float = 300.0, max_ids: int = 65536):
        self.highest = -1
        self.ttl = request_ttl_s
        self.max_ids = max_ids
        self.seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def check_seq(self, seq: int) -> None:
        with self._lock:
            if seq <= self.highest:
                raise SecurityError("replay")
            self.highest = seq

    def check_request(self, request_id: str, now: float) -> None:
        with self._lock:
            if len(self.seen) >= self.max_ids:
                for k in [k for k, t in self.seen.items() if now - t > self.ttl]:
                    del self.seen[k]
                if len(self.seen) >= self.max_ids:
                    raise SecurityError("replay-cache-full")   # fail closed, never evict live ids
            if request_id in self.seen:
                raise SecurityError("replay")
            self.seen[request_id] = now


class Channel:
    """M08: AEAD record layer for one established session."""

    def __init__(self, send_key: bytes, recv_key: bytes, send_dir: int, session_id: bytes):
        if AESGCM is None:
            raise SecurityError("crypto-unavailable")
        self._send = AESGCM(send_key)
        self._recv = AESGCM(recv_key)
        self._dir = send_dir
        self._sid = session_id
        self._seq = 0
        self._lock = threading.Lock()
        self.replay = ReplayWindow()

    def seal(self, plaintext: bytes) -> bytes:
        if len(plaintext) > MAX_RECORD:
            raise SecurityError("record-too-large")
        with self._lock:
            seq = self._seq
            if seq >= 2 ** 63:
                raise SecurityError("rekey-required")
            self._seq += 1
        nonce = bytes([self._dir]) + b"\0\0\0" + struct.pack(">Q", seq)
        return struct.pack(">Q", seq) + self._send.encrypt(nonce, plaintext, self._sid)

    def open(self, record: bytes) -> bytes:
        if len(record) < 8 + 16 or len(record) > MAX_RECORD + 24:
            raise SecurityError("record-malformed")
        seq = struct.unpack(">Q", record[:8])[0]
        nonce = bytes([1 - self._dir]) + b"\0\0\0" + record[:8]
        try:
            pt = self._recv.decrypt(nonce, record[8:], self._sid)
        except Exception:
            raise SecurityError("record-auth-failed") from None
        self.replay.check_seq(seq)        # only after authentication, so forgeries can't advance the window
        return pt


def _keys(psk: bytes, nc: bytes, ns: bytes):
    prk = _hkdf_extract(nc + ns, psk)
    return prk, _hkdf_expand(prk, b"c2s"), _hkdf_expand(prk, b"s2c"), _hkdf_expand(prk, b"sid", 16)


class ClientHandshake:
    def __init__(self, peer: str, key_id: str, psk: bytes, versions=SUPPORTED_VERSIONS):
        self.hello = {"type": "hello", "peer": peer, "key_id": key_id,
                      "versions": list(versions), "nonce": os.urandom(32).hex()}
        self.psk = psk

    def finish(self, accept: dict, expected_server: str) -> tuple[dict, Channel, str]:
        try:
            body = {k: accept[k] for k in ("type", "peer", "version", "nonce")}
            mac_s = bytes.fromhex(accept["mac"])
            ns = bytes.fromhex(accept["nonce"])
        except (KeyError, TypeError, ValueError):
            raise SecurityError("handshake-malformed") from None
        if body["type"] != "accept" or body["peer"] != expected_server or len(ns) != 32:
            raise SecurityError("authentication-failed")
        if body["version"] not in self.hello["versions"]:
            raise SecurityError("downgrade")
        transcript = _canon([self.hello, body])
        prk, c2s, s2c, sid = _keys(self.psk, bytes.fromhex(self.hello["nonce"]), ns)
        if not hmac.compare_digest(mac_s, hmac.new(prk, b"server" + transcript, hashlib.sha256).digest()):
            raise SecurityError("authentication-failed")
        fin = {"type": "finish", "mac": hmac.new(prk, b"client" + transcript, hashlib.sha256).hexdigest()}
        return fin, Channel(c2s, s2c, 0, sid), body["version"]


class ServerHandshake:
    def __init__(self, server_peer: str, keyring: Keyring, supported=SUPPORTED_VERSIONS):
        self.me = server_peer
        self.keyring = keyring
        self.supported = supported

    def accept(self, hello: dict, now: float | None = None) -> dict:
        try:
            if hello.get("type") != "hello":
                raise KeyError
            peer, kid, nc = hello["peer"], hello["key_id"], bytes.fromhex(hello["nonce"])
            versions = hello["versions"]
        except (KeyError, TypeError, ValueError, AttributeError):
            raise SecurityError("handshake-malformed") from None
        if len(nc) != 32 or not isinstance(peer, str) or not isinstance(kid, str):
            raise SecurityError("handshake-malformed")
        psk = self.keyring.lookup(kid, peer, now)
        version = negotiate(versions, self.supported)
        body = {"type": "accept", "peer": self.me, "version": version, "nonce": os.urandom(32).hex()}
        transcript = _canon([{"type": "hello", "peer": peer, "key_id": kid, "versions": versions,
                              "nonce": hello["nonce"]}, body])
        prk, c2s, s2c, sid = _keys(psk, nc, bytes.fromhex(body["nonce"]))
        self._pending = (prk, transcript, c2s, s2c, sid, peer, version)
        return dict(body, mac=hmac.new(prk, b"server" + transcript, hashlib.sha256).hexdigest())

    def complete(self, finish: dict) -> tuple[Channel, str, str]:
        prk, transcript, c2s, s2c, sid, peer, version = self._pending
        try:
            mac_c = bytes.fromhex(finish["mac"])
        except (KeyError, TypeError, ValueError):
            raise SecurityError("handshake-malformed") from None
        if not hmac.compare_digest(mac_c, hmac.new(prk, b"client" + transcript, hashlib.sha256).digest()):
            raise SecurityError("authentication-failed")
        return Channel(s2c, c2s, 1, sid), peer, version
