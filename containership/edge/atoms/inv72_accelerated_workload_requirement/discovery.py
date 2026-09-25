"""Inventory intake from GAP-02 hardware discovery (C004, C018, C044, C045, C048, C055, C056).

The contract's source of truth is *discovered* inventory; an advertised node label is not trusted.  This
module is the only path by which devices enter a decision:

* snapshots must validate against PK_ACCEL_INVENTORY/1 and carry a content ``digest`` (SHA-256 of the
  canonical device list); with ``require_mac`` they must also carry an HMAC from the discovery service's
  key, so a tampered or spoofed snapshot is refused (C044/C045);
* generations must not go backwards (a replayed old snapshot is refused);
* a snapshot older than ``max_age_s`` is ``stale``; within ``offline_grace_s`` beyond that the last
  verified snapshot is still served but flagged **degraded** (intermittent uplink, C018/C056); beyond
  the grace window decisions stop with ``ACCEL_INVENTORY_STALE`` (fail closed);
* several sources may be registered in priority order; failover moves to the next source only if its
  snapshot verifies, so failover never widens trust (C055).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from .errors import AccelError
from .matcher import Device
from .schema_check import check


def canonical_devices(devices: list[dict]) -> bytes:
    return json.dumps(sorted(devices, key=lambda d: d["dev_id"]), sort_keys=True, separators=(",", ":")).encode()


def seal(snapshot: dict, key: bytes | None = None) -> dict:
    """Add digest (and MAC) to a snapshot - what a conforming GAP-02 publisher does."""
    out = dict(snapshot)
    out["digest"] = hashlib.sha256(canonical_devices(out["devices"])).hexdigest()
    if key:
        msg = f"{out['source']}|{out['generation']}|{out['observed_at']}|{out['digest']}".encode()
        out["mac"] = hmac.new(key, msg, hashlib.sha256).hexdigest()
    return out


def to_devices(snapshot: dict) -> list[Device]:
    return [Device(d["dev_id"], d["cls"], d["mem_gb"], d["node"], d["link_group"], d.get("partition_of", ""),
                   set(d.get("tenants", []))) for d in snapshot["devices"]]


@dataclass
class Source:
    name: str
    fetch: Callable[[], dict]
    key: bytes | None = None


@dataclass
class InventoryCache:
    sources: list
    max_age_s: float = 300.0
    offline_grace_s: float = 0.0
    require_mac: bool = True
    clock: Callable[[], float] = time.time
    _snapshot: dict | None = None
    _devices: list | None = None
    _generation: dict = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    last_error: str | None = None
    active_source: str | None = None

    def verify(self, snap: dict, src: Source) -> None:
        errs = check(snap, "PK_ACCEL_INVENTORY-1")
        if errs:
            raise AccelError("ACCEL_INVALID_INVENTORY", "; ".join(errs[:3]), source=src.name)
        if snap["source"] != src.name:
            raise AccelError("ACCEL_INVALID_INVENTORY", "snapshot source mismatch", source=src.name)
        want = hashlib.sha256(canonical_devices(snap["devices"])).hexdigest()
        if not hmac.compare_digest(snap.get("digest", ""), want):
            raise AccelError("ACCEL_INVALID_INVENTORY", "inventory digest mismatch", source=src.name)
        if self.require_mac:
            if not src.key or "mac" not in snap:
                raise AccelError("ACCEL_UNAUTHENTICATED", "inventory not authenticated", source=src.name)
            msg = f"{snap['source']}|{snap['generation']}|{snap['observed_at']}|{snap['digest']}".encode()
            if not hmac.compare_digest(hmac.new(src.key, msg, hashlib.sha256).hexdigest(), snap["mac"]):
                raise AccelError("ACCEL_UNAUTHENTICATED", "inventory MAC invalid", source=src.name)
        if snap["generation"] < self._generation.get(src.name, -1):
            raise AccelError("ACCEL_INVALID_INVENTORY", "inventory generation went backwards", source=src.name)
        if snap["observed_at"] > self.clock() + 30:
            raise AccelError("ACCEL_INVALID_INVENTORY", "inventory observed in the future", source=src.name)

    def refresh(self) -> str:
        """Try sources in priority order; keep the previous snapshot if none verifies."""
        errors = []
        for src in self.sources:
            try:
                snap = src.fetch()
                self.verify(snap, src)
                devices = to_devices(snap)  # Device.__post_init__ re-validates every field
            except AccelError as e:
                errors.append(f"{src.name}: {e.code}")
                continue
            except Exception as e:  # transport failure of one source
                errors.append(f"{src.name}: {type(e).__name__}")
                continue
            with self._lock:
                self._snapshot, self._devices = snap, devices
                self._generation[src.name] = snap["generation"]
                self.active_source, self.last_error = src.name, None
            return src.name
        self.last_error = "; ".join(errors) or "no sources"
        raise AccelError("ACCEL_DEPENDENCY_UNAVAILABLE", "no discovery source verified", errors=errors)

    def age(self) -> float | None:
        return None if self._snapshot is None else self.clock() - self._snapshot["observed_at"]

    def status(self) -> dict:
        a = self.age()
        state = ("empty" if a is None else "fresh" if a <= self.max_age_s
                 else "degraded" if a <= self.max_age_s + self.offline_grace_s else "stale")
        return {"state": state, "age_s": a, "generation": self._snapshot["generation"] if self._snapshot else None,
                "source": self.active_source, "last_error": self.last_error,
                "devices": len(self._devices or [])}

    def current(self) -> tuple[list[Device], dict]:
        st = self.status()
        if st["state"] in ("empty", "stale"):
            raise AccelError("ACCEL_INVENTORY_STALE", f"inventory {st['state']}", age_s=st["age_s"])
        return list(self._devices), st
