"""Evaluate ops/alerts.json against a telemetry snapshot + status (C080). Makes alert rules testable.

    python -m inv69_agentic_workload_layer.tools.alert_eval SNAPSHOT.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RULES = Path(__file__).resolve().parents[1] / "ops" / "alerts.json"


def _metric(snap, status, name):
    if name.startswith("admission."):
        return float(status.get("admission", {}).get(name.split(".", 1)[1], 0))
    return float(sum(c["value"] for c in snap["counters"] if c["name"] == name))


def _code_sum(snap, name, codes):
    return float(sum(c["value"] for c in snap["counters"] if c["name"] == name and c["labels"].get("code") in codes))


def evaluate(snap: dict, status: dict, config_values: dict | None = None, rules: dict | None = None) -> list[dict]:
    rules = rules or json.loads(RULES.read_text(encoding="utf-8"))
    fired = []
    for r in rules["rules"]:
        p = r["rule"]
        t = p["type"]
        hit = False
        if t == "ge":
            thr = p.get("value", (config_values or {}).get(p.get("value_from_config"), float("inf")))
            hit = _metric(snap, status, p["metric"]) >= thr
        elif t == "ratio_ge":
            den = _metric(snap, status, p["den"])
            hit = den >= p.get("min_den", 1) and _metric(snap, status, p["num"]) / den >= p["value"]
        elif t == "code_ge":
            hit = _code_sum(snap, p["metric"], p["codes"]) >= p["value"]
        elif t == "status_reason":
            hit = p["reason"] in status.get("reasons", [])
        if hit:
            fired.append({"id": r["id"], "class": r["class"], "severity": r["severity"], "runbook": r["runbook"],
                          "owner": r["owner"]})
    return fired


if __name__ == "__main__":
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
    print(json.dumps(evaluate(doc["metrics"], doc["status"], doc.get("config")), indent=2))
