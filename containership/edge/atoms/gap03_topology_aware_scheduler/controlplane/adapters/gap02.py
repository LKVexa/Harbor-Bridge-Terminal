"""MC-009 - GAP-02 hardware-capability feed integration (GAP02-INV/1).

Normalises vendor capability reports into canonical types/units, binds
topology node IDs to discovered device identities, enforces freshness TTL,
verifies attestation for security-sensitive claims (fail closed), evaluates
HARD predicates separately from soft preferences, and reconciles drift.
"""
from __future__ import annotations

import re

from .. import canonical
from ..errors import SchedulerError

SUPPORTED = ("1.0",)
ISA = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "arm64", "arm64": "arm64"}
MEM_UNITS = {"MiB": 1, "GiB": 1024, "TiB": 1024 * 1024}
ACCEL = {"nvidia-a100": "gpu.a100", "nvidia-h100": "gpu.h100", "amd-mi300": "gpu.mi300"}
DEVICE_RE = re.compile(r"^dev:[0-9a-f]{16}$")
DEFAULT_TTL_S = 300
MAX_ACCELERATORS = 64
SECURITY_SENSITIVE = ("tee",)


def normalize(report: dict) -> dict:
    """Strict normalisation; any structural defect maps to INVALID_ARGUMENT (fuzz finding FZ-1)."""
    if not isinstance(report, dict):
        raise SchedulerError("INVALID_ARGUMENT", "report must be an object")
    try:
        return _normalize(report)
    except SchedulerError:
        raise
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise SchedulerError("INVALID_ARGUMENT", f"malformed inventory report ({exc.__class__.__name__})") from None


def _normalize(report: dict) -> dict:
    if report.get("version") not in SUPPORTED:
        raise SchedulerError("UNSUPPORTED_VERSION", "GAP-02 inventory version")
    dev = report.get("device_id", "")
    if not DEVICE_RE.match(str(dev)):
        raise SchedulerError("INVALID_ARGUMENT", "device id")
    isa = ISA.get(str(report.get("isa", "")).lower())
    if isa is None:
        raise SchedulerError("INVALID_ARGUMENT", "unsupported/ambiguous ISA")
    mem = report.get("memory", {})
    if not isinstance(mem, dict):
        raise SchedulerError("INVALID_ARGUMENT", "memory must be an object")
    if not isinstance(report.get("node"), str) or not re.match(r"^[A-Za-z0-9][A-Za-z0-9._:\-]{0,62}$", report["node"]):
        raise SchedulerError("INVALID_ARGUMENT", "node id")
    if mem.get("unit") not in MEM_UNITS or not isinstance(mem.get("value"), int) or not 0 < mem["value"] <= 1 << 30:
        raise SchedulerError("INVALID_ARGUMENT", "memory must be an integer with MiB/GiB/TiB unit")
    accels = report.get("accelerators", [])
    if not isinstance(accels, list):
        raise SchedulerError("INVALID_ARGUMENT", "accelerators must be a list")
    if len(accels) > MAX_ACCELERATORS:
        raise SchedulerError("PAYLOAD_TOO_LARGE", "too many accelerators")
    acc = []
    for a in accels:
        if not isinstance(a, str) or a not in ACCEL:
            raise SchedulerError("INVALID_ARGUMENT", "unknown accelerator vendor string")
        acc.append(ACCEL[a])
    cpus = report.get("cpus")
    if isinstance(cpus, bool) or not isinstance(cpus, int) or not 0 < cpus <= 4096:
        raise SchedulerError("INVALID_ARGUMENT", "cpus")
    return {"device_id": dev, "node": report["node"], "isa": isa, "cpus": cpus,
            "memory_mib": mem["value"] * MEM_UNITS[mem["unit"]], "accelerators": sorted(acc),
            "claims": {"tee": report.get("tee", False) is True}, "generation": _int(report["generation"]),
            "observed_at": _num(report["observed_at"]), "source": _str(report["source"]),
            "attestation": report.get("attestation")}


