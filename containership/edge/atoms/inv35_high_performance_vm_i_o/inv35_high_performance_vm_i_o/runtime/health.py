"""Health/stall detection, status surface and interface-version negotiation.

Covers INV-35-C016/C027 (versioning and peer negotiation), C052 (stall
thresholds), C069 (saturation signals) and C071 (health/readiness/version/
config/dependency/capability status surface).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Callable

from .errors import Inv35Error

#: Interface versions this build speaks, newest first. Majors are incompatible.
SUPPORTED = {
    "PK_VIRTQUEUE_SUBMIT": (1,),
    "PK_VIRTQUEUE_COMPLETE": (1,),
    "INV35_STATUS": (1,),
    "INV35_ERROR": (1,),
    "INV35_CONFIG": (1,),
}
DEPRECATED: dict[str, tuple[int, ...]] = {}


def negotiate(offer: dict[str, list[int]]) -> dict[str, int]:
    """Pick the highest mutually supported major for every interface the peer offers.

    Every interface this component requires must be agreed; an unknown interface in
    the offer is ignored (forward compatibility), a missing required one is refused.
    """
    if not isinstance(offer, dict):
        raise Inv35Error("INV35-E503", "offer must be an object")
    agreed: dict[str, int] = {}
    for name in ("PK_VIRTQUEUE_SUBMIT", "PK_VIRTQUEUE_COMPLETE"):
        theirs = offer.get(name)
        if not isinstance(theirs, list) or not all(isinstance(v, int) and not isinstance(v, bool) for v in theirs):
            raise Inv35Error("INV35-E503", f"peer did not offer {name}")
        common = sorted(set(theirs) & set(SUPPORTED[name]), reverse=True)
        if not common:
            raise Inv35Error("INV35-E503", f"{name}: peer {theirs} vs local {list(SUPPORTED[name])}")
        agreed[name] = common[0]
    for name, versions in offer.items():
        if name in SUPPORTED and name not in agreed and isinstance(versions, list):
            common = sorted(set(versions) & set(SUPPORTED[name]), reverse=True)
            if common:
                agreed[name] = common[0]
    return agreed


@dataclass
class StallDetector:
    """A queue is stalled when work is pending and no completion was seen for ``threshold`` seconds."""

    threshold: float
    clock: Callable[[], float] = time.monotonic
    last_progress: dict[str, float] = field(default_factory=dict)

    def progress(self, queue: str) -> None:
        self.last_progress[queue] = self.clock()

    def check(self, queue: str, pending: int) -> dict[str, object]:
        now = self.clock()
        last = self.last_progress.setdefault(queue, now)
        idle = now - last
        stalled = pending > 0 and idle >= self.threshold
        return {"queue": queue, "pending": pending, "idle_s": round(idle, 6), "stalled": stalled,
                "threshold_s": self.threshold}


def status_document(*, version: str, config_digest: str, config_generation: int, queues: dict[str, dict[str, object]],
                    dependencies: dict[str, str], capabilities: list[str], saturation: float,
                    stalls: list[dict[str, object]]) -> dict[str, object]:
    live = True
    ready = bool(queues) and all(q["state"] in ("serving", "degraded") for q in queues.values()) \
        and not any(s["stalled"] for s in stalls) and dependencies.get("key_service") == "ok"
    return {
        "schema": "INV35_STATUS/1",
        "version": version,
        "live": live,
        "ready": ready,
        "config": {"digest": config_digest, "generation": config_generation},
        "interfaces": {k: list(v) for k, v in SUPPORTED.items()},
        "dependencies": dependencies,
        "capabilities": sorted(capabilities),
        "saturation": round(saturation, 6),
        "queues": queues,
        "stalls": [s for s in stalls if s["stalled"]],
    }
