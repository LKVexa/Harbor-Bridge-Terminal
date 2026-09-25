"""MC-034 benchmark harness, MC-035 SLO certification gate, MC-036 large-payload/DoS suite.

Measures per-operation lower+lift latency (p50/p95/p99), allocation counts and
copied bytes for the Python reference engine and the native Rust/Go fixtures,
then evaluates:

* SLO "boundary cost": p99 lower+lift < 2 us for scalar values.  The gate is
  evaluated per implementation and reported honestly; the contractual SLO
  applies to the *production* runtime path, which this package does not ship
  (MC-019).  Native fixtures stand in as the closest measurable proxy.
* Regression thresholds from ``ci/bench_thresholds.json`` (fail if slower than
  threshold x tolerance).
* DoS characterization: worst-case CPU/memory for large and adversarial inputs,
  and proof that over-limit inputs are refused *before* proportional work.

Usage: python tools/bench.py [--quick] [--out evidence/bench.json]
"""
import argparse
import json
import os
import pathlib
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import tracemalloc

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from canon import layout, types as ty  # noqa: E402
from canon.errors import InteropError  # noqa: E402
from canon.limits import Limits  # noqa: E402
from canon.memory import Allocator, CheckedRealloc, GuestMemory  # noqa: E402
from canon.validate import validate  # noqa: E402

SLO_P99_NS = 2000


def pct(lat, p):
    return lat[min(len(lat) - 1, int(len(lat) * p / 100))]


def time_op(fn, n):
    lat = []
    pc = time.perf_counter_ns
    for _ in range(n):
        t0 = pc()
        fn()
        lat.append(pc() - t0)
    lat.sort()
    return {"n": n, "p50_ns": pct(lat, 50), "p95_ns": pct(lat, 95), "p99_ns": pct(lat, 99)}


