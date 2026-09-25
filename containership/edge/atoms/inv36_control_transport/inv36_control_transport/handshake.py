"""PK_CTRL_HS/1 - authenticated, forward-secret session establishment (MC-04).

A SIGMA-style signed-ephemeral X25519 exchange:

    C -> S  CLIENT_HELLO  suites, nonce_c, eph_c, cred_c
    S -> C  SERVER_HELLO  suite, nonce_s, eph_s, cred_s, sig_s, mac_s
    C -> S  CLIENT_FINISH sig_c, mac_c

* ``cred_*`` are Ed25519 identity credentials issued by a trust anchor and bound
  to subject, role, tenant, environment namespace, key epoch and (optionally) an
  attestation measurement.
* ``sig_s`` / ``sig_c`` sign role-labelled transcript hashes, binding both
  ephemerals, both nonces, both credentials, the offered suite list and the
  selected suite (identity binding, role separation, downgrade resistance).
* ``mac_*`` give explicit key confirmation using keys derived from the X25519
  secret and the transcript.
* The PK_CTRL_SESSION/2 shared secret and 32-byte session ID are HKDF exports
  of the full transcript - they never come from unmanaged caller input
  (MC-04.012).  Ephemeral private keys are dropped after use (MC-04.013).

Only suite ``X25519_ED25519_HKDFSHA256_AES256GCMSIV`` (id 1) exists; suite 0 is
reserved and any unknown/weaker suite is refused (MC-04.010).
"""
from __future__ import annotations

import collections
import hashlib
import hmac
import json
import re
import secrets
import struct
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

from . import _wire
from .errors import ErrorCode, Inv36Error
from .keys import EpochPolicy, KeyEpochError, KeyRevoked, SigningKey

HS_MAGIC = b"PKHS"
HS_VERSION = _wire.HS_VERSION
MSG = dict(_wire.HS_MESSAGES)
SUITES = dict(_wire.HS_SUITES)
SUITE_DEFAULT = SUITES["X25519_ED25519_HKDFSHA256_AES256GCMSIV"]
MAX_HS_MESSAGE = _wire.HS_LIMITS["max_message"]
MAX_SUITES = _wire.HS_LIMITS["max_suites"]
NONCE = 32
PUB = 32
SIG = 64
MAC = 32
MAX_CRED_BODY = 2048
ROLES = ("host_agent", "guest_agent", "node", "service", "operator", "relay")
ENVIRONMENTS = ("dev", "test", "stage", "prod")
_SUBJECT_RE = re.compile(r"[a-z0-9][a-z0-9._:/-]{0,127}\Z")
_HDR = struct.Struct(">4sBB")
CRED_LABEL = b"PK_CTRL_CRED/1\x00"


class HandshakeError(Inv36Error, ValueError):
    code = ErrorCode.HS_FORMAT


def _fail(code: ErrorCode, msg: str, **detail) -> HandshakeError:
    return HandshakeError(msg, code=code, detail=detail)


# ---------------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------------
@dataclass(frozen=True)
class Credential:
    subject: str
    role: str
    tenant: str
    env: str
    public_key: bytes
    key_epoch: int
    serial: str
    issuer: str
    anchor_version: int
    not_before: float
    not_after: float
    measurement: str = ""
    raw: bytes = field(default=b"", repr=False, compare=False)

    def body(self) -> dict:
        return {
            "v": 1, "subject": self.subject, "role": self.role, "tenant": self.tenant, "env": self.env,
            "pub": self.public_key.hex(), "key_epoch": self.key_epoch, "serial": self.serial,
            "issuer": self.issuer, "anchor_version": self.anchor_version,
            "not_before": int(self.not_before), "not_after": int(self.not_after), "measurement": self.measurement,
        }

    def safe(self) -> dict:
        """Identity class for evidence/logs without key material (MC-04.026)."""
        return {"subject": self.subject, "role": self.role, "tenant": self.tenant, "env": self.env,
                "key_epoch": self.key_epoch, "serial": self.serial, "anchor_version": self.anchor_version}


