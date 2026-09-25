"""Identity, encryption, trust and abuse resistance (G12-D043..D055).

* ``TrustGate`` — a path is marked trusted only when a GAP-06 attestation
  verifier (injected; GAP-06 is a sibling subsystem not bundled here) accepts
  fresh evidence for the peer.  Reachability never outlives trust: trust
  expires with the attestation and on revocation.  No verifier -> fail closed.
* ``SecureChannel`` — end-to-end AEAD (AES-256-GCM from the ``cryptography``
  package when installed; otherwise the channel refuses to construct —
  there is no plaintext or home-made fallback).  Directional keys derived with
  HKDF-SHA256 from a session secret bound to both identities, role, protocol
  version and epoch; 96-bit nonce = direction-free counter per key, never
  reused; key rotation by epoch; relays only ever see ciphertext.
* ``ReplayWindow`` — RFC 4303-style sliding bitmap (bounded memory) per
  (session, epoch); cross-session and cross-peer frames fail AEAD binding.
* ``TurnRestCredentials`` — time-limited TURN credentials
  (username = expiry:user, password = HMAC(secret, username)), rotation with
  an overlap window, revocation list.
* ``RelayAuthorizer`` — tenancy isolation: a tenant may only use relays of its
  own tenancy and only toward peers its policy names.
* ``RateLimiter`` — hierarchical token buckets (source, peer, tenant, prefix,
  global) with an LRU-bounded key space and a shared overflow bucket so
  attacker-created keys cannot grow memory.
* ``CircuitBreaker`` + ``RetryBudget`` — closed/open/half-open with bounded
  half-open admission and recovery hysteresis; the retry budget is a ratio of
  retries to first attempts shared across nested retry layers.
* ``EgressPolicy`` — deny-by-default CIDR/port/peer allow list; deny wins.
* ``SecretRef`` / ``SecretProvider`` / ``redact`` — secrets are referenced by
  opaque id, loaded through a provider, never repr'd or logged.
* ``AnomalyDetector`` — forced-relay ratio, scan (many distinct peers) and
  credential-failure bursts per source.
* ``AuditLog`` — hash-chained, append-only security events.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import threading
import time
from collections import OrderedDict, deque
from dataclasses import dataclass, field

try:  # optional hardware-backed AEAD; absence disables SecureChannel (fail-closed)
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.hkdf import HKDF
    from cryptography.hazmat.primitives import hashes
    HAVE_AEAD = True
except Exception:  # pragma: no cover - lane-gated
    HAVE_AEAD = False

PROTOCOL = b"GAP12-E2E/1"


# --- D043 trust gate ---------------------------------------------------------------------------

@dataclass
class Attestation:
    peer: str
    issued_at: float
    expires_at: float
    evidence_digest: str


class TrustGate:
    def __init__(self, verifier=None, *, max_age: float = 3600.0, clock=time.time):
        self.verifier, self.max_age, self.clock = verifier, max_age, clock
        self.trusted: dict[str, Attestation] = {}
        self.revoked: set[str] = set()

    def admit(self, peer: str, evidence: bytes) -> tuple[bool, str]:
        if self.verifier is None:
            return False, "DEP_UNAVAILABLE"                 # GAP-06 absent: fail closed
        if peer in self.revoked:
            return False, "POLICY_UNTRUSTED_PEER"
        try:
            att = self.verifier(peer, evidence)
        except Exception:
            return False, "AUTH_FAILED"
        now = self.clock()
        if not isinstance(att, Attestation) or att.peer != peer or not att.issued_at <= now < att.expires_at \
                or now - att.issued_at > self.max_age:
            return False, "POLICY_UNTRUSTED_PEER"
        self.trusted[peer] = att
        return True, "OK"

    def is_trusted(self, peer: str) -> bool:
        att = self.trusted.get(peer)
        if att is None or peer in self.revoked:
            return False
        now = self.clock()
        if not att.issued_at <= now < att.expires_at:
            del self.trusted[peer]                           # reachability cannot outlive trust
            return False
        return True

    def revoke(self, peer: str) -> None:
        self.revoked.add(peer)
        self.trusted.pop(peer, None)


# --- D044/D045/D046 end-to-end channel -----------------------------------------------------------

class ReplayWindow:
    def __init__(self, size: int = 1024):
        if not 64 <= size <= 65536:
            raise ValueError("window size out of range")
        self.size, self.top, self.bitmap = size, -1, 0

    def check_and_set(self, seq: int) -> bool:
        if seq < 0:
            return False
        if seq > self.top:
            shift = seq - self.top
            self.bitmap = ((self.bitmap << shift) | 1) & ((1 << self.size) - 1) if shift < self.size else 1
            self.top = seq
            return True
        off = self.top - seq
        if off >= self.size:
            return False                                      # too old
        if self.bitmap >> off & 1:
            return False                                      # duplicate
        self.bitmap |= 1 << off
        return True


class SecureChannel:
    """AEAD channel; frames: epoch(4) | seq(8) | ciphertext+tag."""

    MAX_SEQ = 2 ** 48                                         # rotate long before nonce exhaustion

    def __init__(self, secret: bytes, *, me: str, peer: str, initiator: bool, epoch: int = 0, window: int = 1024):
        if not HAVE_AEAD:
            raise RuntimeError("AEAD unavailable: install 'cryptography' (no plaintext fallback exists)")
        if len(secret) < 32:
            raise ValueError("session secret must be >= 32 bytes")
        self._secret, self.me, self.peer, self.initiator = secret, me, peer, initiator
        self.window_size = window
        self._install(epoch)

    def _derive(self, label: bytes, epoch: int) -> bytes:
        a, b = sorted([self.me, self.peer])
        info = b"|".join([PROTOCOL, a.encode(), b.encode(), label, epoch.to_bytes(4, "big")])
        return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=info).derive(self._secret)

    def _install(self, epoch: int) -> None:
        i2r, r2i = self._derive(b"i2r", epoch), self._derive(b"r2i", epoch)
        send, recv = (i2r, r2i) if self.initiator else (r2i, i2r)
        self.epoch, self._send, self._recv = epoch, AESGCM(send), AESGCM(recv)
        self.seq, self.replay = 0, ReplayWindow(self.window_size)
        self._aad = PROTOCOL + b"|" + ("|".join(sorted([self.me, self.peer]))).encode()

    def rotate(self) -> int:
        self._install(self.epoch + 1)
        return self.epoch

    def seal(self, plaintext: bytes) -> bytes:
        if self.seq >= self.MAX_SEQ:
            raise OverflowError("sequence exhausted; rotate")
        hdr = self.epoch.to_bytes(4, "big") + self.seq.to_bytes(8, "big")
        nonce = b"\x00" * 4 + self.seq.to_bytes(8, "big")
        self.seq += 1
        return hdr + self._send.encrypt(nonce, plaintext, self._aad + hdr)

    def open(self, frame: bytes) -> bytes:
        if len(frame) < 12 + 16:
            raise ValueError("AUTH_INTEGRITY")
        epoch, seq = int.from_bytes(frame[:4], "big"), int.from_bytes(frame[4:12], "big")
        if epoch != self.epoch:
            raise ValueError("AUTH_REPLAY")                   # stale or future epoch
        nonce = b"\x00" * 4 + frame[4:12]
        try:
            pt = self._recv.decrypt(nonce, frame[12:], self._aad + frame[:12])
        except Exception:
            raise ValueError("AUTH_INTEGRITY") from None
        if not self.replay.check_and_set(seq):
            raise ValueError("AUTH_REPLAY")
        return pt


# --- D047 TURN credentials ---------------------------------------------------------------------------

class TurnRestCredentials:
    def __init__(self, secrets_by_id: dict[str, bytes], active: str, *, ttl: int = 3600, clock=time.time):
        self.secrets, self.active, self.ttl, self.clock = dict(secrets_by_id), active, ttl, clock
        self.revoked: set[str] = set()

    def issue(self, user: str) -> tuple[str, str, str]:
        username = f"{int(self.clock()) + self.ttl}:{user}"
        pw = base64.b64encode(hmac.new(self.secrets[self.active], username.encode(), hashlib.sha1).digest()).decode()
        return username, pw, self.active

    def verify(self, username: str, password: str) -> bool:
        try:
            exp, user = username.split(":", 1)
            if int(exp) < self.clock() or user in self.revoked:
                return False
        except ValueError:
            return False
        for sid, sec in self.secrets.items():                # overlap window: any non-retired secret
            want = base64.b64encode(hmac.new(sec, username.encode(), hashlib.sha1).digest()).decode()
            if hmac.compare_digest(want, password):
                return True
        return False

    def rotate(self, new_id: str, new_secret: bytes, *, retire: str | None = None) -> None:
        self.secrets[new_id] = new_secret
        self.active = new_id
        if retire:
            self.secrets.pop(retire, None)

    def revoke_user(self, user: str) -> None:
        self.revoked.add(user)


# --- D048 relay authorization -------------------------------------------------------------------------

@dataclass
class RelayAuthorizer:
    relay_tenancy: dict[str, str]                 # relay id -> tenant
    peer_policy: dict[str, set[str]]              # tenant -> allowed peer ids

    def authorize(self, tenant: str, relay: str, peer: str) -> str:
        if self.relay_tenancy.get(relay) != tenant:
            return "POLICY_EGRESS_DENIED"
        if peer not in self.peer_policy.get(tenant, set()):
            return "POLICY_EGRESS_DENIED"
        return "OK"


# --- D049 rate limiting -----------------------------------------------------------------------------------

class _Bucket:
    __slots__ = ("tokens", "last")

    def __init__(self, burst, now):
        self.tokens, self.last = float(burst), now


class RateLimiter:
    def __init__(self, limits: dict[str, tuple[float, float]], *, max_keys: int = 10000, clock=time.monotonic):
        """limits: level -> (rate per second, burst). Levels: source, peer, tenant, prefix, destination, global."""
        self.limits, self.max_keys, self.clock = limits, max_keys, clock
        self.buckets: dict[str, OrderedDict] = {lvl: OrderedDict() for lvl in limits}
        self.overflow: dict[str, _Bucket] = {}
        self.denied: dict[str, int] = {lvl: 0 for lvl in limits}
        self._lock = threading.Lock()

    @staticmethod
    def prefix_of(ip: str) -> str:
        a = ipaddress.ip_address(ip)
        return str(ipaddress.ip_network(f"{ip}/{24 if a.version == 4 else 56}", strict=False))

    def _bucket(self, lvl: str, key: str, now: float) -> _Bucket:
        table = self.buckets[lvl]
        b = table.get(key)
        if b is None:
            if len(table) >= self.max_keys:
                # never grow: an unseen key beyond the ceiling shares one overflow bucket
                ob = self.overflow.get(lvl)
                if ob is None:
                    ob = self.overflow[lvl] = _Bucket(self.limits[lvl][1], now)
                return ob
            b = table[key] = _Bucket(self.limits[lvl][1], now)
        table.move_to_end(key)
        return b

    def allow(self, keys: dict[str, str], cost: float = 1.0) -> tuple[bool, str | None]:
        now = self.clock()
        with self._lock:
            touched = []
            for lvl, key in keys.items():
                if lvl not in self.limits:
                    continue
                rate, burst = self.limits[lvl]
                b = self._bucket(lvl, key, now)
                b.tokens = min(burst, b.tokens + (now - b.last) * rate)
                b.last = now
                if b.tokens < cost:
                    self.denied[lvl] += 1
                    return False, lvl
                touched.append(b)
            for b in touched:
                b.tokens -= cost
            return True, None

    def size(self) -> int:
        return sum(len(t) for t in self.buckets.values()) + len(self.overflow)


# --- D050 breaker + retry budget --------------------------------------------------------------------------

class CircuitBreaker:
    def __init__(self, *, failure_threshold: int = 5, open_for: float = 30.0, half_open_max: int = 1,
                 close_after: int = 2, clock=time.monotonic):
        self.failure_threshold, self.open_for = failure_threshold, open_for
        self.half_open_max, self.close_after, self.clock = half_open_max, close_after, clock
        self.state, self.failures, self.opened_at = "closed", 0, None
        self.half_open_inflight = self.half_open_ok = 0
        self.override: str | None = None           # operator: "force_open" | "force_closed" | None
        self.transitions: list[tuple[str, str]] = []

    def _to(self, s):
        self.transitions.append((self.state, s))
        self.state = s

    def admit(self) -> tuple[bool, str]:
        if self.override == "force_open":
            return False, "OPERATOR_DISABLED"
        if self.override == "force_closed":
            return True, "OPERATOR_OVERRIDE"
        if self.state == "open":
            if self.clock() - self.opened_at >= self.open_for:
                self._to("half_open")
                self.half_open_inflight = self.half_open_ok = 0
            else:
                return False, "BUDGET_BREAKER_OPEN"
        if self.state == "half_open":
            if self.half_open_inflight >= self.half_open_max:
                return False, "BUDGET_BREAKER_OPEN"
            self.half_open_inflight += 1
        return True, "OK"

    def record(self, ok: bool) -> None:
        if self.state == "half_open":
            self.half_open_inflight = max(0, self.half_open_inflight - 1)
            if ok:
                self.half_open_ok += 1
                if self.half_open_ok >= self.close_after:
                    self._to("closed")
                    self.failures = 0
            else:
                self._to("open")
                self.opened_at = self.clock()
            return
        if ok:
            self.failures = 0
            return
        self.failures += 1
        if self.state == "closed" and self.failures >= self.failure_threshold:
            self._to("open")
            self.opened_at = self.clock()


class RetryBudget:
    """Retries allowed = ratio * first attempts in the window (+ a small floor).
    One budget object is shared by every nested retry layer, so layers cannot multiply."""

    def __init__(self, ratio: float = 0.2, floor: int = 3, window: float = 10.0, clock=time.monotonic):
        self.ratio, self.floor, self.window, self.clock = ratio, floor, window, clock
        self.firsts: deque = deque()
        self.retries: deque = deque()

    def _trim(self, now):
        for dq in (self.firsts, self.retries):
            while dq and now - dq[0] > self.window:
                dq.popleft()

    def first_attempt(self):
        now = self.clock()
        self._trim(now)
        self.firsts.append(now)

    def try_retry(self) -> bool:
        now = self.clock()
        self._trim(now)
        if len(self.retries) >= self.floor + self.ratio * len(self.firsts):
            return False
        self.retries.append(now)
        return True


# --- D051 egress policy --------------------------------------------------------------------------------------

@dataclass
class EgressPolicy:
    allow: list[tuple[str, tuple[int, int]]] = field(default_factory=list)   # (cidr, (port_lo, port_hi))
    deny: list[str] = field(default_factory=list)
    allowed_peers: set[str] = field(default_factory=set)

    def check(self, ip: str, port: int, peer: str | None = None) -> str:
        a = ipaddress.ip_address(ip)
        if any(a in ipaddress.ip_network(c) for c in self.deny):
            return "POLICY_EGRESS_DENIED"
        if peer is not None and peer not in self.allowed_peers:
            return "POLICY_EGRESS_DENIED"
        for cidr, (lo, hi) in self.allow:
            if a in ipaddress.ip_network(cidr) and lo <= port <= hi:
                return "OK"
        return "POLICY_EGRESS_DENIED"                       # deny by default


# --- D052/D053 secrets and privacy ----------------------------------------------------------------------------

class SecretRef(str):
    """Opaque reference like 'secret://turn/primary'. Never the secret itself."""
    PATTERN = re.compile(r"^secret://[a-z0-9._/-]{1,128}$")

    def __new__(cls, value):
        if not cls.PATTERN.match(value):
            raise ValueError("secret references must look like secret://<path>")
        return super().__new__(cls, value)


class Secret:
    __slots__ = ("_v",)

    def __init__(self, value: bytes):
        self._v = value

    def reveal(self) -> bytes:
        return self._v

    def __repr__(self):
        return "Secret(<redacted>)"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("secrets are not serialisable")


class SecretProvider:
    """Least-privilege lookup: a caller is granted a set of reference prefixes.
    Backends: an in-memory map (tests) or files under a directory (0600) — the
    platform secret manager plugs in behind the same interface."""

    def __init__(self, backend: dict[str, bytes] | str, grants: set[str]):
        self.backend, self.grants = backend, grants
        self.listeners = []
        self.version: dict[str, int] = {}

    def get(self, ref: SecretRef) -> Secret:
        if not any(ref.startswith(g) for g in self.grants):
            raise PermissionError("secret reference outside grant")
        if isinstance(self.backend, dict):
            return Secret(self.backend[ref])
        path = os.path.join(self.backend, ref[len("secret://"):])
        st = os.stat(path)
        if st.st_mode & 0o077:
            raise PermissionError("secret file readable by group/other")
        with open(path, "rb") as fh:
            return Secret(fh.read().strip())

    def on_rotate(self, fn):
        self.listeners.append(fn)

    def rotate(self, ref: SecretRef, value: bytes):
        if not isinstance(self.backend, dict):
            raise NotImplementedError
        self.backend[ref] = value
        self.version[ref] = self.version.get(ref, 0) + 1
        for fn in self.listeners:
            fn(ref)


_IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_IPV6 = re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){2,7}[0-9a-fA-F]{0,4}\b")
_PORTED = re.compile(r"(\[[^\]]+\]|\b(?:\d{1,3}\.){3}\d{1,3}):\d{1,5}\b")
_SECRETISH = re.compile(r"(?i)(password|passwd|secret|token|key|credential)(\"?\s*[:=]\s*\"?)([^\s\",}]+)")


def endpoint_token(ip: str, salt: bytes = b"gap12") -> str:
    """Stable pseudonym for an endpoint (for correlation without disclosure)."""
    return "ep-" + hmac.new(salt, ip.encode(), hashlib.sha256).hexdigest()[:10]


def redact(text: str, *, salt: bytes = b"gap12") -> str:
    text = _SECRETISH.sub(lambda m: m.group(1) + m.group(2) + "<redacted>", text)
    text = _PORTED.sub(lambda m: endpoint_token(m.group(1).strip("[]"), salt), text)
    text = _IPV4.sub(lambda m: endpoint_token(m.group(0), salt), text)
    text = _IPV6.sub(lambda m: endpoint_token(m.group(0), salt) if m.group(0).count(":") >= 2 else m.group(0), text)
    return text


# --- D054 anomalies / D055 audit ---------------------------------------------------------------------------------

@dataclass
class AnomalyDetector:
    window: float = 300.0
    forced_relay_ratio: float = 0.8
    min_attempts: int = 20
    scan_distinct_peers: int = 50
    auth_fail_burst: int = 10
    events: dict[str, deque] = field(default_factory=dict)

    def observe(self, source: str, kind: str, peer: str, now: float) -> None:
        dq = self.events.setdefault(source, deque(maxlen=2048))
        dq.append((now, kind, peer))

    def findings(self, source: str, now: float) -> list[str]:
        ev = [e for e in self.events.get(source, ()) if now - e[0] <= self.window]
        out = []
        attempts = [e for e in ev if e[1] in ("direct_fail", "relay")]
        if len(attempts) >= self.min_attempts and sum(e[1] == "relay" for e in attempts) / len(attempts) >= self.forced_relay_ratio:
            out.append("forced_relay")
        if len({e[2] for e in ev if e[1] in ("attempt", "direct_fail", "relay")}) >= self.scan_distinct_peers:
            out.append("scanning")
        if sum(e[1] == "auth_fail" for e in ev) >= self.auth_fail_burst:
            out.append("credential_misuse")
        return out


class AuditLog:
    """Append-only, hash-chained security events (tamper-evident)."""

    def __init__(self, path: str | None = None, clock=time.time):
        self.path, self.clock = path, clock
        self.entries: list[dict] = []
        self.head = "0" * 64

    def append(self, event: str, *, reason: str, actor: str, subject: str, config_generation: str | None = None,
               detail: dict | None = None) -> dict:
        rec = {"seq": len(self.entries), "ts": self.clock(), "event": event, "reason": reason, "actor": actor,
               "subject": subject, "config_generation": config_generation, "detail": detail or {}, "prev": self.head}
        rec["hash"] = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
        self.entries.append(rec)
        self.head = rec["hash"]
        if self.path:
            with open(self.path, "a") as fh:
                fh.write(json.dumps(rec, sort_keys=True) + "\n")
        return rec

    @staticmethod
    def verify(entries: list[dict]) -> tuple[bool, int | None]:
        prev = "0" * 64
        for i, e in enumerate(entries):
            body = {k: v for k, v in e.items() if k != "hash"}
            if e.get("prev") != prev or e.get("seq") != i or \
                    hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != e.get("hash"):
                return False, i
            prev = e["hash"]
        return True, None
