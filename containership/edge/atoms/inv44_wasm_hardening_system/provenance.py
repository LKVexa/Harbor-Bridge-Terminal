"""Supply-chain provenance for INV-44 (missing component 10).

Produces an in-toto Statement v1 with a SLSA-provenance-v1-shaped predicate
over every file in the package, wrapped in a DSSE envelope (PAE encoding).

Signature scheme: ``hmac-sha256`` — the only MAC the standard library offers.
This proves integrity to holders of the key; it is NOT a publicly verifiable
signature and cannot satisfy SLSA Build L2+. Replacing it with Sigstore or an
Ed25519/ECDSA key held in a KMS is BLOCKED on owner-provisioned key custody
and is recorded as such in the release evidence.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Iterable

PAYLOAD_TYPE = "application/vnd.in-toto+json"
SKIP_PARTS = {"__pycache__", ".pytest_cache", "evidence", ".git", "dist", "build", "inv44_wasm_hardening_system.egg-info"}


def subjects(root: Path, *, exclude: Iterable[str] = ()) -> list[dict]:
    ex = set(exclude)
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if not p.is_file() or SKIP_PARTS & set(p.parts) or p.suffix == ".pyc" or rel in ex:
            continue
        out.append({"name": rel, "digest": {"sha256": hashlib.sha256(p.read_bytes()).hexdigest()}})
    return out


def statement(root: Path, *, version: str, builder_id: str, invocation: dict,
              dependencies: list[dict], exclude: Iterable[str] = ()) -> dict:
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": subjects(root, exclude=exclude),
        "predicateType": "https://slsa.dev/provenance/v1",
        "predicate": {
            "buildDefinition": {
                "buildType": "urn:pk:inv44:local-build:1",
                "externalParameters": {"version": version, **invocation},
                "resolvedDependencies": dependencies,
            },
            "runDetails": {"builder": {"id": builder_id}},
        },
    }


def pae(payload_type: str, payload: bytes) -> bytes:
    t = payload_type.encode()
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def sign(stmt: dict, *, key: bytes, key_id: str) -> dict:
    payload = json.dumps(stmt, sort_keys=True, separators=(",", ":")).encode()
    sig = hmac.new(key, pae(PAYLOAD_TYPE, payload), hashlib.sha256).digest()
    return {"payloadType": PAYLOAD_TYPE, "payload": base64.b64encode(payload).decode(),
            "signatures": [{"keyid": key_id, "alg": "hmac-sha256", "sig": base64.b64encode(sig).decode()}]}


def verify(envelope: dict, *, keys: dict[str, bytes], root: Path | None = None) -> dict:
    payload = base64.b64decode(envelope["payload"])
    ok = False
    for s in envelope.get("signatures", []):
        k = keys.get(s.get("keyid"))
        if k and s.get("alg") == "hmac-sha256":
            want = hmac.new(k, pae(envelope["payloadType"], payload), hashlib.sha256).digest()
            ok |= hmac.compare_digest(want, base64.b64decode(s["sig"]))
    if not ok:
        raise ValueError("no valid provenance signature")
    stmt = json.loads(payload)
    if root is not None:
        for sub in stmt["subject"]:
            p = root / sub["name"]
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != sub["digest"]["sha256"]:
                raise ValueError(f"subject digest mismatch: {sub['name']}")
    return stmt
