"""Asymmetric commit/tag signature verification (component 03).

Replaces the v4.2.0 HMAC stand-in with public-key trust:

* **PKED25519/1** -- an Ed25519 signature carried in the commit's standard
  ``gpgsig`` header (armored ``-----BEGIN PK ED25519 SIGNATURE-----``) over the
  commit object *without* that header, i.e. exactly the bytes git itself
  signs.  Verification is pure Python (``ed25519.py``, RFC 8032 vectors).
* **OpenPGP** -- ``git verify-commit --raw`` against an isolated keyring;
  only a ``VALIDSIG`` whose primary fingerprint is in the trust roots counts
  (``GOODSIG`` alone is not enough; ``EXPKEYSIG``/``REVKEYSIG``/``BADSIG``
  fail closed).

``TrustRoots`` (``PK_GITOPS_TRUST/1``) carries per key: algorithm, public key
or fingerprint, signer identity (the committer e-mail the key may sign as),
validity window, revocation time, and ref scopes.  Algorithm policy is an
allowlist; an unknown algorithm is ``Untrusted``.  Revocation applies to every
commit whose committer time is at/after ``revoked_at`` *and* -- because a
committer time is attacker-chosen -- to every verification after revocation
when ``revocation_mode`` is ``hard`` (the default).
"""
from __future__ import annotations

import base64
import fnmatch
import hashlib
import json
import re
from dataclasses import dataclass, field

from .fsutil import load_json, read_bytes, read_text  # noqa: F401
from . import ed25519
from .errors import Expired, Malformed, Revoked, Unsigned, Untrusted
from .gitrepo import CommitInfo

SCHEMA_ID = "PK_GITOPS_TRUST/1"
ARMOR_BEGIN = "-----BEGIN PK ED25519 SIGNATURE-----"
ARMOR_END = "-----END PK ED25519 SIGNATURE-----"
ALGORITHMS = ("ed25519", "openpgp")


@dataclass(frozen=True)
class TrustedKey:
    key_id: str
    algorithm: str
    identity: str
    public_key: bytes = b""
    fingerprint: str = ""
    not_before: int = 0
    not_after: int = 2**62
    revoked_at: int | None = None
    scopes: tuple[str, ...] = ("refs/heads/*", "refs/tags/*")
    purposes: tuple[str, ...] = ("commit",)


@dataclass
class TrustRoots:
    keys: dict[str, TrustedKey] = field(default_factory=dict)
    version: int = 1
    revocation_mode: str = "hard"
    allowed_algorithms: tuple[str, ...] = ("ed25519",)

    @classmethod
    def from_doc(cls, doc: dict) -> "TrustRoots":
        if not isinstance(doc, dict) or doc.get("schema") != SCHEMA_ID:
            raise Malformed("trust roots document has wrong schema")
        algs = tuple(doc.get("allowed_algorithms", ["ed25519"]))
        if any(a not in ALGORITHMS for a in algs):
            raise Malformed("unknown algorithm in allowed_algorithms")
        keys = {}
        for k in doc.get("keys", []):
            kid = k["key_id"]
            if kid in keys:
                raise Malformed("duplicate key_id in trust roots", key_id=kid)
            pub = bytes.fromhex(k.get("public_key", "")) if k.get("public_key") else b""
            if k["algorithm"] == "ed25519" and len(pub) != 32:
                raise Malformed("ed25519 public key must be 32 bytes", key_id=kid)
            keys[kid] = TrustedKey(kid, k["algorithm"], k["identity"], pub, k.get("fingerprint", "").upper(),
                                   int(k.get("not_before", 0)), int(k.get("not_after", 2**62)),
                                   k.get("revoked_at"), tuple(k.get("scopes", ["refs/heads/*", "refs/tags/*"])),
                                   tuple(k.get("purposes", ["commit"])))
        mode = doc.get("revocation_mode", "hard")
        if mode not in ("hard", "time_bounded"):
            raise Malformed("revocation_mode must be hard or time_bounded")
        return cls(keys, int(doc.get("version", 1)), mode, algs)

    @classmethod
    def load(cls, path: str, expected_sha256: str | None = None) -> "TrustRoots":
        data = read_bytes(path)
        if expected_sha256 and hashlib.sha256(data).hexdigest() != expected_sha256:
            raise Untrusted("trust roots file digest does not match the pinned digest")
        return cls.from_doc(json.loads(data))

    def digest(self) -> str:
        body = json.dumps(sorted((k.key_id, k.algorithm, k.identity, k.public_key.hex(), k.fingerprint,
                                  k.not_before, k.not_after, k.revoked_at, k.scopes, k.purposes)
                                 for k in self.keys.values()), sort_keys=True).encode()
        return hashlib.sha256(body).hexdigest()

    def revoke(self, key_id: str, at: int) -> None:
        k = self.keys[key_id]
        self.keys[key_id] = TrustedKey(**{**k.__dict__, "revoked_at": at})


@dataclass(frozen=True)
class Verdict:
    oid: str
    key_id: str
    algorithm: str
    identity: str
    trust_digest: str

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def armor(key_id: str, sig: bytes) -> str:
    body = base64.b64encode(json.dumps({"key_id": key_id, "sig": sig.hex(), "v": 1}, sort_keys=True).encode()).decode()
    return "\n".join([ARMOR_BEGIN] + [body[i:i + 64] for i in range(0, len(body), 64)] + [ARMOR_END])


