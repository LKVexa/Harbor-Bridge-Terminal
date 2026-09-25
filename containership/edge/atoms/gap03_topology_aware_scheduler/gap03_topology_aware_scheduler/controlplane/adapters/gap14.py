"""MC-010 - GAP-14 data-gravity integration (GAP14-GRAV/1).

Anchors: {dataset (scoped id), replicas: [{node, bytes}], access: reads_per_h,
revision, observed_at, source, signature}.  Contribution (dimensionless,
0..1000) = min over replicas of locality_cost(anchor_node, candidate) *
size-weight; replicas are alternatives, never summed (no double counting).
Soft objective unless policy marks residency hard.  Stale/absent gravity ->
neutral contribution flagged in explain.
"""
from __future__ import annotations

import hashlib
import math

from ..errors import SchedulerError

SUPPORTED = ("1.0",)
TTL_S = 900
MAX_REPLICAS = 32


def scoped_id(tenant: str, dataset: str, salt: bytes) -> str:
    return "ds:" + hashlib.sha256(salt + tenant.encode() + b"\0" + dataset.encode()).hexdigest()[:20]


class Gravity:
    def __init__(self, *, trust=None, ttl_s: float = TTL_S, salt: bytes = b"gap03-default-salt", metrics=None):
        self.trust, self.ttl, self.salt, self.metrics = trust, ttl_s, salt, metrics
        self.anchors: dict[str, dict] = {}

    authorized_producers = None  # verified producer identities; None = not enforced

    def ingest(self, *args, producer: str | None = None, **kwargs):
        """Strict ingest; authorization of the producer, then structural defects map to INVALID_ARGUMENT."""
        if self.authorized_producers is not None and producer not in self.authorized_producers:
            raise SchedulerError("PERMISSION_DENIED", "producer not authorized")
        if not args or not isinstance(args[0], dict):
            raise SchedulerError("INVALID_ARGUMENT", "payload must be an object")
        metrics = getattr(self, "metrics", None)
        try:
            out = self._ingest(*args, **kwargs)
        except SchedulerError as exc:
            if metrics:
                metrics.inc("gap03_adapter_ingest_total", adapter="gap14", result=exc.code)
            raise
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            if metrics:
                metrics.inc("gap03_adapter_ingest_total", adapter="gap14", result="INVALID_ARGUMENT")
            raise SchedulerError("INVALID_ARGUMENT", f"malformed payload ({exc.__class__.__name__})") from None
        if metrics:
            metrics.inc("gap03_adapter_ingest_total", adapter="gap14", result=out if isinstance(out, str) else "ok")
        return out

    def _ingest(self, anchor: dict, snapshot) -> dict:
        if anchor.get("version") not in SUPPORTED:
            raise SchedulerError("UNSUPPORTED_VERSION", "GAP-14 version")
        reps = anchor.get("replicas", [])
        if not reps or len(reps) > MAX_REPLICAS:
            raise SchedulerError("INVALID_ARGUMENT", "replica count")
        for r in reps:
            if r["node"] not in snapshot.nodes:
                raise SchedulerError("NOT_IN_TOPOLOGY", "data anchor refers to unknown/decommissioned node")
            if not isinstance(r["bytes"], int) or r["bytes"] < 0 or r["bytes"] > 1 << 60:
                raise SchedulerError("INVALID_ARGUMENT", "replica size")
        if self.trust is not None:
            from ..identity import verify_artifact
            body = {k: v for k, v in anchor.items() if k != "envelope"}
            verify_artifact(self.trust, anchor.get("envelope", {}), body, kind="gravity_anchor")
        sid = scoped_id(anchor["tenant"], anchor["dataset"], self.salt)
        cur = self.anchors.get(sid)
        if cur and anchor["revision"] < cur["revision"]:
            raise SchedulerError("STALE_STATE", "older data-location revision")
        if cur and anchor["revision"] == cur["revision"] and cur["replicas"] != reps:
            raise SchedulerError("CONFLICT", "conflicting provenance at the same revision")
        rec = {"id": sid, "tenant": anchor["tenant"], "replicas": reps, "reads_per_h": int(anchor.get("reads_per_h", 0)),
               "revision": anchor["revision"], "observed_at": float(anchor["observed_at"]), "source": anchor["source"],
               "residency_hard": bool(anchor.get("residency_hard", False))}
        self.anchors[sid] = rec
        return rec

    def contribution(self, sid: str | None, candidate: str, snapshot, now: float) -> dict:
        rec = self.anchors.get(sid) if sid else None
        if rec is None:
            return {"value": 0, "status": "absent", "revision": None}
        if now - rec["observed_at"] > self.ttl:
            return {"value": 0, "status": "stale", "revision": rec["revision"], "age_s": round(now - rec["observed_at"], 1)}
        best = None
        # units: bytes (log2-scaled, 1 PiB ~ 1.0) x traffic factor (reads/hour, log2-scaled, capped 2x) x locality
        # class distance 0..101 normalised to 0..1 -> dimensionless 0..1000 (lower is better)
        traffic_w = min(2.0, 1.0 + math.log2(1 + rec["reads_per_h"]) / 20)
        for r in rec["replicas"]:
            cost = snapshot.cost(r["node"], candidate)  # 0..101
            size_w = min(1.0, math.log2(1 + r["bytes"]) / 50)
            v = min(1000, round(cost / 101 * size_w * traffic_w * 500))
            best = v if best is None else min(best, v)
        return {"value": best, "status": "fresh", "revision": rec["revision"], "residency_hard": rec["residency_hard"]}

    def hard_residency_ok(self, sid: str | None, candidate: str, snapshot) -> bool:
        rec = self.anchors.get(sid) if sid else None
        if rec is None or not rec["residency_hard"]:
            return True
        regions = {snapshot.path(r["node"])[0] for r in rec["replicas"]}
        return snapshot.path(candidate)[0] in regions

    def telemetry_view(self, sid: str) -> dict:
        rec = self.anchors[sid]
        return {"id": sid, "replica_count": len(rec["replicas"]), "revision": rec["revision"]}  # no names/locations
