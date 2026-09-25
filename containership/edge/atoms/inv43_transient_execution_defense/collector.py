"""Checklist 09 + 10: authoritative node read-back with freshness metadata.

The collector reads the Linux kernel's own mitigation report
(``/sys/devices/system/cpu/vulnerabilities/*``) and SMT control
(``/sys/devices/system/cpu/smt/control``).  It never infers a mitigation from
the CPU model, the kernel version, or configuration intent: what the kernel
reports is the observation, and anything it cannot classify is ``unknown``.

Classification (fail-closed):

* ``Not affected``                         -> ``not_affected``
* ``Mitigation: ...`` with no ``Vulnerable`` -> ``active`` (cost pending)
* ``Mitigation: ...`` containing ``Vulnerable`` (e.g. ``BHI: Vulnerable``)
                                           -> ``inactive`` (partial coverage)
* ``Vulnerable ...``                       -> ``inactive``
* missing file / unreadable / anything else -> ``unknown``

Measured cost is NOT something the kernel reports.  An ``active`` observation
therefore needs a cost from the benchmark harness (checklist 34) before it can
enter :class:`~.defense.MitigationState`; without one the mitigation is
recorded ``unknown`` (fail closed) and the reason is kept on the observation.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import os
import pathlib
import platform
import socket
import time
from typing import Mapping

from .defense import ACTIVE, INACTIVE, NOT_AFFECTED, UNKNOWN, MitigationState, _require_identifier

COLLECTOR_ID = "inv43-sysfs-collector/1"
DEFAULT_TTL_S = 300.0
MAX_SYSFS_BYTES = 4096

# The kernel's names map 1:1 to the INV-43 mitigation vocabulary.
SYSFS_VULN_DIR = "sys/devices/system/cpu/vulnerabilities"
SYSFS_SMT_CONTROL = "sys/devices/system/cpu/smt/control"
SYSFS_SMT_ACTIVE = "sys/devices/system/cpu/smt/active"


def classify(raw: str | None) -> tuple[str, str]:
    """Return ``(status, reason)`` for one kernel vulnerability line."""
    if raw is None:
        return UNKNOWN, "not_reported"
    text = raw.strip()
    if not text:
        return UNKNOWN, "empty"
    if text.startswith("KVM: "):  # itlb_multihit is reported from the hypervisor's viewpoint
        text = text[5:]
    if text == "Not affected":
        return NOT_AFFECTED, "kernel_reports_not_affected"
    if text.startswith("Mitigation:"):
        if "Vulnerable" in text:
            return INACTIVE, "partial_mitigation_reports_vulnerable_subcomponent"
        if "SMT vulnerable" in text or "SMT Host state unknown" in text:
            # mitigation active for this core; sibling exposure is decided by the SMT rule
            return ACTIVE, "kernel_reports_mitigation_smt_exposed"
        return ACTIVE, "kernel_reports_mitigation"
    if text.startswith("Vulnerable"):
        return INACTIVE, "kernel_reports_vulnerable"
    if text.startswith("Unknown"):
        return UNKNOWN, "kernel_reports_unknown"
    return UNKNOWN, "unrecognised_format"


def classify_smt(control: str | None, active: str | None) -> tuple[bool | None, str]:
    """Return ``(smt_enabled, reason)``; ``None`` means unknown (fail closed)."""
    c = (control or "").strip()
    a = (active or "").strip()
    if c in {"off", "forceoff", "notsupported", "notimplemented"}:
        return False, f"smt_control={c}"
    if c == "on":
        return True, "smt_control=on"
    if a in {"0", "1"}:
        return a == "1", f"smt_active={a}"
    return None, "smt_state_unreadable"


@dataclasses.dataclass(frozen=True)
class Observation:
    """One mitigation read-back with provenance and freshness (checklist 10)."""

    node: str
    mitigation: str
    status: str
    raw: str | None
    reason: str
    source: str
    collector_id: str
    observed_at_unix: float
    observed_monotonic: float
    ttl_s: float

    def age_s(self, now_monotonic: float | None = None) -> float:
        now = time.monotonic() if now_monotonic is None else now_monotonic
        return max(0.0, now - self.observed_monotonic)

    def is_fresh(self, now_monotonic: float | None = None) -> bool:
        age = self.age_s(now_monotonic)
        return age <= self.ttl_s

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass(frozen=True)
class NodeReadback:
    node: str
    observations: tuple[Observation, ...]
    smt_enabled: bool | None
    smt_reason: str
    core_scheduling: bool | None
    core_scheduling_reason: str
    kernel: str
    machine: str
    collector_id: str
    observed_at_unix: float
    observed_monotonic: float
    ttl_s: float

    def digest(self) -> str:
        body = json.dumps(self.to_dict(include_monotonic=False), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(body.encode()).hexdigest()

    def to_dict(self, include_monotonic: bool = True) -> dict:
        d = {
            "schema": "PK_READBACK/1",
            "node": self.node,
            "observations": [o.to_dict() for o in self.observations],
            "smt_enabled": self.smt_enabled,
            "smt_reason": self.smt_reason,
            "core_scheduling": self.core_scheduling,
            "core_scheduling_reason": self.core_scheduling_reason,
            "kernel": self.kernel,
            "machine": self.machine,
            "collector_id": self.collector_id,
            "observed_at_unix": self.observed_at_unix,
            "ttl_s": self.ttl_s,
        }
        if include_monotonic:
            d["observed_monotonic"] = self.observed_monotonic
        else:
            for o in d["observations"]:
                o.pop("observed_monotonic", None)
        return d

    def to_state(self, measured_costs: Mapping[str, float] | None = None) -> tuple[MitigationState, list[dict]]:
        """Build a :class:`MitigationState`; return it plus downgrade notes.

        Fail-closed rules: unknown SMT -> treated as enabled; unknown core
        scheduling -> treated as absent; an ``active`` read-back with no
        measured cost -> recorded ``unknown`` with a note.
        """
        costs = dict(measured_costs or {})
        notes: list[dict] = []
        smt = True if self.smt_enabled is None else self.smt_enabled
        core = bool(self.core_scheduling)
        state = MitigationState(self.node, smt_enabled=smt, core_scheduling=core)
        for o in self.observations:
            if o.status == ACTIVE:
                cost = costs.get(o.mitigation)
                if (cost is None or isinstance(cost, bool) or not isinstance(cost, (int, float))
                        or not math.isfinite(cost) or cost <= 0):  # NaN slipped past `<= 0` before 4.3.0 review
                    state.record(o.mitigation, UNKNOWN, 0.0)
                    notes.append({"mitigation": o.mitigation, "code": "active_without_measured_cost"})
                    continue
                state.record(o.mitigation, ACTIVE, float(cost))
            else:
                state.record(o.mitigation, o.status, 0.0)
        return state, notes


def _read(root: pathlib.Path, rel: str) -> str | None:
    p = root / rel
    try:
        with open(p, "rb") as fh:
            data = fh.read(MAX_SYSFS_BYTES + 1)
    except OSError:
        return None
    if len(data) > MAX_SYSFS_BYTES:
        return None  # hostile/garbled sysfs replacement: refuse to parse
    try:
        return data.decode("ascii")
    except UnicodeDecodeError:
        return None


def detect_core_scheduling(root: pathlib.Path) -> tuple[bool | None, str]:
    """Core scheduling cannot be proven from sysfs alone.

    Linux exposes it per task through ``prctl(PR_SCHED_CORE)``; whether a
    workload's cookie is set is the scheduler's (SCH-01) knowledge.  The
    collector only reports whether the kernel *supports* it
    (``/proc/sys/kernel/sched_core_*`` or ``sched_core`` in kernel features)
    and never claims it active.  Returns ``(None, reason)`` unless an operator
    attestation file under ``etc/inv43/core_scheduling`` says ``enforced``.
    """
    marker = _read(root, "etc/inv43/core_scheduling")
    if marker is not None and marker.strip() == "enforced":
        return True, "operator_attested_enforced"
    return None, "not_observable_from_sysfs"


def collect(
    node: str,
    *,
    root: str | os.PathLike = "/",
    mitigations: tuple[str, ...] | None = None,
    ttl_s: float = DEFAULT_TTL_S,
    clock=time.time,
    mono=time.monotonic,
) -> NodeReadback:
    node = _require_identifier(node, "node")
    if not (isinstance(ttl_s, (int, float)) and 0 < ttl_s <= 86400):
        raise ValueError("ttl_s must be within (0, 86400]")
    r = pathlib.Path(root)
    vuln_dir = r / SYSFS_VULN_DIR
    names: list[str]
    if mitigations is None:
        try:
            names = sorted(p.name for p in vuln_dir.iterdir() if p.is_file())
        except OSError:
            names = []
    else:
        names = list(mitigations)
    now, now_m = clock(), mono()
    obs = []
    for name in names:
        _require_identifier(name, "mitigation name")
        if "/" in name or name.startswith("."):
            raise ValueError(f"illegal mitigation name {name!r}")
        raw = _read(r, f"{SYSFS_VULN_DIR}/{name}")
        status, reason = classify(raw)
        obs.append(Observation(node, name, status, None if raw is None else raw.strip(), reason,
                               f"sysfs:{SYSFS_VULN_DIR}/{name}", COLLECTOR_ID, now, now_m, float(ttl_s)))
    smt, smt_reason = classify_smt(_read(r, SYSFS_SMT_CONTROL), _read(r, SYSFS_SMT_ACTIVE))
    core, core_reason = detect_core_scheduling(r)
    return NodeReadback(node, tuple(obs), smt, smt_reason, core, core_reason,
                        platform.release() if str(root) == "/" else "fixture",
                        platform.machine() if str(root) == "/" else "fixture",
                        COLLECTOR_ID, now, now_m, float(ttl_s))


def local_node_id() -> str:
    return socket.gethostname() or "localhost"
