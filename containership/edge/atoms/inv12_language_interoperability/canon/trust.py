"""MC-048 capability/authentication integration and MC-049 trust-service outage policy.

Component identity and capabilities are carried by a *capability token* minted
by the system trust layer (INV-45/SFI and the platform identity service), never
by interop configuration.  The reference token is::

    {"sub": "<component id>", "caps": ["interop.call:<interface>", ...],
     "exp": <unix seconds>, "kid": "<key id>", "mac": "<hmac-sha256 hex>"}

``CapabilityGate.authorize`` verifies MAC, key id, expiry (against *trusted*
time) and the requested capability before any lowering happens.

Outage policy (normative):

* Privileged control-plane actions (config activation, mapping-policy change)
  always FAIL CLOSED when any trust dependency is unavailable.
* Data-plane calls with a token verified *before* the outage may continue for
  ``grace_s`` seconds (health: DEGRADED); new or unverified tokens fail closed.
* If trusted time is unavailable, expiry cannot be evaluated: FAIL CLOSED
  (``PK_INTEROP_TRUST_UNAVAILABLE``) for everything.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading

from .errors import AuthError, InteropError


def _unavailable(what):
    return InteropError(f"{what} unavailable; failing closed", code="PK_INTEROP_TRUST_UNAVAILABLE")


def mint(sub: str, caps: list, exp: int, kid: str, key: bytes) -> dict:
    body = {"sub": sub, "caps": sorted(caps), "exp": int(exp), "kid": kid}
    mac = hmac.new(key, json.dumps(body, sort_keys=True).encode(), hashlib.sha256).hexdigest()
    return dict(body, mac=mac)


class CapabilityGate:
    def __init__(self, keys: dict, clock, *, grace_s: int = 0, health=None, audit=None):
        self._keys = dict(keys)
        self.clock = clock                 # callable -> trusted unix seconds, or raises
        self.grace_s = grace_s
        self.health = health
        self.audit = audit
        self.trust_up = True
        self._verified: dict = {}          # mac -> last successful verification time
        self._revoked_kids: set = set()
        self._revoked_subjects: set = set()
        self._lock = threading.Lock()

    def rotate(self, kid: str, key: bytes, *, retire: str | None = None):
        """Add a new verification key; optionally retire (revoke) an old key id."""
        if type(key) is not bytes or len(key) < 32:
            raise AuthError("rotation key must be >= 32 bytes")
        with self._lock:
            self._keys[kid] = key
            if retire is not None:
                self._keys.pop(retire, None)
                self._revoked_kids.add(retire)
                self._verified.clear()          # cached verifications under the old key are void
        if self.audit:
            self.audit.emit("mapping_policy_change", "trust", action="key_rotated", kid=kid, retired=retire or "")

    def revoke_subject(self, sub: str):
        with self._lock:
            self._revoked_subjects.add(sub)
            self._verified.clear()

    def set_trust_available(self, up: bool):
        self.trust_up = up
        if self.health:
            self.health.set("trust_unavailable", False)
            self.health.set("dependency_slow", not up, "trust service outage")

    def _now(self):
        try:
            t = self.clock()
        except Exception:  # noqa: BLE001
            if self.health:
                self.health.set("trust_unavailable", True, "trusted time")
            raise _unavailable("trusted time") from None
        if type(t) not in (int, float):
            raise _unavailable("trusted time")
        return t

    def authorize(self, token: object, capability: str, *, privileged: bool = False) -> str:
        now = self._now()
        if type(token) is not dict or set(token) != {"sub", "caps", "exp", "kid", "mac"}:
            raise AuthError("malformed capability token")
        if token["kid"] in self._revoked_kids or token["sub"] in self._revoked_subjects:
            self._deny(token, "revoked key or subject")
        if not self.trust_up:
            if privileged:
                raise _unavailable("trust service")
            with self._lock:
                seen = self._verified.get(token["mac"])
            if seen is None or now - seen > self.grace_s or now >= token["exp"]:
                raise _unavailable("trust service")
            if capability not in token["caps"]:
                raise AuthError("capability not granted")
            return token["sub"]
        key = self._keys.get(token["kid"])
        body = {k: token[k] for k in ("sub", "caps", "exp", "kid")}
        if key is None:
            self._deny(token, "unknown key id")
        good = hmac.new(key, json.dumps(body, sort_keys=True).encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(good, str(token["mac"])):
            self._deny(token, "bad token MAC")
        if now >= token["exp"]:
            self._deny(token, "token expired")
        if capability not in token["caps"]:
            self._deny(token, "capability not granted")
        with self._lock:
            self._verified[token["mac"]] = now
        return token["sub"]

    def _deny(self, token, why):
        if self.audit:
            self.audit.emit("trust_check_failed", str(token.get("sub", "?")), reason=why)
        raise AuthError(why)
