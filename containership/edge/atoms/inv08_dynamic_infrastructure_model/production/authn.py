"""Component 20 - authentication boundary (symmetric, NON-PRODUCTION trust root).

Token format ``PK_DYN_IDENT/1``: ``{"claims": {...}, "sig": TrustRoot.sign(...)}``
claims = {typ, iss, sub, role, tenant?, jti, iat, nbf, exp, kid}.
* role in ROLES = controller | node | provider.
* Controller identities are issued only with the admin bootstrap secret;
  node identities only against a single-use join token; provider identities
  only by a controller-authenticated request.
* Verification checks: signature under the authority keyring, typ, role,
  nbf <= now < exp (with ``leeway``), jti/sub/kid not revoked.
* Rotation: ``rotate(new_kid, key, overlap)`` makes the new kid the signer;
  tokens under the old kid verify until ``overlap`` elapses, then the old kid
  is revoked in the TrustRoot.
* Mutual handshake: each side proves possession of a per-identity key
  (derived as the authority MAC over the jti, handed to the holder at
  issuance) by MACing the transcript (both tokens + both nonces).  Nonces are
  single-use within ``nonce_ttl``.

LIMITATION: HMAC is symmetric; the verifier shares the authority keyring.
An asymmetric PKI (X.509/SPIFFE) with KMS/HSM-held roots is required for
production and is not available in the stdlib.
"""
from __future__ import annotations

import hashlib
import hmac

from .core import TrustRoot, canonical
from .errors_catalog import error

ROLES = ("controller", "node", "provider")
TYP = "PK_DYN_IDENT/1"


class Authority:
    def __init__(self, trust: TrustRoot, kid: str, *, clock, admin_secret: bytes,
                 issuer: str = "inv08-authority", leeway: float = 5.0) -> None:
        self.trust, self.kid, self.clock, self.issuer, self.leeway = trust, kid, clock, issuer, leeway
        self._admin = hashlib.sha256(admin_secret).digest()
        self._join: dict[str, str | None] = {}      # sha256(join token) -> tenant
        self._revoked_jti: set[str] = set()
        self._revoked_sub: set[str] = set()
        self._retiring: dict[str, float] = {}       # kid -> retire at
        self._n = 0
        self._nonces: dict[str, float] = {}

    # ---------------------------------------------------------- issuance
    def _issue(self, sub: str, role: str, ttl: float, tenant: str | None) -> dict:
        if role not in ROLES or not sub or ttl <= 0:
            raise error("INV08.AUTHN.INVALID_TOKEN", "bad issuance request")
        self._n += 1
        now = self.clock()
        claims = {"typ": TYP, "iss": self.issuer, "sub": sub, "role": role, "jti": f"{self.kid}-{self._n}",
                  "iat": now, "nbf": now, "exp": now + ttl, "kid": self.kid}
        if tenant:
            claims["tenant"] = tenant
        tok = {"claims": claims, "sig": self.trust.sign(self.kid, claims)}
        return {"token": tok, "pop_key": self._pop(claims)}

    def _pop(self, claims: dict) -> bytes:
        return bytes.fromhex(self.trust.sign(claims["kid"], {"pop": claims["jti"]})["mac"])

    def issue_controller(self, sub: str, admin_secret: bytes, ttl: float = 3600.0) -> dict:
        if not hmac.compare_digest(hashlib.sha256(admin_secret).digest(), self._admin):
            raise error("INV08.AUTHN.BAD_BOOTSTRAP", "admin secret rejected")
        return self._issue(sub, "controller", ttl, None)

    def new_join_token(self, controller_token: dict, rng, tenant: str | None = None) -> str:
        self.verify(controller_token, role="controller")
        jt = "%032x" % rng.getrandbits(128)
        self._join[hashlib.sha256(jt.encode()).hexdigest()] = tenant
        return jt

    def issue_node(self, sub: str, join_token: str, ttl: float = 900.0) -> dict:
        h = hashlib.sha256(join_token.encode()).hexdigest()
        if h not in self._join:
            raise error("INV08.AUTHN.BAD_BOOTSTRAP", "join token unknown or used")
        tenant = self._join.pop(h)                  # single use
        return self._issue(sub, "node", ttl, tenant)

    def issue_provider(self, sub: str, controller_token: dict, ttl: float = 900.0) -> dict:
        self.verify(controller_token, role="controller")
        return self._issue(sub, "provider", ttl, None)

    # ---------------------------------------------------------- verification
    def verify(self, token: dict, *, role: str | None = None) -> dict:
        try:
            claims, sig = token["claims"], token["sig"]
            ok = self.trust.verify(claims, sig) and sig.get("kid") == claims.get("kid")
        except (KeyError, TypeError):
            ok = False
        if not ok or claims.get("typ") != TYP or claims.get("iss") != self.issuer:
            raise error("INV08.AUTHN.INVALID_TOKEN", "signature/format rejected")
        now = self.clock()
        self._retire(now)
        if claims["jti"] in self._revoked_jti or claims["sub"] in self._revoked_sub:
            raise error("INV08.AUTHN.REVOKED", f"{claims['sub']} revoked")
        if not self.trust.verify(claims, sig):       # kid may have been retired just now
            raise error("INV08.AUTHN.REVOKED", f"key {claims['kid']} retired")
        if now + self.leeway < claims["nbf"]:
            raise error("INV08.AUTHN.INVALID_TOKEN", "not yet valid")
        if now >= claims["exp"] + self.leeway:
            raise error("INV08.AUTHN.EXPIRED", f"{claims['sub']} expired")
        if role is not None and claims["role"] != role:
            raise error("INV08.AUTHN.INVALID_TOKEN", f"role {claims['role']} != {role}")
        return claims

    # ---------------------------------------------------------- rotation / revocation
    def rotate(self, new_kid: str, key: bytes, overlap: float) -> None:
        self.trust.add(new_kid, key)
        self._retiring[self.kid] = self.clock() + overlap
        self.kid = new_kid

    def _retire(self, now: float) -> None:
        for kid, at in list(self._retiring.items()):
            if now >= at:
                self.trust.revoke(kid)
                del self._retiring[kid]

    def revoke_token(self, jti: str) -> None:
        self._revoked_jti.add(jti)

    def compromise(self, sub: str) -> None:
        """Compromised credential: revoke every token for the subject."""
        self._revoked_sub.add(sub)

    # ---------------------------------------------------------- mutual handshake
    def _fresh_nonce(self, nonce: str, ttl: float) -> None:
        now = self.clock()
        for n, t in list(self._nonces.items()):
            if now - t > ttl:
                del self._nonces[n]
        if not nonce or len(nonce) < 16 or nonce in self._nonces:
            raise error("INV08.AUTHN.REPLAY", "nonce reused or too short")
        self._nonces[nonce] = now


