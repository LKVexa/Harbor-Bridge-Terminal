"""Authenticated, versioned call context (PK_CALL_CONTEXT/1).

GAP-005 / GAP-040 / GAP-008 (deadline + cancellation).

The tenant and principal on a hop are *never* taken from request-controlled
strings. They come from a :class:`Principal` produced by an
:class:`IdentityVerifier` from a credential issued by the trusted runtime
(HMAC-SHA256 over a canonical claim set with expiry and nonce). A context is
immutable; each hop derives a child context whose path/depth are appended by
the chainer, never by the caller.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from typing import Mapping, Optional

from .errors import Cancelled, DeadlineExceeded, Unauthenticated, ValidationFailed

CONTEXT_SCHEMA = "PK_CALL_CONTEXT/1"
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:\-]{0,127}$")
TRACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]{0,63}$")
MAX_CAPABILITIES = 32
MAX_PATH = 64
MAX_TOKEN_BYTES = 4096
MAX_TOKEN_TTL_S = 3600


def check_id(value, field_name: str, pattern=ID_RE) -> str:
    if not isinstance(value, str) or not pattern.match(value):
        raise ValidationFailed(f"invalid {field_name}", field=field_name)
    return value


class CancelToken:
    """Cooperative cancellation shared by every hop of one logical call."""

    __slots__ = ("_event", "reason")

    def __init__(self) -> None:
        self._event = threading.Event()
        self.reason: Optional[str] = None

    def cancel(self, reason: str = "cancelled") -> None:
        self.reason = reason[:64]
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True)
class Deadline:
    """Absolute monotonic deadline; children inherit it (never extend it)."""

    at_monotonic: float

    @classmethod
    def after(cls, seconds: float) -> "Deadline":
        if not isinstance(seconds, (int, float)) or seconds <= 0 or seconds > 3600:
            raise ValidationFailed("deadline must be within (0, 3600] seconds", field="deadline")
        return cls(time.monotonic() + float(seconds))

    def remaining(self) -> float:
        return self.at_monotonic - time.monotonic()

    @property
    def expired(self) -> bool:
        return self.remaining() <= 0


@dataclass(frozen=True)
class Principal:
    """Authenticated identity. Only IdentityVerifier / trusted runtime builds one."""

    subject: str
    tenant: str
    capabilities: frozenset
    issuer: str
    issued_at: float
    expires_at: float
    token_id: str
    provenance: str = "hmac-sha256"

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


class IdentityVerifier:
    """Issues/verifies runtime identity credentials bound to a key id.

    * signature: HMAC-SHA256 with constant-time compare
    * expiry and not-before with bounded clock skew
    * replay window: a token id may be *presented* once per verifier when
      ``single_use`` (bounded LRU of seen ids)
    * key rotation: several key ids may be active; retired keys are refused
    """

    def __init__(self, keys: Mapping[str, bytes], *, issuer: str = "pk-runtime",
                 active_kid: Optional[str] = None, skew_s: float = 5.0,
                 replay_window: int = 65536) -> None:
        if not keys or any(not isinstance(k, bytes) or len(k) < 32 for k in keys.values()):
            raise ValueError("identity keys must be >= 32 bytes")
        self._keys = dict(keys)
        self.issuer = check_id(issuer, "issuer")
        self.active_kid = active_kid or sorted(self._keys)[0]
        if self.active_kid not in self._keys:
            raise ValueError("active_kid not in keys")
        self.skew_s = skew_s
        self._seen: "OrderedDict[str, float]" = OrderedDict()
        self._seen_max = replay_window
        self._lock = threading.Lock()

    def retire(self, kid: str) -> None:
        with self._lock:
            if kid == self.active_kid:
                raise ValueError("cannot retire active key")
            self._keys.pop(kid, None)

    def issue(self, subject: str, tenant: str, capabilities=(), ttl_s: float = 300.0) -> str:
        check_id(subject, "subject"); check_id(tenant, "tenant")
        caps = sorted({check_id(c, "capability") for c in capabilities})
        if len(caps) > MAX_CAPABILITIES:
            raise ValidationFailed("too many capabilities", field="capabilities")
        if not 0 < ttl_s <= MAX_TOKEN_TTL_S:
            raise ValidationFailed("ttl out of range", field="ttl")
        now_ms = int(time.time() * 1000)  # floor: rounding iat up made fresh tokens "not yet valid"
        claims = {"v": 1, "iss": self.issuer, "sub": subject, "ten": tenant, "cap": caps,
                  "iat": now_ms / 1000, "exp": (now_ms + int(ttl_s * 1000)) / 1000,
                  "jti": secrets.token_hex(12)}
        body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        head = _b64(json.dumps({"alg": "HS256", "kid": self.active_kid}, sort_keys=True).encode())
        signing = f"{head}.{body}".encode()
        sig = _b64(hmac.new(self._keys[self.active_kid], signing, hashlib.sha256).digest())
        return f"{head}.{body}.{sig}"

    def verify(self, token: str, *, single_use: bool = False) -> Principal:
        if not isinstance(token, str) or len(token) > MAX_TOKEN_BYTES or token.count(".") != 2:
            raise Unauthenticated("malformed credential")
        head_s, body_s, sig_s = token.split(".")
        try:
            head = json.loads(_unb64(head_s)); claims = json.loads(_unb64(body_s)); sig = _unb64(sig_s)
        except Exception:
            raise Unauthenticated("malformed credential") from None
        if not isinstance(head, dict) or head.get("alg") != "HS256":
            raise Unauthenticated("unsupported credential algorithm")
        with self._lock:
            key = self._keys.get(head.get("kid"))
        if key is None:
            raise Unauthenticated("unknown or retired key id")
        expect = hmac.new(key, f"{head_s}.{body_s}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expect, sig):
            raise Unauthenticated("bad credential signature")
        if not isinstance(claims, dict) or claims.get("v") != 1 or claims.get("iss") != self.issuer:
            raise Unauthenticated("credential issuer/version mismatch")
        now = time.time()
        try:
            iat, exp = float(claims["iat"]), float(claims["exp"])
            sub, ten, jti = claims["sub"], claims["ten"], claims["jti"]
            caps = frozenset(check_id(c, "capability") for c in claims["cap"])
            check_id(sub, "subject"); check_id(ten, "tenant")
        except (KeyError, TypeError, ValueError, ValidationFailed):
            raise Unauthenticated("credential claims invalid") from None
        if iat - self.skew_s > now:
            raise Unauthenticated("credential not yet valid")
        if exp + self.skew_s <= now:
            raise Unauthenticated("credential expired")
        if single_use:
            with self._lock:
                if jti in self._seen:
                    raise Unauthenticated("credential replayed")
                self._seen[jti] = exp
                while len(self._seen) > self._seen_max:
                    self._seen.popitem(last=False)
        return Principal(sub, ten, caps, self.issuer, iat, exp, jti)


@dataclass(frozen=True)
class CallContext:
    """Validated, versioned, immutable context carried on every hop."""

    principal: Principal
    trace_id: str
    operation: str = "invoke"
    idempotency_key: Optional[str] = None
    deadline: Optional[Deadline] = None
    cancel: CancelToken = field(default_factory=CancelToken, compare=False)
    path: tuple = ()
    schema: str = CONTEXT_SCHEMA
    origin_host: Optional[str] = None
    credential: Optional[str] = field(default=None, repr=False, compare=False)
    # set only by the chainer: seal proving this context was derived by Hop inside an
    # admitted root call (never accepted from callers or from the wire)
    root_id: Optional[str] = field(default=None, repr=False, compare=False)
    hop_seal: Optional[str] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.principal, Principal):
            raise Unauthenticated("call context requires an authenticated principal")
        if self.schema != CONTEXT_SCHEMA:
            raise ValidationFailed("unsupported context schema", schema=str(self.schema)[:32])
        check_id(self.trace_id, "trace_id", TRACE_RE)
        check_id(self.operation, "operation")
        if self.idempotency_key is not None:
            check_id(self.idempotency_key, "idempotency_key")
        if not isinstance(self.path, tuple) or len(self.path) > MAX_PATH:
            raise ValidationFailed("invalid path", field="path")
        for p in self.path:
            check_id(p, "path")

    @property
    def tenant(self) -> str:
        return self.principal.tenant

    @property
    def depth(self) -> int:
        return len(self.path)

    def check_live(self) -> None:
        if self.principal.expired:
            raise Unauthenticated("principal expired mid-chain")
        if self.cancel.cancelled:
            raise Cancelled("call cancelled", reason=self.cancel.reason, trace_id=self.trace_id)
        if self.deadline is not None and self.deadline.expired:
            raise DeadlineExceeded("deadline exceeded", trace_id=self.trace_id)

    def child(self, callee: str) -> "CallContext":
        return replace(self, path=self.path + (callee,))

    def to_wire(self) -> dict:
        """Public, schema-conformant projection (no credential material)."""
        return {
            "schema": self.schema, "trace_id": self.trace_id, "operation": self.operation,
            "tenant": self.tenant, "subject": self.principal.subject,
            "idempotency_key": self.idempotency_key, "path": list(self.path),
            "deadline_ms": None if self.deadline is None else max(0, int(self.deadline.remaining() * 1000)),
        }
