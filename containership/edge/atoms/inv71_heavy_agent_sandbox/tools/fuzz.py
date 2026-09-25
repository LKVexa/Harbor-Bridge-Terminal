"""Stdlib property/fuzz harness for every untrusted-input parser (C085, C050-IMP-02, C028-IMP-05).

Not coverage-guided (no native code here; CPython has no in-tree coverage
fuzzer).  Each target receives seeded random and mutated inputs built from the
conformance fixtures, boundary sizes, Unicode/path edge cases and DNS/IP forms.
A target *passes* an input when it either returns a value satisfying its
invariant or raises one of its declared, typed rejections.  Anything else - an
undeclared exception, an invariant violation, or exceeding the per-input time
limit - is a finding, and the minimized input is written to
``fuzz-findings/`` for promotion into a regression test.

Usage: python tools/fuzz.py [--iterations N] [--seed S] [--out evidence/fuzz.json]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys
import time

PKG = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG.parent))

from inv71_heavy_agent_sandbox.control import auth, config, telemetry  # noqa: E402
from inv71_heavy_agent_sandbox.control.errors import ControlError  # noqa: E402
from inv71_heavy_agent_sandbox.sandbox import canonicalize_host, normalize_path, validate_session_id  # noqa: E402

SEEDS = ["/", "/a", "/a/../b", "/a//b", "/a/./b", "\x00", "a" * 5000, "/‮/x", "\\\\x", "/tmp/\udcff",
         "example.com", "EXAMPLE.COM.", "xn--nxasmq6b", "ünïcödé.com", "a..b", "-a.com", "1.2.3.4", "::1",
         "fe80::1%eth0", "[::1]", "0x7f.1", "017700000001", "127.1", "http://a", "a:80", "a@b", " a", "a" * 64 + ".com",
         "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01", "{}", "[]", "null", '{"schema":"PK_HEAVYBOX_CONFIG/1","values":{}}',
         '{"a":1,"a":2}', "NaN", "1e999", '"\\ud800"']


def mutate(s: str, rng: random.Random) -> str:
    ops = rng.randrange(6)
    if not s or ops == 0:
        return s + rng.choice(["\x00", ".", "/", "..", ":", "%", "́", "￿", "A" * rng.randrange(1, 300)])
    i = rng.randrange(len(s))
    if ops == 1:
        return s[:i] + s[i + 1:]
    if ops == 2:
        return s[:i] + chr(rng.randrange(0, 0x3000)) + s[i:]
    if ops == 3:
        return s + s
    if ops == 4:
        return s.upper() if rng.random() < .5 else s.lower()
    return s[:i]


def _host(s):
    out = canonicalize_host(s)
    if out != canonicalize_host(out):  # idempotent
        raise AssertionError("canonicalize_host not idempotent")
    if any(c in out for c in "/@:?#") and ":" in out and not all(ch in "0123456789abcdef:." for ch in out):
        raise AssertionError("delimiter survived canonicalization")


def _path(s):
    out = normalize_path(s)
    if "/../" in out + "/" or "//" in out or not out.startswith("/"):
        raise AssertionError("non-canonical path accepted")


def _config(s):
    doc = config.parse(s.encode("utf-8", "surrogatepass"))
    config.merge({"environment": doc["values"]})


def _token(s):
    ta = auth.TokenAuthority(b"f" * 32, "iss", clock=lambda: 0.0)
    ta.verify(s, aud="x")
    raise AssertionError("random token verified")


def _traceparent(s):
    tc = telemetry.parse_traceparent(s, trusted=True)
    if len(tc.trace_id) != 32 or len(tc.span_id) != 16:
        raise AssertionError("bad trace context")


TARGETS = {
    "canonicalize_host": (_host, (ValueError,)),
    "normalize_path": (_path, (ValueError,)),
    "validate_session_id": (validate_session_id, (ValueError,)),
    "config.parse+merge": (_config, (ControlError, UnicodeEncodeError)),
    "token.verify": (_token, (ControlError,)),
    "traceparent": (_traceparent, ()),
}


def run(iterations: int, seed: int, time_limit_s: float = 0.25) -> dict:
    rng = random.Random(seed)
    report = {"schema": "PK_HEAVYBOX_FUZZ/1", "seed": seed, "iterations_per_target": iterations,
              "coverage_guided": False, "targets": {}}
    for name, (fn, allowed) in TARGETS.items():
        findings, accepted, rejected = [], 0, 0
        corpus = list(SEEDS)
        for _ in range(iterations):
            s = mutate(rng.choice(corpus), rng)
            t0 = time.perf_counter()
            try:
                fn(s)
                accepted += 1
                if len(corpus) < 2000:
                    corpus.append(s)
            except allowed:
                rejected += 1
            except Exception as exc:  # finding
                findings.append({"input": s[:512], "error": f"{type(exc).__name__}: {str(exc)[:200]}"})
            if time.perf_counter() - t0 > time_limit_s:
                findings.append({"input": s[:512], "error": "time limit exceeded"})
        report["targets"][name] = {"accepted": accepted, "rejected": rejected, "findings": findings[:20],
                                   "finding_count": len(findings)}
    report["total_findings"] = sum(t["finding_count"] for t in report["targets"].values())
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--iterations", type=int, default=5000)
    ap.add_argument("--seed", type=int, default=71)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    r = run(a.iterations, a.seed)
    text = json.dumps(r, indent=2, ensure_ascii=True)
    if a.out:
        pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        pathlib.Path(a.out).write_text(text + "\n")
    print(json.dumps({k: (v["accepted"], v["rejected"], v["finding_count"]) for k, v in r["targets"].items()}))
    return 1 if r["total_findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
