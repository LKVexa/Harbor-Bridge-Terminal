"""Staged canary promotion with automatic abort (closure #37).

A release candidate runs beside the baseline on a deterministic synthetic
workload (or, in production, real traffic split).  Promotion proceeds through
``STAGES`` only if every gate holds; any breach aborts and returns the
rollback instruction.  Gates are the contract invariants plus SLO guards.
"""
from __future__ import annotations

import importlib
import json
import pathlib
import random
import sys

STAGES = (1, 5, 25, 50, 100)            # percent of traffic on the candidate
GATES = {
    "double_delivery_attempts": ("==", 0),
    "listener_failures": ("==", 0),
    "unexpected_in_flight_after_drain": ("==", 0),
    "refusal_rate_delta": ("<=", 0.02),  # candidate refusal rate may exceed baseline by <= 2 points
    "trap_rate_delta": ("<=", 0.0),
}


def workload(fns, rt, n, seed):
    rng = random.Random(seed)
    refused = 0
    for _ in range(n):
        try:
            c = fns.invoke(rng.choice(sorted(fns.declared)))
        except (rt.ReentrancyRefused, rt.ConcurrencyLimitReached):
            refused += 1
            continue
        r = rng.random()
        if r < 0.9:
            fns.complete(c.call_id, 1)
        else:
            fns.cancel(c.call_id, "caller")
    s = fns.snapshot()
    return {"refusal_rate": refused / n, "trap_rate": s["trapped_calls"] / n, "snap": s}


def evaluate(base, cand) -> dict:
    obs = {
        "double_delivery_attempts": cand["snap"]["double_delivery_attempts"],
        "listener_failures": cand["snap"]["listener_failures"],
        "unexpected_in_flight_after_drain": cand["snap"]["calls_in_flight"],
        "refusal_rate_delta": cand["refusal_rate"] - base["refusal_rate"],
        "trap_rate_delta": cand["trap_rate"] - base["trap_rate"],
    }
    breaches = [k for k, (op, lim) in GATES.items()
                if not (obs[k] == lim if op == "==" else obs[k] <= lim)]
    return {"observed": obs, "breaches": breaches}


def promote(make_baseline, make_candidate, rt, requests_per_stage=2000, seed=1):
    log = []
    for pct in STAGES:
        n_c = max(1, requests_per_stage * pct // 100)
        base = workload(make_baseline(), rt, requests_per_stage, seed + pct)
        cand = workload(make_candidate(), rt, n_c, seed + pct)
        ev = evaluate(base, cand)
        log.append({"stage_pct": pct, **ev})
        if ev["breaches"]:
            return {"decision": "ABORT", "rollback": "tools/rollback.py", "stages": log}
    return {"decision": "PROMOTED", "stages": log}


if __name__ == "__main__":
    PKG = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(PKG.parent))
    rt = importlib.import_module(PKG.name + ".runtime")
    mk = lambda: rt.AsyncFunctions("canary", declared={"a": True, "s": True}, stateful=frozenset({"s"}))
    print(json.dumps(promote(mk, mk, rt), indent=2))
