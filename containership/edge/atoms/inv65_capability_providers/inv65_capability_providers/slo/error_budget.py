"""SLO / error-budget measurement and enforcement (M39).

SLO targets live in ``slo/SLO.json``.  ``evaluate`` computes SLIs from the
runtime's own metrics and returns budget consumption and a release verdict:
a no-budget SLO with any violation => BLOCK; a budgeted SLO burning > 1.0 =>
BLOCK; otherwise PASS.  No data => INSUFFICIENT_DATA (never PASS)."""
from __future__ import annotations

import json
import pathlib

SLO_FILE = pathlib.Path(__file__).resolve().parent / "SLO.json"


def load() -> dict:
    return json.loads(SLO_FILE.read_text(encoding="utf-8"))


def evaluate(measurements: dict, slos: dict | None = None) -> dict:
    slos = slos or load()
    out, verdict = {}, "PASS"
    for s in slos["slos"]:
        m = measurements.get(s["id"])
        if m is None or m.get("total", 0) == 0:
            out[s["id"]] = {"status": "INSUFFICIENT_DATA"}
            verdict = "BLOCK" if verdict == "BLOCK" else "INSUFFICIENT_DATA"
            continue
        bad_ratio = m["bad"] / m["total"]
        budget = s["error_budget_ratio"]
        burn = (bad_ratio / budget) if budget > 0 else (float("inf") if m["bad"] else 0.0)
        status = "PASS" if burn <= 1.0 else "BLOCK"
        if status == "BLOCK":
            verdict = "BLOCK"
        out[s["id"]] = {"status": status, "bad": m["bad"], "total": m["total"], "bad_ratio": bad_ratio,
                        "budget_ratio": budget, "burn": None if burn == float("inf") else round(burn, 4)}
    return {"verdict": verdict, "slos": out}
