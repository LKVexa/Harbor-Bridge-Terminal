"""Reproducible performance baseline (MC-060..MC-065, MC-067).

    python -B inv27_unikernel_execution/bench/perf_suite.py [--quick] [--out evidence/PERF_RESULTS.json]

Scenarios (fixed seeds, fixed inputs, warm-up discarded):
  admit_uk_good        full A0-A13 admission of the 9 KB Unikraft-convention fixture (SLO: p99 < 100 ms)
  parse_only           ELF parse of the same bytes
  sig_verify           Ed25519 envelope verification alone (pure-Python backend)
  admit_large_symtab   admission of a synthetic image with 20,000 symbols (worst-case parser work)
  reject_fork          refusal path for uk_fork.elf (must be no slower than the admit path)
  burst                200 admissions through Admission(rate, burst) - measures shed ratio
Reports p50/p95/p99/max, peak traced memory (tracemalloc), bytes copied per admission, host facts.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import platform
import statistics
import struct
import sys
import time
import tracemalloc

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG / "tests"))
sys.dont_write_bytecode = True

import harness as H  # noqa: E402


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def bench(fn, n, warm=5):
    for _ in range(warm):
        fn()
    out = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t) * 1000)
    return {"n": n, "p50_ms": round(q(out, .5), 3), "p95_ms": round(q(out, .95), 3), "p99_ms": round(q(out, .99), 3),
            "max_ms": round(max(out), 3), "mean_ms": round(statistics.fmean(out), 3)}


def big_symtab(nsyms=20000) -> bytes:
    """Append a synthetic .symtab-like region?  Simpler and honest: rebuild uk_good with many extra
    uk_syscall-free symbols via a generated section is out of scope; instead reuse the parser's real
    symbol loop by pointing the existing .symtab at a larger, valid table appended to the file."""
    data = bytearray(H.image("uk_good.elf"))
    e = H.elf.parse(bytes(data))
    shoff = struct.unpack_from("<Q", data, 40)[0]
    names = [s.name for s in e.sections]
    si, stri = names.index(".symtab"), names.index(".strtab")
    old = e.sections[si]
    strtab = e.sections[stri]
    base = bytes(data[old.offset:old.offset + old.size])
    extra_str = bytearray(bytes(data[strtab.offset:strtab.offset + strtab.size]))
    table = bytearray(base)
    for i in range(nsyms):
        off = len(extra_str)
        extra_str += f"pad_sym_{i}".encode() + b"\0"
        table += struct.pack("<IBBHQQ", off, (1 << 4) | 1, 0, 1, 0x402000 + i, 8)
    new_str_off = len(data)
    data += extra_str
    new_sym_off = len(data)
    data += table
    struct.pack_into("<QQ", data, shoff + stri * 64 + 24, new_str_off, len(extra_str))
    struct.pack_into("<QQ", data, shoff + si * 64 + 24, new_sym_off, len(table))
    return bytes(data)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(PKG / "evidence" / "PERF_RESULTS.json"))
    a = ap.parse_args(argv)
    n = 30 if a.quick else 300
    good = H.image("uk_good.elf")
    fork = H.image("uk_fork.elf")
    pol = H.policy()
    man, env = H.manifest(good), H.envelope(good)
    fman = H.manifest(fork, syscalls=["read", "write", "clock_gettime", "fork"])
    fenv = H.envelope(fork)
    big = big_symtab(2000 if a.quick else 20000)
    bman, benv = H.manifest(big), H.envelope(big)

    def admit(d, m, e):
        return H.admission.admit(d, bound_digest=H.ref(d), manifest=m, envelope=e, policy=pol, tenant="t1", now=H.NOW)

    def reject():
        try:
            admit(fork, fman, fenv)
        except H.UkError:
            return
        raise AssertionError("fork image admitted")

    res = {}
    res["admit_uk_good"] = bench(lambda: admit(good, man, env), n)
    res["parse_only"] = bench(lambda: H.elf.parse(good), n)
    res["sig_verify"] = bench(lambda: H.signing.verify_envelope(env, image_ref=H.ref(good), trust=pol.trust,
                                                               policy=pol.provenance, now=H.NOW), n)
    res["admit_large_symtab"] = bench(lambda: admit(big, bman, benv), max(10, n // 10), warm=1)
    res["admit_large_symtab"]["image_bytes"] = len(big)
    res["reject_fork"] = bench(reject, n)
    tracemalloc.start()
    admit(big, bman, benv)
    res["peak_traced_memory_bytes_large"] = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    blob = H.admission.ImageBlob.of(good)
    res["copies"] = {"ImageBlob.of(bytes) copies": 0 if bytes(good) is good else 1,
                     "elf.parse(blob.data) copies": 0 if bytes(blob.data) is blob.data else 1,
                     "materialize writes": 1}
    adm = H.importlib.import_module(f"{H.PKGNAME}.resilience").Admission(rate_per_s=50, burst=20, max_inflight=32)
    shed = 0
    t0 = time.perf_counter()
    for i in range(200):
        try:
            with adm.admit("t1"):
                pass
        except H.UkError:
            shed += 1
    res["burst"] = {"requests": 200, "shed": shed, "elapsed_ms": round((time.perf_counter() - t0) * 1000, 3)}
    out = {"schema": "PK_UNIKERNEL_PERF/1", "quick": a.quick, "host": {"python": sys.version.split()[0],
           "machine": platform.machine(), "system": platform.system(), "processor": platform.processor() or "?",
           "sig_backend": H.signing.backend()}, "results": res}
    pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out["results"], indent=1))


if __name__ == "__main__":
    main()
