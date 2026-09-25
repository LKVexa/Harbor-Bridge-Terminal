"""Authentication, capability authorization, tenant isolation checks and a
tamper-evident audit chain (components 19, 20, 37, 39, 42, 43).

Deny-by-default: a principal holds no capability unless a grant names it.  Security
dependencies that are unavailable cause a fail-closed refusal (INV54-E0105), never a pass.
"""
from __future__ import annotations

import base64
import fnmatch
import hashlib
import hmac
import json
import re
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable, Iterable

from .config import Secret
from .errors import (INTEGRITY_FAILURE, INVALID_ARGUMENT, PERMISSION_DENIED, REPLAYED_CREDENTIAL,
                     SECURITY_SERVICE_UNAVAILABLE, TENANT_VIOLATION, UNAUTHENTICATED, BrokerError)

ACTIONS = ("publish", "subscribe", "consume", "seek", "admin", "config")
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


def check_name(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not _NAME.fullmatch(value):
        raise BrokerError(INVALID_ARGUMENT, f"{field_name} must match {_NAME.pattern}", field=field_name)
    return value


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    workload: str = "default"
    roles: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Grant:
    tenant: str
    actions: frozenset[str]
    resource_glob: str = "*"
    subject: str | None = None  # None = any subject of the tenant holding ``role``
    role: str | None = None


class Authorizer:
    def __init__(self, grants: Iterable[Grant] = ()) -> None:
        self._grants = list(grants)
        for g in self._grants:
            bad = set(g.actions) - set(ACTIONS)
            if bad:
                raise BrokerError(INVALID_ARGUMENT, f"unknown actions {sorted(bad)}")

    def check(self, p: Principal, action: str, tenant: str, resource: str) -> str:
        """Return the matching grant description or raise. Cross-tenant is always refused."""
        if p.tenant != tenant:
            raise BrokerError(TENANT_VIOLATION, principal_tenant=p.tenant, target_tenant=tenant)
        for g in self._grants:
            if g.tenant != tenant or action not in g.actions:
                continue
            if g.subject is not None and g.subject != p.subject:
                continue
            if g.role is not None and g.role not in p.roles:
                continue
            if fnmatch.fnmatchcase(resource, g.resource_glob):
                return f"grant(tenant={g.tenant},actions={sorted(g.actions)},glob={g.resource_glob})"
        raise BrokerError(PERMISSION_DENIED, action=action, resource=resource, subject=p.subject)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class HmacAuthenticator:
    """Compact HMAC-SHA256 bearer tokens: ``b64(claims).b64(mac)``.

    Claims: sub, ten, wl, roles, iat, exp, nonce.  Replay protection via a bounded nonce
    cache sized to the token TTL.  The key source is a callable so rotation (component 32)
    and key-service outage (component 42) are exercised: previous keys verify during the
    rotation grace window; an unavailable key source fails closed.
    """

    def __init__(self, keys: Callable[[], list[Secret]], clock: Callable[[], float] = time.time,
                 ttl: int = 300, nonce_cache: int = 100_000) -> None:
        self._keys = keys
        self.clock = clock
        self.ttl = ttl
        self._nonces: OrderedDict[str, float] = OrderedDict()
        self._cap = nonce_cache
        self._lock = RLock()

    def issue(self, p: Principal, nonce: str) -> str:
        keys = self._keyset()
        now = int(self.clock())
        claims = {"sub": p.subject, "ten": p.tenant, "wl": p.workload, "roles": sorted(p.roles),
                  "iat": now, "exp": now + self.ttl, "nonce": nonce}
        body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        mac = hmac.new(keys[0].reveal(), body.encode(), hashlib.sha256).digest()
        return f"{body}.{_b64(mac)}"

    def _keyset(self) -> list[Secret]:
        try:
            keys = self._keys()
        except BrokerError:
            raise
        except Exception as exc:
            raise BrokerError(SECURITY_SERVICE_UNAVAILABLE, "key source failed") from exc
        if not keys:
            raise BrokerError(SECURITY_SERVICE_UNAVAILABLE, "no verification keys")
        return keys

    def authenticate(self, token: object) -> Principal:
        if not isinstance(token, str) or token.count(".") != 1 or len(token) > 8192:
            raise BrokerError(UNAUTHENTICATED, "malformed token")
        body, mac = token.split(".")
        try:
            mac_b = _unb64(mac)
        except Exception:
            raise BrokerError(UNAUTHENTICATED, "malformed token") from None
        keys = self._keyset()
        if not any(hmac.compare_digest(hmac.new(k.reveal(), body.encode(), hashlib.sha256).digest(), mac_b)
                   for k in keys):
            raise BrokerError(UNAUTHENTICATED, "bad signature")
        try:
            c = json.loads(_unb64(body))
            sub, ten, exp, nonce = c["sub"], c["ten"], int(c["exp"]), str(c["nonce"])
        except Exception:
            raise BrokerError(UNAUTHENTICATED, "malformed claims") from None
        now = self.clock()
        if exp < now:
            raise BrokerError(UNAUTHENTICATED, "token expired")
        with self._lock:
            # evict expired nonces, then check replay
            while self._nonces and next(iter(self._nonces.values())) < now:
                self._nonces.popitem(last=False)
            if nonce in self._nonces:
                raise BrokerError(REPLAYED_CREDENTIAL)
            self._nonces[nonce] = exp
            if len(self._nonces) > self._cap:
                self._nonces.popitem(last=False)
        return Principal(check_name(sub, "sub"), check_name(ten, "ten"), check_name(c.get("wl", "default"), "wl"),
                         frozenset(c.get("roles", [])))


# ------------------------------------------------------------- tamper-evident audit (43)

@dataclass
class AuditEvent:
    seq: int
    ts: float
    actor: str
    tenant: str
    action: str
    resource: str
    decision: str
    reason: str
    prev: str
    mac: str = ""

    def body(self) -> bytes:
        d = {k: v for k, v in self.__dict__.items() if k != "mac"}
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


class AuditLog:
    """Append-only HMAC hash chain. ``verify()`` detects edit, reorder, deletion and
    (given an externally retained head) tail truncation."""

    GENESIS = "0" * 64

    def __init__(self, key: Secret, clock: Callable[[], float] = time.time, sink: Callable[[dict], None] | None = None,
                 max_events: int = 1_000_000) -> None:
        self._key = key
        self.clock = clock
        self.events: list[AuditEvent] = []
        self._sink = sink
        self._max = max_events
        self._lock = RLock()
        self.dropped_to_sink = 0

    def record(self, actor: str, tenant: str, action: str, resource: str, decision: str, reason: str) -> AuditEvent:
        with self._lock:
            prev = self.events[-1].mac if self.events else self.GENESIS
            ev = AuditEvent(len(self.events) + self.dropped_to_sink, self.clock(), actor, tenant, action,
                            resource, decision, reason[:512], prev)
            ev.mac = hmac.new(self._key.reveal(), ev.body(), hashlib.sha256).hexdigest()
            self.events.append(ev)
            if self._sink:
                self._sink(dict(ev.__dict__))
            if len(self.events) > self._max:  # bounded in memory; sink retains the full stream
                self.events.pop(0)
                self.dropped_to_sink += 1
            return ev

    @property
    def head(self) -> str:
        return self.events[-1].mac if self.events else self.GENESIS

    def verify(self, expected_head: str | None = None, events: list[AuditEvent] | None = None) -> None:
        evs = self.events if events is None else events
        prev = evs[0].prev if evs and self.dropped_to_sink else self.GENESIS
        for i, ev in enumerate(evs):
            if ev.prev != prev:
                raise BrokerError(INTEGRITY_FAILURE, "audit chain link broken", index=i)
            want = hmac.new(self._key.reveal(), ev.body(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(want, ev.mac):
                raise BrokerError(INTEGRITY_FAILURE, "audit event MAC mismatch", index=i)
            prev = ev.mac
        if expected_head is not None and prev != expected_head:
            raise BrokerError(INTEGRITY_FAILURE, "audit head mismatch (truncation?)")


# ------------------------------------------------------- artifact digest verification (38)

@dataclass
class ArtifactPolicy:
    """Allow-list of sha256 digests (optionally HMAC-attested) for executable/policy artifacts."""

    allowed: dict[str, str] = field(default_factory=dict)  # relative path -> sha256

    def verify_bytes(self, name: str, data: bytes) -> str:
        want = self.allowed.get(name)
        if want is None:
            raise BrokerError(INTEGRITY_FAILURE, "artifact not on allow-list", artifact=name)
        got = hashlib.sha256(data).hexdigest()
        if not hmac.compare_digest(want, got):
            raise BrokerError(INTEGRITY_FAILURE, "artifact digest mismatch", artifact=name)
        return got
