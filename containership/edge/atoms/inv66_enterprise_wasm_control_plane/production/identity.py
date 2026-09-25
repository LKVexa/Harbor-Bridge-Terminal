"""Authentication boundary and identity federation (MC-015, MC-031; C023, C044).

``admit()`` in 4.2.0 trusted a caller-supplied user string.  The production path now
requires an :class:`Principal` produced here, from one of:

* a signed bearer token (compact JWS, ``alg=EdDSA``) from a *trusted issuer* —
  the shape an OIDC IdP or workload-identity issuer emits.  Validation checks
  issuer, key id, signature, audience, ``nbf``/``exp`` with bounded skew, a
  maximum lifetime, a required ``jti`` and single use of that ``jti``
  (replay cache, bounded and expiring);
* an mTLS peer identity in SPIFFE form ``spiffe://<trust-domain>/ns/<tenant>/sa/<name>``
  (the TLS handshake itself belongs to the listener, see ``http_api.serve(tls=...)``).

Live OIDC discovery/JWKS fetch from an enterprise IdP is an adapter slot
(:class:`JwksSource`); only the static source ships.  Connecting a real IdP is
OPEN_EXTERNAL in the status ledger.
"""
from __future__ import annotations

import base64
import json
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from .errors import EcpError
from .keys import Signer, verify_sig
from .util import now

_KIND = frozenset({"user", "service", "workload"})
_SPIFFE = re.compile(r"^spiffe://([a-z0-9.\-]{1,255})/ns/([A-Za-z0-9_.\-]{1,128})/sa/([A-Za-z0-9_.\-]{1,128})$")


@dataclass(frozen=True)
class Principal:
    subject: str
    kind: str
    issuer: str
    org: str
    tenant: str | None = None
    groups: tuple[str, ...] = ()
    auth_method: str = "token"
    token_id: str | None = None
    expires_at: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def ref(self) -> dict[str, Any]:
        """Audit-safe reference (no token material)."""
        return {"subject": self.subject, "kind": self.kind, "issuer": self.issuer, "org": self.org,
                "tenant": self.tenant, "groups": list(self.groups), "auth_method": self.auth_method,
                "token_id": self.token_id}


class JwksSource(Protocol):
    def key(self, issuer: str, kid: str) -> str | None: ...


class StaticJwks:
    def __init__(self, keys: dict[str, dict[str, str]]):
        self._keys = {iss: dict(k) for iss, k in keys.items()}

    def key(self, issuer: str, kid: str) -> str | None:
        return self._keys.get(issuer, {}).get(kid)

    def issuers(self) -> list[str]:
        return sorted(self._keys)


def _b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def mint_token(signer: Signer, claims: dict[str, Any]) -> str:
    """Issue a token (test/bootstrap issuer; production tokens come from the IdP)."""
    header = {"alg": "EdDSA", "typ": "JWT", "kid": signer.key_id}
    h = _b64u(json.dumps(header, separators=(",", ":"), sort_keys=True).encode())
    c = _b64u(json.dumps(claims, separators=(",", ":"), sort_keys=True).encode())
    sig = base64.b64decode(signer.sign(f"{h}.{c}".encode()))
    return f"{h}.{c}.{_b64u(sig)}"


class ReplayCache:
    def __init__(self, capacity: int = 100_000):
        self.capacity = capacity
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def check_and_add(self, jti: str, exp: float, t: float) -> bool:
        with self._lock:
            if len(self._seen) >= self.capacity:
                for k in [k for k, e in self._seen.items() if e < t]:
                    del self._seen[k]
                if len(self._seen) >= self.capacity:
                    return False  # fail closed rather than forget a live jti
            if jti in self._seen and self._seen[jti] >= t:
                return False
            self._seen[jti] = exp
            return True


