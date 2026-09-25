# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""Authentication, authorization and root-capability provenance (GAP-016, GAP-017, GAP-028).

* **Principals** authenticate each request with HMAC-SHA256 over the canonical
  request, a timestamp and a single-use nonce (replay-protected, bounded skew).
* **Authorization** is a static, deny-by-default policy: principal → allowed
  actions × tenants. Only principals holding ``mint`` may create root capabilities.
* **Provenance**: every root capability is minted by the ``MintingAuthority``,
  which signs a grant binding tenant, bounds, permissions, backend enforcement and
  a unique grant id. Handles whose grant does not verify are refused.
* **Peer/artifact attestation** (``verify_attestation``) accepts an attestation
  document only when its MAC verifies under a registered trust anchor, its
  measurement is on the allow-list, and it is fresh. Hardware-rooted attestation
  (Morello/CCA, TPM quotes) plugs in as another anchor type — not bundled.

Keys come from the secret provider (``secrets.py``), never from config values.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field

from .errors import ProvenanceInvalid, Replay, TenantMismatch, Unauthenticated, Unauthorized

ACTIONS = frozenset({"mint", "derive", "access", "invalidate", "describe", "admin"})


def _canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def sign(key: bytes, payload: dict) -> str:
    return hmac.new(key, _canon(payload), hashlib.sha256).hexdigest()


class NonceCache:
    def __init__(self, capacity: int, window_s: float):
        self.capacity, self.window = capacity, window_s
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()

    def use(self, nonce: str, now: float) -> None:
        with self._lock:
            while self._seen and (next(iter(self._seen.values())) < now - self.window
                                  or len(self._seen) >= self.capacity):
                self._seen.popitem(last=False)
            if nonce in self._seen:
                raise Replay("nonce already used")
            self._seen[nonce] = now


@dataclass
class Principal:
    name: str
    key: bytes
    actions: frozenset
    tenants: frozenset  # "*" means all tenants (admin only)


@dataclass
class Authenticator:
    principals: dict = field(default_factory=dict)
    max_skew_s: float = 30.0
    nonce_capacity: int = 262_144
    clock: object = time.time

    def __post_init__(self):
        self._nonces = NonceCache(self.nonce_capacity, 2 * self.max_skew_s)

    def register(self, name: str, key: bytes, actions, tenants) -> None:
        actions = frozenset(actions)
        if not actions <= ACTIONS:
            raise ValueError(f"unknown actions {sorted(actions - ACTIONS)}")
        if len(key) < 32:
            raise ValueError("principal keys must be at least 256 bits")
        self.principals[name] = Principal(name, key, actions, frozenset(tenants))

    @staticmethod
    def request_mac(key: bytes, principal: str, action: str, body: dict, ts: float, nonce: str) -> str:
        return sign(key, {"p": principal, "a": action, "b": body, "ts": ts, "n": nonce})

    def authenticate(self, *, principal: str, action: str, body: dict, ts: float, nonce: str, mac: str) -> Principal:
        p = self.principals.get(principal)
        # Constant-time compare against a dummy key when the principal is unknown.
        key = p.key if p else b"\0" * 32
        good = self.request_mac(key, principal, action, body, ts, nonce)
        if not hmac.compare_digest(good, mac or "") or p is None:
            raise Unauthenticated("request authentication failed")
        now = self.clock()
        if abs(now - ts) > self.max_skew_s:
            raise Unauthenticated("request timestamp outside the permitted skew")
        self._nonces.use(f"{principal}:{nonce}", now)
        return p

    @staticmethod
    def authorize(p: Principal, action: str, tenant: str) -> None:
        if action not in p.actions:
            raise Unauthorized(f"principal {p.name!r} may not {action}")
        if "*" not in p.tenants and tenant not in p.tenants:
            raise Unauthorized(f"principal {p.name!r} has no authority over tenant {tenant!r}")


class MintingAuthority:
    """The only source of root capabilities. Grants are signed and bound to one tenant."""

    def __init__(self, key: bytes, *, clock=time.time):
        if len(key) < 32:
            raise ValueError("minting key must be at least 256 bits")
        self._key = key
        self.clock = clock

    def grant(self, *, tenant: str, base: int, length: int, permissions, enforcement: str, minted_by: str) -> dict:
        g = {"grant_id": uuid.uuid4().hex, "tenant": tenant, "base": base, "length": length,
             "permissions": sorted(permissions), "enforcement": enforcement, "minted_by": minted_by,
             "minted_at": round(self.clock(), 6)}
        return dict(g, sig=sign(self._key, g))

    def verify(self, grant: dict, *, tenant: str) -> None:
        body = {k: v for k, v in grant.items() if k != "sig"}
        if not hmac.compare_digest(sign(self._key, body), grant.get("sig", "")):
            raise ProvenanceInvalid("root grant signature invalid")
        if grant["tenant"] != tenant:
            raise TenantMismatch("capability belongs to a different tenant")


def verify_attestation(doc: dict, *, anchors: dict[str, bytes], allowed_measurements: set[str],
                       max_age_s: float, now: float) -> dict:
    """Verify a peer/node/artifact attestation document; fail closed on any doubt."""
    anchor = anchors.get(doc.get("anchor", ""))
    if anchor is None:
        raise Unauthenticated("attestation anchor unknown")
    body = {k: v for k, v in doc.items() if k != "sig"}
    if not hmac.compare_digest(sign(anchor, body), doc.get("sig", "")):
        raise Unauthenticated("attestation signature invalid")
    if doc.get("measurement") not in allowed_measurements:
        raise Unauthorized("attested measurement not on the allow-list")
    if not (0 <= now - float(doc.get("issued_at", -1e18)) <= max_age_s):
        raise Unauthenticated("attestation stale or from the future")
    return {"subject": doc.get("subject"), "measurement": doc["measurement"], "anchor": doc["anchor"]}
