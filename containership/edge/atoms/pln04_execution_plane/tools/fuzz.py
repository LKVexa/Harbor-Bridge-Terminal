"""M23 - seeded fuzz + property harness (stdlib only).

    python tools/fuzz.py --iterations 5000 --seed 1

Targets: bounded JSON parse/validate, signed-envelope parser, config loader,
identifier validation, WAL recovery, and a model-based property test of the
plane (random admit/teardown/attestation/reap sequences with invariants).
Any exception other than the documented typed errors is a finding.
"""
from __future__ import annotations

import json
import os
import pathlib
import random
import shutil
import string
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))

from pln04_execution_plane import errors, policy, providers, runtime, security, store, validation  # noqa: E402
from pln04_execution_plane import plane as plane_mod  # noqa: E402
from pln04_execution_plane.resilience import RetryPolicy  # noqa: E402

EXPECTED = (errors.PlaneError, ValueError, TypeError, PermissionError, runtime.ExecutionPlaneError)
SEED_DOC = {"schema": "PK_ADMISSION/1", "kind": "request", "request_id": "r", "workload": "w",
            "tenant": "t", "trust_class": "trusted"}


def _rand_value(rng: random.Random, depth: int = 0):
    choice = rng.randrange(9 if depth < 4 else 6)
    if choice == 0:
        return rng.randint(-2**40, 2**40)
    if choice == 1:
        return rng.random() * rng.choice([1, 1e308, -1e-308])
    if choice == 2:
        return "".join(rng.choice(string.printable + "\x00‮퟿") for _ in range(rng.randrange(0, 300)))
    if choice == 3:
        return rng.choice([True, False, None])
    if choice == 4:
        return rng.choice(runtime.TIERS + tuple(runtime.TRUST_CLASSES))
    if choice == 5:
        return ""
    if choice == 6:
        return [_rand_value(rng, depth + 1) for _ in range(rng.randrange(4))]
    return {rng.choice(list(SEED_DOC) + ["x", "resources", "deadline_ms"]): _rand_value(rng, depth + 1) for _ in range(rng.randrange(4))}


def fuzz_parse(rng: random.Random) -> None:
    doc = dict(SEED_DOC)
    for _ in range(rng.randrange(1, 4)):
        doc[rng.choice(list(SEED_DOC) + ["tier", "idempotency_key", "resources", "extra"])] = _rand_value(rng)
    raw = json.dumps(doc, allow_nan=True).encode()
    if rng.random() < 0.3:
        raw = bytearray(raw)
        for _ in range(rng.randrange(1, 8)):
            raw[rng.randrange(len(raw))] = rng.randrange(256)
        raw = bytes(raw)
    if rng.random() < 0.05:
        raw = b"[" * rng.randrange(10, 5000) + raw
    try:
        validation.parse(raw, "PK_ADMISSION/1")
    except EXPECTED:
        pass


def fuzz_envelope(rng: random.Random, ring) -> None:
    parts = [security._b64e(json.dumps(_rand_value(rng)).encode()) for _ in range(3)]
    token = ".".join(parts[: rng.randrange(1, 4)])
    if rng.random() < 0.3:
        token = "".join(rng.choice(string.printable) for _ in range(rng.randrange(0, 200)))
    try:
        security.open_sealed(token, "pln04.actor", {"HS256": ring})
        raise AssertionError("forged/random envelope verified")
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError, TypeError):
        pass


def fuzz_config(rng: random.Random) -> None:
    over = {rng.choice(list(policy.DEFAULT_CONFIG)): _rand_value(rng) for _ in range(rng.randrange(1, 3))}
    try:
        policy.PlaneConfig.load(over)
    except EXPECTED:
        pass


def fuzz_identifier(rng: random.Random) -> None:
    node = runtime.Node({"process": True})
    try:
        runtime.admit(node, _rand_value(rng), _rand_value(rng), rng.choice(list(runtime.TRUST_CLASSES)))
    except EXPECTED:
        pass


