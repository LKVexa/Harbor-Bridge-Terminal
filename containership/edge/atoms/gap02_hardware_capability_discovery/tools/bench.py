"""GAP02-MC-47 — sweep latency benchmark (fixture host + optional real host).

    python -m gap02_hardware_capability_discovery.tools.bench [--iterations N] [--real]
"""
import argparse, json, statistics, sys, time

from ..production.agent import build_probes
from ..production.config import ProbeConfig
from ..production.evidence import Host
from ..production.executor import ProbeExecutor


def run(iterations: int = 50, real: bool = False) -> dict:
    host = None if real else Host(files={"/proc/cpuinfo": "flags : avx2 aes vmx ept", "/dev/kvm": "",
                                         "/sys/block/sda/size": "100", "/sys/class/net/eth0/device/x": ""},
                                  commands={}, system="Linux", machine="x86_64")
    ex = ProbeExecutor("bench", build_probes(ProbeConfig(), host), clock=iter(range(10**9)).__next__)
    lat = []
    for _ in range(iterations):
        t0 = time.perf_counter(); ex.sweep(); lat.append(time.perf_counter() - t0)
    ex.stop()
    lat.sort()
    return {"schema": "GAP02_BENCH/1", "host": "real" if real else "fixture", "iterations": iterations,
            "p50_ms": round(statistics.median(lat) * 1000, 3), "p95_ms": round(lat[int(0.95 * (len(lat) - 1))] * 1000, 3),
            "max_ms": round(lat[-1] * 1000, 3), "slo_ms": 5000, "slo_met": lat[-1] < 5.0}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--iterations", type=int, default=50); ap.add_argument("--real", action="store_true")
    a = ap.parse_args(); print(json.dumps(run(a.iterations, a.real), indent=1))
