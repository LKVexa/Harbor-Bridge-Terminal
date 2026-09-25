"""GAP02-MC-10 — Signed report envelope API.

Envelope = canonical capability bytes + sequence block + attested identity
reference, signed by a ``Signer`` (GAP-07 in production). Verification checks:
schema, identity binding (GAP-06 verifier), signature, digest, freshness
(trusted time), and replay (sequence guard) — any failure is a coded refusal.

``HmacSigner`` is a *reference/test* signer (symmetric, stdlib); production
must bind a GAP-07 asymmetric key via the ``Signer`` protocol.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
import hmac
import json
from typing import Any, Callable, Protocol

from ..capabilities import CapabilityReport
from .errors import Code, Gap02Error
from .replay import ReplayGuard
from .timepolicy import TrustedClock

ENVELOPE_SCHEMA = "PK_SIGNED_CAPABILITIES/1"


class Signer(Protocol):
    key_id: str
    alg: str
    def sign(self, data: bytes) -> bytes: ...


class Verifier(Protocol):
    def verify(self, key_id: str, alg: str, data: bytes, sig: bytes) -> bool: ...


class HmacSigner:
    alg = "HS256-REFERENCE"

    def __init__(self, key_id: str, key: bytes):
        if len(key) < 32:
            raise Gap02Error(Code.CONFIG_INVALID, "key too short")
        self.key_id, self._key = key_id, bytearray(key)

    def sign(self, data: bytes) -> bytes:
        return hmac.new(bytes(self._key), data, hashlib.sha256).digest()

    def verify(self, key_id: str, alg: str, data: bytes, sig: bytes) -> bool:
        return key_id == self.key_id and alg == self.alg and hmac.compare_digest(self.sign(data), sig)

    def zeroize(self) -> None:
        for i in range(len(self._key)):
            self._key[i] = 0


def _canon(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


@dataclass(frozen=True)
class SignedEnvelope:
    body: dict
    key_id: str
    alg: str
    signature: str

    def to_dict(self) -> dict:
        return {"schema": ENVELOPE_SCHEMA, "body": self.body, "key_id": self.key_id,
                "alg": self.alg, "signature": self.signature}

    @classmethod
    def from_dict(cls, d: dict) -> "SignedEnvelope":
        if not isinstance(d, dict) or d.get("schema") != ENVELOPE_SCHEMA:
            raise Gap02Error(Code.SCHEMA_INCOMPATIBLE, str(d.get("schema") if isinstance(d, dict) else d)[:64])
        try:
            return cls(dict(d["body"]), str(d["key_id"]), str(d["alg"]), str(d["signature"]))
        except (KeyError, TypeError) as e:
            raise Gap02Error(Code.MALFORMED_RESPONSE, "envelope fields") from e


def seal(report: CapabilityReport, now: int, signer: Signer, *, identity: dict, sequence: dict,
         generation: str) -> SignedEnvelope:
    if not identity.get("attested"):
        raise Gap02Error(Code.UNATTESTED, "refusing to sign for an unattested identity")
    facts = json.loads(report.canonical_bytes(now))
    body = {"facts": facts, "facts_sha256": hashlib.sha256(_canon(facts)).hexdigest(),
            "identity": {"node": report.node, "identity_id": identity["identity_id"],
                         "evidence_digest": identity["evidence_digest"]},
            "sequence": sequence, "generation": generation, "signed_at": now}
    if body["identity"]["node"] != facts["node"]:
        raise Gap02Error(Code.UNATTESTED, "identity/node mismatch")
    sig = signer.sign(_canon(body))
    return SignedEnvelope(body, signer.key_id, signer.alg, base64.b64encode(sig).decode())


def open_envelope(env: SignedEnvelope, *, verifier: Verifier, identity_check: Callable[[dict], bool],
                  clock: TrustedClock, guard: ReplayGuard, max_age: int = 60,
                  revoked: frozenset[str] = frozenset()) -> dict:
    """Return verified facts or raise a coded Gap02Error. Order is fail-closed."""
    b = env.body
    if env.key_id in revoked:
        raise Gap02Error(Code.SIGNATURE_FAILURE, "key revoked")
    try:
        sig = base64.b64decode(env.signature, validate=True)
    except (ValueError, TypeError) as e:
        raise Gap02Error(Code.MALFORMED_RESPONSE, "signature encoding") from e
    try:
        ok = verifier.verify(env.key_id, env.alg, _canon(b), sig)
    except Exception as e:  # noqa: BLE001
        raise Gap02Error(Code.DEPENDENCY_FAILURE, "verifier unavailable") from e
    if ok is not True:
        raise Gap02Error(Code.SIGNATURE_FAILURE, "bad signature")
    if hashlib.sha256(_canon(b["facts"])).hexdigest() != b["facts_sha256"]:
        raise Gap02Error(Code.SIGNATURE_FAILURE, "facts digest mismatch")
    if not identity_check(b["identity"]):
        raise Gap02Error(Code.UNATTESTED, "identity evidence not accepted by GAP-06")
    now = clock.now()
    clock.check_signed_at(int(b["signed_at"]), now, max_age)
    guard.admit(b["identity"]["node"], b["sequence"])
    return b["facts"]
