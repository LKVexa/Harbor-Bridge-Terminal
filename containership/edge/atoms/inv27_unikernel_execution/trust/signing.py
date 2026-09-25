"""Signature + provenance verification (MC-005; C045).

Envelope: DSSE-style ``{"payloadType", "payload" (base64 of canonical JSON), "signatures":[{"keyid","sig"}]}``.
The signed bytes are the DSSE PAE: ``"DSSEv1" SP len(type) SP type SP len(body) SP body``.

Payload: ``PK_UNIKERNEL_PROVENANCE/1`` (schemas/PK_UNIKERNEL_PROVENANCE-1.schema.json)::

    {"schema": "PK_UNIKERNEL_PROVENANCE/1",
     "subject": {"digest": "sha256:<hex>", "name": "..."},
     "builder": "builder-id", "toolchain": "unikraft", "toolchain_version": "0.17.0",
     "source": {"uri": "...", "digest": "sha256:<hex>"},
     "built_at": "2026-09-23T00:00:00Z",
     "attested_facts": {...optional, only honoured for stripped images...}}

Trust root: ``TrustRoot`` - keys with validity windows, revocation, and the builders each key may
speak for.  Every failure fails closed with a registered code.  Ed25519 is the vendored RFC 8032
implementation (pure Python, NOT constant-time; ``set_backend`` swaps in ``cryptography`` when
installed - TD-2).
"""
from __future__ import annotations

import base64
import binascii
import datetime as dt
import json
from dataclasses import dataclass, field
from typing import Callable

from ..errors import UkError
from . import ed25519

PAYLOAD_TYPE = "application/vnd.pk.unikernel.provenance.v1+json"
SCHEMA = "PK_UNIKERNEL_PROVENANCE/1"
_MAX_ENVELOPE = 256 * 1024


def _verify_pure(pub: bytes, msg: bytes, sig: bytes) -> bool:
    return ed25519.verify(pub, msg, sig)


def _verify_cryptography(pub: bytes, msg: bytes, sig: bytes) -> bool:  # pragma: no cover - optional
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    try:
        Ed25519PublicKey.from_public_bytes(pub).verify(sig, msg)
        return True
    except (InvalidSignature, ValueError):
        return False


_BACKEND: dict[str, Callable[[bytes, bytes, bytes], bool]] = {"verify": _verify_pure, "name": "pure-rfc8032"}  # type: ignore


def set_backend(name: str) -> str:
    """Select ``pure`` or ``cryptography`` (constant-time).  Returns the active backend name."""
    if name == "cryptography":
        import cryptography  # noqa: F401  (raises if absent -> caller keeps pure)
        _BACKEND.update(verify=_verify_cryptography, name="cryptography")
    elif name == "pure":
        _BACKEND.update(verify=_verify_pure, name="pure-rfc8032")
    else:
        raise ValueError(name)
    return _BACKEND["name"]  # type: ignore


def backend() -> str:
    return _BACKEND["name"]  # type: ignore


def pae(payload_type: str, body: bytes) -> bytes:
    t = payload_type.encode()
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(body), body)


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


@dataclass(frozen=True)
class TrustedKey:
    keyid: str
    public: bytes
    builders: frozenset
    not_before: dt.datetime
    not_after: dt.datetime
    revoked: bool = False


@dataclass
class TrustRoot:
    version: int
    keys: dict = field(default_factory=dict)
    fetched_at: dt.datetime | None = None
    max_age: dt.timedelta = dt.timedelta(hours=24)

    @classmethod
    def from_dict(cls, d: dict, *, fetched_at: dt.datetime | None = None) -> "TrustRoot":
        if not isinstance(d, dict) or d.get("schema") != "PK_UNIKERNEL_TRUST_ROOT/1" or not isinstance(d.get("version"), int):
            raise UkError("UK_CONFIG_INVALID", "trust root must be PK_UNIKERNEL_TRUST_ROOT/1 with integer version")
        keys = {}
        for k in d.get("keys", []):
            try:
                pub = bytes.fromhex(k["public_hex"])
                if len(pub) != 32:
                    raise ValueError("len")
                keys[k["keyid"]] = TrustedKey(k["keyid"], pub, frozenset(k["builders"]),
                                              dt.datetime.fromisoformat(k["not_before"]),
                                              dt.datetime.fromisoformat(k["not_after"]), bool(k.get("revoked", False)))
            except (KeyError, ValueError, TypeError) as e:
                raise UkError("UK_CONFIG_INVALID", f"trust root key invalid: {e}") from None
        return cls(d["version"], keys, fetched_at or dt.datetime.now(dt.timezone.utc))

    def check_fresh(self, now: dt.datetime) -> None:
        if self.fetched_at is None or now - self.fetched_at > self.max_age:
            raise UkError("UK_TRUST_UNAVAILABLE", "trust root is stale; admission fails closed")


@dataclass(frozen=True)
class ProvenancePolicy:
    approved_builders: frozenset
    approved_toolchains: dict           # toolchain -> frozenset of approved versions
    require_source_digest: bool = True


@dataclass(frozen=True)
class VerifiedProvenance:
    keyid: str
    statement: dict
    backend: str