def _transcript(tok_a: dict, nonce_a: str, tok_b: dict, nonce_b: str) -> bytes:
    return canonical({"a": tok_a["claims"]["jti"], "na": nonce_a, "b": tok_b["claims"]["jti"], "nb": nonce_b})


def prove(pop_key: bytes, tok_a: dict, nonce_a: str, tok_b: dict, nonce_b: str, side: str) -> str:
    return hmac.new(pop_key, side.encode() + _transcript(tok_a, nonce_a, tok_b, nonce_b), hashlib.sha256).hexdigest()


def mutual_handshake(auth: Authority, a: dict, b: dict, rng, *, roles=("controller", "node"),
                     nonce_ttl: float = 300.0, tamper: str | None = None) -> dict:
    """Run both legs.  ``a``/``b`` are issuance dicts {token, pop_key}.
    Returns the established session descriptor or raises."""
    na, nb = "%032x" % rng.getrandbits(128), "%032x" % rng.getrandbits(128)
    auth._fresh_nonce(na, nonce_ttl)
    ca = auth.verify(a["token"], role=roles[0])          # B verifies A's credential
    auth._fresh_nonce(nb, nonce_ttl)
    cb = auth.verify(b["token"], role=roles[1])          # A verifies B's credential
    pb = prove(b["pop_key"], a["token"], na, b["token"], nb, "B")
    pa = prove(a["pop_key"], a["token"], na, b["token"], nb, "A")
    if tamper == "B":
        pb = "0" * 64
    for side, tok, proof in (("B", b["token"], pb), ("A", a["token"], pa)):
        want = prove(auth._pop(tok["claims"]), a["token"], na, b["token"], nb, side)
        if not hmac.compare_digest(want, proof):
            raise error("INV08.AUTHN.INVALID_TOKEN", f"proof of possession failed for {side}")
    return {"a": ca["sub"], "b": cb["sub"], "nonces": (na, nb)}
