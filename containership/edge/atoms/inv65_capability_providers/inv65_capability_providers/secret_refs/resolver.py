"""INV-55 secret resolver integration and rotation semantics (M09).

Links store only ``secret://`` references.  Resolution happens at call time
through a ``SecretBackend`` (the INV-55 adapter seam), is scoped to the caller's
identity, cached briefly with version pinning, and invalidated on rotation or
revocation.  Resolved values live in ``SecretValue`` whose repr/str redact, and
which can be zeroized.  Values never enter link records, logs, errors or audit.
"""
from __future__ import annotations

import re
import threading
import time
from typing import Protocol

from ..errors.mapping import ProviderFault
from ..identity.context import IdentityContext

REF_RE = re.compile(r"^secret://[a-z0-9][a-z0-9._/-]{0,250}$")


class SecretValue:
    __slots__ = ("_buf", "version")

    def __init__(self, value: bytes, version: int):
        self._buf = bytearray(value)
        self.version = version

    def reveal(self) -> bytes:
        if not self._buf and self.version < 0:
            raise ProviderFault("PK_PROVIDER_SECRET_UNAVAILABLE", "secret zeroized")
        return bytes(self._buf)

    def zeroize(self) -> None:
        for i in range(len(self._buf)):
            self._buf[i] = 0
        self._buf = bytearray()
        self.version = -1

    def __repr__(self) -> str:
        return "SecretValue(<redacted>)"

    __str__ = __repr__


class SecretBackend(Protocol):
    def fetch(self, ref: str, scope: tuple[str, ...]) -> tuple[bytes, int]: ...


class InMemoryInv55Backend:
    """Fixture backend modelling INV-55: scope-bound refs, versions, rotation, revocation, outage."""

    def __init__(self):
        self._store: dict[tuple[str, tuple], list[bytes]] = {}
        self._revoked: set[tuple[str, tuple]] = set()
        self.available = True
        self.fetches = 0

    def put(self, ref: str, scope: tuple, value: bytes) -> int:
        self._store.setdefault((ref, scope), []).append(value)
        self._revoked.discard((ref, scope))
        return len(self._store[(ref, scope)])

    def revoke(self, ref: str, scope: tuple) -> None:
        self._revoked.add((ref, scope))

    def fetch(self, ref, scope):
        self.fetches += 1
        if not self.available:
            raise ConnectionError("inv55 unavailable")
        k = (ref, scope)
        if k in self._revoked or k not in self._store:
            raise KeyError(ref)
        vals = self._store[k]
        return vals[-1], len(vals)


class SecretResolver:
    def __init__(self, backend: SecretBackend, *, ttl_s: float = 30.0):
        self.backend = backend
        self.ttl_s = ttl_s
        self._cache: dict[tuple, tuple[SecretValue, float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def validate_ref(ref: object) -> str:
        if not isinstance(ref, str) or not REF_RE.match(ref) or ".." in ref:
            raise ProviderFault("PK_PROVIDER_INVALID_LINK", "invalid secret reference")
        return ref

    def resolve(self, ref: str, identity: IdentityContext, *, now: float | None = None) -> SecretValue:
        ref = self.validate_ref(ref)
        now = time.monotonic() if now is None else now
        key = (ref, identity.scope())
        with self._lock:
            hit = self._cache.get(key)
            if hit and hit[1] > now:
                return hit[0]
        try:
            value, version = self.backend.fetch(ref, identity.scope())
        except KeyError:
            self.invalidate(ref, identity)
            raise ProviderFault("PK_PROVIDER_SECRET_UNAVAILABLE", "secret reference not resolvable in caller scope") from None
        except Exception:
            # Fail closed: an outage never falls back to a stale cached secret past TTL.
            raise ProviderFault("PK_PROVIDER_SECRET_UNAVAILABLE", "secret backend unavailable") from None
        sv = SecretValue(value, version)
        with self._lock:
            old = self._cache.get(key)
            self._cache[key] = (sv, now + self.ttl_s)
        if old and old[0] is not sv:
            old[0].zeroize()
        return sv

    def invalidate(self, ref: str, identity: IdentityContext | None = None) -> int:
        """Rotation/revocation hook: drop and zeroize cached values for ref (optionally one scope)."""
        n = 0
        with self._lock:
            for k in [k for k in self._cache if k[0] == ref and (identity is None or k[1] == identity.scope())]:
                self._cache.pop(k)[0].zeroize()
                n += 1
        return n
