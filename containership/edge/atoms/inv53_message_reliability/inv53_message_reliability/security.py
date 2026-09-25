"""Boundary security for INV-53 (components 13, 14, 27, 30, 33-36).

* Authentication: every request carries ``auth = {kid, principal, ts, nonce, mac}``
  where ``mac`` is HMAC-SHA256 over the canonical request.  Keys come from a
  :class:`KeyProvider`; timestamps outside the skew window and replayed nonces are
  refused.  Raw keys are never logged or returned.
* Key rotation: a :class:`Keyring` has exactly one *active* signing key and any
  number of *verify-only* keys; retired keys verify nothing.
* Authorization: least-privilege capability grants
  ``(principal, tenant, queue, actions)``; nothing is allowed by default and
  ``admin`` does not imply ``consume``/``produce``.
* Security dependency outage: a provider or audit-sink failure raises
  :class:`SecurityDependencyError` and callers fail closed.
* Audit: :class:`AuditLog` is an append-only, hash-chained JSONL file; ``verify``
  detects edits, deletions and reordering; ``head()`` is exported for external
  anchoring because a chain alone cannot detect tail truncation.

Encryption of payloads at rest is **not** implemented here (the standard library
has no authenticated cipher); see docs/security/ENCRYPTION.md for the KMS-bound
specification and the explicit blocker.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock
from typing import Any, Iterable, Mapping, Protocol

ACTIONS = frozenset({"produce", "consume", "admin", "redrive", "read_dlq"})


class SecurityError(Exception):
    pass


class AuthenticationError(SecurityError):
    pass


class AuthorizationError(SecurityError):
    pass


class SecurityDependencyError(SecurityError):
    """A key provider or audit sink is unavailable. Callers must fail closed."""


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


class KeyProvider(Protocol):
    def get(self, kid: str) -> bytes: ...


@dataclass
class Keyring:
    """Rotation-aware in-process keyring.  ``get`` returns key bytes for kid."""

    active: str | None = None
    _keys: dict[str, bytes] = field(default_factory=dict)
    _retired: set[str] = field(default_factory=set)

    def add(self, kid: str, key: bytes, *, activate: bool = False) -> None:
        if not kid or len(key) < 32:
            raise ValueError("keys need a kid and >= 32 bytes")
        self._keys[kid] = bytes(key)
        if activate:
            self.active = kid

    def rotate(self, kid: str, key: bytes) -> None:
        """New key becomes active; the previous active key stays verify-only."""
        self.add(kid, key, activate=True)

    def retire(self, kid: str) -> None:
        if kid == self.active:
            raise ValueError("cannot retire the active key; rotate first")
        self._retired.add(kid)

    def get(self, kid: str) -> bytes:
        if kid in self._retired or kid not in self._keys:
            raise AuthenticationError("unknown or retired key id")
        return self._keys[kid]

    def kids(self) -> dict[str, str]:
        return {k: ("active" if k == self.active else "retired" if k in self._retired else "verify-only")
                for k in self._keys}


class EnvKeyProvider:
    """Reads hex keys from ``INV53_KEY_<KID>`` environment variables."""

    def get(self, kid: str) -> bytes:
        raw = os.environ.get(f"INV53_KEY_{kid.upper()}")
        if raw is None:
            raise AuthenticationError("unknown key id")
        try:
            key = bytes.fromhex(raw)
        except ValueError as exc:
            raise SecurityDependencyError("malformed key material in environment") from exc
        if len(key) < 32:
            raise SecurityDependencyError("key material shorter than 32 bytes")
        return key


class UnboundKmsProvider:
    """Placeholder boundary for an external KMS.  No KMS is bound: always fails closed."""

    def get(self, kid: str) -> bytes:
        raise SecurityDependencyError("no KMS is bound to this deployment")


def sign(key: bytes, request: Mapping[str, Any], *, kid: str, principal: str, ts: float, nonce: str) -> dict:
    body = {k: v for k, v in request.items() if k != "auth"}
    msg = canonical({"body": body, "kid": kid, "principal": principal, "ts": ts, "nonce": nonce})
    return {"kid": kid, "principal": principal, "ts": ts, "nonce": nonce,
            "mac": hmac.new(key, msg, hashlib.sha256).hexdigest()}


class Authenticator:
    def __init__(self, provider: KeyProvider, *, skew_seconds: float = 300.0, nonce_cache: int = 100_000,
                 principals: Mapping[str, str] | None = None) -> None:
        """``principals`` maps principal -> the only kid it may sign with (binding)."""
        self.provider = provider
        self.skew = skew_seconds
        self._nonces: OrderedDict[str, float] = OrderedDict()
        self._cap = nonce_cache
        self._bind = dict(principals or {})
        self._lock = RLock()

    def authenticate(self, request: Mapping[str, Any], *, now: float) -> str:
        auth = request.get("auth")
        if not isinstance(auth, Mapping):
            raise AuthenticationError("missing auth block")
        try:
            kid, principal, ts, nonce, mac = (auth["kid"], auth["principal"], auth["ts"], auth["nonce"], auth["mac"])
        except KeyError as exc:
            raise AuthenticationError(f"auth block missing {exc.args[0]}") from None
        if not all(isinstance(x, str) and x for x in (kid, principal, nonce, mac)):
            raise AuthenticationError("malformed auth block")
        if isinstance(ts, bool) or not isinstance(ts, (int, float)) or abs(float(ts) - now) > self.skew:
            raise AuthenticationError("timestamp outside the allowed skew window")
        if self._bind and self._bind.get(principal) != kid:
            raise AuthenticationError("principal is not bound to this key id")
        try:
            key = self.provider.get(kid)
        except (AuthenticationError, SecurityDependencyError):
            raise
        except Exception as exc:  # provider outage of any shape fails closed
            raise SecurityDependencyError("key provider failure") from exc
        expected = sign(key, request, kid=kid, principal=principal, ts=ts, nonce=nonce)["mac"]
        if not hmac.compare_digest(expected, mac):
            raise AuthenticationError("bad signature")
        with self._lock:
            tag = f"{kid}:{nonce}"
            if tag in self._nonces:
                raise AuthenticationError("replayed nonce")
            while len(self._nonces) >= self._cap:
                oldest_tag, oldest_ts = next(iter(self._nonces.items()))
                if now - oldest_ts <= self.skew:
                    # evicting a nonce still inside the window would re-open replay
                    raise SecurityDependencyError("nonce cache saturated inside the skew window")
                self._nonces.popitem(last=False)
            self._nonces[tag] = float(ts)
        return principal


@dataclass(frozen=True)
class Grant:
    principal: str
    tenant: str
    queue: str          # exact queue name or "*" for every queue of the tenant
    actions: frozenset[str]

    def __post_init__(self) -> None:
        bad = set(self.actions) - ACTIONS
        if bad:
            raise ValueError(f"unknown actions {sorted(bad)}")
        if self.tenant in ("", "*"):
            raise ValueError("grants are always scoped to one tenant")


class Authorizer:
    def __init__(self, grants: Iterable[Grant] = ()) -> None:
        self._grants = list(grants)

    def check(self, principal: str, tenant: str, queue: str, action: str) -> None:
        if action not in ACTIONS:
            raise AuthorizationError(f"unknown action {action!r}")
        for g in self._grants:
            if g.principal == principal and g.tenant == tenant and g.queue in ("*", queue) and action in g.actions:
                return
        raise AuthorizationError(f"{principal!r} may not {action} on {tenant}/{queue}")


class AuditLog:
    """Append-only hash-chained audit log (JSON lines)."""

    GENESIS = "0" * 64

    def __init__(self, path: str | os.PathLike, *, fsync: bool = True) -> None:
        self.path = Path(path)
        self.fsync = fsync
        self._lock = RLock()
        try:
            self._head, self._seq = self._scan()
        except (OSError, ValueError, KeyError) as exc:
            # An unreadable or unparsable sink is a security-dependency outage: fail closed.
            raise SecurityDependencyError("audit sink unreadable at open") from exc

    def _scan(self) -> tuple[str, int]:
        head, seq = self.GENESIS, 0
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    head, seq = rec["hash"], rec["seq"]
        return head, seq

    def append(self, event: str, **fields: Any) -> str:
        for k, v in fields.items():
            if k in ("key", "mac", "lease_token", "payload"):
                raise ValueError(f"audit field {k!r} would record secret or tenant payload material")
        with self._lock:
            rec = {"seq": self._seq + 1, "prev": self._head, "event": event, "fields": fields}
            rec["hash"] = hashlib.sha256(canonical(rec)).hexdigest()
            try:
                self.path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
                    fh.flush()
                    if self.fsync:
                        os.fsync(fh.fileno())
            except OSError as exc:
                raise SecurityDependencyError("audit sink unavailable") from exc
            self._head, self._seq = rec["hash"], rec["seq"]
            return rec["hash"]

    def head(self) -> dict[str, Any]:
        with self._lock:
            return {"seq": self._seq, "hash": self._head}

    def verify(self, *, anchored_head: Mapping[str, Any] | None = None) -> tuple[bool, str]:
        prev, seq = self.GENESIS, 0
        seen: dict[int, str] = {0: self.GENESIS}
        text = self.path.read_text(encoding="utf-8") if self.path.exists() else ""
        for n, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                return False, f"line {n}: not JSON"
            if not isinstance(rec, dict):
                return False, f"line {n}: not an audit record"
            body = {k: rec[k] for k in ("seq", "prev", "event", "fields") if k in rec}
            if rec.get("prev") != prev or rec.get("seq") != seq + 1:
                return False, f"line {n}: chain break"
            if hashlib.sha256(canonical(body)).hexdigest() != rec.get("hash"):
                return False, f"line {n}: hash mismatch"
            prev, seq = rec["hash"], rec["seq"]
            seen[seq] = prev
        if anchored_head is not None:
            aseq, ahash = anchored_head.get("seq"), anchored_head.get("hash")
            if isinstance(aseq, bool) or not isinstance(aseq, int) or not isinstance(ahash, str):
                return False, "malformed external anchor"
            if seen.get(aseq) != ahash:
                return False, "tail truncated or rewritten relative to the external anchor"
        return True, f"{seq} records"
