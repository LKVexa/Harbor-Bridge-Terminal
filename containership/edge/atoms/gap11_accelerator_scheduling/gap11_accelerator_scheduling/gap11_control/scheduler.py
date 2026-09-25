"""Scheduling policy: GAP11-P0-14 admission quotas & fairness, P1-17 multi-device
topology, P1-18 fragmentation-aware placement, P1-22 preemption/reservation,
P1-23 constraint policy engine.

All functions are pure over their inputs (deterministic for identical state):
candidates are sorted by an explicit total order ending in the device id, so two
equivalent requests never get different answers from dict/iteration order.
"""
from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass, field
from typing import Any, Callable

from .common import ControlError

# ------------------------------------------------------------------ constraint engine (P1-23)
# Precedence: security > residency > health/thermal > workload class > generation > features > cost > power > SLO.
HARD_ORDER = ("security", "residency", "health", "thermal", "workload_class", "generation", "features")
SOFT_ORDER = ("cost", "power", "slo", "locality")


@dataclass
class Decision:
    device: str | None
    reasons: list[dict[str, Any]] = field(default_factory=list)
    score: tuple = ()


class ConstraintEngine:
    def __init__(self, hard: dict[str, Callable[[dict[str, Any], dict[str, Any]], bool]],
                 soft: dict[str, Callable[[dict[str, Any], dict[str, Any]], float]] | None = None) -> None:
        unknown = (set(hard) - set(HARD_ORDER)) | (set(soft or {}) - set(SOFT_ORDER))
        if unknown:
            raise ControlError("CONFIG_INVALID", f"unknown constraint class {sorted(unknown)}")
        self.hard = hard
        self.soft = soft or {}

    def decide(self, request: dict[str, Any], devices: list[dict[str, Any]]) -> Decision:
        reasons = []
        survivors = []
        for d in sorted(devices, key=lambda x: x["device"]):
            failed = next((c for c in HARD_ORDER if c in self.hard and not self.hard[c](request, d)), None)
            if failed:
                reasons.append({"device": d["device"], "rejected_by": failed})
            else:
                survivors.append(d)
        if not survivors:
            return Decision(None, reasons)

        def score(d: dict[str, Any]) -> tuple:
            return tuple(round(self.soft[c](request, d), 9) for c in SOFT_ORDER if c in self.soft) + (d["device"],)

        best = min(survivors, key=score)
        return Decision(best["device"], reasons + [{"device": best["device"], "selected": True}], score(best))


# ------------------------------------------------------------------ quotas & fair queue (P0-14)
class QuotaBook:
    """Per-tenant caps on concurrent devices and memory; reservation classes."""

    def __init__(self, caps: dict[str, dict[str, int]], default: dict[str, int] | None = None) -> None:
        self.caps = caps
        self.default = default or {"devices": 0, "memory_gb": 0}   # secure default: no quota = no access

    def check(self, tenant: str, active: list[dict[str, Any]], request: dict[str, Any]) -> None:
        cap = self.caps.get(tenant, self.default)
        mine = [l for l in active if l["tenant"] == tenant]
        if len(mine) + 1 > cap["devices"]:
            raise ControlError("QUOTA_EXCEEDED", tenant_devices=len(mine), cap=cap["devices"])
        if sum(l.get("memory_gb") or 0 for l in mine) + request.get("memory_gb", 0) > cap["memory_gb"]:
            raise ControlError("QUOTA_EXCEEDED", "memory quota", cap=cap["memory_gb"])


