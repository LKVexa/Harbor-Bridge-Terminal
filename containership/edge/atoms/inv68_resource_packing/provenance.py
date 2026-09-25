"""Release provenance producer (INV-68 MC-09/MC-32) — carried from the owner's INV-64 4.3.0 ``provenance.py`` (originally INV-44 v4.3.0).

Produces an in-toto Statement v1 with a SLSA-provenance-v1-shaped predicate,
wrapped in a DSSE envelope (PAE encoding). Two signature algorithms:

* ``ed25519`` (requires the optional ``cryptography`` package) — publicly
  verifiable; the private key must come from a managed signer (KMS/HSM/OIDC
  keyless). This repository never stores one; release tooling generates an
  **ephemeral** key when none is supplied and says so in the evidence.
* ``hmac-sha256`` (stdlib) — integrity for holders of the key only. It cannot
  satisfy SLSA Build L2+ and the release gate records it as such.

:mod:`trust` is the consumer side; producer and consumer are tested together.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Iterable

PAYLOAD_TYPE = "application/vnd.in-toto+json"
SKIP_PARTS = {"__pycache__", ".pytest_cache", ".git", "dist", "build", "_build", "evidence", "release"}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def subjects(root: Path, *, exclude: Iterable[str] = ()) -> list[dict]:
    ex = set(exclude)
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if not p.is_file() or SKIP_PARTS & set(p.relative_to(root).parts) or p.suffix == ".pyc" \
                or rel in ex or ".egg-info" in rel:
            continue
        out.append({"name": rel, "digest": {"sha256": sha256_file(p)}})
    return out


def statement(subject: list[dict], *, version: str, builder_id: str, invocation: dict,
              dependencies: list[dict], build_type: str = "urn:pk:inv68:local-build:1") -> dict:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": subject,
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": build_type,
                "externalParameters": {"version": version, **invocation},
                "resolvedDependencies": dependencies,
            },
            "runDetails": {"builder": {"id": builder_id}},
        },
    }


def pae(payload_type: str, payload: bytes) -> bytes:
    t = payload_type.encode()
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def sign(stmt: dict, *, key: bytes, key_id: str, alg: str = "hmac-sha256") -> dict:
    payload = json.dumps(stmt, sort_keys=True, separators=(",", ":")).encode()
    msg = pae(PAYLOAD_TYPE, payload)
    if alg == "hmac-sha256":
        sig = hmac.new(key, msg, hashlib.sha256).digest()
    elif alg == "ed25519":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        sig = Ed25519PrivateKey.from_private_bytes(key).sign(msg)
    else:
        raise ValueError("unsupported alg")
    return {"payloadType": PAYLOAD_TYPE, "payload": base64.b64encode(payload).decode(),
            "signatures": [{"keyid": key_id, "sig": base64.b64encode(sig).decode()}]}


def check_signature(alg: str, key: bytes, msg: bytes, sig: bytes) -> bool:
    if alg == "hmac-sha256":
        return hmac.compare_digest(hmac.new(key, msg, hashlib.sha256).digest(), sig)
    if alg == "ed25519":
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        except ImportError:
            return False
        try:
            Ed25519PublicKey.from_public_bytes(key).verify(sig, msg)
            return True
        except (InvalidSignature, ValueError):
            return False
    return False


def ed25519_keypair() -> tuple[bytes, bytes]:
    """Return (private_raw, public_raw). Ephemeral use only; see module docstring."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    k = Ed25519PrivateKey.generate()
    priv = k.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                           serialization.NoEncryption())
    pub = k.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return priv, pub
