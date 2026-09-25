"""Executable rollback 4.3.0 -> 4.2.0 (closure #38).

Rollback unit: the runtime module + its configuration.  In-flight state is
*ephemeral* (never persisted), so the procedure is:

1. drain: stop admission, give live calls ``drain_timeout`` to finish;
2. cancel the remainder with ``CancelCode.SHUTDOWN`` (evidence records how many);
3. map configuration down: queue policies become refusal (4.2.0 has no queue);
   bounded-tombstone / call-id-width / transport settings are dropped with a
   recorded warning;
4. start the previous runtime behind a ``GenerationFence`` so delayed terminal
   messages addressed to the rolled-back generation can never alias a fresh
   4.2.0 call id (4.2.0 restarts ids at 1);
5. emit a JSON rollback record with timings.
"""
from __future__ import annotations

import importlib.util
import importlib
import json
import pathlib
import sys
import time

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
RTO_SECONDS = 1.0          # declared recovery objective for the in-process swap


def load_legacy():
    spec = importlib.util.spec_from_file_location("inv16_runtime_4_2_0", PKG_DIR / "compat" / "runtime_4_2_0.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class StaleGenerationMessage(ValueError):
    pass


class GenerationFence:
    """Wraps a 4.2.0 runtime; every call id is (generation, id) at the boundary."""

    def __init__(self, legacy, generation: int):
        self.inner, self.generation = legacy, generation

    def invoke(self, function, caller_is_async=True):
        st = self.inner.invoke(function, caller_is_async)
        return self.generation, st

    def _check(self, generation):
        if generation != self.generation:
            raise StaleGenerationMessage(f"generation {generation} != {self.generation}")

    def complete(self, generation, call_id, value):
        self._check(generation)
        return self.inner.complete(call_id, value)

    def cancel(self, generation, call_id):
        self._check(generation)
        return self.inner.cancel(call_id)


def rollback(current, drain_timeout: float = 0.2) -> tuple[GenerationFence, dict]:
    t0 = time.monotonic()
    from importlib import import_module
    rt = import_module(type(current).__module__)
    deadline = t0 + drain_timeout
    while current.calls_in_flight and time.monotonic() < deadline:
        time.sleep(0.005)
    drained_naturally = current.snapshot()["completed_calls"]
    cancelled = current.cancel_all(rt.CancelReason(rt.CancelCode.SHUTDOWN, "rollback to 4.2.0", "operator"))
    warnings = []
    stateful = set(current.stateful)
    for fn, pol in current.reentrancy.items():
        if pol.mode.value == "queue":
            warnings.append(f"{fn}: queue policy downgraded to refuse (4.2.0 has no queue)")
    if current.tombstone_capacity != 65_536:
        warnings.append("tombstone_capacity ignored: 4.2.0 retains tombstones unbounded")
    if current.transport is not None:
        warnings.append("ABI transport disabled: 4.2.0 stores Python values")
    legacy = load_legacy()
    old = legacy.AsyncFunctions(current.instance, declared=dict(current.declared), stateful=frozenset(stateful),
                                concurrency_limit=current.concurrency_limit)
    fence = GenerationFence(old, current.generation + 1)
    record = {
        "schema": "inv16.rollback/1", "from": "4.3.0", "to": "4.2.0", "instance": current.instance,
        "old_generation": current.generation, "new_generation": fence.generation,
        "drained_completed_total": drained_naturally, "cancelled_in_flight": cancelled,
        "warnings": warnings, "duration_s": round(time.monotonic() - t0, 6), "rto_s": RTO_SECONDS,
    }
    record["within_rto"] = record["duration_s"] <= RTO_SECONDS
    return fence, record


if __name__ == "__main__":
    sys.path.insert(0, str(PKG_DIR.parent))
    rt = importlib.import_module(PKG_DIR.name + ".runtime")
    cur = rt.AsyncFunctions("demo", declared={"f": True, "q": True},
                            reentrancy={"q": rt.ReentrancyPolicy(rt.ReentrancyMode.QUEUE, 2)})
    for _ in range(5):
        cur.invoke("f")
    _, rec = rollback(cur, drain_timeout=0.05)
    print(json.dumps(rec, indent=2))