class Inventory:
    def __init__(self, *, ttl_s: float = DEFAULT_TTL_S, trust=None, measurement_allowlist=frozenset(), metrics=None):
        self.ttl, self.trust, self.allow, self.metrics = ttl_s, trust, set(measurement_allowlist), metrics
        self.by_node: dict[str, dict] = {}
        self.drift: list[dict] = []

    authorized_producers: frozenset | None = None  # verified GAP-02 producer identities; None = not enforced

    def ingest(self, report: dict, *, producer: str | None = None) -> dict:
        if self.authorized_producers is not None and producer not in self.authorized_producers:
            if self.metrics:
                self.metrics.inc("gap03_adapter_ingest_total", adapter="gap02", result="PERMISSION_DENIED")
            raise SchedulerError("PERMISSION_DENIED", "producer not authorized for GAP-02 inventory")
        try:
            rec = self._ingest(report)
        except SchedulerError as exc:
            if self.metrics:
                self.metrics.inc("gap03_adapter_ingest_total", adapter="gap02", result=exc.code)
            raise
        if self.metrics:
            self.metrics.inc("gap03_adapter_ingest_total", adapter="gap02", result="ok")
        return rec

    def _ingest(self, report: dict) -> dict:
        rec = normalize(report)
        cur = self.by_node.get(rec["node"])
        if cur and rec["generation"] < cur["generation"]:
            raise SchedulerError("STALE_STATE", "older inventory generation")
        dup = [n for n, r in self.by_node.items() if r["device_id"] == rec["device_id"] and n != rec["node"]]
        if dup:
            self.drift.append({"event": "duplicate_device_identity", "device": rec["device_id"], "nodes": sorted(dup + [rec["node"]])})
            raise SchedulerError("CONFLICT", "device identity bound to two topology nodes")
        if cur and cur["source"] != rec["source"] and cur["generation"] == rec["generation"] and cur != rec:
            self.drift.append({"event": "conflicting_sources", "node": rec["node"]})
            raise SchedulerError("CONFLICT", "conflicting discovery sources at same generation")
        if rec["claims"]["tee"]:
            if self.trust is None:
                rec["claims"]["tee"] = False  # unverifiable security claim is not honoured
            else:
                from ..identity import verify_attestation
                try:
                    verify_attestation(self.trust, "confidential", rec["attestation"], measurement_allowlist=self.allow)
                except SchedulerError:
                    rec["claims"]["tee"] = False
                    rec["attestation_failed"] = True
        self.by_node[rec["node"]] = rec  # replaces whole record: removed accelerators vanish (no phantom capability)
        return rec

    def remove(self, node: str) -> None:
        self.by_node.pop(node, None)

    def fresh(self, node: str, now: float) -> dict | None:
        rec = self.by_node.get(node)
        if rec is None or now - rec["observed_at"] > self.ttl or rec["observed_at"] > now + 30:
            return None
        return rec

    def feasible(self, node: str, requirements: dict, now: float) -> tuple[bool, str]:
        """HARD predicates. Unknown / stale capability is never treated as sufficient."""
        rec = self.fresh(node, now)
        if rec is None:
            return False, "inventory_stale_or_missing"
        if "isa" in requirements and rec["isa"] != requirements["isa"]:
            return False, "isa"
        if rec["cpus"] < requirements.get("cpus", 0):
            return False, "cpus"
        if rec["memory_mib"] < requirements.get("memory_mib", 0):
            return False, "memory"
        for a in requirements.get("accelerators", []):
            if a not in rec["accelerators"]:
                return False, f"accelerator:{a}"
        if requirements.get("tee") and not rec["claims"]["tee"]:
            return False, "tee_unverified"
        return True, "ok"

    def reconcile(self, topology_nodes: set[str], placed_nodes: set[str], now: float) -> list[dict]:
        events = []
        for n in sorted(topology_nodes - set(self.by_node)):
            events.append({"event": "topology_node_without_inventory", "node": n})
        for n in sorted(set(self.by_node) - topology_nodes):
            events.append({"event": "inventory_without_topology_node", "node": n})
        for n in sorted(placed_nodes):
            if self.fresh(n, now) is None:
                events.append({"event": "placement_on_stale_inventory", "node": n})
        return events

    def snapshot_meta(self) -> dict:
        return {"inventory_digest": canonical.digest({n: {k: v for k, v in r.items() if k != "attestation"}
                                                      for n, r in sorted(self.by_node.items())}),
                "max_generation": max((r["generation"] for r in self.by_node.values()), default=0)}


def _int(v):
    if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= 2**53:
        raise SchedulerError("INVALID_ARGUMENT", "integer field")
    return v


def _num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
        raise SchedulerError("INVALID_ARGUMENT", "numeric field")
    return float(v)


def _str(v):
    if not isinstance(v, str) or not 0 < len(v) <= 128:
        raise SchedulerError("INVALID_ARGUMENT", "string field")
    return v
