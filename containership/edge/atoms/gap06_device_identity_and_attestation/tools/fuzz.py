"""MC-40: mutation fuzzing of every parser that faces untrusted bytes.

Property: a parser either returns or raises Gap06Error -- never any other
exception, never unbounded time.  Writes evidence/fuzz.json.
Usage: python -m gap06_device_identity_and_attestation.tools.fuzz [iterations]
"""
import json
import random
import sys
import time
from pathlib import Path

from ..mc import schemas, simulator, tpm, verifier
from ..mc.errors import Gap06Error


def mutate(rng, b: bytes) -> bytes:
    b = bytearray(b)
    for _ in range(rng.randint(1, 4)):
        op = rng.randrange(5)
        if op == 0 and b:
            b[rng.randrange(len(b))] ^= 1 << rng.randrange(8)
        elif op == 1:
            b = b[: rng.randrange(len(b) + 1)]
        elif op == 2:
            i = rng.randrange(len(b) + 1); b[i:i] = bytes(rng.randrange(256) for _ in range(rng.randint(1, 8)))
        elif op == 3 and b:
            i = rng.randrange(len(b)); b[i] = rng.choice([0, 0xFF, 0x7F, 0x80])
        elif op == 4 and len(b) > 4:
            i = rng.randrange(len(b) - 2); b[i:i + 2] = b"\xff\xff"
    return bytes(b)


def run(iterations=20000, seed=20260922):
    rng = random.Random(seed)
    t = simulator.SoftTPM("fuzz")
    for p, d in [(0, b"fw"), (7, b"sb")]:
        t.extend(p, d)
    attest, sig, _ = t.quote(b"\x01" * 32)
    log = t.event_log()
    ima = "10 " + "a" * 64 + " ima-ng sha256:" + "b" * 64 + " /bin/x"
    seeds = {"parse_attest": (tpm.parse_attest, attest), "parse_signature": (tpm.parse_signature, sig),
             "parse_event_log": (tpm.parse_event_log, log),
             "parse_ima": (lambda b: verifier.parse_ima(b.decode("latin-1")), ima.encode()),
             "schemas.validate": (schemas.validate, json.dumps({"schema": "PK_ATTESTATION/1", "node": "n", "nonce": "ab",
                                  "attest": "00", "signature": "00", "pcrs": {"0": "00" * 32}, "idempotency_key": "k"}).encode())}
    out = {}
    for name, (fn, seed_bytes) in seeds.items():
        stats = {"iterations": iterations, "accepted": 0, "rejected": 0, "crashes": [], "max_ms": 0.0}
        for _ in range(iterations):
            data = mutate(rng, seed_bytes)
            t0 = time.perf_counter()
            try:
                fn(data)
                stats["accepted"] += 1
            except Gap06Error:
                stats["rejected"] += 1
            except Exception as e:  # property violation
                if len(stats["crashes"]) < 10:
                    stats["crashes"].append({"type": type(e).__name__, "input": data.hex()[:256]})
            stats["max_ms"] = max(stats["max_ms"], (time.perf_counter() - t0) * 1000)
        stats["max_ms"] = round(stats["max_ms"], 3)
        out[name] = stats
    return {"schema": "GAP06-FUZZ/1", "seed": seed, "targets": out,
            "property_holds": all(not s["crashes"] for s in out.values())}


if __name__ == "__main__":
    res = run(int(sys.argv[1]) if len(sys.argv) > 1 else 20000)
    Path("evidence").mkdir(exist_ok=True)
    Path("evidence/fuzz.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: {kk: v[kk] for kk in ("accepted", "rejected", "max_ms")} | {"crashes": len(v["crashes"])}
                      for k, v in res["targets"].items()}, indent=1))
    print("property_holds:", res["property_holds"])