def python_suite(n):
    vec = {v["id"]: v for v in json.loads((ROOT / "fixtures/corpus/vectors.json").read_text())["valid"]}
    from canon.cjv import from_cjv
    out = {}
    for vid in ("u32-max", "record-point", "list-string", "record-doc"):
        t = ty.from_descriptor(vec[vid]["descriptor"])
        val = from_cjv(vec[vid]["value"], t)

        def op(t=t, val=val):
            v = validate(val, t)
            img, root = layout.encode(v, t, validated=True)
            layout.decode(img, root, t)
        r = time_op(op, n if vid != "record-doc" else n // 4)
        mem = GuestMemory()
        cr = CheckedRealloc(mem, Allocator(mem))
        layout.lower_to_memory(validate(val, t), t, mem, cr.alloc)
        r["allocations"] = cr.allocations
        r["copied_bytes"] = len(mem)
        out[vid] = r
    return out


def native_suite():
    res = {}
    vec = ROOT / "fixtures/corpus/vectors.json"
    if shutil.which("cargo"):
        subprocess.run(["cargo", "build", "-q", "--release", "--offline"], cwd=ROOT / "fixtures/rust", check=True)
        p = subprocess.run([str(ROOT / "fixtures/rust/target/release/inv12rs"), "bench", str(vec)],
                           capture_output=True, text=True, check=True)
        res["rust"] = json.loads(p.stdout)
    if shutil.which("go"):
        exe = pathlib.Path(tempfile.gettempdir()) / "inv12go"
        subprocess.run(["go", "build", "-o", str(exe), "."], cwd=ROOT / "fixtures/go", check=True)
        p = subprocess.run([str(exe), "bench", str(vec)], capture_output=True, text=True, check=True)
        res["go"] = json.loads(p.stdout)
    return res


def dos_suite():
    rows = []

    def measure(name, fn, expect=None):
        tracemalloc.start()
        t0 = time.perf_counter()
        code = "ok"
        try:
            fn()
        except InteropError as e:
            code = e.code
        dt = time.perf_counter() - t0
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        rows.append({"case": name, "result": code, "seconds": round(dt, 4), "peak_bytes": peak,
                     "expected": expect, "pass": expect is None or code == expect})

    L = ty.parse_type
    measure("list<u8> 100k valid", lambda: layout.encode(list(range(256)) * 390, L("list<u8>")))
    measure("string 16 MiB valid", lambda: layout.encode("a" * (16 * 1024 * 1024), L("string")))
    measure("string 16 MiB + 1 refused", lambda: validate("a" * (16 * 1024 * 1024 + 1), L("string")),
            "PK_INTEROP_LIMIT")
    big = [0] * 5_000_000
    measure("list 5M items refused before iteration", lambda: validate(big, L("list<u8>")), "PK_INTEROP_LIMIT")
    deep_t = L("list<" * 60 + "u8" + ">" * 60)
    v = [1]
    for _ in range(59):
        v = [v]
    measure("nesting depth 60 valid", lambda: layout.encode(v, deep_t))
    measure("node budget exceeded", lambda: validate([[1] * 1000] * 300, L("list<list<u8>>")), "PK_INTEROP_LIMIT")
    measure("total-bytes budget exceeded",
            lambda: validate(["x" * 1_000_000] * 80, L("list<string>")), "PK_INTEROP_LIMIT")
    measure("tight per-interface limit",
            lambda: validate(list(range(100)), L("list<u32>"), limits=Limits(max_list_items=10)), "PK_INTEROP_LIMIT")
    hostile = (0).to_bytes(4, "little") + (0x1FFFFFFF).to_bytes(4, "little")
    measure("hostile list length (lift)", lambda: layout.decode(hostile, 0, L("list<u64>")),
            "PK_INTEROP_MEMORY_BOUNDS")
    hostile3 = (0).to_bytes(4, "little") + (0x20000000).to_bytes(4, "little")
    measure("hostile list length overflow (lift)", lambda: layout.decode(hostile3, 0, L("list<u64>")),
            "PK_INTEROP_MEMORY_OVERFLOW")
    hostile2 = (8).to_bytes(4, "little") + (0xFFFFFF).to_bytes(4, "little") + b"\x00" * 8
    measure("hostile string length (lift)", lambda: layout.decode(hostile2, 0, L("string")),
            "PK_INTEROP_MEMORY_BOUNDS")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "evidence/bench.json"))
    a = ap.parse_args()
    n = 5_000 if a.quick else 50_000
    report = {
        "environment": {"python": platform.python_version(), "machine": platform.machine(),
                        "processor": platform.processor() or "unknown", "cpus": os.cpu_count(),
                        "system": f"{platform.system()} {platform.release()}",
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
        "python_reference": python_suite(n),
        "native": native_suite(),
        "dos": dos_suite(),
    }
    slo = {}
    slo["python_reference"] = report["python_reference"]["u32-max"]["p99_ns"] < SLO_P99_NS
    for lang, r in report["native"].items():
        slo[lang] = r["u32-max"]["p99_ns"] < SLO_P99_NS
    report["slo_boundary_cost_scalar_p99_lt_2us"] = slo
    thr = json.loads((ROOT / "ci/bench_thresholds.json").read_text())
    regress = []
    for impl, cases in thr["p99_ns_max"].items():
        src = report["python_reference"] if impl == "python_reference" else report["native"].get(impl, {})
        for case, limit in cases.items():
            got = src.get(case, {}).get("p99_ns")
            if got is not None and got > limit * thr["tolerance"]:
                regress.append({"impl": impl, "case": case, "p99_ns": got, "limit": limit})
    report["regressions"] = regress
    report["dos_pass"] = all(r["pass"] for r in report["dos"])
    report["verdict"] = {
        "benchmark_regression_gate": "PASS" if not regress else "FAIL",
        "dos_gate": "PASS" if report["dos_pass"] else "FAIL",
        "slo_certification": ("PROXY_PASS_NATIVE_ONLY" if all(v for k, v in slo.items() if k != "python_reference")
                              and report["native"] else "NOT_CERTIFIED"),
    }
    pathlib.Path(a.out).write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({"verdict": report["verdict"], "slo": slo,
                      "python_u32": report["python_reference"]["u32-max"],
                      "native_u32": {k: v["u32-max"] for k, v in report["native"].items()}}, indent=1))
    sys.exit(0 if not regress and report["dos_pass"] else 1)


if __name__ == "__main__":
    main()
