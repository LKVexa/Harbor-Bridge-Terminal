"""M14 - fuzzing harness and malformed corpus.

Two engines, both deterministic from a seed so every finding reproduces:

* **mutation fuzzing** over the seed corpus (bit flips, interesting bytes,
  insert/delete/splice, truncation, section duplication, LEB over-length);
* **generative fuzzing**: a typed random program generator that emits
  *valid* function bodies (tracking the operand stack), then mutates them -
  this reaches deep type-checker states that byte mutation rarely hits.

Oracle (safety properties checked on every input):
  1. only :class:`InvalidModule` escapes; never ``INTERNAL_ERROR``;
  2. validation is deterministic (same bytes -> same verdict, twice);
  3. every input finishes inside the M13 deadline.
Inputs are also fed to the M15 differential oracle in batches.
"""
from __future__ import annotations

import random
import time
from typing import Callable, Iterator

from .errors import Code, InvalidModule
from .typecheck import validate_module

INTERESTING = [0x00, 0x01, 0x7F, 0x80, 0xFF, 0x40, 0x0B, 0x60, 0x70, 0x6F, 0x7B, 0xFC, 0xFD, 0xFE]

I32, I64, F32, F64 = 0x7F, 0x7E, 0x7D, 0x7C


def _u(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _s(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        done = (n == 0 and not b & 0x40) or (n == -1 and b & 0x40)
        out.append(b if done else b | 0x80)
        if done:
            return bytes(out)


# ------------------------------------------------------------- mutation
def mutate(rng: random.Random, data: bytes, corpus: list[bytes]) -> bytes:
    b = bytearray(data)
    for _ in range(rng.randint(1, 4)):
        op = rng.randrange(9)
        if not b:
            b = bytearray(rng.choice(corpus))
        i = rng.randrange(len(b))
        if op == 0:
            b[i] ^= 1 << rng.randrange(8)
        elif op == 1:
            b[i] = rng.choice(INTERESTING)
        elif op == 2:
            b.insert(i, rng.randrange(256))
        elif op == 3 and len(b) > 9:
            del b[max(8, i)]
        elif op == 4:
            other = rng.choice(corpus)
            j = rng.randrange(len(other))
            b[i:] = other[j:j + rng.randint(1, 32)] + b[i:]
        elif op == 5:
            del b[rng.randint(8, max(8, len(b))):]
        elif op == 6:  # over-long / overflowing LEB
            b[i:i + 1] = rng.choice([b"\x80\x80\x80\x80\x00", b"\xff\xff\xff\xff\x0f",
                                     b"\xff\xff\xff\xff\x7f", b"\x80\x80\x80\x80\x80\x00"])
        elif op == 7 and len(b) > 12:  # duplicate a chunk (often a section)
            j = rng.randrange(8, len(b))
            b[j:j] = b[j:j + rng.randint(2, 16)]
        else:
            b[i] = rng.randrange(256)
    return bytes(b)


# ------------------------------------------------------------- generator
_BIN = {I32: [0x6A, 0x6B, 0x6C, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76], I64: [0x7C, 0x7D, 0x7E, 0x83, 0x84],
        F32: [0x92, 0x93, 0x94, 0x96, 0x97], F64: [0xA0, 0xA1, 0xA2, 0xA4, 0xA5]}
_CMP = {I32: 0x46, I64: 0x51, F32: 0x5B, F64: 0x61}
_CONST = {I32: lambda r: b"\x41" + _s(r.randint(-2**31, 2**31 - 1)),
          I64: lambda r: b"\x42" + _s(r.randint(-2**63, 2**63 - 1)),
          F32: lambda r: b"\x43" + r.randbytes(4), F64: lambda r: b"\x44" + r.randbytes(8)}
_CONV = [(0xA7, I64, I32), (0xAC, I32, I64), (0xB2, I32, F32), (0xB7, I32, F64), (0xBB, F32, F64),
         (0xB6, F64, F32), (0xBC, F32, I32), (0xBF, I64, F64), (0xC0, I32, I32), (0xC4, I64, I64)]


def gen_expr(rng: random.Random, t: int, depth: int, locals_: list[int]) -> bytes:
    """Emit code that leaves exactly one value of type ``t`` on the stack."""
    if depth <= 0 or rng.random() < 0.25:
        cands = [i for i, lt in enumerate(locals_) if lt == t]
        if cands and rng.random() < 0.5:
            return b"\x20" + _u(rng.choice(cands))
        return _CONST[t](rng)
    k = rng.randrange(7)
    if k == 0:
        return gen_expr(rng, t, depth - 1, locals_) + gen_expr(rng, t, depth - 1, locals_) + bytes([rng.choice(_BIN[t])])
    if k == 1 and t == I32:
        st = rng.choice([I32, I64, F32, F64])
        return gen_expr(rng, st, depth - 1, locals_) + gen_expr(rng, st, depth - 1, locals_) + bytes([_CMP[st]])
    if k == 2:
        convs = [c for c in _CONV if c[2] == t]
        if convs:
            op, src, _ = rng.choice(convs)
            return gen_expr(rng, src, depth - 1, locals_) + bytes([op])
    if k == 3:  # block with result + optional br_if
        inner = gen_expr(rng, t, depth - 1, locals_)
        if rng.random() < 0.5:
            inner = gen_expr(rng, t, depth - 1, locals_) + gen_expr(rng, I32, depth - 1, locals_) + b"\x0d\x00\x1a" + inner
        return b"\x02" + bytes([t]) + inner + b"\x0b"
    if k == 4:  # if/else
        return (gen_expr(rng, I32, depth - 1, locals_) + b"\x04" + bytes([t]) + gen_expr(rng, t, depth - 1, locals_)
                + b"\x05" + gen_expr(rng, t, depth - 1, locals_) + b"\x0b")
    if k == 5:  # select
        return gen_expr(rng, t, depth - 1, locals_) + gen_expr(rng, t, depth - 1, locals_) + gen_expr(rng, I32, depth - 1, locals_) + b"\x1b"
    if k == 6:  # loop that falls through
        return b"\x03" + bytes([t]) + gen_expr(rng, t, depth - 1, locals_) + b"\x0b"
    return _CONST[t](rng)


def gen_module(rng: random.Random) -> bytes:
    from_types = [I32, I64, F32, F64]
    params = [rng.choice(from_types) for _ in range(rng.randint(0, 3))]
    result = rng.choice(from_types)
    locals_ = params + [rng.choice(from_types) for _ in range(rng.randint(0, 3))]
    body_locals = locals_[len(params):]
    code = gen_expr(rng, result, rng.randint(1, 6), locals_) + b"\x0b"
    lg = b"".join(_u(1) + bytes([t]) for t in body_locals)
    body = _u(len(body_locals)) + lg + code
    functype = b"\x60" + _u(len(params)) + bytes(params) + b"\x01" + bytes([result])

    def sec(i, p):
        return bytes([i]) + _u(len(p)) + p
    return (b"\x00asm\x01\x00\x00\x00" + sec(1, b"\x01" + functype) + sec(3, b"\x01\x00")
            + sec(10, b"\x01" + _u(len(body)) + body))


# ------------------------------------------------------------- driver
def inputs(seed: int, seeds: list[bytes], n: int) -> Iterator[tuple[str, bytes]]:
    rng = random.Random(seed)
    corpus = list(seeds)
    for i in range(n):
        r = rng.random()
        if r < 0.35:
            m = gen_module(rng)
        elif r < 0.55:
            m = mutate(rng, gen_module(rng), corpus)
        else:
            m = mutate(rng, rng.choice(corpus), corpus)
        yield f"s{seed}-i{i}", m


def run(seed: int, seeds: list[bytes], n: int, on_input: Callable[[str, bytes], None] | None = None) -> dict:
    stats: dict[str, int] = {}
    crashes: list[dict] = []
    nondet: list[str] = []
    slowest = 0.0
    t0 = time.perf_counter()
    for name, m in inputs(seed, seeds, n):
        t = time.perf_counter()
        res = []
        for _ in range(2):
            try:
                validate_module(m)
                res.append("OK")
            except InvalidModule as e:
                res.append(e.code.value)
                if e.code == Code.INTERNAL_ERROR:
                    crashes.append({"name": name, "hex": m.hex(), "detail": e.detail})
            except Exception as e:  # noqa: BLE001 - oracle violation
                res.append("ESCAPED:" + type(e).__name__)
                crashes.append({"name": name, "hex": m.hex(), "detail": repr(e)})
        slowest = max(slowest, (time.perf_counter() - t) / 2)
        if res[0] != res[1]:
            nondet.append(name)
        stats[res[0]] = stats.get(res[0], 0) + 1
        if on_input:
            on_input(name, m)
    return {"schema": "PK_FUZZ_REPORT/1", "seed": seed, "executions": n,
            "seconds": round(time.perf_counter() - t0, 2), "slowest_ms": round(slowest * 1000, 2),
            "outcomes": dict(sorted(stats.items())), "crashes": crashes, "nondeterministic": nondet}
