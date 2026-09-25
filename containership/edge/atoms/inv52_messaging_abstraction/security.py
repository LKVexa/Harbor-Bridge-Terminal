"""Trust primitives for INV-52 (C023, C024, C039, C042, C044-C049, C075).

Token authority, audit chain, redaction and artifact admission are adapted from
the shop's sibling car INV-46 v4.3.0 (same owner; see THIRD-PARTY-NOTICES.md).

Stdlib only.  Identity is an HMAC-SHA256 signed caller token with expiry and a
single-use nonce; the key comes from a caller-supplied key provider, never from
configuration.  Every failure to establish trust denies (fail closed).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .runtime import MessagingError as _StructuredError


class Unauthenticated(_StructuredError, PermissionError):
    code = "PK_MSG_UNAUTHENTICATED"
    retryable = False


class TrustUnavailable(_StructuredError, RuntimeError):
    """A trust dependency (key, identity, time) is unavailable: deny, never allow."""

    code = "PK_MSG_TRUST_UNAVAILABLE"
    retryable = True


class ArtifactRejected(_StructuredError, PermissionError):
    code = "PK_MSG_ARTIFACT_REJECTED"
    retryable = False


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ----------------------------------------------------------------- identity
@dataclass(frozen=True)
class Principal:
    app: str
    tenant: str
    key_id: str
    expires_at: int


class TokenAuthority:
    """Issue/verify signed caller tokens.  ``keys`` returns {key_id: secret}.

    Rotation: keep the old key id in the provider until tokens signed with it
    expire; ``active_key_id`` selects the signing key.
    """

    MAX_TTL = 3600
    CLOCK_SKEW = 30

    def __init__(
        self,
        keys: Callable[[], Mapping[str, bytes]],
        active_key_id: str,
        *,
        clock: Callable[[], float] = time.time,
        nonce_capacity: int = 100_000,
    ):
        self._keys = keys
        self.active_key_id = active_key_id
        self.clock = clock
        self._seen: OrderedDict[str, int] = OrderedDict()
        self._capacity = nonce_capacity
        self._lock = threading.Lock()

    def _key(self, key_id: str) -> bytes:
        try:
            keys = self._keys()
        except Exception as exc:  # noqa: BLE001
            raise TrustUnavailable("identity key provider unavailable") from exc
        key = keys.get(key_id) if keys else None
        if not key or len(key) < 32:
            raise Unauthenticated("unknown or weak signing key")
        return key

    def _now(self) -> int:
        try:
            now = self.clock()
        except Exception as exc:  # noqa: BLE001
            raise TrustUnavailable("time source unavailable") from exc
        if not isinstance(now, (int, float)) or now <= 0:
            raise TrustUnavailable("time source returned an invalid value")
        return int(now)

    def replay_cache_fill(self) -> float:
        """Saturation signal: sustained new-token rate is bounded by capacity / TTL."""
        with self._lock:
            return len(self._seen) / self._capacity

    def issue(self, app: str, tenant: str, ttl: int = 300, nonce: str | None = None) -> str:
        if not (0 < ttl <= self.MAX_TTL):
            raise ValueError("ttl out of range")
        import secrets

        claims = {
            "app": app,
            "tenant": tenant,
            "kid": self.active_key_id,
            "exp": self._now() + ttl,
            "nonce": nonce or secrets.token_hex(16),
        }
        body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        sig = _b64(hmac.new(self._key(self.active_key_id), body.encode(), hashlib.sha256).digest())
        return f"{body}.{sig}"

    def verify(self, token: Any) -> Principal:
        if not isinstance(token, str) or len(token) > 4096 or token.count(".") != 1:
            raise Unauthenticated("malformed token")
        body, sig = token.split(".")
        try:
            claims = json.loads(_unb64(body))
            given = _unb64(sig)
        except Exception as exc:  # noqa: BLE001
            raise Unauthenticated("malformed token") from exc
        if not isinstance(claims, dict) or set(claims) != {"app", "tenant", "kid", "exp", "nonce"}:
            raise Unauthenticated("token claims invalid")
        if not all(isinstance(claims[k], str) and claims[k] for k in ("app", "tenant", "kid", "nonce")):
            raise Unauthenticated("token claims invalid")
        if not isinstance(claims["exp"], int):
            raise Unauthenticated("token claims invalid")
        expected = hmac.new(self._key(claims["kid"]), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, given):
            raise Unauthenticated("bad signature")
        now = self._now()
        if claims["exp"] + self.CLOCK_SKEW < now:
            raise Unauthenticated("token expired")
        if claims["exp"] > now + self.MAX_TTL + self.CLOCK_SKEW:
            raise Unauthenticated("token lifetime exceeds policy")
        with self._lock:
            # Evict expired nonces from the oldest end.  (The INV-46 donor copied the
            # whole cache with list(...) on every verify: O(cache) per call, found
            # by this car's per-tenant benchmark.)
            while self._seen:
                oldest_exp = next(iter(self._seen.values()))
                if oldest_exp + self.CLOCK_SKEW >= now:
                    break
                self._seen.popitem(last=False)
            if claims["nonce"] in self._seen:
                raise Unauthenticated("token replay detected")
            if len(self._seen) >= self._capacity:
                raise TrustUnavailable("replay cache full; refusing rather than forgetting")
            self._seen[claims["nonce"]] = claims["exp"]
        return Principal(claims["app"], claims["tenant"], claims["kid"], claims["exp"])


# ----------------------------------------------------------------- audit chain
class AuditChain:
    """Append-only SHA-256 hash chain.  Truncation of the tail is detected by
    comparing ``head()`` against an externally recorded head."""

    GENESIS = "0" * 64

    def __init__(self, max_events: int = 100_000):
        self.max_events = max_events
        self._events: list[dict[str, Any]] = []
        self._base = self.GENESIS  # hash preceding the first retained event
        self._lock = threading.Lock()

    @staticmethod
    def _digest(prev: str, event: Mapping[str, Any]) -> str:
        payload = json.dumps(event, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256((prev + payload).encode()).hexdigest()

    def append(self, kind: str, **fields: Any) -> dict[str, Any]:
        with self._lock:
            prev = self._events[-1]["hash"] if self._events else self._base
            event = {"seq": (self._events[-1]["seq"] + 1) if self._events else 1,
                     "ts_ns": time.time_ns(), "kind": kind, **redact(fields)}
            event["prev"] = prev
            event["hash"] = self._digest(prev, {k: v for k, v in event.items() if k != "hash"})
            self._events.append(event)
            if len(self._events) > self.max_events:
                dropped = self._events.pop(0)
                self._base = dropped["hash"]
            return dict(event)

    def head(self) -> str:
        with self._lock:
            return self._events[-1]["hash"] if self._events else self._base

    def events(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(e) for e in self._events]

    @classmethod
    def verify(cls, events: Iterable[Mapping[str, Any]], base: str = GENESIS, head: str | None = None) -> bool:
        prev = base
        last = base
        for e in events:
            if e.get("prev") != prev:
                return False
            if cls._digest(prev, {k: v for k, v in e.items() if k != "hash"}) != e.get("hash"):
                return False
            prev = last = e["hash"]
        return head is None or head == last

    @property
    def base(self) -> str:
        return self._base


# ----------------------------------------------------------------- secrets
_SECRET_KEY = re.compile(r"(pass(word)?|secret|token|api[_-]?key|private[_-]?key|credential|connection[_-]?string)", re.I)
_SECRET_VALUE = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"(?i)\b(password|pwd)=[^;\s]+"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
]
REDACTED = "[REDACTED]"


def looks_secret(key: str, value: Any) -> bool:
    if isinstance(value, str):
        if any(p.search(value) for p in _SECRET_VALUE):
            return True
        if _SECRET_KEY.search(key or "") and not value.startswith("secretref:"):
            return True
    return False


def redact(obj: Any, _key: str = "") -> Any:
    """Recursively replace secret-looking values; safe for logs and diagnostics."""
    if isinstance(obj, Mapping):
        return {k: redact(v, str(k)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v, _key) for v in obj]
    if isinstance(obj, str) and looks_secret(_key, obj):
        return REDACTED
    return obj


def find_secrets(obj: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            p = f"{path}.{k}"
            if isinstance(v, str) and looks_secret(str(k), v):
                hits.append(p)
            else:
                hits.extend(find_secrets(v, p))
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            hits.extend(find_secrets(v, f"{path}[{i}]"))
    elif isinstance(obj, str) and looks_secret("", obj):
        hits.append(path)
    return hits


# ----------------------------------------------------------------- artifacts
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_artifact(path: Path, approved: Mapping[str, Mapping[str, str]]) -> dict[str, str]:
    """Admit an artifact only if its digest is on the approved list.

    ``approved`` maps sha256 -> {"name":..., "version":..., "provenance":...}.
    Signature verification (Sigstore/cosign) is external; see THREAT_MODEL.md.
    """
    path = Path(path)
    if not path.is_file():
        raise ArtifactRejected(f"artifact {path.name} not found")
    digest = sha256_file(path)
    entry = approved.get(digest)
    if not entry:
        raise ArtifactRejected(f"artifact {path.name} digest {digest[:12]}... is not approved")
    if not entry.get("provenance"):
        raise ArtifactRejected("approved entry lacks provenance")
    return {"sha256": digest, **entry}


# ----------------------------------------------------------------- tenant bus
TENANT_SEP = "::"


class TenantBus:
    """Authenticated, tenant-isolated facade over a ``PubSub`` (C023, C024, C042, C046, C049).

    * the caller presents a signed token; the envelope ``source`` must equal the
      token's app, so identity is never taken from the message (spoofing)
    * every topic is namespaced by the token's tenant, so tenant A cannot
      publish to, subscribe to, or read dead letters of tenant B's topic
    * capabilities are explicit per (tenant, app): ``publish:<topic>`` and
      ``subscribe:<topic>``; nothing is granted by default (least privilege)
    * every security-relevant decision is appended to a tamper-evident chain
    * if the identity key or clock is unavailable, every call is denied
    """

    def __init__(self, bus: Any, authority: TokenAuthority, audit: AuditChain | None = None):
        self.bus = bus
        self.authority = authority
        self.audit = audit or AuditChain()
        self._caps: dict[tuple[str, str], frozenset[str]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _check_name(value: str, what: str) -> str:
        if not isinstance(value, str) or not value or TENANT_SEP in value or len(value) > 256:
            raise Unauthenticated(f"invalid {what}")
        return value

    def qualified(self, tenant: str, topic: str) -> str:
        return f"{self._check_name(tenant, 'tenant')}{TENANT_SEP}{self._check_name(topic, 'topic')}"

    def grant(self, tenant: str, app: str, *capabilities: str) -> None:
        caps = set()
        for c in capabilities:
            verb, _, topic = str(c).partition(":")
            if verb not in ("publish", "subscribe") or not topic or TENANT_SEP in topic:
                raise ValueError(f"invalid capability {c!r}")
            caps.add(f"{verb}:{topic}")
        with self._lock:
            before = self._caps.get((tenant, app), frozenset())
            self._caps[(tenant, app)] = frozenset(caps)
            touched = {c[8:] for c in before | caps if c.startswith("publish:")}
            plan = {t: sorted(a for (tt, a), cs in self._caps.items() if tt == tenant and f"publish:{t}" in cs)
                    for t in touched}
        for t, apps in plan.items():  # revocation included: a removed publisher is dropped
            self.bus.allow(self.qualified(tenant, t), *apps)
        self.audit.append("capability.grant", tenant=tenant, app=app, capabilities=sorted(caps))

    def _principal(self, token: str, op: str, topic: str) -> Principal:
        try:
            p = self.authority.verify(token)
        except (Unauthenticated, TrustUnavailable) as exc:
            self.audit.append("authn.denied", op=op, topic=str(topic)[:256], code=exc.code)
            raise
        need = f"{op}:{topic}"
        if need not in self._caps.get((p.tenant, p.app), frozenset()):
            self.audit.append("authz.denied", op=op, tenant=p.tenant, app=p.app, topic=topic)
            from .runtime import TopicDenied
            raise TopicDenied(f"{p.app} lacks capability {need}", details={"capability": need})
        return p

    def publish(self, token: str, topic: str, msg: Any) -> int:
        p = self._principal(token, "publish", topic)
        try:
            n = self.bus.publish(p.app, self.qualified(p.tenant, topic), msg)
        except Exception as exc:
            self.audit.append("publish.rejected", tenant=p.tenant, app=p.app, topic=topic,
                              code=getattr(exc, "code", type(exc).__name__))
            raise
        self.audit.append("publish.accepted", tenant=p.tenant, app=p.app, topic=topic,
                          message_id=msg.get("id") if hasattr(msg, "get") else None, delivered=n)
        return n

    def subscribe(self, token: str, topic: str, predicate: Any, sink: Any) -> str:
        p = self._principal(token, "subscribe", topic)
        sid = self.bus.subscribe(self.qualified(p.tenant, topic), predicate, sink)
        self.audit.append("subscription.add", tenant=p.tenant, app=p.app, topic=topic, subscription=sid)
        return sid

    def dead_letters(self, token: str, topic: str) -> list[dict[str, Any]]:
        p = self._principal(token, "subscribe", topic)
        q = self.qualified(p.tenant, topic)
        return [dict(e, topic=topic) for e in self.bus.dead_letter if e["topic"] == q]
