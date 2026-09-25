"""Evaluate observability/alerts.json against a sequence of plane snapshots (MC-27).

A snapshot is ``{"counters": {(name, labels_tuple): value}, "gauges": {...}, "health": {...}}``
taken once per evaluation window; ``rate`` rules use the counter delta between windows."""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES = json.loads((ROOT / "observability" / "alerts.json").read_text())["rules"]


def snapshot(plane) -> dict:
    return {"counters": dict(plane.metrics.counters), "gauges": dict(plane.metrics.gauges),
            "health": plane.health()}


def _sum(d, name, labels):
    want = set((labels or {}).items())
    return sum(v for (n, lab), v in d.items() if n == name and want <= set(lab))


def _cond(expr, prev, cur) -> bool:
    ops = {">": lambda a, b: a > b, "==": lambda a, b: a == b, "<": lambda a, b: a < b}
    if "health" in expr:
        return ops[expr["op"]](cur["health"][expr["health"]], expr["value"])
    if "health_degraded" in expr:
        return expr["health_degraded"] in cur["health"]["degraded"]
    if "gauge" in expr:
        return ops[expr["op"]](_sum(cur["gauges"], expr["gauge"], expr.get("labels")), expr["value"])
    if "rate" in expr:
        delta = _sum(cur["counters"], expr["rate"], expr.get("labels")) - _sum(prev["counters"], expr["rate"], expr.get("labels"))
        return ops[expr["op"]](delta, expr["value"])
    raise ValueError("unsupported expression")


def _burn(expr, snaps) -> bool:
    def ratio(windows):
        if len(snaps) <= windows:
            return 0.0
        a, b = snaps[-windows - 1], snaps[-1]
        bad = sum(_sum(b["counters"], "errors", {"reason_code": c}) - _sum(a["counters"], "errors", {"reason_code": c})
                  for c in ("E_INTERNAL", "E_STATE_UNAVAILABLE"))
        total = (_sum(b["counters"], "decisions", None) - _sum(a["counters"], "decisions", None)) + bad
        return bad / total if total else 0.0
    budget = 1 - expr["slo"]
    return (ratio(expr["fast_windows"]) > expr["fast_rate"] * budget and
            ratio(expr["slow_windows"]) > expr["slow_rate"] * budget)


def evaluate(snaps: list) -> set:
    firing = set()
    for rule in RULES:
        if "burn" in rule["expr"]:
            if _burn(rule["expr"], snaps):
                firing.add(rule["name"])
            continue
        need = rule["for_windows"]
        if len(snaps) < need + 1:
            continue
        if all(_cond(rule["expr"], snaps[i - 1], snaps[i]) for i in range(len(snaps) - need, len(snaps))):
            firing.add(rule["name"])
    return firing


def prometheus() -> str:
    out = ["groups:", "- name: pln05", "  rules:"]
    for r in RULES:
        out += [f"  - alert: {r['name']}", f"    labels: {{severity: {r['severity']}, route: {r['route']}}}",
                f"    annotations: {{runbook: {r['runbook']}}}"]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    import sys
    if "--prometheus" in sys.argv:
        print(prometheus())
