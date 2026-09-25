"""Hermetic adjacent-layer emulators (INV-68 MC-08, MC-29; C030, C082, C083).

The 4.2.0 contract names four neighbours.  None of their real implementations
was supplied, so INV-68 4.3.0 ships **emulators** that implement each
neighbour's side of the documented interface and are versioned with fixtures
in ``tests/fixtures/adjacent/``.  They prove INV-68's half of every boundary;
they do not certify the neighbours (``INTEGRATION_REAL`` evidence stays FAIL
until the real components are wired in -- see ``tools/integration.py``).

* **INV-67 Kubernetes integration mechanism (upstream)** --
  :func:`k8s_translate` turns Pod-style ``resources.requests`` quantities
  (``"500m"``, ``"2"``, ``"512Mi"``, ``"4Gi"``, ``"1G"``) into INV-68 ``cpu``
  (cores) and ``mem`` (GiB), refusing limits-only, negative, or unknown-unit
  quantities.
* **SCH-01 multi-runtime scheduler (upstream)** -- :class:`SchedulerClient`
  submits batches through :class:`service.PackingService`, retries only
  registry-retryable codes with the published backoff, and degrades to
  "hold batch" on terminal refusals.
* **GAP-10 power/thermal-aware scheduling (downstream)** --
  :func:`power_overlay` consumes a pack response and applies per-host power
  caps (W = idle + per-core * cpu_used); hosts over cap are reported, never
  silently re-packed (INV-68 does not own thermal policy).
* **INV-72 accelerated workload requirement (peer)** --
  :func:`split_accelerated` routes workloads carrying accelerator requests to
  INV-72 and passes the rest to INV-68, so the packer never sees a dimension it
  does not own.
"""
from __future__ import annotations

import re
import time
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterable, Mapping

from .errors import PackError
from .resilience import backoff_schedule, should_retry

_QTY = re.compile(r"^([0-9]+(?:\.[0-9]+)?)([a-zA-Z]*)$")
_CPU_UNITS = {"": Decimal(1), "m": Decimal("0.001")}
_MEM_UNITS = {
    "": Decimal(1) / Decimal(1024 ** 3), "k": Decimal(1000) / Decimal(1024 ** 3), "M": Decimal(10 ** 6) / Decimal(1024 ** 3),
    "G": Decimal(10 ** 9) / Decimal(1024 ** 3), "T": Decimal(10 ** 12) / Decimal(1024 ** 3),
    "Ki": Decimal(1) / Decimal(1024 ** 2), "Mi": Decimal(1) / Decimal(1024), "Gi": Decimal(1), "Ti": Decimal(1024),
}
ACCELERATOR_KEYS = ("nvidia.com/gpu", "amd.com/gpu", "gpu", "accelerator", "tpu")


def _quantity(text: Any, units: Mapping[str, Decimal], what: str) -> float:
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        text = str(text)
    if not isinstance(text, str):
        raise PackError("INVALID_REQUEST", f"{what} quantity must be a string")
    m = _QTY.fullmatch(text.strip())
    if not m or m.group(2) not in units:
        raise PackError("INVALID_REQUEST", f"unsupported {what} quantity", details={"quantity": text[:32]})
    try:
        return float(Decimal(m.group(1)) * units[m.group(2)])
    except InvalidOperation:
        raise PackError("INVALID_REQUEST", f"invalid {what} quantity") from None


def k8s_translate(pods: Iterable[Mapping[str, Any]]) -> list[dict]:
    """INV-67 emulator: Pod specs -> INV-68 workloads (requests, summed over containers)."""
    out = []
    for pod in pods:
        name = pod.get("metadata", {}).get("name")
        ns = pod.get("metadata", {}).get("namespace", "default")
        cpu = mem = 0.0
        for c in pod.get("spec", {}).get("containers", []):
            req = c.get("resources", {}).get("requests")
            if not req:
                raise PackError("INVALID_REQUEST", "container without resources.requests cannot be packed",
                                details={"pod": str(name)[:64]})
            cpu += _quantity(req.get("cpu", "0"), _CPU_UNITS, "cpu")
            mem += _quantity(req.get("memory", "0"), _MEM_UNITS, "memory")
        out.append({"name": f"{ns}/{name}", "cpu": round(cpu, 6), "mem": round(mem, 6)})
    return out


def split_accelerated(workloads: Iterable[Mapping[str, Any]]) -> tuple[list[dict], list[dict]]:
    """INV-72 emulator: return ``(for_inv68, for_inv72)``."""
    mine, peer = [], []
    for w in workloads:
        if any(k in w for k in ACCELERATOR_KEYS):
            peer.append(dict(w))
        else:
            mine.append({k: v for k, v in w.items()})
    return mine, peer


def power_overlay(response: Mapping[str, Any], *, idle_w: float, per_core_w: float, cap_w: float) -> dict:
    """GAP-10 emulator: apply a per-host power cap on top of a pack response."""
    hosts = response["result"]["hosts"]
    rows = []
    for h in hosts:
        watts = idle_w + per_core_w * h["used"]["cpu"]
        rows.append({"host": h["name"], "watts": round(watts, 3), "over_cap": watts > cap_w})
    return {"schema": "GAP10_POWER_VIEW/emulated", "cap_w": cap_w, "hosts": rows,
            "over_cap": [r["host"] for r in rows if r["over_cap"]]}


class SchedulerClient:
    """SCH-01 emulator: batches work through the packing service with safe retries."""

    def __init__(self, service, token_factory: Callable[[], str], *, attempts: int = 4,
                 sleep: Callable[[float], None] = time.sleep, rng=None):
        self.service = service
        self.token_factory = token_factory
        self.attempts = attempts
        self.sleep = sleep
        self.rng = rng
        self.log: list[str] = []

    def place(self, request: Mapping[str, Any]) -> dict:
        delays = backoff_schedule(self.attempts, rng=self.rng)
        last: PackError | None = None
        for attempt in range(self.attempts + 1):
            try:
                resp = self.service.pack(dict(request), self.token_factory())
                self.log.append(f"attempt {attempt}: {resp['outcome']}")
                return {"state": "placed" if resp["outcome"] == "success" else "partially_placed", "response": resp}
            except PackError as err:
                last = err
                self.log.append(f"attempt {attempt}: {err.code}")
                if not should_retry(err.code) or attempt == self.attempts:
                    break
                self.sleep(delays[attempt] / 1000.0)
        return {"state": "held", "error": last.to_dict() if last else None}
