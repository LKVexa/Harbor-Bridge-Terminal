"""Hardware-facing adapters: GAP11-P0-06 inventory, P0-07 partition topology,
P0-08 scrub/reset executor, P1-19 power/thermal admission, P1-20 health/RAS.

Every adapter here is written against a *provider protocol*. The shipped providers
are deterministic simulators that reproduce vendor payload shapes, units, transient
errors and lifecycle events. **No real vendor binding (NVML, ROCm SMI, Level Zero,
FPGA/NPU SDKs) is bundled**: this environment has no accelerator hardware, so every
check that requires "live hardware" is recorded BLOCKED in the traceability matrix,
never satisfied by the simulator.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from .common import ControlError, Telemetry, digest, utc_iso

# ------------------------------------------------------------------ canonical model
CANONICAL_FIELDS = ("stable_id", "device", "kind", "vendor", "generation", "memory_gb", "features",
                    "partitions", "node", "topology", "driver", "firmware", "health")
KINDS = {"gpu", "npu", "fpga", "generic"}


class TransientProviderError(Exception):
    """Retryable provider failure (busy, timeout, try-again)."""


class PermanentProviderError(Exception):
    """Non-retryable provider failure."""


class InventoryProvider(Protocol):
    vendor: str

    def list_devices(self) -> list[dict[str, Any]]: ...


def with_retry(fn: Callable[[], Any], *, deadline: float, clock: Any, attempts: int = 5,
               base_delay: float = 0.05, sleep: Callable[[float], None] | None = None) -> Any:
    """Bounded retry with exponential backoff that never overruns ``deadline`` (monotonic)."""
    sleep = sleep or (lambda s: clock.advance(s) if hasattr(clock, "advance") else time.sleep(s))
    delay = base_delay
    last: Exception | None = None
    for _ in range(attempts):
        if clock.monotonic() >= deadline:
            break
        try:
            return fn()
        except TransientProviderError as exc:
            last = exc
            if clock.monotonic() + delay >= deadline:
                break
            sleep(delay)
            delay *= 2
    raise ControlError("DEADLINE_EXCEEDED", f"provider did not succeed before deadline: {last}")


# -- vendor normalisation -------------------------------------------------------------
def normalize(vendor: str, raw: dict[str, Any], node: str) -> dict[str, Any]:
    """Map a vendor payload into the canonical model. Unknown vendors are refused."""
    if vendor == "simnv":        # NVML-like: bytes, uuid, MIG profiles
        mem = raw["memory_total_bytes"] // (1024 ** 3)
        parts = [{"name": p["profile"], "memory_gb": p["memory_mib"] // 1024, "features": None} for p in raw.get("mig", [])]
        rec = {"stable_id": raw["uuid"], "device": raw["uuid"][-12:], "kind": "gpu", "generation": raw["arch"],
               "memory_gb": mem, "features": sorted(raw.get("caps", [])), "partitions": parts,
               "topology": {"pci": raw["pci_bus_id"], "numa": raw.get("numa_node", 0), "fabric": raw.get("nvlink_domain")},
               "driver": raw["driver"], "firmware": raw["vbios"], "health": "failed" if raw.get("xid_errors") else "ok"}
    elif vendor == "simamd":     # ROCm-SMI-like: MiB, serial, "GFX" enums
        mem = raw["vram_mib"] // 1024
        rec = {"stable_id": "amd-" + raw["serial"], "device": "amd-" + raw["serial"][-8:], "kind": "gpu",
               "generation": {"GFX942": "cdna3", "GFX90A": "cdna2"}.get(raw["gfx"], raw["gfx"].lower()),
               "memory_gb": mem, "features": sorted(raw.get("features", [])), "partitions": [],
               "topology": {"pci": raw["bdf"], "numa": raw.get("numa", 0), "fabric": raw.get("xgmi_hive")},
               "driver": raw["driver_version"], "firmware": raw["fw"], "health": "ok" if raw.get("ras_ue", 0) == 0 else "failed"}
    elif vendor == "simnpu":
        rec = {"stable_id": raw["id"], "device": raw["id"], "kind": "npu", "generation": raw["gen"],
               "memory_gb": raw["mem_gb"], "features": sorted(raw.get("ops", [])), "partitions": [],
               "topology": {"numa": raw.get("numa", 0)}, "driver": raw["drv"], "firmware": raw["fw"], "health": "ok"}
    else:
        raise ControlError("SCHEMA_INVALID", f"unsupported vendor {vendor!r}")
    rec.update(vendor=vendor, node=node)
    if rec["kind"] not in KINDS or rec["memory_gb"] <= 0:
        raise ControlError("SCHEMA_INVALID", "normalised record invalid", stable_id=rec["stable_id"])
    return rec


class InventoryAdapter:
    """Collects, normalises and diffs inventory; keyed by stable identity, not PCI address."""

    def __init__(self, providers: list[InventoryProvider], *, node: str, clock: Any,
                 telemetry: Telemetry | None = None, deadline_s: float = 2.0) -> None:
        self.providers = providers
        self.node = node
        self.clock = clock
        self.tel = telemetry or Telemetry(clock)
        self.deadline_s = deadline_s
        self.known: dict[str, dict[str, Any]] = {}

    def collect(self) -> dict[str, Any]:
        seen: dict[str, dict[str, Any]] = {}
        errors = []
        for p in self.providers:
            try:
                raw = with_retry(p.list_devices, deadline=self.clock.monotonic() + self.deadline_s, clock=self.clock)
            except ControlError as exc:
                errors.append({"vendor": p.vendor, "code": exc.code})
                self.tel.emit("inventory", "provider_failed", code=exc.code, severity="ERROR", detail=p.vendor)
                continue
            for item in raw:
                rec = normalize(p.vendor, item, self.node)
                seen[rec["stable_id"]] = rec
        failed_vendors = {e["vendor"] for e in errors}
        added = sorted(set(seen) - set(self.known))
        # a device from a vendor whose provider failed is *unknown*, not *removed*
        removed = sorted(k for k in set(self.known) - set(seen) if self.known[k]["vendor"] not in failed_vendors)
        changed = sorted(k for k in set(seen) & set(self.known) if digest(seen[k]) != digest(self.known[k]))
        renumbered = sorted(k for k in changed if seen[k]["topology"].get("pci") != self.known[k]["topology"].get("pci")
                            and {**seen[k], "topology": None} == {**self.known[k], "topology": None})
        for k in removed:
            del self.known[k]
        self.known.update(seen)
        evidence = {"schema": "PK_INVENTORY_EVIDENCE/1", "node": self.node, "ts": utc_iso(self.clock.wall()),
                    "devices": sorted(seen), "added": added, "removed": removed, "changed": changed,
                    "renumbered_only": renumbered, "provider_errors": errors}
        return {"devices": seen, "evidence": evidence}


# ------------------------------------------------------------------ partition topology (P0-07)
@dataclass(frozen=True)
class PartitionProfile:
    """One *layout*: a set of slices that may exist simultaneously on a device."""
    name: str
    slices: tuple[tuple[str, int], ...]  # (slice name, memory_gb)


class PartitionTopology:
    """Alternative layouts per device model; reconfiguration only on an idle device."""

    def __init__(self, memory_gb: int, profiles: list[PartitionProfile]) -> None:
        for p in profiles:
            if sum(m for _, m in p.slices) > memory_gb:
                raise ControlError("CONFIG_INVALID", f"profile {p.name} oversubscribes memory")
            if len({n for n, _ in p.slices}) != len(p.slices):
                raise ControlError("CONFIG_INVALID", f"profile {p.name} repeats a slice name")
        self.memory_gb = memory_gb
        self.profiles = {p.name: p for p in profiles}
        self.active: str | None = None

    def compatible(self, a: str, b: str) -> bool:
        return a == b  # distinct layouts are mutually exclusive on one device

    def reconfigure(self, profile: str, *, active_leases: int, drained: bool) -> list[dict[str, Any]]:
        if profile not in self.profiles:
            raise ControlError("CONSTRAINT_UNSATISFIED", f"unknown profile {profile}")
        if active_leases or not drained:
            raise ControlError("ILLEGAL_TRANSITION", "reconfigure requires a drained device with no leases")
        self.active = profile
        return [{"name": n, "memory_gb": m, "features": None} for n, m in self.profiles[profile].slices]

    def residual_after(self, profile: str, demand: list[int]) -> int:
        """Unusable residual memory if ``demand`` slices are placed on ``profile``."""
        free = sorted((m for _, m in self.profiles[profile].slices))
        waste = 0
        for need in sorted(demand, reverse=True):
            fit = next((m for m in free if m >= need), None)
            if fit is None:
                return 10 ** 9
            free.remove(fit)
            waste += fit - need
        return waste + sum(free)

    def best_profile(self, demand: list[int]) -> str:
        return min(sorted(self.profiles), key=lambda p: (self.residual_after(p, demand), p))


# ------------------------------------------------------------------ scrub/reset executor (P0-08)
class ScrubBackend(Protocol):
    def reset(self, device: dict[str, Any]) -> None: ...
    def zeroize(self, device: dict[str, Any]) -> None: ...
    def verify(self, device: dict[str, Any]) -> dict[str, Any]: ...


class ScrubExecutor:
    """Runs reset -> zeroize -> independent verify with a deadline; any doubt quarantines."""

    def __init__(self, backend: ScrubBackend, *, clock: Any, deadline_s: float = 60.0, attempts: int = 3) -> None:
        self.backend = backend
        self.clock = clock
        self.deadline_s = deadline_s
        self.attempts = attempts

    def scrub(self, device: dict[str, Any]) -> dict[str, Any]:
        start = self.clock.monotonic()
        deadline = start + self.deadline_s
        ev = {"schema": "PK_SCRUB_EVIDENCE/1", "device": device["device"], "stable_id": device.get("stable_id"),
              "started": utc_iso(self.clock.wall()), "steps": []}
        try:
            for step in ("reset", "zeroize"):
                with_retry(lambda: getattr(self.backend, step)(device), deadline=deadline, clock=self.clock, attempts=self.attempts)
                ev["steps"].append(step)
            check = with_retry(lambda: self.backend.verify(device), deadline=deadline, clock=self.clock, attempts=self.attempts)
            ev["steps"].append("verify")
        except ControlError as exc:
            return {**ev, "verified": False, "code": "SCRUB_TIMEOUT" if exc.code == "DEADLINE_EXCEEDED" else exc.code,
                    "elapsed_s": self.clock.monotonic() - start}
        except PermanentProviderError as exc:
            return {**ev, "verified": False, "code": "SCRUB_FAILED", "error": str(exc), "elapsed_s": self.clock.monotonic() - start}
        ok = bool(check.get("zero_pattern_ok")) and bool(check.get("health_ok")) and check.get("residual_nonzero_pages", 1) == 0
        return {**ev, "verified": ok, "code": "OK" if ok else "SCRUB_FAILED", "verify": check,
                "elapsed_s": self.clock.monotonic() - start}


class SimScrubBackend:
    """Simulated device memory: zeroize clears pages unless a fault is configured."""

    def __init__(self, *, fail: str | None = None, transient: int = 0, slow_s: float = 0.0, clock: Any = None) -> None:
        self.memory: dict[str, list[int]] = {}
        self.fail, self.transient, self.slow_s, self.clock = fail, transient, slow_s, clock

    def load(self, device: str, pages: list[int]) -> None:
        self.memory[device] = list(pages)

    def _maybe(self) -> None:
        if self.slow_s and self.clock is not None:
            self.clock.advance(self.slow_s)
        if self.transient > 0:
            self.transient -= 1
            raise TransientProviderError("busy")

    def reset(self, device: dict[str, Any]) -> None:
        self._maybe()
        if self.fail == "reset":
            raise PermanentProviderError("reset rejected by device")

    def zeroize(self, device: dict[str, Any]) -> None:
        self._maybe()
        if self.fail != "zeroize_partial":
            self.memory[device["device"]] = [0] * len(self.memory.get(device["device"], [0] * 8))
        else:
            pages = self.memory.get(device["device"], [7] * 8)
            self.memory[device["device"]] = [0] * (len(pages) // 2) + pages[len(pages) // 2:]

    def verify(self, device: dict[str, Any]) -> dict[str, Any]:
        pages = self.memory.get(device["device"], [0] * 8)
        nz = sum(1 for p in pages if p)
        return {"zero_pattern_ok": nz == 0, "residual_nonzero_pages": nz, "health_ok": self.fail != "health"}


# ------------------------------------------------------------------ power / thermal (P1-19)
class ThermalAdmission:
    """GAP-10 adapter: stale or missing readings fail closed (device not admissible)."""

    def __init__(self, *, clock: Any, max_age_s: float = 5.0, max_temp_c: float = 85.0, max_power_w: float = 700.0) -> None:
        self.clock = clock
        self.max_age_s, self.max_temp_c, self.max_power_w = max_age_s, max_temp_c, max_power_w
        self.readings: dict[str, dict[str, float]] = {}

    def report(self, device: str, *, temp_c: float, power_w: float, budget_ok: bool = True) -> None:
        self.readings[device] = {"temp_c": temp_c, "power_w": power_w, "at": self.clock.monotonic(), "budget_ok": budget_ok}

    def admissible(self, device: str) -> tuple[bool, str]:
        r = self.readings.get(device)
        if r is None:
            return False, "THERMAL_UNAVAILABLE"
        if self.clock.monotonic() - r["at"] > self.max_age_s:
            return False, "THERMAL_UNAVAILABLE"
        if r["temp_c"] >= self.max_temp_c or r["power_w"] > self.max_power_w or not r["budget_ok"]:
            return False, "THERMAL_UNAVAILABLE"
        return True, "OK"


# ------------------------------------------------------------------ health / RAS (P1-20)
class HealthMonitor:
    """Classifies RAS signals; reset storms and uncorrectable errors quarantine."""

    UNCORRECTABLE = {"ecc_uncorrectable", "xid_fatal", "link_down", "fallen_off_bus"}
    DEGRADING = {"ecc_correctable", "link_degraded", "thermal_throttle", "xid_recoverable"}

    def __init__(self, *, clock: Any, storm_window_s: float = 600.0, storm_threshold: int = 3,
                 correctable_threshold: int = 100) -> None:
        self.clock = clock
        self.storm_window_s, self.storm_threshold = storm_window_s, storm_threshold
        self.correctable_threshold = correctable_threshold
        self.resets: dict[str, list[float]] = {}
        self.correctable: dict[str, int] = {}

    def observe(self, device: str, signal: str, count: int = 1) -> str:
        now = self.clock.monotonic()
        if signal in self.UNCORRECTABLE:
            return "failed"
        if signal == "reset":
            hist = [t for t in self.resets.get(device, []) if now - t <= self.storm_window_s] + [now]
            self.resets[device] = hist
            return "failed" if len(hist) >= self.storm_threshold else "degraded"
        if signal in self.DEGRADING:
            if signal == "ecc_correctable":
                self.correctable[device] = self.correctable.get(device, 0) + count
                return "failed" if self.correctable[device] >= self.correctable_threshold else "degraded"
            return "degraded"
        raise ControlError("SCHEMA_INVALID", f"unknown RAS signal {signal!r}")
