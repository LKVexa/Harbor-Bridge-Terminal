"""Boundary identity and capability enforcement for PLN-05.

Credentials are compact HMAC tokens ``v1.<kid>.<payload>.<mac>`` issued by the
identity issuer (tests use :func:`Issuer.mint`).  Verification is local, so an
issuer outage degrades to *bounded fail-static*: already-issued tokens remain
valid until their own expiry and never longer than the actor class allows; no
new authority is created during an outage.

Authorization is default-deny against ``security/capabilities.json``:
a token's capabilities must be a subset of its actor class, the action must be
among them, and the resource tenant/site must fall inside the token scope.
Control/administrative actions are *single-use*: their token nonce is consumed
on first use, so a captured control request cannot be replayed.
"""
from __future__ import annotations

import base64
from collections import OrderedDict
from dataclasses import dataclass
import json
import pathlib
import secrets

from .errors import PlaneError
from .keys import KeyRing

POLICY_PATH = pathlib.Path(__file__).resolve().parent / "security" / "capabilities.json"
POLICY = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
POLICY_VERSION = POLICY["version"]
_SINGLE_USE = frozenset(POLICY["single_use_actions"])
_MAX_TOKEN = 2048


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass(frozen=True)
class Principal:
    sub: str
    actor_class: str
    tenant: str
    sites: tuple[str, ...]
    caps: frozenset
    source: str | None
    nonce: str
    exp: float
    ticket: str | None = None

    @property
    def break_glass(self) -> bool:
        return bool(POLICY["actor_classes"][self.actor_class].get("break_glass"))


class Issuer:
    """Token issuer (the identity provider's role; used by tests and tooling)."""

    def __init__(self, ring: KeyRing) -> None:
        self.ring = ring

    def mint(self, *, sub: str, actor_class: str, tenant: str, sites=("*",), caps=None,
             source: str | None = None, now: float, lifetime: float = 300.0,
             ticket: str | None = None, iat: float | None = None) -> str:
        cls = POLICY["actor_classes"][actor_class]
        body = {
            "sub": sub, "cls": actor_class, "ten": tenant, "sites": list(sites),
            "caps": sorted(caps if caps is not None else cls["capabilities"]),
            "src": source, "iat": now if iat is None else iat, "exp": now + lifetime,
            "nonce": secrets.token_hex(12), "tkt": ticket,
        }
        payload = _b64e(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
        kid, mac = self.ring.sign(f"v1.{payload}".encode(), now)
        return f"v1.{kid}.{payload}.{mac}"


class Authenticator:
    NONCE_CAPACITY = 10000

    def __init__(self, ring: KeyRing) -> None:
        self.ring = ring
        self._nonces: OrderedDict[str, float] = OrderedDict()
        self.skew = float(POLICY["max_clock_skew_s"])

    def authenticate(self, token, now: float) -> Principal:
        if not isinstance(token, str) or len(token) > _MAX_TOKEN or token.count(".") != 3:
            raise PlaneError("E_AUTHN_FAILED", "malformed credential")
        ver, kid, payload, mac = token.split(".")
        if ver != "v1":
            raise PlaneError("E_AUTHN_FAILED", "unsupported credential version")
        self.ring.verify(kid, f"v1.{payload}".encode(), mac, now)
        try:
            body = json.loads(_b64d(payload))
            cls_name = body["cls"]
            cls = POLICY["actor_classes"][cls_name]
            iat, exp = float(body["iat"]), float(body["exp"])
            caps = frozenset(body["caps"])
            sites = tuple(body["sites"])
            tenant, sub, nonce = str(body["ten"]), str(body["sub"]), str(body["nonce"])
        except (ValueError, KeyError, TypeError):
            raise PlaneError("E_AUTHN_FAILED", "malformed credential body") from None
        if iat > now + self.skew:
            raise PlaneError("E_AUTHN_FAILED", "credential issued in the future")
        if now >= exp:
            raise PlaneError("E_AUTHN_EXPIRED", "credential expired")
        if exp - iat > cls["max_lifetime_s"]:
            raise PlaneError("E_AUTHN_FAILED", "credential lifetime exceeds actor-class maximum")
        if not caps <= set(cls["capabilities"]):
            raise PlaneError("E_AUTHORITY_ESCALATION", "credential claims capabilities beyond its actor class")
        if tenant == "*" and cls.get("tenant_scope") != "any":
            raise PlaneError("E_AUTHORITY_ESCALATION", "wildcard tenant not permitted for actor class")
        if cls.get("requires_ticket") and not body.get("tkt"):
            raise PlaneError("E_AUTHN_FAILED", "break-glass credential requires a ticket reference")
        if cls.get("requires_source_binding") and not body.get("src"):
            raise PlaneError("E_AUTHN_FAILED", "reporter credential requires a source binding")
        return Principal(sub, cls_name, tenant, sites, caps, body.get("src"), nonce, exp, body.get("tkt"))

    def _consume(self, principal: Principal, now: float) -> None:
        if principal.nonce in self._nonces and self._nonces[principal.nonce] > now:
            raise PlaneError("E_AUTHN_REPLAY", "single-use credential already consumed")
        if len(self._nonces) >= self.NONCE_CAPACITY:
            # purge expired entries only when full (O(n) at capacity, O(1) otherwise)
            for n in [n for n, e in self._nonces.items() if e <= now]:
                del self._nonces[n]
            if len(self._nonces) >= self.NONCE_CAPACITY:
                # Bounded replay cache: fail closed rather than forget a live nonce.
                raise PlaneError("E_OVERLOADED", "replay cache full")
        self._nonces[principal.nonce] = principal.exp

    def authorize(self, principal: Principal, action: str, *, tenant: str, site: str,
                  now: float) -> None:
        if action not in POLICY["actions"]:
            raise PlaneError("E_AUTHZ_DENIED", "unknown action")
        if action not in principal.caps:
            raise PlaneError("E_AUTHZ_DENIED", "capability not granted", {"action": action})
        if principal.tenant != "*" and principal.tenant != tenant:
            raise PlaneError("E_AUTHZ_SCOPE", "tenant outside credential scope")
        if "*" not in principal.sites and site not in principal.sites:
            raise PlaneError("E_AUTHZ_SCOPE", "site outside credential scope")
        if action in _SINGLE_USE:
            self._consume(principal, now)
