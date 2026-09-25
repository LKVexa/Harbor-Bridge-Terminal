"""Capacity model / sizing calculator (GAP04-C40). Coefficients are the measured
values in evidence/perf_baseline.json (build host); override them with numbers
from representative edge hardware before production sizing.

  python -m gap04_disconnected_operation_controller.runtime.capacity --rate-per-min 10 --max-partition-h 72
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parents[1] / "evidence" / "perf_baseline.json"
SAFETY = 1.5            # headroom multiplier on nominal load
DEGRADED = 2.0          # latency/drain multiplier when a dependency is degraded


def coefficients() -> dict:
    r = json.loads(EVIDENCE.read_text())
    d = r["decide"]
    rec = max(r["recovery"], key=lambda x: x["pending_decisions"])
    return {"journal_bytes_per_decision": d["journal_bytes_per_decision"],
            "decisions_per_s_single_writer": d["throughput_decisions_per_s"],
            "cpu_s_per_decision": d["cpu_s_per_1k_decisions"] / 1000,
            "p99_decide_ms": d["decide_latency_ms"]["p99"],
            "recovery_s_per_pending": rec["cold_start_recovery_s"] / rec["pending_decisions"],
            "reconcile_bytes_per_decision": d["reconcile_bytes_per_decision_to_GAP05"],
            "reconcile_local_s_per_decision": d["reconcile_s"] / d["decisions"],
            "memory_bytes_per_pending": d["decision_record_bytes_plain"] * 2}


def size(rate_per_min: float, max_partition_h: float, reserve_bytes: int = 1 << 20, sites: int = 1,
         peer_decisions_per_s: float = 2000.0) -> dict:
    c = coefficients()
    decisions = math.ceil(rate_per_min * 60 * max_partition_h)
    jb = decisions * c["journal_bytes_per_decision"] * SAFETY + reserve_bytes
    return {
        "inputs": {"rate_per_min": rate_per_min, "max_partition_h": max_partition_h, "sites": sites},
        "max_decisions_per_partition": math.ceil(decisions * SAFETY),
        "journal.max_bytes": int(2 ** math.ceil(math.log2(jb))),
        "journal.reserve_bytes": reserve_bytes,
        "min_disk_free_bytes": int(jb * 0.25),
        "cpu_core_utilization_at_rate": rate_per_min / 60 * c["cpu_s_per_decision"],
        "headroom_x_vs_measured_throughput": (c["decisions_per_s_single_writer"] / max(rate_per_min / 60, 1e-9)),
        "memory_bytes_pending_log": int(decisions * c["memory_bytes_per_pending"] * SAFETY),
        "cold_start_recovery_s": decisions * c["recovery_s_per_pending"] * DEGRADED,
        "reconnect_payload_bytes": int(decisions * c["reconcile_bytes_per_decision"]),
        "fleet_storm_payload_bytes": int(decisions * c["reconcile_bytes_per_decision"] * sites),
        "fleet_drain_s_at_peer": decisions * sites / peer_decisions_per_s * DEGRADED,
        "saturation_signals": {"journal_utilization_ratio": [0.8, "alert"], "journal_full": "emergency freeze",
                               "admission_rejections_total": "load shedding", "decision_latency p99 > 50ms": "SLO"},
        "coefficients": c,
    }


if __name__ == "__main__":  # pragma: no cover
    ap = argparse.ArgumentParser()
    ap.add_argument("--rate-per-min", type=float, required=True)
    ap.add_argument("--max-partition-h", type=float, required=True)
    ap.add_argument("--sites", type=int, default=1)
    a = ap.parse_args()
    print(json.dumps(size(a.rate_per_min, a.max_partition_h, sites=a.sites), indent=2))
