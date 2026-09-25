"""Deterministic mutation fuzzer for the untrusted-input boundaries (INV-40-C085).

Targets: create-request parser/validator, credential parser, config validator,
journal replay.  Oracle: every input either succeeds or raises a *classified*
OpError / SchemaError / JournalCorrupt - never any other exception.  Crashing
inputs are written to tests/fixtures/fuzz_regressions/.
"""
from __future__ import annotations

import json
import pathlib
import random
import sys
import tempfile

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))
from fvt import config, errors, identity, journal, schema  # noqa: E402

SEED_REQ = {"schema": "PK_FULL_VM/1", "name": "g", "tenant": "t", "memory_mib": 512,
            "image_digest": "sha256:" + "a" * 64, "idempotency_key": "k"}
EXPECTED = (errors.OpError, schema.SchemaError, journal.JournalCorrupt)


def mutate(b: bytes, rng: random.Random) -> bytes:
    b = bytearray(b)
    for _ in range(rng.randint(1, 8)):
        op = rng.randrange(5)
        i = rng.randrange(len(b) + 1)
        if op == 0 and b:
            b[min(i, len(b) - 1)] = rng.randrange(256)
        elif op == 1:
            b[i:i] = bytes(rng.randrange(256) for _ in range(rng.randint(1, 16)))
        elif op == 2 and b:
            del b[i:i + rng.randint(1, 16)]
        elif op == 3:
            b[i:i] = rng.choice([b"{", b"[", b'"', b"\\u0000", b"1e999", b"-0", b"true", b"null", b"\xff\xfe"])
        else:
            b = b + b[: rng.randint(0, len(b))]
    return bytes(b)


def run(iterations: int = 20000, seed: int = 40) -> dict:
    rng = random.Random(seed)
    kp = identity.KeyProvider({"k1": b"k" * 32})
    auth = identity.Authenticator(kp)
    good_tok = identity.issue(kp, "k1", sub="s", kind="service", tenants=["t"], ops=["read"], nonce="n0")
    cfg_seed = json.dumps(config.layer()).encode()
    crashes, counts = [], {"req": 0, "tok": 0, "cfg": 0, "wal": 0}
    tmp = pathlib.Path(tempfile.mkdtemp())
    for n in range(iterations):
        target = ("req", "tok", "cfg", "wal")[n % 4]
        counts[target] += 1
        try:
            if target == "req":
                schema.parse_and_validate(mutate(json.dumps(SEED_REQ).encode(), rng), "PK_FULL_VM_CREATE_REQUEST.v1")
            elif target == "tok":
                auth.authenticate(mutate(good_tok.encode(), rng).decode("latin-1"))
            elif target == "cfg":
                raw = mutate(cfg_seed, rng)
                try:
                    doc = json.loads(raw)
                except (ValueError, UnicodeDecodeError, RecursionError):
                    continue
                if isinstance(doc, dict):
                    config.validate(doc)
            elif n % 8 == 3:   # D-03: structure-aware lane - valid CRC around a mutated body
                import zlib
                body = mutate(b'{"op":"create","instance_id":"a","tenant":"t"}', rng)
                p = tmp / "g.wal"
                p.write_bytes(f"{zlib.crc32(body):08x}\t".encode() + body + b"\n")
                journal.Journal(p).state()
            else:
                p = tmp / "f.wal"
                j = journal.Journal(p)
                p.write_bytes(b"")
                j.append({"op": "create", "instance_id": "a", "tenant": "t"})
                p.write_bytes(mutate(p.read_bytes(), rng))
                j.state()
        except EXPECTED:
            pass
        except Exception as exc:  # noqa: BLE001
            crashes.append({"target": target, "iteration": n, "error": f"{type(exc).__name__}: {exc}"[:300]})
    out = {"schema": "PK_FULL_VM_FUZZ/1", "seed": seed, "iterations": iterations, "per_target": counts,
           "unclassified_crashes": len(crashes), "crashes": crashes[:20]}
    if crashes:
        d = PKG / "tests/fixtures/fuzz_regressions"
        d.mkdir(parents=True, exist_ok=True)
        (d / f"seed{seed}.json").write_text(json.dumps(crashes[:50], indent=1))
    return out


if __name__ == "__main__":
    r = run(int(sys.argv[1]) if len(sys.argv) > 1 else 20000)
    print(json.dumps(r, indent=1))
    sys.exit(1 if r["unclassified_crashes"] else 0)