def fuzz_wal(rng: random.Random) -> None:
    d = tempfile.mkdtemp()
    try:
        s = store.FileStateStore(d, fsync=False)
        for i in range(rng.randrange(1, 6)):
            s.cas(f"k{i}", 0, {"i": i})
        s.close()
        path = os.path.join(d, "state.wal.jsonl")
        data = bytearray(open(path, "rb").read())
        for _ in range(rng.randrange(1, 4)):
            data[rng.randrange(len(data))] = rng.randrange(256)
        open(path, "wb").write(bytes(data))
        try:
            store.FileStateStore(d, fsync=False).close()
        except errors.PlaneError:
            pass
    finally:
        shutil.rmtree(d, ignore_errors=True)


def property_plane(rng: random.Random, steps: int = 60) -> None:
    reg = providers.ProviderRegistry(allow_reference=True)
    provs = {t: providers.ReferenceProvider(t) for t in runtime.TIERS}
    for p in provs.values():
        reg.register(p)
    pl = plane_mod.ExecutionPlane(policy.PlaneConfig.load({"limits": {"max_instances": 20, "per_tenant_limit": 8,
                                                                       "cpu_milli": 16000, "memory_mib": 16384, "headroom": 0.1}}),
                                  reg, retry_policy=RetryPolicy(max_attempts=2, base_s=0.0001, cap_s=0.0002))
    for t in runtime.TIERS:
        pl.attest_tier(t)
    for _ in range(steps):
        op = rng.random()
        wl, tenant = f"w{rng.randrange(12)}", f"t{rng.randrange(3)}"
        try:
            if op < 0.5:
                if rng.random() < 0.15:
                    provs[rng.choice(runtime.TIERS)].fail_start = 1
                pl.admit({**SEED_DOC, "workload": wl, "tenant": tenant, "trust_class": rng.choice(list(runtime.TRUST_CLASSES)),
                          "resources": {"cpu_milli": rng.choice([250, 1000, 3000]), "memory_mib": 256}})
            elif op < 0.8:
                if rng.random() < 0.1:
                    provs[rng.choice(runtime.TIERS)].zeroize_unverifiable = True
                pl.teardown(wl, tenant)
            elif op < 0.88:
                tier = rng.choice(runtime.TIERS)
                pl.fail_tier(tier, "fuzz")
                pl.attest_tier(tier)
            else:
                for p in provs.values():
                    p.zeroize_unverifiable = False
                pl.reap()
        except errors.PlaneError:
            pass
        # ---- invariants
        records = {k[5:]: r for k, _, r in pl.store.items("inst/")}
        for name, inst in pl.node.instances.items():
            assert name in records, f"node has {name} unknown to store"
            assert records[name]["tier"] == inst.tier
            assert runtime.TIERS.index(inst.tier) >= runtime.TIERS.index(runtime.TRUST_CLASSES[inst.trust_class]), "below floor"
        live = [i.workload for p in provs.values() for i in p.list_instances()]
        assert len(live) == len(set(live)), "duplicate live provider instance"
        for name, rec in records.items():
            if rec["state"] == "active":
                assert name in live, f"{name} active without provider instance"
        usage = pl.fair.usage()
        for tenant_id, used in usage.items():
            expect = sum(r["resources"]["cpu_milli"] for r in records.values() if r["tenant"] == tenant_id)
            assert used["cpu_milli"] == expect, f"fair-share drift for {tenant_id}: {used} vs {expect}"
        assert pl.audit._node.verify_audit_chain()


def run(iterations: int, seed: int) -> dict:
    rng = random.Random(seed)
    ring = security.HmacKeyring()
    ring.add("k1", b"f" * 32)
    counts = {}
    targets = [("parse", fuzz_parse), ("envelope", lambda r: fuzz_envelope(r, ring)), ("config", fuzz_config),
               ("identifier", fuzz_identifier)]
    for name, fn in targets:
        for _ in range(iterations):
            fn(rng)
        counts[name] = iterations
    for _ in range(max(1, iterations // 50)):
        fuzz_wal(rng)
    counts["wal"] = max(1, iterations // 50)
    for _ in range(max(1, iterations // 100)):
        property_plane(rng)
    counts["plane_property_runs"] = max(1, iterations // 100)
    return counts


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    print(json.dumps({"seed": args.seed, "result": "PASS", "counts": run(args.iterations, args.seed)}, indent=2))
