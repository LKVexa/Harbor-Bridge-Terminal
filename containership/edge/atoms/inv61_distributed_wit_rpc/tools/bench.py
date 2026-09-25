"""M28 - reproducible micro/loopback benchmark. Emits JSON; compares against the
README SLO (p99 framing overhead < 50 us) and an optional baseline for regressions.

    python tools/bench.py --out evidence/bench.json [--baseline old.json --max-regress 0.25]
"""
from __future__ import annotations

import argparse, json, os, platform, resource, statistics, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from rpc import fingerprint  # noqa: E402
from wrpc import codec, controls, ops, security, wit, node  # noqa: E402

WIT = "package b:m@1.0.0; interface i { record r { k: string, v: list<u8> } f: func(a: r, n: u64) -> u64; }"


def pct(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p / 100 * len(xs)))]


def bench_framing(n):
    f = wit.parse(WIT).interfaces["i"].functions["f"]
    types = [t for _, t in f.params]
    fp = fingerprint(f.param_texts(), f.result_texts())
    args = [{"k": "key-123", "v": list(range(64))}, 42]
    samples = []
    for _ in range(n):
        t0 = time.perf_counter_ns()
        frame = codec.encode_frame({"interface": "b:m/i", "version": "1.0.0", "function": "f", "fp": fp,
                                    "deadline": 1e12, "request_id": "00" * 16, "traceparent": ""},
                                   codec.encode_args(types, args))
        h, payload = codec.decode_header(frame)
        assert h["fp"] == fingerprint(f.param_texts(), f.result_texts())
        codec.decode_args(types, payload)
        samples.append((time.perf_counter_ns() - t0) / 1000)
    return {"n": n, "bytes": len(frame), "p50_us": pct(samples, 50), "p99_us": pct(samples, 99),
            "mean_us": statistics.fmean(samples)}


def bench_envelope_only(n):
    """The SLO's 'framing overhead': envelope encode + header decode + cached fingerprint
    compare, with a pre-encoded payload (argument codec cost excluded)."""
    f = wit.parse(WIT).interfaces["i"].functions["f"]
    fp = fingerprint(f.param_texts(), f.result_texts())
    payload = codec.encode_args([t for _, t in f.params], [{"k": "key-123", "v": list(range(64))}, 42])
    samples = []
    for _ in range(n):
        t0 = time.perf_counter_ns()
        frame = codec.encode_frame({"interface": "b:m/i", "version": "1.0.0", "function": "f", "fp": fp,
                                    "deadline": 1e12, "request_id": "00" * 16, "traceparent": ""}, payload)
        h, _ = codec.decode_header(frame)
        assert h["fp"] == fp
        samples.append((time.perf_counter_ns() - t0) / 1000)
    return {"n": n, "p50_us": pct(samples, 50), "p99_us": pct(samples, 99)}


def bench_loopback(n):
    pkg = wit.parse(WIT)
    kr = security.Keyring(); psk = os.urandom(32); kid = kr.add("c", psk, 3600)
    cfg, _ = ops.ConfigStore.build(("bench", {"log_level": "ERROR", "trace_sample_ratio": 0.0}))
    nd = node.Node(cfg, kr, pkg, {("b:m/i", "f"): lambda a, n: n + len(a["v"])}, {"c": "t"},
                   controls.Authorizer([controls.Grant("t", "c", "*", "*")]))
    h, p = nd.start()
    c = node.Client(h, p, "c", kid, psk, cfg["node_id"], pkg)
    c.call("i", "f", [{"k": "w", "v": []}, 0])
    lat = []
    t_all = time.perf_counter()
    for i in range(n):
        t0 = time.perf_counter_ns()
        r = c.call("i", "f", [{"k": "k", "v": list(range(64))}, i])
        lat.append((time.perf_counter_ns() - t0) / 1000)
        assert r == {"ok": i + 64}, r
    wall = time.perf_counter() - t_all
    nd.stop()
    return {"n": n, "p50_us": pct(lat, 50), "p99_us": pct(lat, 99), "calls_per_s": n / wall}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--out")
    ap.add_argument("--baseline")
    ap.add_argument("--max-regress", type=float, default=0.25)
    a = ap.parse_args()
    res = {"schema": "INV61_BENCH/1", "python": platform.python_version(), "machine": platform.machine(),
           "system": platform.system(), "framing_plus_args": bench_framing(a.n), "framing": bench_envelope_only(a.n), "loopback": bench_loopback(max(200, a.n // 5)),
           "max_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    # The README SLO says "framing overhead". Both readings are reported; neither is hidden.
    res["slo_envelope_overhead_p99_under_50us"] = res["framing"]["p99_us"] < 50
    res["slo_including_arg_codec_p99_under_50us"] = res["framing_plus_args"]["p99_us"] < 50
    verdict = 0
    if a.baseline:
        base = json.load(open(a.baseline))
        reg = res["framing"]["p99_us"] / base["framing"]["p99_us"] - 1
        res["regression_vs_baseline"] = reg
        verdict = 1 if reg > a.max_regress else 0
    text = json.dumps(res, indent=2)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        open(a.out, "w").write(text)
    print(text)
    return verdict


if __name__ == "__main__":
    sys.exit(main())
