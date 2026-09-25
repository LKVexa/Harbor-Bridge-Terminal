"""INV-44 performance measurement suite (missing component 16).

Measures, never certifies: every result is labelled MEASURED with host facts,
and thresholds stay UNAPPROVED until the owner signs SLO targets. Swivel's own
overhead cannot be measured here (component 8 is BLOCKED).

    python bench/perf_suite.py [--out evidence/PERF_RESULTS.json] [--repeat 5]
"""
from __future__ import annotations

import argparse
import importlib
import json
import pathlib
import platform
import statistics
import sys
import tempfile
import time

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG_DIR.parent))
sys.path.insert(0, str(PKG_DIR / "tests"))
P = PKG_DIR.name
rt = importlib.import_module(f"{P}.runtime")
wv = importlib.import_module(f"{P}.wasm_verify")
al = importlib.import_module(f"{P}.audit_log")
import test_v43 as T  # reuse the test world builder  # noqa: E402
import wasm_fixtures as fx  # noqa: E402


def bench(fn, n: int, repeat: int) -> dict:
    runs = []
    for _ in range(repeat):
        t0 = time.perf_counter()
        for _ in range(n):
            fn()
        runs.append((time.perf_counter() - t0) / n)
    return {"ops_per_run": n, "repeat": repeat, "median_us": round(statistics.median(runs) * 1e6, 3),
            "min_us": round(min(runs) * 1e6, 3), "max_us": round(max(runs) * 1e6, 3)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PKG_DIR / "evidence" / "PERF_RESULTS.json"))
    ap.add_argument("--repeat", type=int, default=5)
    a = ap.parse_args(argv)
    eng = rt.Engine("bench", rt.REQUIRED_HARDENING, memory_page_ceiling=1 << 16)
    inst = eng.instantiate("b", output_valid=True, fuel=10**12)
    mem = eng.instantiate("m", output_valid=True, fuel=1, pages=0)
    data = fx.module(imports=(("env", "log"),))
    big = fx.module(extra=fx.section(0, fx.name("pad") + b"\0" * (1 << 20)))
    rc = T.receipt(data)
    ring = wv.Keyring({"k1": T.KEY})
    tmp = tempfile.mkdtemp()
    authn, authz, audit, metrics, gate, clock = T.make_world(tmp, max_instances=10**9, max_inflight=4)
    p = T.login(authn)
    tok = authz.grant(p, token_id="b", operations={"instantiate"}, imports={"env.log"})
    counter = iter(range(10**9))
    log = al.AuditLog(pathlib.Path(tmp) / "bench.jsonl")
    results = {
        "instance_step": bench(lambda: inst.step(1), 20000, a.repeat),
        "instance_grow_0": bench(lambda: mem.grow(0), 20000, a.repeat),
        "engine_instantiate_legacy": bench(lambda: eng.instantiate("x", output_valid=True, fuel=10), 5000, a.repeat),
        "parse_module_small": bench(lambda: wv.parse_module(data), 5000, a.repeat),
        "parse_module_1MiB": bench(lambda: wv.parse_module(big), 50, a.repeat),
        "verify_receipt": bench(lambda: wv.verify_receipt(data, rc, keyring=ring,
                                                          approved_toolchains=[T.TC.ident()]), 3000, a.repeat),
        "gateway_admit_full_path_fsync": bench(lambda: gate.instantiate(p, tok, f"g{next(counter)}", data, rc, fuel=5),
                                               200, a.repeat),
        "audit_append_fsync": bench(lambda: log.append("b", actor="bench", outcome="success"), 200, a.repeat),
    }
    out = {
        "schema": "INV44_PERF_RESULTS/1",
        "label": "MEASURED",
        "thresholds": "UNAPPROVED",
        "host": {"python": platform.python_version(), "implementation": platform.python_implementation(),
                 "machine": platform.machine(), "system": platform.system()},
        "not_measured": ["Swivel compile/run overhead vs. unhardened baseline (component 8 BLOCKED)",
                         "soak, burst at fleet scale, power/thermal, multi-node capacity"],
        "results": results,
    }
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for k, v in results.items():
        print(f"{k:34s} median {v['median_us']:>10.3f} us")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
