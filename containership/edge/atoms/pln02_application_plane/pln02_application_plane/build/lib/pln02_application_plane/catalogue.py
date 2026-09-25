"""MC-27 / MC-06 - Signed provider catalogue client, freshness, and disconnected cache.

``PK_SIGNED_CATALOGUE/1`` document::

    {"schema": "PK_SIGNED_CATALOGUE/1", "environment": "prod", "site": "eu-1",
     "generation": 42, "issued_at": 1.7e9, "expires_at": 1.7e9+3600,
     "providers": {"state": [{"id": "redis-a", "region": "eu", "residency": ["eu"],
                              "tier": "hardened", "consistency": "strong",
                              "slo_ms": 50, "latency_ms": 3, "cost": 2, "healthy": true}]},
     "key_id": "cat-2026", "signature": "<b64>"}

The client verifies the signature against the ``catalogue`` trust roots,
refuses generation rollback, enforces freshness, and persists the last good
snapshot atomically for disconnected operation. Offline serving is allowed
only under a live autonomy lease (GAP-04 contract) and only within
``max_offline_seconds``; signatures are *still* verified offline.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
import pathlib
import tempfile
import time
from typing import Any, Callable, Mapping

from .admission import CircuitBreaker
from .errors import PlaneError
from .trust import KeyRing

SIGNED_CATALOGUE_SCHEMA = "PK_SIGNED_CATALOGUE/1"
MAX_PROVIDERS_PER_CAPABILITY = 64
PROVIDER_FIELDS = {"id", "region", "residency", "tier", "consistency", "slo_ms", "latency_ms", "cost", "healthy"}
TOP_FIELDS = {"schema", "environment", "site", "generation", "issued_at", "expires_at", "providers", "key_id", "signature"}


def _body(doc: Mapping[str, Any]) -> dict:
    return {k: doc[k] for k in TOP_FIELDS - {"signature", "key_id"}}


def sign_catalogue(ring: KeyRing, key_id: str, body: Mapping[str, Any]) -> dict:
    doc = dict(body)
    doc["schema"] = SIGNED_CATALOGUE_SCHEMA
    doc["key_id"] = key_id
    doc["signature"] = ring.sign(key_id, "catalogue", _body(doc))
    return doc


def validate_shape(doc: Any) -> None:
    def bad(reason: str) -> PlaneError:
        return PlaneError(f"catalogue malformed: {reason}", code="CATALOGUE_UNTRUSTED", details={"key_id": None})
    if not isinstance(doc, Mapping) or set(doc) != TOP_FIELDS or doc.get("schema") != SIGNED_CATALOGUE_SCHEMA:
        raise bad("envelope")
    if type(doc["generation"]) is not int or doc["generation"] < 0:
        raise bad("generation")
    if not isinstance(doc["providers"], Mapping) or len(doc["providers"]) > 4096:
        raise bad("providers")
    for cap, cands in doc["providers"].items():
        if not isinstance(cands, list) or not 0 < len(cands) <= MAX_PROVIDERS_PER_CAPABILITY:
            raise bad(f"candidates for {cap}")
        for c in cands:
            if not isinstance(c, Mapping) or set(c) != PROVIDER_FIELDS or not isinstance(c["residency"], list):
                raise bad(f"candidate for {cap}")


@dataclass
class Snapshot:
    doc: dict
    received_at: float
    degraded: bool = False  # served from cache while disconnected

    @property
    def generation(self) -> int:
        return self.doc["generation"]

    @property
    def digest(self) -> str:
        from .resolver import _digest
        return _digest(self.doc)


class AutonomyLease:
    """Minimal GAP-04 lease contract: offline authority granted until ``expires``."""

    def __init__(self, holder: str, expires: float) -> None:
        self.holder, self.expires = holder, expires

    def live(self, now: float) -> bool:
        return now < self.expires


class CatalogueClient:
    def __init__(self, source: Callable[[], Mapping[str, Any]], ring: KeyRing, *, environment: str, site: str,
                 cache_path: str | os.PathLike | None = None, max_age_seconds: float = 300.0,
                 max_offline_seconds: float = 3600.0, clock: Callable[[], float] = time.time,
                 breaker: CircuitBreaker | None = None) -> None:
        self.source, self.ring = source, ring
        self.environment, self.site = environment, site
        self.cache_path = pathlib.Path(cache_path) if cache_path else None
        self.max_age, self.max_offline = max_age_seconds, max_offline_seconds
        self._clock = clock
        self.breaker = breaker or CircuitBreaker("catalogue", clock=time.monotonic)
        self.lease: AutonomyLease | None = None
        self._current: Snapshot | None = self._load_cache()

    # -- verification -------------------------------------------------------------
    def _verify(self, doc: Mapping[str, Any]) -> dict:
        validate_shape(doc)
        self.ring.verify(doc["key_id"], "catalogue", _body(doc), doc["signature"])
        if doc["environment"] != self.environment or doc["site"] != self.site:
            raise PlaneError("catalogue scope mismatch", code="CATALOGUE_UNTRUSTED", details={"key_id": doc["key_id"]})
        return json.loads(json.dumps(doc))  # detached copy

    def _load_cache(self) -> Snapshot | None:
        if not self.cache_path or not self.cache_path.exists():
            return None
        try:
            wrapper = json.loads(self.cache_path.read_text("utf-8"))
            return Snapshot(self._verify(wrapper["doc"]), float(wrapper["received_at"]))
        except Exception:
            return None  # a corrupt/untrusted cache is ignored, never trusted

    def _persist(self, snap: Snapshot) -> None:
        if not self.cache_path:
            return
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.cache_path.parent, prefix=".cat-")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"doc": snap.doc, "received_at": snap.received_at}, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.cache_path)

    # -- acquisition --------------------------------------------------------------
    def refresh(self) -> Snapshot:
        doc = self.breaker.call(self.source)
        verified = self._verify(doc)
        now = self._clock()
        if verified["expires_at"] <= now:
            raise PlaneError("catalogue already expired", code="CATALOGUE_STALE",
                             details={"age_seconds": now - verified["issued_at"], "max_age_seconds": self.max_age})
        if self._current is not None and verified["generation"] < self._current.generation:
            raise PlaneError("catalogue generation rollback refused", code="CATALOGUE_UNTRUSTED",
                             details={"key_id": verified["key_id"]})
        snap = Snapshot(verified, now)
        self._current = snap
        self._persist(snap)
        return snap

    def snapshot(self) -> Snapshot:
        """Return a fresh snapshot, refreshing if needed; degrade to cache only under a live lease."""
        now = self._clock()
        cur = self._current
        if cur is not None and now - cur.received_at <= self.max_age and cur.doc["expires_at"] > now:
            return cur
        try:
            return self.refresh()
        except PlaneError as exc:
            if exc.code not in {"CATALOGUE_UNAVAILABLE", "CIRCUIT_OPEN"}:
                raise
            return self._offline(now)
        except Exception:
            return self._offline(now)

    def _offline(self, now: float) -> Snapshot:
        cur = self._current
        if cur is None:
            raise PlaneError("no catalogue available", code="CATALOGUE_UNAVAILABLE")
        if self.lease is None or not self.lease.live(now):
            raise PlaneError("catalogue stale and no autonomy lease", code="CATALOGUE_STALE",
                             details={"age_seconds": round(now - cur.received_at, 3), "max_age_seconds": self.max_age})
        if now - cur.received_at > self.max_offline:
            raise PlaneError("offline window exceeded", code="CATALOGUE_STALE",
                             details={"age_seconds": round(now - cur.received_at, 3), "max_age_seconds": self.max_offline})
        return Snapshot(cur.doc, cur.received_at, degraded=True)