class FairQueue:
    """Bounded admission queue: weighted round-robin across tenants + age-based boost.

    Starvation bound: an entry waiting ``aging_s`` gains one priority level per
    ``aging_s`` elapsed, so any queued request reaches the top priority after at most
    ``2 * aging_s`` and is then served FIFO among top-priority entries.
    """

    PRIO = {"high": 0, "normal": 1, "low": 2}

    def __init__(self, *, capacity: int, clock: Any, aging_s: float = 30.0) -> None:
        self.capacity, self.clock, self.aging_s = capacity, clock, aging_s
        self.items: list[dict[str, Any]] = []
        self.seq = itertools.count()
        self.served: dict[str, int] = {}

    def push(self, tenant: str, request: dict[str, Any]) -> None:
        if len(self.items) >= self.capacity:
            raise ControlError("OVERLOADED", queue_depth=len(self.items))
        self.items.append({"tenant": tenant, "req": request, "at": self.clock.monotonic(), "seq": next(self.seq),
                           "prio": self.PRIO.get(request.get("priority", "normal"), 1)})

    def effective_prio(self, it: dict[str, Any]) -> int:
        waited = self.clock.monotonic() - it["at"]
        return max(0, it["prio"] - int(waited // self.aging_s))

    def pop(self) -> dict[str, Any] | None:
        if not self.items:
            return None
        best = min(self.items, key=lambda it: (self.effective_prio(it), self.served.get(it["tenant"], 0), it["seq"]))
        self.items.remove(best)
        self.served[best["tenant"]] = self.served.get(best["tenant"], 0) + 1
        return best

    def depth(self) -> int:
        return len(self.items)


# ------------------------------------------------------------------ topology (P1-17)
def gang_candidates(devices: list[dict[str, Any]], size: int, *, domain_key: str = "fabric") -> list[list[str]]:
    """Return device sets of ``size`` that share one fabric domain, best-locality first."""
    by_domain: dict[Any, list[str]] = {}
    for d in sorted(devices, key=lambda x: x["device"]):
        by_domain.setdefault(d.get("topology", {}).get(domain_key), []).append(d["device"])
    out = []
    for dom in sorted(by_domain, key=lambda x: (x is None, str(x))):
        members = by_domain[dom]
        if dom is not None and len(members) >= size:
            out.append(members[:size])
    return out


# ------------------------------------------------------------------ fragmentation (P1-18)
def fragmentation(devices: list[dict[str, Any]], leases: list[dict[str, Any]], *, typical_gb: int) -> dict[str, Any]:
    """Residual unusable capacity: free memory on devices that cannot host a ``typical_gb`` job."""
    free_total = 0
    unusable = 0
    for d in devices:
        used = sum(l.get("memory_gb") or 0 for l in leases if l["device"] == d["device"])
        free = max(0, d["memory_gb"] - used)
        whole_free = not any(l["device"] == d["device"] for l in leases)
        free_total += free
        parts_free = [p for p in d.get("partitions", []) if p.get("memory_gb") and p["memory_gb"] >= typical_gb
                      and not any(l["device"] == d["device"] and l.get("partition") == p["name"] for l in leases)
                      and not any(l["device"] == d["device"] and l.get("partition") is None for l in leases)]
        if free and not (whole_free and d["memory_gb"] >= typical_gb) and not parts_free:
            unusable += free
    return {"free_gb": free_total, "unusable_gb": unusable, "ratio": (unusable / free_total) if free_total else 0.0}


def place_partition(candidates: list[dict[str, Any]], need_gb: int, leases: list[dict[str, Any]]) -> tuple[str, str] | None:
    """Smallest sufficient free declared slice; ties -> device already partially used
    (keeps whole devices whole), then device id."""
    opts = []
    for d in candidates:
        if any(l["device"] == d["device"] and l.get("partition") is None for l in leases):
            continue
        used_parts = {l.get("partition") for l in leases if l["device"] == d["device"]}
        partially_used = bool(used_parts)
        for p in d.get("partitions", []):
            if p["name"] in used_parts or p.get("memory_gb") is None or p["memory_gb"] < need_gb:
                continue
            opts.append((p["memory_gb"] - need_gb, 0 if partially_used else 1, d["device"], p["name"]))
    if not opts:
        return None
    best = min(opts)
    return best[2], best[3]


# ------------------------------------------------------------------ preemption (P1-22)
def choose_victims(request: dict[str, Any], leases: list[dict[str, Any]], *, need_devices: int = 1,
                   now: float, min_runtime_s: float = 60.0, budget: int = 1) -> list[dict[str, Any]]:
    """Victims must be strictly lower priority, past ``min_runtime_s``, not marked
    ``non_preemptible``, and fewer than ``budget``. Ordering: lowest priority,
    then youngest (least work lost), then lease id. Returns [] when not permitted."""
    rp = FairQueue.PRIO.get(request.get("priority", "normal"), 1)
    elig = [l for l in leases if FairQueue.PRIO.get(l.get("priority", "normal"), 1) > rp
            and not l.get("non_preemptible") and now - l.get("created_mono", now) >= min_runtime_s]
    elig.sort(key=lambda l: (-FairQueue.PRIO.get(l.get("priority", "normal"), 1), -l.get("created_mono", 0), l["lease_id"]))
    victims = elig[:need_devices]
    if len(victims) < need_devices or len(victims) > budget:
        return []
    return victims
