"""Generate the PK_BULK_*/1 conformance fixture set (C029).

Fixtures are deterministic (seeded) and frozen by conformance/FIXTURES.lock.
Regenerating with different expected results requires a schema/contract
review; the runner refuses fixtures whose digest differs from the lock.
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE.parent))
pkg = __import__(HERE.name)

OUT = HERE / "conformance" / "fixtures"


def fx(fid, kind, inp, ok, code=None, **extra):
    return {"id": fid, "kind": kind, "input": inp, "expect": {"ok": ok, "code": code, **extra}}


def main() -> None:
    rng = random.Random(3737)
    fixtures = []
    for name, size, chunk in [("zero_length", 0, 4096), ("one_chunk", 100, 4096), ("exact_multiple", 8192, 4096),
                              ("final_short_chunk", 10000, 4096), ("single_byte_chunks", 7, 1),
                              ("max_chunk_16MiB_geometry", 0, 16 << 20)]:
        data = bytes(rng.getrandbits(8) for _ in range(size))
        m = pkg.manifest(data, chunk)
        fixtures.append(fx(f"manifest.valid.{name}", "manifest", {"manifest": m, "object_hex": data.hex()}, True,
                           object_sha256=hashlib.sha256(data).hexdigest(), object_digest=m["object"]))
    base = pkg.manifest(b"conformance" * 1000, 4096)
    bad = {
        "wrong_schema": {**base, "schema": "PK_BULK_MANIFEST/2"},
        "wrong_algorithm": {**base, "algorithm": "md5"},
        "negative_size": {**base, "size": -1},
        "bool_chunk": {**base, "chunk": True},
        "zero_chunk": {**base, "chunk": 0},
        "geometry_mismatch": {**base, "size": base["size"] + 4096},
        "count_mismatch": {**base, "chunk_count": base["chunk_count"] + 1},
        "uppercase_digest": {**base, "chunks": [base["chunks"][0].upper()] + base["chunks"][1:]},
        "short_digest": {**base, "chunks": [base["chunks"][0][:63]] + base["chunks"][1:]},
        "object_digest_tampered": {**base, "object": "0" * 64},
        "chunk_reordered": {**base, "chunks": base["chunks"][::-1]},
        "not_an_object": ["PK_BULK_MANIFEST/1"],
        "unicode_digest": {**base, "chunks": ["ä" * 64] + base["chunks"][1:]},
        "exceeds_object_limit": {**base, "size": (1 << 30) + 1},
    }
    for k, v in bad.items():
        fixtures.append(fx(f"manifest.invalid.{k}", "manifest", {"manifest": v}, False, "invalid_manifest"))
    data = b"conformance" * 1000
    good_chunk = data[:4096]
    fixtures += [
        fx("chunk.valid.first", "chunk", {"manifest": base, "index": 0, "payload_hex": good_chunk.hex()}, True),
        fx("chunk.valid.duplicate", "chunk", {"manifest": base, "index": 0, "payload_hex": good_chunk.hex(), "repeat": 2}, True),
        fx("chunk.invalid.corrupt", "chunk", {"manifest": base, "index": 0, "payload_hex": (b"X" + good_chunk[1:]).hex()}, False, "digest_mismatch"),
        fx("chunk.invalid.index_oob", "chunk", {"manifest": base, "index": 99, "payload_hex": good_chunk.hex()}, False, "digest_mismatch"),
        fx("chunk.invalid.negative_index", "chunk", {"manifest": base, "index": -1, "payload_hex": good_chunk.hex()}, False, "digest_mismatch"),
        fx("chunk.invalid.wrong_length", "chunk", {"manifest": base, "index": 0, "payload_hex": good_chunk[:-1].hex()}, False, "digest_mismatch"),
        fx("object.invalid.incomplete", "object", {"manifest": base, "indices": [0, 1]}, False, "transfer_incomplete"),
        fx("object.valid.complete", "object", {"manifest": base, "indices": list(range(base["chunk_count"]))}, True,
           object_sha256=hashlib.sha256(data).hexdigest()),
        fx("resume.v1.shape", "resume", {"manifest": base, "indices": [0, 2]}, True,
           resume={"schema": "PK_BULK_RESUME/1", "manifest_object": base["object"], "last_verified": 0, "verified": [0, 2]}),
        fx("negotiate.v1_peer", "negotiate", {"offer": {"manifest": ["PK_BULK_MANIFEST/1"], "chunk": ["PK_BULK_CHUNK/1"],
                                                         "resume": ["PK_BULK_RESUME/1"], "transport": ["INV37_COPY/1"], "auth": ["v1"]}},
           True, chosen={"manifest": "PK_BULK_MANIFEST/1", "chunk": "PK_BULK_CHUNK/1", "resume": "PK_BULK_RESUME/1",
                         "transport": "INV37_COPY/1", "auth": "v1"}),
        fx("negotiate.no_auth_downgrade", "negotiate", {"offer": {"manifest": ["PK_BULK_MANIFEST/1"], "chunk": ["PK_BULK_CHUNK/1"]}},
           False, "version_incompatible"),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    lock = {}
    for f in fixtures:
        p = OUT / f"{f['id']}.json"
        blob = json.dumps(f, sort_keys=True, indent=1, ensure_ascii=False).encode()
        p.write_bytes(blob)
        lock[p.name] = hashlib.sha256(blob).hexdigest()
    (HERE / "conformance" / "FIXTURES.lock").write_text(json.dumps({"schema": "INV37_FIXTURES_LOCK/1", "fixtures": lock},
                                                                  sort_keys=True, indent=1))
    print(f"wrote {len(fixtures)} fixtures")


if __name__ == "__main__":
    main()
