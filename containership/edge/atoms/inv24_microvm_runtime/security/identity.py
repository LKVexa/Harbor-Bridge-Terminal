"""Identity/authentication and capability authorization (MC-021, MC-022).

Tokens are compact ``base64url(json).kid.hmac`` envelopes signed by the
control-plane keyring.  Verification is fail closed: missing token, unknown
or retired key, bad MAC, wrong audience, expiry, not-yet-valid, replayed
nonce, or capability/tenant mismatch are all rejected with stable codes.
Production deployments are expected to swap HMAC for mTLS/SPIFFE or
attested asymmetric identity; that swap is tracked as MC-021 BLOCKED.
"""
from __future__ import annotations

import base64
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Final

from ..errors import Inv24Error
from .keys import Keyring

AUDIENCE: Final[str] = "inv24-microvm-runtime"
MAX_TOKEN_TTL_S: Final[int] = 900
MAX_TOKEN_BYTES: Final[int] = 4096
CAPABILITIES: Final[frozenset[str]] = frozenset({
    "microvm:create", "microvm:boot", "microvm:pause", "microvm:stop",
    "microvm:snapshot", "microvm:restore", "operator:quarantine", "operator:freeze",
    "operator:config", "diagnostics:read",
})


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    tenant: str | None
    capabilities: frozenset[str]
    kind: str  # "workload" | "node" | "operator" | "control-plane"
    expires_at: float
    nonce: str

    def require(self, capability: str, *, tenant: str | None = None) -> None:
        if capability not in self.capabilities:
            raise Inv24Error("UNAUTHORIZED", f"capability {capability} not granted")
        if tenant is not None and self.kind != "operator" and self.tenant != tenant:
            raise Inv24Error("TENANT_MISMATCH", "principal tenant does not match resource tenant")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


class TokenAuthority:
    def __init__(self, keyring: Keyring, *, clock=time.time, replay_window: int = 100_000) -> None:
        self.keyring, self.clock = keyring, clock
        self._seen: OrderedDict[str, float] = OrderedDict()
        self._lock = threading.Lock()
        self._window = replay_window

    def issue(self, subject: str, kind: str, capabilities: set[str], *, tenant: str | None = None,
              ttl_s: int = 300, nonce: str | None = None) -> str:
        import secrets
        unknown = set(capabilities) - CAPABILITIES
        if unknown:
            raise Inv24Error("UNAUTHORIZED", f"unknown capabilities {sorted(unknown)}")
        if not 0 < ttl_s <= MAX_TOKEN_TTL_S:
            raise Inv24Error("UNAUTHORIZED", "ttl out of range")
        now = self.clock()
        claims = {"sub": subject, "kind": kind, "ten": tenant, "cap": sorted(capabilities), "aud": AUDIENCE,
                  "iat": int(now), "nbf": int(now), "exp": int(now + ttl_s), "nonce": nonce or secrets.token_hex(12)}
        body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        kid, mac = self.keyring.sign(body.encode())
        return f"{body}.{kid}.{mac}"

    def verify(self, token: object, *, consume_nonce: bool = True) -> Principal:
        if not isinstance(token, str) or not token:
            raise Inv24Error("UNAUTHENTICATED", "missing token")
        if len(token) > MAX_TOKEN_BYTES or token.count(".") != 2:
            raise Inv24Error("UNAUTHENTICATED", "malformed token")
        body, kid, mac = token.split(".")
        if not self.keyring.verify(kid, body.encode(), mac):
            raise Inv24Error("UNAUTHENTICATED", "signature invalid or key retired")
        try:
            c = json.loads(_unb64(body))
        except ValueError:
            raise Inv24Error("UNAUTHENTICATED", "malformed claims") from None
        now = self.clock()
        if c.get("aud") != AUDIENCE:
            raise Inv24Error("UNAUTHENTICATED", "audience mismatch")
        if not (c.get("nbf", 1 << 62) - 5 <= now < c.get("exp", 0)):
            raise Inv24Error("UNAUTHENTICATED", "token expired or not yet valid")
        if c["exp"] - c["iat"] > MAX_TOKEN_TTL_S:
            raise Inv24Error("UNAUTHENTICATED", "token lifetime exceeds policy")
        caps = frozenset(c.get("cap", ()))
        if not caps <= CAPABILITIES:
            raise Inv24Error("UNAUTHORIZED", "token carries unknown capabilities")
        nonce = str(c.get("nonce", ""))
        if consume_nonce:
            with self._lock:
                for k in [k for k, exp in self._seen.items() if exp < now][:1024]:
                    del self._seen[k]
                if nonce in self._seen:
                    raise Inv24Error("REPLAY_DETECTED", "token nonce replayed")
                self._seen[nonce] = float(c["exp"])
                while len(self._seen) > self._window:
                    self._seen.popitem(last=False)
        return Principal(str(c["sub"]), c.get("ten"), caps, str(c["kind"]), float(c["exp"]), nonce)