def _canon(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def issue_credential(anchor: SigningKey | Ed25519PrivateKey, *, subject: str, role: str, tenant: str, env: str,
                     public_key: bytes, key_epoch: int, issuer: str, anchor_version: int,
                     not_before: float, not_after: float, measurement: str = "",
                     serial: str | None = None) -> bytes:
    cred = Credential(subject, role, tenant, env, public_key, key_epoch, serial or secrets.token_hex(8), issuer,
                      anchor_version, not_before, not_after, measurement)
    _validate_fields(cred)
    body = _canon(cred.body())
    sig = anchor.sign(CRED_LABEL + body)
    return len(body).to_bytes(2, "big") + body + sig


def _validate_fields(c: Credential) -> None:
    if not _SUBJECT_RE.match(c.subject or ""):
        raise _fail(ErrorCode.HS_IDENTITY, "invalid subject")
    if c.role not in ROLES:
        raise _fail(ErrorCode.HS_IDENTITY, "invalid role")
    if not re.match(r"[a-z0-9][a-z0-9._-]{0,63}\Z", c.tenant or ""):
        raise _fail(ErrorCode.HS_IDENTITY, "invalid tenant")
    if c.env not in ENVIRONMENTS:
        raise _fail(ErrorCode.HS_IDENTITY, "invalid environment")
    if len(c.public_key) != PUB:
        raise _fail(ErrorCode.HS_IDENTITY, "invalid public key length")
    if c.measurement and not re.match(r"[0-9a-f]{64}\Z", c.measurement):
        raise _fail(ErrorCode.HS_ATTESTATION, "invalid measurement encoding")
    if c.not_after <= c.not_before:
        raise _fail(ErrorCode.HS_IDENTITY, "invalid validity window")


def parse_credential(blob: bytes) -> tuple[Credential, bytes, bytes]:
    """Return (credential, signed_body, signature). Rejects non-canonical encodings."""
    if len(blob) < 2 + 2 + SIG:
        raise _fail(ErrorCode.HS_FORMAT, "credential truncated")
    n = int.from_bytes(blob[:2], "big")
    if n > MAX_CRED_BODY or len(blob) != 2 + n + SIG:
        raise _fail(ErrorCode.HS_FORMAT, "credential length invalid")
    body, sig = blob[2:2 + n], blob[2 + n:]
    try:
        obj = json.loads(body.decode("ascii"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise _fail(ErrorCode.HS_FORMAT, "credential body is not canonical json") from exc
    if not isinstance(obj, dict) or _canon(obj) != body or obj.get("v") != 1:
        raise _fail(ErrorCode.HS_FORMAT, "credential body is not canonical")
    expected = {"v", "subject", "role", "tenant", "env", "pub", "key_epoch", "serial", "issuer",
                "anchor_version", "not_before", "not_after", "measurement"}
    if set(obj) != expected:
        raise _fail(ErrorCode.HS_FORMAT, "credential fields invalid")
    try:
        cred = Credential(str(obj["subject"]), str(obj["role"]), str(obj["tenant"]), str(obj["env"]),
                          bytes.fromhex(obj["pub"]), int(obj["key_epoch"]), str(obj["serial"])[:64],
                          str(obj["issuer"])[:128], int(obj["anchor_version"]), float(obj["not_before"]),
                          float(obj["not_after"]), str(obj["measurement"]), raw=blob)
    except (TypeError, ValueError) as exc:
        raise _fail(ErrorCode.HS_FORMAT, "credential field types invalid") from exc
    _validate_fields(cred)
    return cred, body, sig


# ---------------------------------------------------------------------------------
# Trust, revocation, attestation, clock (dependencies with explicit failure modes)
# ---------------------------------------------------------------------------------
@dataclass
class TrustStore:
    issuer: str
    anchors: dict[int, bytes]  # anchor_version -> Ed25519 public key bytes
    min_anchor_version: int = 1

    def verify(self, cred: Credential, body: bytes, sig: bytes) -> None:
        if cred.issuer != self.issuer:
            raise _fail(ErrorCode.HS_TRUST_CHAIN, "unknown issuer")
        if cred.anchor_version < self.min_anchor_version or cred.anchor_version not in self.anchors:
            raise _fail(ErrorCode.HS_TRUST_CHAIN, "untrusted anchor version", anchor_version=cred.anchor_version)
        try:
            Ed25519PublicKey.from_public_bytes(self.anchors[cred.anchor_version]).verify(sig, CRED_LABEL + body)
        except InvalidSignature as exc:
            raise _fail(ErrorCode.HS_TRUST_CHAIN, "credential signature invalid") from exc


class RevocationSource(Protocol):
    def snapshot(self) -> tuple[frozenset[str], float]:
        """Return (revoked serials, fetched_at wall time); raise on unavailability."""


@dataclass
class StaticRevocations:
    serials: set[str] = field(default_factory=set)
    fetched_at: float | None = None
    available: bool = True

    def snapshot(self) -> tuple[frozenset[str], float]:
        if not self.available:
            raise _fail(ErrorCode.HS_DEPENDENCY, "revocation service unavailable")
        return frozenset(self.serials), (self.fetched_at if self.fetched_at is not None else time.time())


class AttestationVerifier(Protocol):
    def verify(self, cred: Credential) -> None: ...


@dataclass
class AllowlistAttestation:
    """Accepts credentials whose measurement is allow-listed for their role.

    Roles not listed in ``required_roles`` need no measurement.  This is a
    reference verifier; production uses the GAP-06 attestation service.
    """

    allowed: dict[str, set[str]] = field(default_factory=dict)
    required_roles: set[str] = field(default_factory=set)
    available: bool = True

    def verify(self, cred: Credential) -> None:
        if cred.role not in self.required_roles:
            return
        if not self.available:
            raise _fail(ErrorCode.HS_DEPENDENCY, "attestation verifier unavailable")
        if cred.measurement not in self.allowed.get(cred.role, set()):
            raise _fail(ErrorCode.HS_ATTESTATION, "attestation measurement not allowed")


class _RevocationCache:
    def __init__(self) -> None:
        self.last: tuple[frozenset[str], float] | None = None
        self.lock = threading.Lock()


@dataclass
class HandshakePolicy:
    env: str
    trust: TrustStore
    revocations: RevocationSource
    attestation: AttestationVerifier = field(default_factory=AllowlistAttestation)
    epochs: EpochPolicy = field(default_factory=EpochPolicy)
    allowed_peer_roles: frozenset[str] = frozenset(ROLES)
    suites: tuple[int, ...] = (SUITE_DEFAULT,)
    min_suite: int = SUITE_DEFAULT
    max_clock_skew_s: float = 300.0
    revocation_max_staleness_s: float = 600.0
    allow_cached_revocation_s: float = 0.0  # 0 = fail closed when revocation service is down
    clock: Callable[[], float] = time.time
    timeout_s: float = 10.0
    expected_peer: str | None = None
    session_id_cache: int = 4096
    revocation_cache: _RevocationCache = field(default_factory=lambda: _RevocationCache(), repr=False)

    def now(self) -> float:
        try:
            t = self.clock()
        except Exception as exc:  # noqa: BLE001 - any clock failure is a dependency failure
            raise _fail(ErrorCode.HS_DEPENDENCY, "time service unavailable") from exc
        if not isinstance(t, (int, float)) or t <= 0:
            raise _fail(ErrorCode.HS_DEPENDENCY, "time service returned invalid time")
        return float(t)


def _check_credential(policy: HandshakePolicy, cred: Credential, body: bytes, sig: bytes) -> None:
    """Validation order is fixed so failure codes are deterministic."""
    policy.trust.verify(cred, body, sig)
    if cred.env != policy.env:
        raise _fail(ErrorCode.HS_IDENTITY, "credential environment namespace mismatch", env=cred.env)
    now = policy.now()
    skew = policy.max_clock_skew_s
    if now + skew < cred.not_before:
        raise _fail(ErrorCode.HS_EXPIRED, "credential not yet valid")
    if now - skew >= cred.not_after:
        raise _fail(ErrorCode.HS_EXPIRED, "credential expired")
    cache = policy.revocation_cache
    try:
        serials, fetched = policy.revocations.snapshot()
        with cache.lock:
            cache.last = (serials, fetched)
    except HandshakeError:
        with cache.lock:
            last = cache.last
        if not last or policy.allow_cached_revocation_s <= 0 or now - last[1] > policy.allow_cached_revocation_s:
            raise
        serials, fetched = last
    if now - fetched > policy.revocation_max_staleness_s and policy.allow_cached_revocation_s <= 0:
        raise _fail(ErrorCode.HS_DEPENDENCY, "revocation data stale")
    if cred.serial in serials:
        raise _fail(ErrorCode.HS_REVOKED, "credential revoked", serial=cred.serial)
    try:
        policy.epochs.check(cred.key_epoch)
    except KeyRevoked as exc:
        raise _fail(ErrorCode.HS_REVOKED, "credential key epoch revoked") from exc
    except KeyEpochError as exc:
        raise _fail(ErrorCode.HS_POLICY, "credential key epoch not accepted") from exc
    if cred.role not in policy.allowed_peer_roles:
        raise _fail(ErrorCode.HS_POLICY, "peer role not permitted", role=cred.role)
    if policy.expected_peer is not None and cred.subject != policy.expected_peer:
        raise _fail(ErrorCode.HS_IDENTITY, "peer identity does not match expected subject")
    policy.attestation.verify(cred)


# ---------------------------------------------------------------------------------
# Transcript / key schedule
# ---------------------------------------------------------------------------------
def _h(*parts: bytes) -> bytes:
    d = hashlib.sha256()
    for p in parts:
        d.update(len(p).to_bytes(4, "big"))
        d.update(p)
    return d.digest()


def _expand(prk: bytes, label: bytes, th: bytes, n: int = 32) -> bytes:
    return HKDFExpand(hashes.SHA256(), n, b"PK_CTRL_HS/1 " + label + b"\x00" + th).derive(prk)


def _extract(ecdh: bytes, th: bytes) -> bytes:
    # HKDF-Extract via HKDF with an empty expand context is not exposed; emulate RFC 5869 extract.
    return hmac.new(th, ecdh, hashlib.sha256).digest()


def _x25519_pub(priv: X25519PrivateKey) -> bytes:
    return priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _pack(msg_type: int, *parts: bytes) -> bytes:
    out = _HDR.pack(HS_MAGIC, HS_VERSION, msg_type) + b"".join(parts)
    if len(out) > MAX_HS_MESSAGE:
        raise _fail(ErrorCode.HS_FORMAT, "handshake message above bound")
    return out


def _unpack(data: bytes, msg_type: int) -> memoryview:
    if len(data) > MAX_HS_MESSAGE:
        raise _fail(ErrorCode.HS_FORMAT, "handshake message above bound")
    if len(data) < _HDR.size:
        raise _fail(ErrorCode.HS_FORMAT, "handshake message truncated")
    magic, ver, t = _HDR.unpack_from(data)
    if magic != HS_MAGIC:
        raise _fail(ErrorCode.HS_FORMAT, "bad handshake magic")
    if ver != HS_VERSION:
        raise _fail(ErrorCode.HS_NEGOTIATION, "unsupported handshake version", version=ver)
    if t != msg_type:
        raise _fail(ErrorCode.HS_FORMAT, "unexpected handshake message", got=t, want=msg_type)
    return memoryview(data)[_HDR.size:]


def _take(view: memoryview, n: int) -> tuple[bytes, memoryview]:
    if len(view) < n:
        raise _fail(ErrorCode.HS_FORMAT, "handshake field truncated")
    return bytes(view[:n]), view[n:]


def _take_cred(view: memoryview) -> tuple[bytes, memoryview]:
    head, _ = _take(view, 2)
    n = 2 + int.from_bytes(head, "big") + SIG
    if int.from_bytes(head, "big") > MAX_CRED_BODY:
        raise _fail(ErrorCode.HS_FORMAT, "credential length invalid")
    return _take(view, n)


@dataclass
class HandshakeResult:
    shared: bytes = field(repr=False)
    session_id: bytes
    peer: Credential
    local: Credential
    suite: int
    transcript_hash: bytes
    started: float
    completed: float

    def evidence(self) -> dict:
        return {
            "protocol": "PK_CTRL_HS/1", "suite": self.suite,
            "suite_name": {v: k for k, v in SUITES.items()}[self.suite],
            "peer": self.peer.safe(), "local_role": self.local.role,
            "trust_anchor_version": self.peer.anchor_version,
            "session_id_sha256": hashlib.sha256(self.session_id).hexdigest()[:16],
            "duration_ms": round((self.completed - self.started) * 1000, 3), "result": "established",
        }

    def wipe(self) -> None:
        self.shared = b""


class _SessionIdRegistry:
    """Bounded registry rejecting reuse of client nonces / session IDs (MC-04.011)."""

    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self._seen: collections.OrderedDict[bytes, None] = collections.OrderedDict()
        self._lock = threading.Lock()

    def claim(self, key: bytes) -> None:
        with self._lock:
            if key in self._seen:
                raise _fail(ErrorCode.HS_REPLAY, "handshake nonce or session id reused")
            self._seen[key] = None
            while len(self._seen) > self.capacity:
                self._seen.popitem(last=False)


class ClientHandshake:
    def __init__(self, policy: HandshakePolicy, identity: SigningKey, credential: bytes) -> None:
        self.policy = policy
        self.identity = identity
        self.cred_blob = credential
        self.local, _, _ = parse_credential(credential)
        self.started = time.monotonic()
        self._eph: X25519PrivateKey | None = X25519PrivateKey.generate()
        self._nonce = secrets.token_bytes(NONCE)
        self._ch = b""
        self._done = False

    def hello(self) -> bytes:
        suites = [s for s in self.policy.suites if s >= self.policy.min_suite and s in SUITES.values()]
        if not suites or len(suites) > MAX_SUITES:
            raise _fail(ErrorCode.HS_NEGOTIATION, "no acceptable suites configured")
        if self._eph is None:
            raise _fail(ErrorCode.HS_FORMAT, "handshake already used")
        self._ch = _pack(MSG["CLIENT_HELLO"], bytes([len(suites)]), b"".join(struct.pack(">H", s) for s in suites),
                         self._nonce, _x25519_pub(self._eph), self.cred_blob)
        return self._ch

    def on_server_hello(self, data: bytes) -> tuple[bytes, HandshakeResult]:
        if time.monotonic() - self.started > self.policy.timeout_s:
            raise _fail(ErrorCode.HS_TIMEOUT, "handshake time limit exceeded")
        if self._eph is None or not self._ch:
            raise _fail(ErrorCode.HS_FORMAT, "unexpected SERVER_HELLO")
        v = _unpack(data, MSG["SERVER_HELLO"])
        suite_b, v = _take(v, 2)
        nonce_s, v = _take(v, NONCE)
        eph_s, v = _take(v, PUB)
        cred_s, v = _take_cred(v)
        sig_s, v = _take(v, SIG)
        mac_s, v = _take(v, MAC)
        if len(v):
            raise _fail(ErrorCode.HS_FORMAT, "trailing bytes in SERVER_HELLO")
        suite = struct.unpack(">H", suite_b)[0]
        if suite not in self.policy.suites or suite < self.policy.min_suite:
            raise _fail(ErrorCode.HS_NEGOTIATION, "server selected a suite that was not offered", suite=suite)
        peer, body, csig = parse_credential(cred_s)
        _check_credential(self.policy, peer, body, csig)
        if peer.subject == self.local.subject:
            raise _fail(ErrorCode.HS_IDENTITY, "reflected identity")
        sh_core = data[: len(data) - SIG - MAC]
        th1 = _h(self._ch, sh_core)
        try:
            Ed25519PublicKey.from_public_bytes(peer.public_key).verify(sig_s, b"PK_CTRL_HS/1 server\x00" + th1)
        except InvalidSignature as exc:
            raise _fail(ErrorCode.HS_TRANSCRIPT, "server transcript signature invalid") from exc
        try:
            ecdh = self._eph.exchange(X25519PublicKey.from_public_bytes(eph_s))
        except ValueError as exc:
            raise _fail(ErrorCode.HS_FORMAT, "invalid server ephemeral") from exc
        finally:
            self._eph = None  # MC-04.013
        prk = _extract(ecdh, th1)
        th2 = _h(self._ch, sh_core, sig_s)
        if not hmac.compare_digest(mac_s, hmac.new(_expand(prk, b"s fin", th2), th2, hashlib.sha256).digest()):
            raise _fail(ErrorCode.HS_TRANSCRIPT, "server key confirmation failed")
        th3 = _h(self._ch, data)
        sig_c = self.identity.sign(b"PK_CTRL_HS/1 client\x00" + th3)
        th4 = _h(self._ch, data, sig_c)
        mac_c = hmac.new(_expand(prk, b"c fin", th4), th4, hashlib.sha256).digest()
        cf = _pack(MSG["CLIENT_FINISH"], sig_c, mac_c)
        th_final = _h(self._ch, data, cf)
        result = HandshakeResult(_expand(prk, b"exporter", th_final), _expand(prk, b"session id", th_final),
                                 peer, self.local, suite, th_final, self.started, time.monotonic())
        self._done = True
        return cf, result


class ServerHandshake:
    def __init__(self, policy: HandshakePolicy, identity: SigningKey, credential: bytes,
                 registry: _SessionIdRegistry | None = None,
                 pre_accept: Callable[[Credential], None] | None = None) -> None:
        self.policy = policy
        self.identity = identity
        self.cred_blob = credential
        self.local, _, _ = parse_credential(credential)
        self.registry = registry or _SessionIdRegistry(policy.session_id_cache)
        self.pre_accept = pre_accept
        self.started = time.monotonic()
        self._state: tuple | None = None

    def on_client_hello(self, data: bytes) -> bytes:
        v = _unpack(data, MSG["CLIENT_HELLO"])
        n_b, v = _take(v, 1)
        n = n_b[0]
        if not 1 <= n <= MAX_SUITES:
            raise _fail(ErrorCode.HS_NEGOTIATION, "suite list length invalid")
        raw_suites, v = _take(v, 2 * n)
        offered = [struct.unpack_from(">H", raw_suites, 2 * i)[0] for i in range(n)]
        if len(set(offered)) != n:
            raise _fail(ErrorCode.HS_NEGOTIATION, "duplicate suites offered")
        nonce_c, v = _take(v, NONCE)
        eph_c, v = _take(v, PUB)
        cred_c, v = _take_cred(v)
        if len(v):
            raise _fail(ErrorCode.HS_FORMAT, "trailing bytes in CLIENT_HELLO")
        mutual = [s for s in self.policy.suites if s in offered and s >= self.policy.min_suite]
        if not mutual:
            raise _fail(ErrorCode.HS_NEGOTIATION, "no mutually acceptable suite", offered=len(offered))
        suite = max(mutual)
        peer, body, csig = parse_credential(cred_c)
        _check_credential(self.policy, peer, body, csig)
        if peer.subject == self.local.subject:
            raise _fail(ErrorCode.HS_IDENTITY, "reflected identity")
        if self.pre_accept:
            self.pre_accept(peer)  # quarantine / admission hooks before spending ECDH
        self.registry.claim(b"n" + nonce_c)
        eph = X25519PrivateKey.generate()
        sh_core = _pack(MSG["SERVER_HELLO"], struct.pack(">H", suite), secrets.token_bytes(NONCE), _x25519_pub(eph),
                        self.cred_blob)
        th1 = _h(data, sh_core)
        sig_s = self.identity.sign(b"PK_CTRL_HS/1 server\x00" + th1)
        try:
            ecdh = eph.exchange(X25519PublicKey.from_public_bytes(eph_c))
        except ValueError as exc:
            raise _fail(ErrorCode.HS_FORMAT, "invalid client ephemeral") from exc
        finally:
            del eph
        prk = _extract(ecdh, th1)
        th2 = _h(data, sh_core, sig_s)
        mac_s = hmac.new(_expand(prk, b"s fin", th2), th2, hashlib.sha256).digest()
        sh = sh_core + sig_s + mac_s
        if len(sh) > MAX_HS_MESSAGE:
            raise _fail(ErrorCode.HS_FORMAT, "handshake message above bound")
        self._state = (data, sh, prk, peer, suite)
        return sh

    def on_client_finish(self, data: bytes) -> HandshakeResult:
        if self._state is None:
            raise _fail(ErrorCode.HS_FORMAT, "unexpected CLIENT_FINISH")
        if time.monotonic() - self.started > self.policy.timeout_s:
            self._state = None
            raise _fail(ErrorCode.HS_TIMEOUT, "handshake time limit exceeded")
        ch, sh, prk, peer, suite = self._state
        self._state = None
        v = _unpack(data, MSG["CLIENT_FINISH"])
        sig_c, v = _take(v, SIG)
        mac_c, v = _take(v, MAC)
        if len(v):
            raise _fail(ErrorCode.HS_FORMAT, "trailing bytes in CLIENT_FINISH")
        th3 = _h(ch, sh)
        try:
            Ed25519PublicKey.from_public_bytes(peer.public_key).verify(sig_c, b"PK_CTRL_HS/1 client\x00" + th3)
        except InvalidSignature as exc:
            raise _fail(ErrorCode.HS_TRANSCRIPT, "client transcript signature invalid") from exc
        th4 = _h(ch, sh, sig_c)
        if not hmac.compare_digest(mac_c, hmac.new(_expand(prk, b"c fin", th4), th4, hashlib.sha256).digest()):
            raise _fail(ErrorCode.HS_TRANSCRIPT, "client key confirmation failed")
        th_final = _h(ch, sh, data)
        sid = _expand(prk, b"session id", th_final)
        self.registry.claim(b"s" + sid)
        return HandshakeResult(_expand(prk, b"exporter", th_final), sid, peer, self.local, suite, th_final,
                               self.started, time.monotonic())


def new_registry(capacity: int = 4096) -> _SessionIdRegistry:
    return _SessionIdRegistry(capacity)


def offered_suites(ch: bytes) -> Iterable[int]:
    v = _unpack(ch, MSG["CLIENT_HELLO"])
    n = v[0]
    return [struct.unpack_from(">H", v, 1 + 2 * i)[0] for i in range(n)]
