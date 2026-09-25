#!/usr/bin/env python3
"""MC-036 - canary evaluator over Prometheus text exports (see ROLLOUT.md)."""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

LINE = re.compile(r'^(\w+)\{([^}]*)\}\s+([0-9.eE+-]+)$|^(\w+)\s+([0-9.eE+-]+)$')
SECURITY = {"invalid_descriptor", "foreign_descriptor", "descriptor_closed", "type_mismatch", "forked_table"}
PKG = pathlib.Path(__file__).resolve().parents[1]


def parse(text):
    ops, buckets, disabled = {}, {}, 0.0
    for line in text.splitlines():
        m = LINE.match(line.strip())
        if not m:
            continue
        if m.group(4):
            if m.group(4) == "inv42_emergency_disabled":
                disabled = float(m.group(5))
            continue
        name, labels, val = m.group(1), dict(re.findall(r'(\w+)="([^"]*)"', m.group(2))), float(m.group(3))
        if name == "inv42_operations_total":
            ops[labels["outcome"]] = ops.get(labels["outcome"], 0) + val
        elif name == "inv42_operation_duration_seconds_bucket" and labels["op"] == "resolve":
            buckets[labels["le"]] = val
    return ops, buckets, disabled


def p99(buckets):
    total = buckets.get("+Inf", 0)
    if not total:
        return 0.0
    for le, c in sorted(((float(k), v) for k, v in buckets.items() if k != "+Inf")):
        if c >= 0.99 * total:
            return le
    return float("inf")


def evaluate(base_text, can_text, min_ops=1000, p99_threshold_s=None):
    th = p99_threshold_s if p99_threshold_s is not None else json.loads((PKG / "PERF_THRESHOLDS.json").read_text())["latency_us"]["resolve"]["p99_us"] / 1e6
    b, bb, _ = parse(base_text)
    c, cb, cdis = parse(can_text)
    reasons = []
    ctotal, btotal = sum(c.values()), sum(b.values()) or 1
    if cdis:
        reasons.append("canary emergency-disabled")
    if c.get("internal_error", 0) > 0:
        reasons.append("internal errors on canary")
    csec, bsec = sum(c.get(k, 0) for k in SECURITY), sum(b.get(k, 0) for k in SECURITY)
    if csec > 10 and ctotal and csec / ctotal > 2 * (bsec / btotal):
        reasons.append("security-class error rate > 2x baseline")
    if p99(cb) > th:
        reasons.append(f"resolve p99 bucket {p99(cb)}s > {th}s")
    if reasons:
        return "rollback", reasons, 7
    if ctotal < min_ops:
        return "hold", [f"only {int(ctotal)} ops observed"], 8
    return "promote", [], 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["evaluate"])
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--canary", required=True)
    ap.add_argument("--min-ops", type=int, default=1000)
    a = ap.parse_args()
    decision, reasons, code = evaluate(pathlib.Path(a.baseline).read_text(), pathlib.Path(a.canary).read_text(), a.min_ops)
    print(json.dumps({"decision": decision, "reasons": reasons}))
    return code


if __name__ == "__main__":
    sys.exit(main())
