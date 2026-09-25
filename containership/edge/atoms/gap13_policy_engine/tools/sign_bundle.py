"""Offline signing helper (fixtures / air-gapped publisher).  NEVER imported by the runtime.

usage: python -m gap13_policy_engine.tools.sign_bundle bundle.json private_key.raw key_id > envelope.json
"""
from __future__ import annotations

import base64
import json
import sys

from ..canonical import canonical_bytes, sha256_hex
from ..verify import DOMAIN_TAG, ENVELOPE_SCHEMA


def sign(bundle_doc: dict, private_key_bytes: bytes, key_id: str) -> bytes:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    payload = canonical_bytes(bundle_doc)
    sig = Ed25519PrivateKey.from_private_bytes(private_key_bytes).sign(DOMAIN_TAG + payload)
    env = {"schema": ENVELOPE_SCHEMA, "payload_b64": base64.b64encode(payload).decode(),
           "digest": "sha256:" + sha256_hex(payload),
           "signature": {"alg": "ed25519", "key_id": key_id, "value_b64": base64.b64encode(sig).decode()}}
    return canonical_bytes(env)


def main(argv: list[str]) -> int:
    doc = json.load(open(argv[1], encoding="utf-8"))
    key = open(argv[2], "rb").read()
    sys.stdout.write(sign(doc, key, argv[3]).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
