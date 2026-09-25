"""Canonical encoding, signing, clocks and strict validation (stdlib only).

Signatures use HMAC-SHA256 over canonical JSON with a key registry that carries
issuer, key id, validity window and revocation.  HMAC is symmetric: it proves the
producer holds an estate-distributed key, not non-repudiation.  An asymmetric
verifier (e.g. Ed25519 via the estate crypto library) plugs in through the
``Verifier`` protocol without changing any caller; see docs/DESIGN.md §Trust.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Iterable, Mapping, Protocol

from .errors import G14Error

MAX_ID_LEN = 128
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]*$")


# --------------------------------------------------------------------------- clock
class Clock(Protocol):
    def now(self) -> float: ...
    def monotonic(self) -> float: ...


class SystemClock:
    def now(self) -> float:
        return time.time()

    def monotonic(self) -> float:
        return time.monotonic()


class FakeClock:
    """Deterministic clock for tests, fault injection and simulation."""

    def __init__(self, start: float = 1_790_000_000.0):
        self._t = float(start)
        self._m = 0.0
        self._lock = threading.Lock()

    def now(self) -> float:
        return self._t

    def monotonic(self) -> float:
        return self._m

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._t += seconds
            self._m += seconds


# --------------------------------------------------------------------- canonical
def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON: sorted keys, no whitespace, finite floats only."""
    try:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except ValueError:
        raise G14Error("G14_INVALID_REQUEST", "non-finite number in signed payload") from None
    except TypeError:
        raise G14Error("G14_INVALID_REQUEST", "payload is not JSON-serialisable") from None


def digest(obj: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(obj)).hexdigest()


# ----------------------------------------------------------------------- signing
@dataclass(frozen=True)
class Key:
    kid: str
    issuer: str
    secret: bytes = field(repr=False)
    not_before: float = 0.0
    not_after: float = float("inf")
    revoked: bool = False


class Verifier(Protocol):
    def verify(self, payload: Mapping[str, Any], signature: Mapping[str, Any], *, expected_issuer: str | None, now: float) -> None: ...


class KeyRing:
    """Trust store: HMAC keys indexed by kid, scoped to an issuer."""

    def __init__(self, keys: Iterable[Key] = ()):
        self._keys: dict[str, Key] = {}
        for k in keys:
            self.add(k)

    def add(self, key: Key) -> None:
        if len(key.secret) < 32:
            raise ValueError("HMAC keys must be at least 256 bits")
        self._keys[key.kid] = key

    def revoke(self, kid: str) -> None:
        k = self._keys[kid]
        self._keys[kid] = Key(k.kid, k.issuer, k.secret, k.not_before, k.not_after, True)

    def kids(self) -> list[str]:
        return sorted(self._keys)

    def sign(self, payload: Mapping[str, Any], kid: str) -> dict[str, str]:
        k = self._keys.get(kid)
        if k is None or k.revoked:
            raise G14Error("G14_UNKNOWN_ISSUER", "signing key unavailable or revoked", details={"kid": kid})
        mac = hmac.new(k.secret, canonical_json(payload), hashlib.sha256).hexdigest()
        return {"alg": "HS256", "kid": k.kid, "iss": k.issuer, "mac": mac}

    def verify(self, payload: Mapping[str, Any], signature: Mapping[str, Any], *, expected_issuer: str | None, now: float) -> None:
        if not isinstance(signature, Mapping) or signature.get("alg") != "HS256":
            raise G14Error("G14_SIGNATURE_INVALID", "unsupported or missing signature algorithm")
        k = self._keys.get(signature.get("kid", ""))
        if k is None:
            raise G14Error("G14_UNKNOWN_ISSUER", "unknown key id", details={"kid": signature.get("kid")})
        if k.revoked or not (k.not_before <= now <= k.not_after):
            raise G14Error("G14_UNKNOWN_ISSUER", "key revoked or outside validity window", details={"kid": k.kid})
        if signature.get("iss") != k.issuer or (expected_issuer is not None and k.issuer != expected_issuer):
            raise G14Error("G14_UNKNOWN_ISSUER", "issuer mismatch", details={"kid": k.kid, "expected": expected_issuer})
        mac = hmac.new(k.secret, canonical_json(payload), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(mac, str(signature.get("mac", ""))):
            raise G14Error("G14_SIGNATURE_INVALID", "MAC verification failed", details={"kid": k.kid})


# -------------------------------------------------------------------- validation
def ident(value: Any, field_name: str, *, max_len: int = MAX_ID_LEN) -> str:
    """Strict identifier: str, NFC-normalized, bounded, restricted charset."""
    if not isinstance(value, str):
        raise G14Error("G14_INVALID_REQUEST", f"{field_name} must be a string", details={"field": field_name})
    norm = unicodedata.normalize("NFC", value)
    if norm != value or not value or len(value) > max_len or not _ID_RE.match(value):
        raise G14Error("G14_INVALID_REQUEST", f"{field_name} is not a valid identifier", details={"field": field_name})
    return value


def number(value: Any, field_name: str, *, minimum: float = 0.0, maximum: float = 1e15) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise G14Error("G14_INVALID_REQUEST", f"{field_name} must be a number", details={"field": field_name})
    v = float(value)
    if not isfinite(v) or v < minimum or v > maximum:
        raise G14Error("G14_INVALID_REQUEST", f"{field_name} out of range", details={"field": field_name})
    return v


def exact_fields(obj: Any, name: str, required: Iterable[str], optional: Iterable[str] = ()) -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise G14Error("G14_INVALID_REQUEST", f"{name} must be an object", details={"field": name})
    req, opt = set(required), set(optional)
    missing = req - obj.keys()
    unknown = obj.keys() - req - opt
    if missing:
        raise G14Error("G14_INVALID_REQUEST", f"{name} missing fields {sorted(missing)}", details={"field": name, "missing": sorted(missing)})
    if unknown:
        raise G14Error("G14_INVALID_REQUEST", f"{name} has unknown fields {sorted(map(str, unknown))}", details={"field": name, "unknown": sorted(map(str, unknown))})
    return obj


def check_fresh(issued_at: float, ttl: float, now: float, what: str, *, skew: float = 5.0) -> float:
    """Return age; raise on stale or future-dated artifacts."""
    age = now - issued_at
    if age < -skew:
        raise G14Error("G14_CLOCK_SKEW", f"{what} issued in the future", details={"what": what, "age_s": age})
    if age > ttl:
        raise G14Error("G14_STALE_INPUT", f"{what} is stale", details={"what": what, "age_s": round(age, 3), "ttl_s": ttl})
    return max(age, 0.0)


class ReplayGuard:
    """Bounded memory of seen nonces within a window (anti-replay)."""

    def __init__(self, window_s: float = 900.0, max_entries: int = 100_000):
        self.window_s, self.max_entries = window_s, max_entries
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def check_and_add(self, nonce: str, now: float) -> None:
        with self._lock:
            if len(self._seen) >= self.max_entries:
                cutoff = now - self.window_s
                self._seen = {k: t for k, t in self._seen.items() if t >= cutoff}
                if len(self._seen) >= self.max_entries:
                    raise G14Error("G14_OVERLOADED", "replay guard full")
            t = self._seen.get(nonce)
            if t is not None and now - t <= self.window_s:
                raise G14Error("G14_REPLAY", "nonce replayed", details={"nonce_digest": hashlib.sha256(nonce.encode()).hexdigest()[:16]})
            self._seen[nonce] = now
