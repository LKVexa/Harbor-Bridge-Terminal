"""Authentication at every INV-64 boundary (MC-07; C023, C044).

Credential: compact token ``v1.<header>.<claims>.<sig>`` (base64url, no padding).

* header ``{"alg": "HS256"|"EdDSA", "kid": str, "typ": "pk-app+jwt"}``
* claims ``iss sub aud tid (tenant) kind roles iat nbf exp jti [cnf]``

Verification order is fixed and fail-closed: shape -> algorithm allowlist ->
key lookup *by (issuer, kid) from the configured trust set, never from the
token* -> signature -> issuer/audience -> time window with bounded skew ->
max lifetime -> revocation -> replay (jti, bounded cache) -> optional channel
binding (``cnf`` must equal the caller-supplied TLS exporter/peer digest).

Trust material comes from a ``TrustSource`` (configuration, KMS, JWKS mirror —
an operations choice); it is never read from a manifest. If the source is
unavailable, keys cached within ``cache_ttl`` still verify *existing* tokens,
but nothing is verified once the cache is stale: ``auth.trust_unavailable``.
EdDSA requires the optional ``cryptography`` package and is refused without it.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
import heapq
from dataclasses import dataclass
from typing import Callable, Mapping

from .errors import Inv64Error

TOKEN_PREFIX = "v1"
ALLOWED_ALGS = frozenset({"HS256", "EdDSA"})
IDENTITY_KINDS = frozenset({"human", "workload", "node", "service", "provider", "signer", "automation", "breakglass"})
MAX_TOKEN_BYTES = 8192


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _canon(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant: str
    kind: str
    roles: tuple[str, ...]
    issuer: str
    token_id: str
    expires_at: float
    breakglass: bool = False


@dataclass
class TrustConfig:
    """Versioned trust roots (MC-07 'identity mechanism and trust roots are versioned')."""

    version: str
    audience: str
    # issuer -> kid -> (alg, key material: HMAC secret bytes or Ed25519 public key bytes)
    issuers: Mapping[str, Mapping[str, tuple[str, bytes]]]
    max_lifetime_s: int = 3600
    breakglass_max_lifetime_s: int = 900
    clock_skew_s: int = 60
    revoked_token_ids: frozenset = frozenset()
    revoked_subjects: frozenset = frozenset()
    require_channel_binding: bool = False


class TrustUnavailable(Exception):
    pass


class Authenticator:
    def __init__(self, trust_source: Callable[[], TrustConfig], *, clock: Callable[[], float] = time.time,
                 cache_ttl_s: float = 300.0, replay_capacity: int = 100_000,
                 failure_limit: int = 20, failure_window_s: float = 60.0, audit=None, metrics=None):
        self._source = trust_source
        self._clock = clock
        self._cache_ttl = cache_ttl_s
        self._cached: TrustConfig | None = None
        self._cached_at = float("-inf")
        self._seen: dict[str, float] = {}
        self._heap: list[tuple[float, str]] = []
        self._replay_capacity = replay_capacity
        self._fail: dict[str, list[float]] = {}
        self._failure_limit = failure_limit
        self._failure_window = failure_window_s
        self._lock = threading.Lock()
        self._audit = audit
        self._metrics = metrics

    # -- trust material ---------------------------------------------------
    def trust(self) -> TrustConfig:
        now = self._clock()
        try:
            cfg = self._source()
            if not isinstance(cfg, TrustConfig):
                raise TrustUnavailable("trust source returned an invalid object")
            self._cached, self._cached_at = cfg, now
            return cfg
        except TrustUnavailable:
            if self._cached is not None and now - self._cached_at <= self._cache_ttl:
                return self._cached
            raise Inv64Error("auth.trust_unavailable")

    # -- failure rate limiting (per calling source, not per tenant) --------
    def _limited(self, source: str) -> bool:
        now = self._clock()
        hist = [t for t in self._fail.get(source, []) if now - t < self._failure_window]
        self._fail[source] = hist
        if len(self._fail) > 50_000:  # bound the table itself
            for k in list(self._fail)[:10_000]:
                self._fail.pop(k, None)
        return len(hist) >= self._failure_limit

    def _record_failure(self, source: str) -> None:
        self._fail.setdefault(source, []).append(self._clock())

    # -- verification -------------------------------------------------------
    def authenticate(self, token: str | None, *, source: str = "unknown",
                     channel_binding: str | None = None, correlation_id: str | None = None) -> Principal:
        with self._lock:
            if self._limited(source):
                self._emit("authn", "denied", source, "auth.rate_limited", correlation_id)
                raise Inv64Error("auth.rate_limited", correlation_id=correlation_id)
            try:
                principal = self._verify(token, channel_binding)
            except Inv64Error as exc:
                self._record_failure(source)
                self._emit("authn", "denied", source, exc.code, correlation_id)
                exc.correlation_id = correlation_id
                raise
            self._emit("authn", "allowed", source, None, correlation_id, principal)
            return principal

    def _verify(self, token: str | None, channel_binding: str | None) -> Principal:
        if not token:
            raise Inv64Error("auth.missing")
        if not isinstance(token, str) or len(token) > MAX_TOKEN_BYTES:
            raise Inv64Error("auth.malformed")
        parts = token.split(".")
        if len(parts) != 4 or parts[0] != TOKEN_PREFIX:
            raise Inv64Error("auth.malformed")
        try:
            header = json.loads(_b64d(parts[1]))
            claims = json.loads(_b64d(parts[2]))
            sig = _b64d(parts[3])
        except (ValueError, UnicodeDecodeError):
            raise Inv64Error("auth.malformed")
        if not isinstance(header, dict) or not isinstance(claims, dict):
            raise Inv64Error("auth.malformed")
        alg = header.get("alg")
        if alg not in ALLOWED_ALGS:  # includes "none" and anything unexpected
            raise Inv64Error("auth.algorithm")
        cfg = self.trust()
        iss = claims.get("iss")
        keys = cfg.issuers.get(iss) if isinstance(iss, str) else None
        if keys is None:
            raise Inv64Error("auth.issuer")
        kid = header.get("kid")
        entry = keys.get(kid) if isinstance(kid, str) else None
        if entry is None or entry[0] != alg:  # key's own algorithm binds; token cannot downgrade it
            raise Inv64Error("auth.signature")
        signing_input = f"{parts[0]}.{parts[1]}.{parts[2]}".encode()
        if not _check_sig(alg, entry[1], signing_input, sig):
            raise Inv64Error("auth.signature")
        aud = claims.get("aud")
        if aud != cfg.audience and not (isinstance(aud, list) and cfg.audience in aud):
            raise Inv64Error("auth.audience")
        for k in ("sub", "tid", "kind", "jti"):
            if not isinstance(claims.get(k), str) or not claims[k]:
                raise Inv64Error("auth.malformed", details={"claim": k})
        if claims["kind"] not in IDENTITY_KINDS:
            raise Inv64Error("auth.malformed", details={"claim": "kind"})
        try:
            iat, nbf, exp = float(claims["iat"]), float(claims.get("nbf", claims["iat"])), float(claims["exp"])
        except (KeyError, TypeError, ValueError):
            raise Inv64Error("auth.malformed", details={"claim": "iat/exp"})
        now = self._clock()
        if now > exp + cfg.clock_skew_s:
            raise Inv64Error("auth.expired")
        if now + cfg.clock_skew_s < nbf or now + cfg.clock_skew_s < iat:
            raise Inv64Error("auth.not_yet_valid")
        breakglass = claims["kind"] == "breakglass"
        max_life = cfg.breakglass_max_lifetime_s if breakglass else cfg.max_lifetime_s
        if exp - iat > max_life:
            raise Inv64Error("auth.lifetime")
        if claims["jti"] in cfg.revoked_token_ids or claims["sub"] in cfg.revoked_subjects:
            raise Inv64Error("auth.revoked")
        if cfg.require_channel_binding or "cnf" in claims:
            if not channel_binding or not hmac.compare_digest(str(claims.get("cnf", "")), channel_binding):
                raise Inv64Error("auth.signature", details={"reason": "channel binding"})
        self._check_replay(f"{iss}\x00{claims['jti']}", exp + cfg.clock_skew_s, now)
        roles = claims.get("roles", [])
        if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
            raise Inv64Error("auth.malformed", details={"claim": "roles"})
        return Principal(claims["sub"], claims["tid"], claims["kind"], tuple(sorted(set(roles))),
                         iss, claims["jti"], exp, breakglass)

    def _check_replay(self, key: str, until: float, now: float) -> None:
        while self._heap and self._heap[0][0] < now:
            _, k = heapq.heappop(self._heap)
            self._seen.pop(k, None)
        if key in self._seen:
            raise Inv64Error("auth.replay")
        if len(self._seen) >= self._replay_capacity:
            # Cannot remember more tokens: refusing is safe, forgetting is not.
            raise Inv64Error("auth.rate_limited", details={"reason": "replay cache full"})
        self._seen[key] = until
        heapq.heappush(self._heap, (until, key))

    def _emit(self, event, outcome, source, code, correlation_id, principal: Principal | None = None):
        if self._metrics is not None:
            self._metrics.inc("inv64_authn_total", outcome=outcome)
        if self._audit is not None:
            self._audit.append(event, actor=principal.subject if principal else f"source:{source}",
                               tenant=principal.tenant if principal else None, outcome=outcome,
                               reason=code, correlation_id=correlation_id,
                               token_id=principal.token_id if principal else None)


def _check_sig(alg: str, key: bytes, msg: bytes, sig: bytes) -> bool:
    if alg == "HS256":
        return hmac.compare_digest(hmac.new(key, msg, hashlib.sha256).digest(), sig)
    if alg == "EdDSA":
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.exceptions import InvalidSignature
        except ImportError:
            return False  # backend absent: refuse rather than accept
        try:
            Ed25519PublicKey.from_public_bytes(key).verify(sig, msg)
            return True
        except (InvalidSignature, ValueError):
            return False
    return False


def mint(claims: Mapping, *, kid: str, key: bytes, alg: str = "HS256") -> str:
    """Issue a token (tests, local tooling, and HS256 service identities)."""
    header = {"alg": alg, "kid": kid, "typ": "pk-app+jwt"}
    signing_input = f"{TOKEN_PREFIX}.{_b64e(_canon(header))}.{_b64e(_canon(dict(claims)))}"
    if alg == "HS256":
        sig = hmac.new(key, signing_input.encode(), hashlib.sha256).digest()
    elif alg == "EdDSA":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        sig = Ed25519PrivateKey.from_private_bytes(key).sign(signing_input.encode())
    else:
        raise ValueError("unsupported alg")
    return f"{signing_input}.{_b64e(sig)}"