def dearmor(text: str) -> tuple[str, bytes]:
    lines = [ln.strip() for ln in text.strip().splitlines()]
    if len(lines) < 3 or lines[0] != ARMOR_BEGIN or lines[-1] != ARMOR_END:
        raise Malformed("not a PK ED25519 signature block")
    try:
        doc = json.loads(base64.b64decode("".join(lines[1:-1]), validate=True))
        kid, sig = doc["key_id"], bytes.fromhex(doc["sig"])
    except (ValueError, KeyError, TypeError):
        raise Malformed("signature block payload unparseable") from None
    if doc.get("v") != 1 or not isinstance(kid, str) or len(sig) != 64:
        raise Malformed("signature block has wrong version/length")
    return kid, sig


def _check_key(k: TrustedKey, roots: TrustRoots, *, ref: str, when: int, now: int, identity: str,
               purpose: str) -> None:
    if k.algorithm not in roots.allowed_algorithms:
        raise Untrusted("signature algorithm not allowed by policy", algorithm=k.algorithm)
    if k.revoked_at is not None and (roots.revocation_mode == "hard" and now >= k.revoked_at
                                     or when >= k.revoked_at):
        raise Revoked("signing key is revoked", key_id=k.key_id)
    if not (k.not_before <= when <= k.not_after) or now > k.not_after:
        raise Expired("signing key outside its validity window", key_id=k.key_id)
    if identity.lower() != k.identity.lower():
        raise Untrusted("signer identity does not match the key's identity", key_id=k.key_id)
    if not any(fnmatch.fnmatchcase(ref, s) for s in k.scopes):
        raise Untrusted("key is not scoped for this ref", key_id=k.key_id, ref=ref)
    if purpose not in k.purposes:
        raise Untrusted("key is not authorised for this purpose", key_id=k.key_id, purpose=purpose)


def verify_commit(c: CommitInfo, roots: TrustRoots, *, ref: str, now: int) -> Verdict:
    """Fail closed unless ``c`` carries a valid signature from a trusted, in-scope, unrevoked key."""
    if not c.signature:
        raise Unsigned("commit carries no signature", oid=c.oid)
    if c.signature.startswith(ARMOR_BEGIN):
        kid, sig = dearmor(c.signature)
        k = roots.keys.get(kid)
        if k is None or k.algorithm != "ed25519":
            raise Untrusted("signature key is not in the trust roots", oid=c.oid, key_id=kid)
        _check_key(k, roots, ref=ref, when=c.commit_time, now=now, identity=c.committer_email, purpose="commit")
        if not ed25519.verify(k.public_key, c.signed_payload, sig):
            raise Unsigned("commit signature does not verify", oid=c.oid, key_id=kid)
        return Verdict(c.oid, kid, "ed25519", k.identity, roots.digest())
    if c.signature.startswith("-----BEGIN PGP SIGNATURE-----"):
        raise Untrusted("OpenPGP signature requires the OpenPGP lane (verify_openpgp_status)", oid=c.oid)
    raise Untrusted("unsupported signature format", oid=c.oid)


def verify_openpgp_status(c: CommitInfo, status_lines: list[str], roots: TrustRoots, *, ref: str,
                          now: int) -> Verdict:
    """Interpret ``git verify-commit --raw`` status lines under the trust roots."""
    bad = [ln for ln in status_lines if re.search(r"\[GNUPG:\] (BADSIG|ERRSIG|EXPKEYSIG|REVKEYSIG|EXPSIG|NO_PUBKEY)", ln)]
    if bad:
        raise Unsigned("OpenPGP verification failed", status=bad[0].split("] ", 1)[-1].split(" ")[0])
    valid = [ln.split() for ln in status_lines if "[GNUPG:] VALIDSIG" in ln]
    if len(valid) != 1:
        raise Unsigned("OpenPGP: exactly one VALIDSIG required", count=len(valid))
    toks = valid[0]
    primary = (toks[-1] if len(toks) >= 12 else toks[2]).upper()
    for k in roots.keys.values():
        if k.algorithm == "openpgp" and k.fingerprint and k.fingerprint in (primary, toks[2].upper()):
            _check_key(k, roots, ref=ref, when=c.commit_time, now=now, identity=c.committer_email, purpose="commit")
            return Verdict(c.oid, k.key_id, "openpgp", k.identity, roots.digest())
    raise Untrusted("OpenPGP signer fingerprint is not in the trust roots")


# -- signing helpers (fixtures, test repos and the operator revert tool) ----
def sign_payload(secret: bytes, key_id: str, payload: bytes) -> str:
    return armor(key_id, ed25519.sign(secret, payload))


def insert_signature(raw_commit: bytes, sig_armor: str) -> bytes:
    """Place the armored signature in a ``gpgsig`` header (git's own layout)."""
    head, _, msg = raw_commit.partition(b"\n\n")
    lines = sig_armor.encode().split(b"\n")
    hdr = b"gpgsig " + lines[0] + b"".join(b"\n " + ln for ln in lines[1:])
    return head + b"\n" + hdr + b"\n\n" + msg
