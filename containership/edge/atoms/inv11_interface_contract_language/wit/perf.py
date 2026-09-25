"""Benchmark harness, scale/soak runner and capacity model (INV11-MC-26/27/28).

Datasets are generated deterministically from a seed, so results are
reproducible modulo machine speed; each run records the machine profile.
"""
from __future__ import annotations

import functools
import gc
import platform
import random
import statistics
import time
import tracemalloc
from collections.abc import Callable
from typing import Any

from .compat import classify_packages
from .parser import parse_text
from .resolve import resolve_documents

PRIMS = ["u8", "u16", "u32", "u64", "s32", "s64", "f32", "f64", "string", "bool", "char"]


def gen_package(seed: int, n_ifaces: int, n_funcs: int, n_types: int, version: str = "1.0.0", mutate: float = 0.0) -> str:
    rnd = random.Random(seed)
    mut = random.Random(seed * 7919 + 1)
    out = [f"package bench:p{seed % 1000}@{version};"]
    for i in range(n_ifaces):
        lines = [f"interface if{i} {{"]
        for t in range(n_types):
            fields = ", ".join(f"f{k}: {rnd.choice(PRIMS)}" for k in range(1 + rnd.randrange(6)))
            if mutate and mut.random() < mutate:
                fields += ", extra: u8"
            lines.append(f"  record rec{t} {{ {fields} }}")
        for f in range(n_funcs):
            ps = ", ".join(f"a{k}: {rnd.choice(PRIMS + [f'rec{rnd.randrange(n_types)}' if n_types else 'u8'])}" for k in range(rnd.randrange(4)))
            res = rnd.choice(PRIMS + [f"list<{rnd.choice(PRIMS)}>", f"option<{rnd.choice(PRIMS)}>"])
            lines.append(f"  op{f}: func({ps}) -> {res};")
        if mutate and mut.random() < mutate:
            lines.append("  added-op: func();")
        lines.append("}")
        out.append("\n".join(lines))
    return "\n".join(out) + "\n"


def resolve_text(text: str) -> Any:
    r = parse_text(text)
    res = resolve_documents(r.documents, diags=r.diagnostics)
    if not res.ok:
        raise ValueError([d.render() for d in res.diagnostics.sorted()][:3])
    return res


def _pct(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    k = max(0, min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1)))))
    return xs[k]


def timeit(fn: Callable[[], Any], n: int) -> dict[str, float]:
    samples = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t) * 1000)
    return {"n": n, "p50_ms": _pct(samples, 50), "p95_ms": _pct(samples, 95), "p99_ms": _pct(samples, 99),
            "mean_ms": statistics.fmean(samples), "max_ms": max(samples)}


def machine() -> dict[str, str]:
    return {"python": platform.python_version(), "impl": platform.python_implementation(),
            "machine": platform.machine(), "system": platform.system()}


def benchmark(iterations: int = 200) -> dict[str, Any]:
    """SLO under test: comparison latency p99 < 5 ms per interface pair."""
    sizes = {"small": (1, 10, 3), "medium": (1, 60, 15), "large": (1, 300, 60)}
    out: dict[str, Any] = {"machine": machine(), "slo_p99_ms": 5.0, "cases": {}}
    for name, (ni, nf, nt) in sizes.items():
        a_txt = gen_package(11, ni, nf, nt, "1.0.0")
        b_txt = gen_package(11, ni, nf, nt, "1.1.0", mutate=0.3)
        a, b = resolve_text(a_txt), resolve_text(b_txt)
        n = iterations if name != "large" else max(20, iterations // 5)
        cold = timeit(functools.partial(classify_packages, resolve_text(a_txt), resolve_text(b_txt)), 1)["max_ms"]
        classify_packages(a, b)  # warm-up: fingerprints are cached per immutable Resolved
        out["cases"][name] = {
            "compare_cold_first_call_ms": cold,
            "source_bytes": len(a_txt), "functions": nf, "types": nt,
            "parse": timeit(functools.partial(parse_text, a_txt), max(10, n // 4)),
            "compare": timeit(functools.partial(classify_packages, a, b), n),
        }
        out["cases"][name]["compare_meets_slo"] = out["cases"][name]["compare"]["p99_ms"] < 5.0
        out["cases"][name]["tokens_per_s"] = int(len(a_txt.split()) / (out["cases"][name]["parse"]["mean_ms"] / 1000))
    return out


def soak(packages: int = 2000, rounds: int = 3) -> dict[str, Any]:
    """Thousands of packages, repeated rounds; reports memory growth between rounds."""
    gc.collect()
    tracemalloc.start()
    peaks, currents, t0 = [], [], time.perf_counter()
    classes: dict[str, int] = {}
    for _ in range(rounds):
        for i in range(packages):
            a = resolve_text(gen_package(i, 1, 6, 2, "1.0.0"))
            b = resolve_text(gen_package(i, 1, 6, 2, "1.0.1", mutate=0.25))
            c = classify_packages(a, b)["class"]
            classes[c] = classes.get(c, 0) + 1
        gc.collect()
        cur, peak = tracemalloc.get_traced_memory()
        currents.append(cur)
        peaks.append(peak)
    tracemalloc.stop()
    growth = currents[-1] - currents[0]
    return {"machine": machine(), "packages_per_round": packages, "rounds": rounds,
            "comparisons": packages * rounds, "seconds": round(time.perf_counter() - t0, 2),
            "retained_bytes_by_round": currents, "peak_bytes": max(peaks),
            "growth_bytes_first_to_last": growth, "leak_suspected": growth > 1_000_000, "class_counts": classes}


def capacity_fit() -> dict[str, Any]:
    """Fit compare time and memory against function count (expected O(n))."""
    rows = []
    for nf in (25, 50, 100, 200, 400, 800):
        a = resolve_text(gen_package(5, 1, nf, max(1, nf // 5), "1.0.0"))
        b = resolve_text(gen_package(5, 1, nf, max(1, nf // 5), "1.1.0", mutate=0.3))
        t = timeit(functools.partial(classify_packages, a, b), 15)["p50_ms"]
        tracemalloc.start()
        classify_packages(a, b)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rows.append({"functions": nf, "compare_p50_ms": round(t, 4), "peak_bytes": peak})
    xs = [r["functions"] for r in rows]
    ys = [r["compare_p50_ms"] for r in rows]
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=True)) / sum((x - mx) ** 2 for x in xs)
    ratio = (ys[-1] / ys[0]) / (xs[-1] / xs[0])
    return {"rows": rows, "ms_per_function": slope, "scaling_ratio_vs_linear": ratio,
            "model": "compare = O(F + T + E) for F functions, T types, E type edges; memory O(F + T)",
            "max_functions_within_slo_estimate": int(5.0 / slope) if slope > 0 else None}
