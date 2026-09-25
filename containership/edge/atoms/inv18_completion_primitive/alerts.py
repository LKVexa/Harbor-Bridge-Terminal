"""Evaluate dashboards/inv18_alerts.json rules against a Metrics object (C080)."""
from __future__ import annotations

import json
import operator
import pathlib

from .telemetry import Metrics

OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "==": operator.eq}
RULES_PATH = pathlib.Path(__file__).resolve().parent / "dashboards" / "inv18_alerts.json"


def load_rules(path=RULES_PATH) -> list[dict]:
    return json.loads(pathlib.Path(path).read_text())["rules"]


def _value(m: Metrics, cond: list) -> float:
    kind = cond[0]
    if kind == "counter":
        _, name, labels, *_ = cond
        return m.counter(name, **labels) if labels else m.counter(name)
    if kind == "counter_any":
        _, name, labels, *_ = cond
        if not labels:
            return m.counter(name)
        (k, vals), = labels.items()
        return sum(m.counter(name, **{k: v}) for v in vals)
    if kind == "ratio":
        _, num, den, *_ = cond
        d = m.counter(den)
        return m.counter(num) / d if d else 0.0
    if kind == "percentile":
        _, name, p, *_ = cond
        return m.percentiles(name).get(p, 0.0)
    raise ValueError(f"unknown condition kind {kind}")


def evaluate(m: Metrics, rules: list[dict] | None = None) -> list[dict]:
    fired = []
    for r in rules or load_rules():
        if all(OPS[c[-2]](_value(m, c), c[-1]) for c in r["when"]):
            fired.append({"id": r["id"], "class": r["class"], "severity": r["severity"], "runbook": r["runbook"]})
    return fired
