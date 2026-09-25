"""Production agent wiring: config → probes → executor → sweep → envelope.

    python -m gap02_hardware_capability_discovery.production.agent sweep [--config FILE]
    python -m gap02_hardware_capability_discovery.production.agent explain CAPABILITY
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from .accelerators import probe_accelerators
from .config import ProbeConfig
from .confidential import TECH, probe_confidential
from .cpu import KNOWN, probe_cpu, feature_evidence
from .evidence import Host
from .executor import ProbeExecutor
from .explain import explain
from .nic import probe_nics
from .securedev import probe_tpm
from .storage import probe_storage
from .topology import probe_numa
from .virt import probe_virt


def build_probes(cfg: ProbeConfig, host: Host | None = None) -> dict:
    host = host or Host()
    table = {
        "cpu": (lambda: (lambda r: [r["evidence"], *feature_evidence(r)])(probe_cpu(host)), ("cpu.features",)),
        "numa": (lambda: (lambda r: [r["evidence"], r["ecc_evidence"], r["hugepage_evidence"]])(probe_numa(host)),
                 ("memory.numa", "memory.ecc", "memory.hugepages")),
        "storage": (lambda: (lambda r: [r["evidence"], *r["derived"]])(probe_storage(host)),
                    ("storage.block",)),
        "nic": (lambda: (lambda r: [r["evidence"], *r["derived"]])(probe_nics(host)), ("network.nic",)),
        "virt": (lambda: (lambda r: [r["evidence"], *r["derived"]])(probe_virt(host)), ("virtualization.host",)),
        "confidential": (lambda: probe_confidential(host)["evidence"],
                         tuple(f"cc.{t}.{s}" for t in TECH for s in ("enabled", "attested"))),
        "tpm": (lambda: [probe_tpm(host)["evidence"]], ("tpm2",)),
        "accelerators": (lambda: probe_accelerators(host, cfg.probe_cfg())["evidence"],
                         ("gpu.compute.nvidia", "gpu.compute.amd", "gpu.compute.intel",
                          "gpu.compute.apple", "npu.compute")),
    }
    return {k: v for k, v in table.items() if k in cfg.active_probes}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="gap02-agent")
    ap.add_argument("cmd", choices=["sweep", "explain"])
    ap.add_argument("capability", nargs="?")
    ap.add_argument("--config")
    a = ap.parse_args(argv)
    cfg = ProbeConfig.load(a.config) if a.config else ProbeConfig()
    ex = ProbeExecutor(cfg.node, build_probes(cfg), max_concurrency=cfg.max_concurrency,
                       probe_timeout=cfg.probe_timeout_seconds, sweep_deadline=cfg.sweep_deadline_seconds)
    snap = ex.sweep()
    if a.cmd == "explain":
        print(json.dumps(explain(snap, a.capability or ""), indent=2))
    else:
        print(json.dumps({"generation": snap.generation, "sequence": snap.sequence,
                          "report": snap.report.for_consumer(snap.report.published_at),
                          "evidence": snap.evidence}, indent=1, default=str))
    ex.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
