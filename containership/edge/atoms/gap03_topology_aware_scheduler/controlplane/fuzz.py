"""MC-033 - Seeded fuzz driver with limits, regression corpus and minimisation.

Targets are callables taking bytes.  Acceptable outcomes: return or raise
``SchedulerError``.  Anything else (uncaught exception, hang past the time
limit, output over the memory proxy limit) is a finding; the input is
delta-minimised and written to the regression corpus with seed + env metadata.
"""
from __future__ import annotations

from .canonical import readb

import json
import os
import platform
import random
import sys
import time

from .errors import SchedulerError

SEEDS = [
    b'{"schema":"PK_TOPOLOGY/1.1","environment":"prod","generation":1,"nodes":[{"node":"a","region":"eu","site":"d","rack":"r"}]}',
    b'{"schema":"PK_FAIR_SHARE/1.0","ledger_revision":1,"capacity":4,"tenant":"t","requested_slots":1,"allowed":true,'
    b'"reason":"surplus_available","reserved_slots":0,"held_slots":0,"state_token":"' + b"0" * 64 + b'","starved_tenants":[]}',
    b'{"schema":"PK_LOCALITY_COST/1.0","topology_generation":1,"a":"x","b":"y","cost":1,"level":"same_rack"}',
]
DICT = [b"{", b"}", b"[", b"]", b'"', b"\\u0000", b"1e999", b"NaN", b"-0", b"9" * 40, b'"a":1,"a":2', b"\xff", b"\xc0\x80",
        b"null", b"true", b"\\ud800", b"[" * 64, b"\x00", b"\xe2\x80\xae", b",", b":"]


def mutate(rng: random.Random, data: bytes, pool=None) -> bytes:
    b = bytearray(data)
    for _ in range(rng.randint(1, 4)):
        op = rng.randrange(5)
        pos = rng.randrange(len(b) + 1)
        if op == 0 and b:
            b[rng.randrange(len(b))] = rng.randrange(256)
        elif op == 1:
            b[pos:pos] = rng.choice(DICT)
        elif op == 2 and b:
            del b[pos:pos + rng.randint(1, 8)]
        elif op == 3 and b:
            s = rng.randrange(len(b))
            b[pos:pos] = b[s:s + rng.randint(1, 16)]
        else:
            b = bytearray(rng.choice(pool or SEEDS))
    return bytes(b[:1 << 16])


def _ok(target, data, time_limit):
    t = time.perf_counter()
    try:
        out = target(data)
    except SchedulerError:
        out = None
    except RecursionError:
        return False, "recursion"
    except Exception as exc:  # noqa: BLE001
        return False, f"uncaught:{exc.__class__.__name__}"
    if time.perf_counter() - t > time_limit:
        return False, "slow"
    if out is not None and len(repr(out)) > 8 << 20:
        return False, "memory"
    return True, None


def minimize(target, data: bytes, time_limit: float) -> bytes:
    n = 2
    while len(data) >= 2:
        chunk = max(1, len(data) // n)
        reduced = False
        for i in range(0, len(data), chunk):
            cand = data[:i] + data[i + chunk:]
            if not _ok(target, cand, time_limit)[0]:
                data, n, reduced = cand, max(n - 1, 2), True
                break
        if not reduced:
            if chunk == 1:
                break
            n = min(len(data), n * 2)
    return data


def run(target, *, name: str, seed: int, iterations: int, time_limit: float = 0.5, corpus_dir: str | None = None,
        seeds: list[bytes] | None = None) -> dict:
    rng = random.Random(seed)
    findings = []
    corpus = list(SEEDS) + list(seeds or [])
    if corpus_dir and os.path.isdir(corpus_dir):
        for fn in sorted(os.listdir(corpus_dir)):
            if fn.endswith(".bin"):
                corpus.append(readb(os.path.join(corpus_dir, fn)))
    for c in corpus:  # regression corpus first
        ok, why = _ok(target, c, time_limit)
        if not ok:
            findings.append({"input": c.hex(), "why": why, "regression": True})
    for i in range(iterations):
        data = mutate(rng, rng.choice(corpus), corpus)
        ok, why = _ok(target, data, time_limit)
        if not ok:
            small = minimize(target, data, time_limit)
            findings.append({"input": small.hex(), "why": why, "iteration": i})
            if corpus_dir:
                os.makedirs(corpus_dir, exist_ok=True)
                open(os.path.join(corpus_dir, f"{name}-{seed}-{i}.bin"), "wb").write(small)
    return {"target": name, "seed": seed, "iterations": iterations, "findings": findings,
            "env": {"python": sys.version.split()[0], "platform": platform.platform()}}


def write_report(report: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, sort_keys=True)