def sign_envelope(statement: dict, seed: bytes, keyid: str) -> dict:
    """Build a signed envelope (used by tests, fixtures and the reference builder tool)."""
    body = canonical(statement)
    sig = ed25519.sign(seed, pae(PAYLOAD_TYPE, body))
    return {"payloadType": PAYLOAD_TYPE, "payload": base64.b64encode(body).decode(),
            "signatures": [{"keyid": keyid, "sig": base64.b64encode(sig).decode()}]}


def _b64(s, what: str) -> bytes:
    if not isinstance(s, str):
        raise UkError("UK_SIG_INVALID", f"{what} must be base64 text")
    try:
        raw = base64.b64decode(s, validate=True)
    except (binascii.Error, ValueError):
        raise UkError("UK_SIG_INVALID", f"{what} is not canonical base64") from None
    if base64.b64encode(raw).decode() != s:
        raise UkError("UK_SIG_INVALID", f"{what} base64 is non-canonical (malleable)")
    return raw


def verify_envelope(envelope: dict | None, *, image_ref: str, trust: TrustRoot, policy: ProvenancePolicy,
                    now: dt.datetime | None = None) -> VerifiedProvenance:
    now = now or dt.datetime.now(dt.timezone.utc)
    if envelope is None:
        raise UkError("UK_SIG_MISSING")
    trust.check_fresh(now)
    if not isinstance(envelope, dict) or set(envelope) != {"payloadType", "payload", "signatures"}:
        raise UkError("UK_SIG_INVALID", "envelope must have exactly payloadType, payload, signatures")
    if len(json.dumps(envelope)) > _MAX_ENVELOPE:
        raise UkError("UK_LIMIT_EXCEEDED", "envelope too large")
    if envelope["payloadType"] != PAYLOAD_TYPE:
        raise UkError("UK_SIG_INVALID", "unexpected payloadType")
    body = _b64(envelope["payload"], "payload")
    sigs = envelope["signatures"]
    if not isinstance(sigs, list) or not 1 <= len(sigs) <= 4:
        raise UkError("UK_SIG_INVALID", "1..4 signatures required")
    msg = pae(PAYLOAD_TYPE, body)
    good: TrustedKey | None = None
    for s in sigs:
        if not isinstance(s, dict) or set(s) != {"keyid", "sig"}:
            raise UkError("UK_SIG_INVALID", "signature entries need exactly keyid, sig")
        key = trust.keys.get(s["keyid"])
        if key is None or key.revoked or not (key.not_before <= now <= key.not_after):
            continue
        sig = _b64(s["sig"], "sig")
        if len(sig) == 64 and _BACKEND["verify"](key.public, msg, sig):  # type: ignore
            good = key
            break
    if good is None:
        # distinguish "bad signature from a trusted key" from "no trusted key at all"
        trusted = [s for s in sigs if isinstance(s, dict) and s.get("keyid") in trust.keys
                   and not trust.keys[s["keyid"]].revoked
                   and trust.keys[s["keyid"]].not_before <= now <= trust.keys[s["keyid"]].not_after]
        raise UkError("UK_SIG_INVALID" if trusted else "UK_SIG_UNTRUSTED_KEY")
    try:
        st = json.loads(body)
    except ValueError:
        raise UkError("UK_PROVENANCE_INVALID", "payload is not JSON") from None
    if canonical(st) != body:
        raise UkError("UK_PROVENANCE_INVALID", "payload is not canonical JSON")
    _check_statement(st, image_ref, good, policy)
    return VerifiedProvenance(good.keyid, st, backend())


_FIELDS = {"schema", "subject", "builder", "toolchain", "toolchain_version", "source", "built_at", "attested_facts"}


def _check_statement(st: dict, image_ref: str, key: TrustedKey, policy: ProvenancePolicy) -> None:
    if not isinstance(st, dict) or st.get("schema") != SCHEMA:
        raise UkError("UK_PROVENANCE_INVALID", f"schema must be {SCHEMA}")
    extra = set(st) - _FIELDS
    missing = (_FIELDS - {"attested_facts"}) - set(st)
    if extra or missing:
        raise UkError("UK_PROVENANCE_INVALID", f"unknown fields {sorted(extra)} / missing {sorted(missing)}")
    subj = st["subject"]
    if not isinstance(subj, dict) or subj.get("digest") != image_ref:
        raise UkError("UK_PROVENANCE_INVALID", "provenance subject does not bind this image digest",
                      subject=subj.get("digest") if isinstance(subj, dict) else None, image=image_ref)
    if st["builder"] not in key.builders:
        raise UkError("UK_PROVENANCE_POLICY", "signing key is not authorised for this builder")
    if st["builder"] not in policy.approved_builders:
        raise UkError("UK_PROVENANCE_POLICY", f"builder {st['builder']!r} not approved")
    versions = policy.approved_toolchains.get(st["toolchain"])
    if not versions or st["toolchain_version"] not in versions:
        raise UkError("UK_PROVENANCE_POLICY", f"toolchain {st['toolchain']}@{st['toolchain_version']} not approved")
    src = st["source"]
    if policy.require_source_digest and (not isinstance(src, dict) or not str(src.get("digest", "")).startswith("sha256:")):
        raise UkError("UK_PROVENANCE_POLICY", "source digest required")
