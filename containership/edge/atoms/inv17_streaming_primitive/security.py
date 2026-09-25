"""Boundary security for INV-17: capability tokens, trust-service handling, audit chain.

Controls: C023/C044 (boundary authentication), C024/C042/C043 (capability policy),
C046 (isolation), C047 (data classification), C048 (trust-service outage), C049
(tamper-evident audit events). Stdlib only (``hmac``/``hashlib``).

Trust model (see ``security/THREAT_MODEL.md``): a stream handle is instance-local;
anything that crosses the handle boundary -- an adjacent layer opening, transferring
or operating an end on behalf of a tenant/workload -- must present a capability token
minted by the host's issuer. Tokens are HMAC-SHA256 over a canonical JSON claim set,
bound to one stream id, tenant, workload and a subset of rights, carry an expiry and a
single-use nonce for transfer operations, and are verified fail-closed.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable, Iterable, Mapping

from .stream import StreamError

RIGHTS = frozenset({"open", "read", "write", "grant", "close", "transfer", "admin"})
#: Rights a plain endpoint may hold; ``admin`` is reserved for emergency controls.
END_RIGHTS = {"reader": frozenset({"read", "grant", "close"}), "writer": frozenset({"write", "close"})}
CLASSIFICATIONS = ("public", "internal", "confidential", "restricted")


class AuthError(StreamError):
    code = "PK_STREAM_AUTH"


class AuthzDenied(StreamError, PermissionError):
    code = "PK_STREAM_AUTHZ_DENIED"


class TokenReplay(AuthError):
    code = "PK_STREAM_TOKEN_REPLAY"


class TrustServiceUnavailable(StreamError):
    """A key/time/policy dependency is unavailable: security decisions fail closed."""

    code = "PK_STREAM_TRUST_UNAVAILABLE"


class DataPolicyViolation(StreamError):
    code = "PK_STREAM_DATA_POLICY"


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class KeyRing:
    """Key provider. ``available=False`` simulates a key-service outage (C048)."""

    def __init__(self, keys: Mapping[str, bytes] | None = None, active: str | None = None) -> None:
        self._keys = dict(keys or {"k1": secrets.token_bytes(32)})
        self.active = active or next(iter(self._keys))
        self.available = True
        for kid, key in self._keys.items():
            if len(key) < 32:
                raise ValueError(f"key {kid!r} shorter than 256 bits")

    def get(self, kid: str) -> bytes:
        if not self.available:
            raise TrustServiceUnavailable("key service unavailable", dependency="keys")
        try:
            return self._keys[kid]
        except KeyError:
            raise AuthError("unknown key id", kid=kid) from None

    def rotate(self, kid: str, key: bytes) -> None:
        if len(key) < 32:
            raise ValueError("key shorter than 256 bits")
        self._keys[kid] = key
        self.active = kid

    def retire(self, kid: str) -> None:
        if kid == self.active:
            raise ValueError("cannot retire the active key")
        self._keys.pop(kid, None)


class TrustedClock:
    """Time source. ``available=False`` simulates a time-service outage (C048)."""

    def __init__(self, now: Callable[[], float] = time.time) -> None:
        self._now = now
        self.available = True

    def now(self) -> float:
        if not self.available:
            raise TrustServiceUnavailable("trusted time unavailable", dependency="time")
        return self._now()


@dataclass(frozen=True)
class Capability:
    stream_id: str
    tenant: str
    workload: str
    rights: frozenset[str]
    expires_at: float
    nonce: str
    kid: str
    issuer: str = "inv17-host"
    single_use: bool = False

    def claims(self) -> dict[str, object]:
        return {"aud": self.stream_id, "ten": self.tenant, "wl": self.workload, "rgt": sorted(self.rights),
                "exp": self.expires_at, "non": self.nonce, "kid": self.kid, "iss": self.issuer, "su": self.single_use,
                "v": 1}


class CapabilityAuthority:
    """Issues and verifies capability tokens; verification is fail-closed.

    Replay protection: single-use nonces are remembered until their token expires; the
    cache is bounded and fails closed when full rather than evicting a live nonce.
    ``transfer`` tokens are always single-use (signed ``su`` claim); other rights may be
    re-presented until expiry unless ``single_use=True`` was requested at issue.
    """

    def __init__(self, keys: KeyRing | None = None, clock: TrustedClock | None = None,
                 *, max_ttl: float = 300.0, replay_cache: int = 65536) -> None:
        self.keys = keys or KeyRing()
        self.clock = clock or TrustedClock()
        self.max_ttl = max_ttl
        self._replay: OrderedDict[str, float] = OrderedDict()
        self._replay_cap = replay_cache
        self._revoked: set[str] = set()
        self._lock = RLock()

    def issue(self, stream_id: str, tenant: str, workload: str, rights: Iterable[str], *,
              ttl: float = 60.0, single_use: bool = False) -> str:
        rights = frozenset(rights)
        unknown = rights - RIGHTS
        if unknown or not rights:
            raise ValueError(f"invalid rights {sorted(unknown) or '[]'}")
        if not (0 < ttl <= self.max_ttl):
            raise ValueError("ttl outside policy bounds")
        for label, value in (("stream_id", stream_id), ("tenant", tenant), ("workload", workload)):
            if not isinstance(value, str) or not value or len(value) > 128:
                raise ValueError(f"{label} must be a non-empty string of at most 128 chars")
        cap = Capability(stream_id, tenant, workload, rights, self.clock.now() + ttl,
                         secrets.token_hex(16), self.keys.active,
                         single_use=bool(single_use or "transfer" in rights))
        body = canonical(cap.claims())  # single-use is a signed claim, not verifier memory
        mac = hmac.new(self.keys.get(cap.kid), body, hashlib.sha256).digest()
        return f"{_b64(body)}.{_b64(mac)}"

    def revoke(self, token: str) -> None:
        with self._lock:
            self._revoked.add(token.split(".", 1)[0])

    def verify(self, token: str, *, stream_id: str, tenant: str, workload: str, right: str) -> Capability:
        if right not in RIGHTS:
            raise ValueError(f"unknown right {right!r}")
        if not isinstance(token, str) or token.count(".") != 1 or len(token) > 4096:
            raise AuthError("malformed token")
        body_b64, mac_b64 = token.split(".")
        try:
            body = _unb64(body_b64)
            mac = _unb64(mac_b64)
            claims = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise AuthError("malformed token") from None
        if not isinstance(claims, dict) or claims.get("v") != 1 or not isinstance(claims.get("kid"), str):
            raise AuthError("unsupported token version")
        expected = hmac.new(self.keys.get(claims["kid"]), body, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, mac):
            raise AuthError("bad token signature")
        if body_b64 in self._revoked:
            raise AuthError("token revoked")
        now = self.clock.now()
        if not isinstance(claims.get("exp"), (int, float)) or claims["exp"] <= now:
            raise AuthError("token expired")
        if claims.get("aud") != stream_id:
            raise AuthzDenied("token bound to a different stream", expected=stream_id)
        if claims.get("ten") != tenant or claims.get("wl") != workload:
            raise AuthzDenied("token bound to a different tenant/workload")
        rights = frozenset(claims.get("rgt") or ())
        if right not in rights:
            raise AuthzDenied("right not granted", right=right)
        nonce = str(claims.get("non"))
        with self._lock:
            self._expire(now)
            if claims.get("su") is True:
                if nonce in self._replay:
                    raise TokenReplay("single-use token presented twice")
                # Only single-use nonces need remembering. They are never evicted early:
                # evicting an unexpired nonce would re-open the replay window, so a full
                # cache fails closed instead.
                if len(self._replay) >= self._replay_cap:
                    raise TrustServiceUnavailable("replay cache full; refusing single-use token",
                                                  dependency="replay-cache")
                self._replay[nonce] = float(claims["exp"])
        return Capability(stream_id, tenant, workload, rights, float(claims["exp"]), nonce, claims["kid"],
                          str(claims.get("iss")), claims.get("su") is True)

    def _expire(self, now: float) -> None:
        for nonce in [n for n, exp in self._replay.items() if exp <= now]:
            del self._replay[nonce]


@dataclass(frozen=True)
class DataPolicy:
    """C047: when payloads crossing a stream boundary need encryption/residency."""

    require_encryption_at: str = "confidential"
    allowed_regions: frozenset[str] = frozenset({"any"})

    def check(self, *, classification: str, encrypted: bool, crosses_boundary: bool,
              region: str = "any") -> None:
        if classification not in CLASSIFICATIONS:
            raise DataPolicyViolation("unknown classification", classification=classification)
        if crosses_boundary and CLASSIFICATIONS.index(classification) >= CLASSIFICATIONS.index(
                self.require_encryption_at) and not encrypted:
            raise DataPolicyViolation("payload class requires encryption across a boundary",
                                      classification=classification)
        if "any" not in self.allowed_regions and region not in self.allowed_regions:
            raise DataPolicyViolation("region not permitted by residency policy", region=region)


@dataclass
class AuditEvent:
    seq: int
    ts: float
    kind: str
    actor: str
    subject: str
    outcome: str
    detail: dict[str, object] = field(default_factory=dict)
    prev: str = ""
    mac: str = ""

    def body(self) -> dict[str, object]:
        return {"seq": self.seq, "ts": self.ts, "kind": self.kind, "actor": self.actor, "subject": self.subject,
                "outcome": self.outcome, "detail": self.detail, "prev": self.prev}


class AuditLedger:
    """C049: HMAC-chained security events. Detects edits, reordering and deletion.

    Tail truncation is detectable only against an externally recorded head
    (``verify(expected_head=...)``); ``anchor()`` returns the value to record.
    """

    KINDS = frozenset({"auth.denied", "auth.replay", "authz.denied", "policy.violation", "trust.unavailable",
                       "control.freeze", "control.unfreeze", "control.disable", "control.enable",
                       "config.activate", "config.rollback", "stream.open", "stream.transfer", "quota.denied"})

    def __init__(self, key: bytes | None = None, clock: Callable[[], float] = time.time) -> None:
        self._key = key or secrets.token_bytes(32)
        self._clock = clock
        self.events: list[AuditEvent] = []
        self._lock = RLock()

    def _mac(self, ev: AuditEvent) -> str:
        return hmac.new(self._key, canonical(ev.body()), hashlib.sha256).hexdigest()

    def record(self, kind: str, actor: str, subject: str, outcome: str, **detail: object) -> AuditEvent:
        if kind not in self.KINDS:
            raise ValueError(f"unknown audit event kind {kind!r}")
        with self._lock:
            prev = self.events[-1].mac if self.events else "0" * 64
            ev = AuditEvent(len(self.events), self._clock(), kind, actor, subject, outcome,
                            {k: v for k, v in detail.items()}, prev)
            ev.mac = self._mac(ev)
            self.events.append(ev)
            return ev

    def anchor(self) -> str:
        with self._lock:
            return self.events[-1].mac if self.events else "0" * 64

    def verify(self, expected_head: str | None = None) -> list[str]:
        problems: list[str] = []
        prev = "0" * 64
        for i, ev in enumerate(self.events):
            if ev.seq != i:
                problems.append(f"event {i}: sequence {ev.seq} out of order")
            if ev.prev != prev:
                problems.append(f"event {i}: chain link broken")
            if not hmac.compare_digest(self._mac(ev), ev.mac):
                problems.append(f"event {i}: mac mismatch (tampered)")
            prev = ev.mac
        if expected_head is not None and prev != expected_head:
            problems.append("head does not match the externally anchored head (truncation or fork)")
        return problems

    def export_jsonl(self) -> str:
        with self._lock:
            return "".join(json.dumps({**ev.body(), "mac": ev.mac}, sort_keys=True) + "\n" for ev in self.events)