class Authenticator:
    def __init__(self, jwks: JwksSource, *, audience: str, trust_domain: str | None = None,
                 skew_s: float = 30.0, max_lifetime_s: float = 3600.0, single_use: bool = False,
                 clock: Callable[[], float] = now, replay: ReplayCache | None = None,
                 spiffe_org: str = "estate"):
        self.jwks = jwks
        self.audience = audience
        self.trust_domain = trust_domain
        self.skew = skew_s
        self.max_lifetime = max_lifetime_s
        self.single_use = single_use
        self.clock = clock
        self.replay = replay or ReplayCache()
        self.spiffe_org = spiffe_org

    def _fail(self, why: str) -> EcpError:
        return EcpError("ECP_UNAUTHENTICATED", "credential rejected", reason=why)

    def authenticate_token(self, token: Any) -> Principal:
        if not isinstance(token, str) or len(token) > 8192 or token.count(".") != 2:
            raise self._fail("malformed")
        h64, c64, s64 = token.split(".")
        try:
            header = json.loads(_unb64u(h64))
            claims = json.loads(_unb64u(c64))
            sig = _unb64u(s64)
        except (ValueError, TypeError):
            raise self._fail("undecodable") from None
        if not isinstance(header, dict) or not isinstance(claims, dict):
            raise self._fail("malformed")
        if header.get("alg") != "EdDSA":  # no alg=none, no HS/RS confusion
            raise self._fail("alg")
        iss, kid = claims.get("iss"), header.get("kid")
        if not isinstance(iss, str) or not isinstance(kid, str):
            raise self._fail("iss/kid")
        pub = self.jwks.key(iss, kid)
        if pub is None:
            raise self._fail("untrusted issuer or key")
        if not verify_sig(pub, base64.b64encode(sig).decode(), f"{h64}.{c64}".encode()):
            raise self._fail("signature")
        aud = claims.get("aud")
        if not (aud == self.audience or (isinstance(aud, list) and self.audience in aud)):
            raise self._fail("audience")
        t = self.clock()
        raw = (claims.get("exp"), claims.get("nbf", claims.get("iat")), claims.get("iat"))
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in raw):
            raise self._fail("time claims")
        exp, nbf, iat = (float(x) for x in raw)  # type: ignore[arg-type]
        if t > exp + self.skew or t + self.skew < nbf:
            raise self._fail("expired or not yet valid")
        if exp - iat > self.max_lifetime:
            raise self._fail("lifetime exceeds policy")
        jti = claims.get("jti")
        if not isinstance(jti, str) or not jti:
            raise self._fail("jti")
        if self.single_use and not self.replay.check_and_add(f"{iss}|{jti}", exp + self.skew, t):
            raise EcpError("ECP_REPLAY_DETECTED", "token already used", reason="jti replay")
        kind = claims.get("kind", "user")
        sub, org = claims.get("sub"), claims.get("org")
        if kind not in _KIND or not isinstance(sub, str) or not sub or not isinstance(org, str) or not org:
            raise self._fail("subject")
        groups = claims.get("groups", [])
        if not isinstance(groups, list) or not all(isinstance(g, str) for g in groups) or len(groups) > 256:
            raise self._fail("groups")
        tenant = claims.get("tenant")
        if tenant is not None and not isinstance(tenant, str):
            raise self._fail("tenant")
        return Principal(subject=sub, kind=kind, issuer=iss, org=org, tenant=tenant, groups=tuple(sorted(groups)),
                         auth_method="token", token_id=jti, expires_at=float(exp))

    def authenticate_peer(self, spiffe_id: Any) -> Principal:
        """Map a verified mTLS peer SAN to a workload principal (listener must have verified the chain)."""
        m = _SPIFFE.match(spiffe_id) if isinstance(spiffe_id, str) else None
        if m and (set(m.group(2)) <= {"."} or set(m.group(3)) <= {"."}):
            m = None  # "." / ".." segments would alias other tenants
        if not m or (self.trust_domain and m.group(1) != self.trust_domain):
            raise self._fail("peer identity")
        return Principal(subject=f"{m.group(2)}/{m.group(3)}", kind="workload", issuer=f"spiffe://{m.group(1)}",
                         org=self.spiffe_org, tenant=m.group(2), auth_method="mtls")
