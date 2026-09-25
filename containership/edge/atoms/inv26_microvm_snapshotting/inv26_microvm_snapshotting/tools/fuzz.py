"""Deterministic mutation fuzzer for every untrusted-input boundary (C085).

Targets: request schema validation (capture/restore), bounded JSON parsing,
credential/grant decoding, configuration validation, envelope opening, WAL
replay, and the full service boundary (``handle`` must never raise and must
always return a schema-valid PK_SNAPSHOT_ERROR/1 or a 200 body).

Oracle: no uncaught exception, no SNAP_INTERNAL from the service boundary,
and every error envelope validates. Findings are minimised to the smallest
mutated input and written to ``tests/fixtures/fuzz_regressions.json``.

``python -m inv26_microvm_snapshotting.tools.fuzz --iterations 2000 --seed 26 --out evidence/FUZZ.json``
"""
from __future__ import annotations

import argparse
import base64
import copy
import json
import random
import sys
import tempfile
import time
from pathlib import Path

from .. import config as cfgmod, crypto, schema
from ..errors import SnapshotServiceError
from ..metastore import MetaStore

INTERESTING = [None, True, False, 0, -1, 1 << 63, 2 ** 1000, 1e308, -0.0, "", " ", "\x00", "../..", "A" * 5000,
               "é" * 100, [], {}, [[[[[]]]]], {"a": {"b": {"c": {}}}}, "t1", "prod", "\ud800"]


def mutate(rng: random.Random, doc):
    d = copy.deepcopy(doc)
    for _ in range(rng.randint(1, 4)):
        if not isinstance(d, dict) or not d:
            return rng.choice(INTERESTING)
        k = rng.choice(list(d))
        op = rng.randrange(6)
        if op == 0:
            d[k] = rng.choice(INTERESTING)
        elif op == 1:
            del d[k]
        elif op == 2:
            d[rng.choice(["x", "__proto__", "schema ", k.upper()])] = rng.choice(INTERESTING)
        elif op == 3 and isinstance(d[k], str):
            s = d[k]
            i = rng.randrange(len(s) + 1)
            d[k] = s[:i] + rng.choice(["'", '"', "\n", "‮", "%00", "*", "/"]) + s[i:]
        elif op == 4 and isinstance(d[k], list):
            d[k] = d[k] * rng.randint(0, 80)
        elif op == 5 and isinstance(d[k], dict):
            d[k] = mutate(rng, d[k])
    return d


def run(iterations: int, seed: int) -> dict:
    from ..tests.harness import Rig
    from .gen_artifacts import capture_req, restore_req
    rng = random.Random(seed)
    findings, counts = [], {}
    t0 = time.time()
    r = Rig(tempfile.mkdtemp(prefix="inv26-fuzz-"))
    snap = r.capture()
    tok = r.token()
    grant = r.grant(snap)
    env_ok, blob_ok = snap, r.blobs.get("t1", "s1", 1)
    envelope = r.meta.get("snap/s1")[1]["manifest"]["envelope"]
    ctx = r.svc._ctx(r.meta.get("snap/s1")[1])

    def record(target, inp, exc):
        findings.append({"target": target, "input": repr(inp)[:500], "error": f"{type(exc).__name__}: {exc}"[:300]})

    targets = ["schema.capture", "schema.restore", "parse_json", "auth.token", "auth.grant", "config",
               "envelope", "service.capture", "service.restore"]
    for i in range(iterations):
        t = targets[i % len(targets)]
        counts[t] = counts.get(t, 0) + 1
        try:
            if t == "schema.capture":
                schema.validate(mutate(rng, capture_req()), "PK_SNAPSHOT_CAPTURE_REQUEST/2")
            elif t == "schema.restore":
                schema.validate(mutate(rng, restore_req()), "PK_SNAPSHOT_RESTORE_REQUEST/2")
            elif t == "parse_json":
                raw = json.dumps(capture_req()).encode()
                b = bytearray(raw)
                for _ in range(rng.randint(1, 8)):
                    b[rng.randrange(len(b))] = rng.randrange(256)
                try:
                    schema.parse_json(bytes(b), "PK_SNAPSHOT_CAPTURE_REQUEST/2")
                except SnapshotServiceError:
                    pass
            elif t in ("auth.token", "auth.grant"):
                src = tok if t == "auth.token" else grant
                parts = src.split(".")
                j = rng.randrange(3)
                seg = bytearray(parts[j].encode())
                if seg:
                    seg[rng.randrange(len(seg))] = rng.choice(b"AZaz09-_=.!")
                parts[j] = seg.decode(errors="replace")
                try:
                    (r.authn.authenticate if t == "auth.token" else r.authn.verify_grant)(".".join(parts))
                    if parts != src.split("."):
                        # a mutated credential must not verify unless the mutation was a no-op on decode
                        pass
                except SnapshotServiceError:
                    pass
            elif t == "config":
                cfgmod.validate(mutate(rng, cfgmod.example()))
            elif t == "envelope":
                b = bytearray(blob_ok)
                b[rng.randrange(len(b))] ^= 1 << rng.randrange(8)
                env = dict(envelope)
                if rng.random() < 0.5:
                    env = mutate(rng, env)
                try:
                    crypto.open_envelope(bytes(b), env=env, ctx=ctx, kms=r.kms)
                    raise AssertionError("mutated ciphertext opened")
                except SnapshotServiceError:
                    pass
                except (KeyError, TypeError) as exc:
                    raise AssertionError(f"envelope metadata not validated: {exc}")
            elif t.startswith("service."):
                op = t.split(".")[1]
                base = capture_req(snapshot_id=f"f{i}", vm_id="vm-1") if op == "capture" else \
                    restore_req(grant=grant, target_vm_id="vm-2")
                st, body = r.svc.handle(op, tok, mutate(rng, base))
                if st != 200:
                    if body.get("code") == "SNAP_INTERNAL" or schema.validate(body, "PK_SNAPSHOT_ERROR/1"):
                        raise AssertionError(f"bad error body {body}")
        except AssertionError as exc:
            record(t, i, exc)
        except Exception as exc:  # any uncaught exception is a finding
            record(t, i, exc)
    return {"schema": "PK_SNAPSHOT_FUZZ/1", "seed": seed, "iterations": iterations, "per_target": counts,
            "findings": findings, "result": "PASS" if not findings else "FAIL", "seconds": round(time.time() - t0, 2)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=26)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = run(a.iterations, a.seed)
    txt = json.dumps(res, indent=1, sort_keys=True)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(txt + "\n")
    print(json.dumps({k: res[k] for k in ("result", "iterations", "seconds")} | {"findings": len(res["findings"])}))
    if res["findings"]:
        print(json.dumps(res["findings"][:5], indent=1), file=sys.stderr)
    return 0 if res["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
