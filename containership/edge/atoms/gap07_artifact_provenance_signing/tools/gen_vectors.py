"""Regenerate vectors/v6_vectors.json (deterministic; Ed25519 only so bytes are stable).

Other-language verifiers consume this file: every vector gives the exact
signed bytes (hex) so an implementation can prove byte-identical encoding.
"""
from __future__ import annotations

import base64
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from cryptography.hazmat.primitives.asymmetric import ed25519  # noqa: E402

from gap07_artifact_provenance_signing import algorithms as algs  # noqa: E402
from gap07_artifact_provenance_signing.canonical import b64u_encode, canonical_bytes, ld_encode  # noqa: E402
from gap07_artifact_provenance_signing.dsse import pae  # noqa: E402
from gap07_artifact_provenance_signing.signing import signed_message  # noqa: E402
from gap07_artifact_provenance_signing.tlog import mth  # noqa: E402

SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")  # RFC 8032 test 1


def build() -> dict:
    sk = ed25519.Ed25519PrivateKey.from_private_bytes(SEED)
    env = {"v": 3, "alg": "ed25519", "kid": "acme/site-a/prod/software:k1@1", "signer": "spiffe://acme/prod/release-bot", "tenant": "acme",
           "site": "site-a", "env": "prod", "kind": "code", "purpose": "sign:code", "policy_domain": "default", "digest_alg": "sha256",
           "digest": "a" * 64, "issued_at": 1800000000, "nonce": None, "refs": []}
    msg = signed_message(env)
    env_signed = dict(env, sig=b64u_encode(sk.sign(msg)))
    ct_leaves = [b"", b"\x00", b"\x10", b"\x20\x21", b"\x30\x31", b"\x40\x41\x42\x43", bytes(range(0x50, 0x58)), bytes(range(0x60, 0x70))]
    return {
        "schema": "PK_INTEROP_VECTORS/1",
        "rfc8032_test1": {"seed_hex": SEED.hex(), "public_hex": algs.spki(sk.public_key())[-32:].hex(), "message_hex": "",
                          "signature_hex": sk.sign(b"").hex()},
        "canonical_json": [
            {"input": {"b": 1, "a": [True, None, "é"]}, "canonical_hex": canonical_bytes({"b": 1, "a": [True, None, "é"]}).hex()},
            {"input": {"z": {"y": "\u2028"}, "a": -9007199254740991}, "canonical_hex": canonical_bytes({"z": {"y": "\u2028"}, "a": -9007199254740991}).hex()},
            {"note": "RFC 8785 key order is by UTF-16 code units: U+1F600 sorts before U+FFFF",
             "input": {"\uffff": 1, "\U0001F600": 2}, "canonical_hex": canonical_bytes({"\uffff": 1, "\U0001F600": 2}).hex()},
        ],
        "ld_encode": {"domain": "example/1", "fields": [["a", "bc"], ["ab", "c"], ["n", 7], ["none", None]],
                      "hex": ld_encode("example/1", [("a", "bc"), ("ab", "c"), ("n", 7), ("none", None)]).hex()},
        "dsse_pae": {"type": "http://example.com/HelloWorld", "body": "hello world",
                     "hex": pae("http://example.com/HelloWorld", b"hello world").hex()},
        "signature_v3": {"envelope": env_signed, "signed_bytes_hex": msg.hex(), "public_spki_b64": base64.b64encode(algs.spki(sk.public_key())).decode()},
        "rfc6962_root_8": {"leaves_hex": [x.hex() for x in ct_leaves], "root_hex": mth(ct_leaves).hex()},
    }


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vectors", "v6_vectors.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(build(), fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")
    print(out)
