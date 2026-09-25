"""Capacity model (C069): resource profile + workload mix -> safe concurrency / throughput and saturation signals.

    python -m inv69_agentic_workload_layer.tools.capacity_model --cores 4 --mem-mb 2048 \
        --mix readonly=0.8,side_effect=0.15,high_risk=0.05 --tool-ms readonly=20,side_effect=150,high_risk=900 \
        [--perf evidence/PERF_RESULTS.json] [--quota authz_rps=500,sandbox_heavy_concurrency=16]

Model (versioned with the benchmark it reads, PK_CAPACITY_MODEL/1):
  governance CPU per step  = measured cpu_s_per_op                       (C061)
  memory per active run    = measured bytes_per_completed_run x 2 (headroom)
  per-core step rate       = 1 / governance CPU per step
  tool concurrency needed  = arrival_rate x mean tool time  (Little's law)
  safe max_active          = min(memory bound, external quotas, cores x per-core rate x mean tool time x 0.7)
  saturation signals       = admission.waiting > 0 for > queue_age_warning_s; admission.shed rate > 0;
                             p95 invoke latency > 2x baseline; CPU > 70%
External quotas are applied as limits of their own, so a dependency limit is never mistaken for host capacity.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL_VERSION = "PK_CAPACITY_MODEL/1.0.0"


def _kv(s):
    return {k: float(v) for k, v in (x.split("=") for x in s.split(","))} if s else {}


def model(cores, mem_mb, mix, tool_ms, perf, quotas):
    cpu_per_step = perf["throughput"]["cpu_s_per_op"] / 1e6
    mem_per_run = perf["memory"]["bytes_per_completed_run"] * 2
    mean_tool_s = sum(mix[k] * tool_ms[k] / 1000 for k in mix)
    per_core_steps = 1 / cpu_per_step
    cpu_bound_rate = cores * per_core_steps * 0.7
    mem_bound_active = int(mem_mb * 1024 * 1024 * 0.5 / mem_per_run)
    active_for_cpu_rate = int(cpu_bound_rate * mean_tool_s)
    limits = {"memory": mem_bound_active, "cpu": max(1, active_for_cpu_rate)}
    if "sandbox_heavy_concurrency" in quotas and mix.get("high_risk"):
        limits["quota:sandbox_heavy"] = int(quotas["sandbox_heavy_concurrency"] / mix["high_risk"])
    if "authz_rps" in quotas:
        limits["quota:authz_rps"] = int(quotas["authz_rps"] * mean_tool_s)
    safe_active = max(3, min(limits.values()))
    binding = min(limits, key=limits.get)
    return {"schema": MODEL_VERSION, "benchmark_fingerprint": perf["fingerprint"],
            "inputs": {"cores": cores, "mem_mb": mem_mb, "mix": mix, "tool_ms": tool_ms, "quotas": quotas},
            "derived": {"governance_cpu_us_per_step": round(cpu_per_step * 1e6, 2), "mean_tool_s": round(mean_tool_s, 4),
                        "cpu_bound_steps_per_s": round(cpu_bound_rate, 1), "limits": limits, "binding_limit": binding},
            "recommendation": {"concurrency.max_active": safe_active, "concurrency.max_waiting": safe_active * 2,
                               "max_sustainable_steps_per_s": round(min(cpu_bound_rate, safe_active / mean_tool_s), 1)},
            "saturation_signals": ["admission.oldest_wait_s >= health.queue_age_warning_s (HLT-QUEUE-WARN)",
                                   "admission.shed increasing (A-SATURATION)",
                                   "invoke_latency_s p95 > 2x baseline", "process CPU > 70% of cores"]}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cores", type=float, required=True)
    ap.add_argument("--mem-mb", type=float, required=True)
    ap.add_argument("--mix", required=True)
    ap.add_argument("--tool-ms", required=True)
    ap.add_argument("--quota", default="")
    ap.add_argument("--perf", default=str(ROOT / "evidence" / "PERF_RESULTS.json"))
    a = ap.parse_args(argv)
    perf = json.loads(Path(a.perf).read_text())
    print(json.dumps(model(a.cores, a.mem_mb, _kv(a.mix), _kv(a.tool_ms), perf, _kv(a.quota)), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
