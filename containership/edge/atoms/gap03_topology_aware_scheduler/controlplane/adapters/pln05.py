"""MC-011 - PLN-05 elasticity/demand integration (PLN05-DEMAND/1).

Demand signals are ADVISORY: they may re-order surplus preference and feed
capacity planning; they can never override physical capacity, security or
fairness gates.  Stale (> ttl) or low-confidence forecasts are discarded;
PLN-05 outage falls back to last-known-good for ``lkg_ttl`` then to a zero
baseline.  Updates are debounced with hysteresis.
"""
from __future__ import annotations

from ..errors import SchedulerError

SUPPORTED = ("1.0",)
UNITS = {"slot": 1, "kslot": 1000}
MIN_CONFIDENCE = 0.5
TTL_S = 600
LKG_TTL_S = 1800
HYSTERESIS = 0.1
MIN_INTERVAL_S = 30


class Demand:
    def __init__(self, metrics=None):
        self.metrics = metrics
        self.current: dict[str, dict] = {}
        self.last_update: dict[str, float] = {}
        self.in_flight: dict[str, int] = {}
        self.seen_requests: set[str] = set()

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
                metrics.inc("gap03_adapter_ingest_total", adapter="pln05", result=exc.code)
            raise
        except (KeyError, TypeError, AttributeError, ValueError) as exc:
            if metrics:
                metrics.inc("gap03_adapter_ingest_total", adapter="pln05", result="INVALID_ARGUMENT")
            raise SchedulerError("INVALID_ARGUMENT", f"malformed payload ({exc.__class__.__name__})") from None
        if metrics:
            metrics.inc("gap03_adapter_ingest_total", adapter="pln05", result=out if isinstance(out, str) else "ok")
        return out

    def _ingest(self, sig: dict, now: float) -> str:
        if sig.get("version") not in SUPPORTED:
            raise SchedulerError("UNSUPPORTED_VERSION", "PLN-05 version")
        if sig["request_id"] in self.seen_requests:
            return "duplicate"
        if sig["unit"] not in UNITS or sig.get("resource_class") != "slots":
            raise SchedulerError("INVALID_ARGUMENT", "unit/resource class")
        q = sig["quantity"]
        if isinstance(q, bool) or not isinstance(q, int) or not 0 <= q <= 10_000:
            raise SchedulerError("INVALID_ARGUMENT", "quantity bounds")
        conf = float(sig["confidence"])
        if not 0.0 <= conf <= 1.0:
            raise SchedulerError("INVALID_ARGUMENT", "confidence bounds")
        self.seen_requests.add(sig["request_id"])
        if conf < MIN_CONFIDENCE:
            return "discarded_low_confidence"
        if now - sig["observed_at"] > TTL_S:
            return "discarded_stale"
        tenant = sig["tenant"]
        slots = q * UNITS[sig["unit"]]
        cur = self.current.get(tenant)
        if cur and cur["revision"] > sig["revision"]:
            return "discarded_out_of_order"
        if cur and now - self.last_update.get(tenant, 0) < MIN_INTERVAL_S:
            return "debounced"
        if cur and abs(slots - cur["slots"]) <= HYSTERESIS * max(1, cur["slots"]):
            return "within_hysteresis"
        self.current[tenant] = {"slots": slots, "revision": sig["revision"], "request_id": sig["request_id"],
                                "observed_at": sig["observed_at"], "confidence": conf}
        self.last_update[tenant] = now
        return "accepted"

    def note_placement(self, tenant: str, slots: int):
        self.in_flight[tenant] = self.in_flight.get(tenant, 0) + slots

    def advisory(self, tenant: str, now: float) -> dict:
        cur = self.current.get(tenant)
        if cur is None:
            return {"slots": 0, "status": "baseline", "request_id": None}
        age = now - cur["observed_at"]
        if age > TTL_S + LKG_TTL_S:
            return {"slots": 0, "status": "baseline", "request_id": cur["request_id"]}
        net = max(0, cur["slots"] - self.in_flight.get(tenant, 0))  # no double counting of capacity in transit
        return {"slots": net, "status": "fresh" if age <= TTL_S else "last_known_good", "request_id": cur["request_id"],
                "revision": cur["revision"]}
