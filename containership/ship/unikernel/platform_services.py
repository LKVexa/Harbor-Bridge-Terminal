"""Bounded local platform primitives for UC-2.7.0.

These primitives advance a subset of the 150-component master-series roadmap.
They are deliberately local and do not claim hypervisor isolation, multi-host
consensus, public networking, HSM-backed keys, or production authority.
"""
from __future__ import annotations

import hashlib
import heapq
import os
import platform
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import Refusal
from . import strictjson as J
from .safety import atomic_write, contained_path, ship_lock

MAX_EVENT_BYTES = 64 * 1024
MAX_EVENT_TOPIC = 64
MAX_QUEUE = 4096
MAX_METRICS = 4096
MAX_FLAGS = 1024
MAX_QUOTAS = 128


def _token(value: Any, label: str, maximum: int = 64) -> str:
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise Refusal(f"invalid {label}")
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.:-/"
    if any(c not in allowed for c in value):
        raise Refusal(f"invalid {label}")
    return value


def _nonnegative_int(value: Any, label: str, maximum: int = (1 << 63) - 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
        raise Refusal(f"invalid {label}")
    return value


def _canonical_payload(value: Any) -> bytes:
    raw = J.canonical_bytes(value)
    if len(raw) > MAX_EVENT_BYTES:
        raise Refusal("event payload exceeds local byte budget", {"limit": MAX_EVENT_BYTES})
    return raw


class EventBus:
    """Synchronous bounded local event bus with monotonic sequence numbers.

    It is not a distributed broker. Subscribers are in-process callbacks and a
    failing callback cannot prevent later subscribers from observing the event.
    """
    def __init__(self, max_history: int = 1024):
        self.max_history = _nonnegative_int(max_history, "max_history", 100000)
        if self.max_history == 0:
            raise Refusal("max_history must be positive")
        self._seq = 0
        self._subs: dict[str, list] = {}
        self._history: list[dict[str, Any]] = []

    def subscribe(self, topic: str, callback):
        _token(topic, "event topic", MAX_EVENT_TOPIC)
        if not callable(callback):
            raise Refusal("event subscriber must be callable")
        self._subs.setdefault(topic, []).append(callback)

    def publish(self, topic: str, payload: Any) -> dict[str, Any]:
        _token(topic, "event topic", MAX_EVENT_TOPIC)
        _canonical_payload(payload)
        self._seq += 1
        rec = {"schema": "UC/EVENT/1", "seq": self._seq, "topic": topic, "payload": payload}
        errors = []
        for cb in tuple(self._subs.get(topic, ())):
            try:
                cb(rec)
            except Exception as exc:  # subscriber isolation; evidence is returned
                errors.append(f"{type(exc).__name__}: {exc}")
        rec = {**rec, "subscriber_errors": errors}
        self._history.append(rec)
        if len(self._history) > self.max_history:
            del self._history[:len(self._history) - self.max_history]
        return rec

    def history(self, topic: str | None = None) -> list[dict[str, Any]]:
        if topic is not None:
            _token(topic, "event topic", MAX_EVENT_TOPIC)
        return [dict(r) for r in self._history if topic is None or r["topic"] == topic]


class AuditLedger:
    """Append-only hash-chained local audit ledger.

    Hash chaining makes accidental/tampering changes detectable on verification,
    but this is not an externally anchored transparency service.
    """
    GENESIS = "0" * 64

    def __init__(self, root: str, relative: str = "_runs/audit/events.jsonl"):
        self.root = os.path.abspath(root)
        self.path = Path(contained_path(self.root, relative))

    def _read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        if self.path.is_symlink():
            raise Refusal("audit ledger symlink refused")
        records = []
        with self.path.open("rb") as fh:
            for n, raw in enumerate(fh, 1):
                if len(raw) > MAX_EVENT_BYTES * 2:
                    raise Refusal("audit ledger line exceeds budget", {"line": n})
                try:
                    records.append(J.loads(raw))
                except Exception as exc:
                    raise Refusal("audit ledger parse failure", {"line": n}) from exc
        return records

    @staticmethod
    def _digest(core: dict[str, Any]) -> str:
        return hashlib.sha256(J.canonical_bytes(core)).hexdigest()

    def verify(self) -> dict[str, Any]:
        prior = self.GENESIS
        count = 0
        for rec in self._read_records():
            if not isinstance(rec, dict) or set(rec) != {"schema", "seq", "event", "payload", "prev_sha256", "sha256"}:
                raise Refusal("audit ledger record shape invalid", {"seq": rec.get("seq") if isinstance(rec, dict) else None})
            if rec["schema"] != "UC/AUDIT_EVENT/1" or rec["seq"] != count + 1 or rec["prev_sha256"] != prior:
                raise Refusal("audit ledger chain invalid", {"seq": rec.get("seq")})
            core = {k: rec[k] for k in ("schema", "seq", "event", "payload", "prev_sha256")}
            if self._digest(core) != rec["sha256"]:
                raise Refusal("audit ledger digest mismatch", {"seq": rec["seq"]})
            prior = rec["sha256"]
            count += 1
        return {"schema": "UC/AUDIT_VERIFY/1", "records": count, "head_sha256": prior, "verified": True,
                "external_anchor": False}

    def append(self, event: str, payload: Any) -> dict[str, Any]:
        _token(event, "audit event", 96)
        _canonical_payload(payload)
        with ship_lock(self.root):
            state = self.verify()
            seq = state["records"] + 1
            core = {"schema": "UC/AUDIT_EVENT/1", "seq": seq, "event": event, "payload": payload,
                    "prev_sha256": state["head_sha256"]}
            rec = {**core, "sha256": self._digest(core)}
            old = self.path.read_bytes() if self.path.exists() else b""
            atomic_write(str(self.path), old + J.dumps(rec, sort_keys=True).encode("utf-8") + b"\n")
            return rec


class Metrics:
    """Bounded integer counter/gauge registry suitable for deterministic evidence."""
    def __init__(self):
        self._values: dict[tuple[str, str], int] = {}

    def _key(self, name: str, labels: dict[str, str] | None):
        _token(name, "metric name", 96)
        labels = labels or {}
        if not isinstance(labels, dict) or len(labels) > 16:
            raise Refusal("metric labels out of bounds")
        bits = []
        for k, v in sorted(labels.items()):
            _token(k, "metric label", 48); _token(v, "metric label value", 96)
            bits.append(f"{k}={v}")
        return name, ",".join(bits)

    def inc(self, name: str, amount: int = 1, labels: dict[str, str] | None = None) -> int:
        amount = _nonnegative_int(amount, "metric increment")
        key = self._key(name, labels)
        if key not in self._values and len(self._values) >= MAX_METRICS:
            raise Refusal("metric cardinality limit reached")
        value = self._values.get(key, 0) + amount
        if value > (1 << 63) - 1:
            raise Refusal("metric counter overflow")
        self._values[key] = value
        return value

    def set(self, name: str, value: int, labels: dict[str, str] | None = None) -> int:
        value = _nonnegative_int(value, "metric gauge")
        key = self._key(name, labels)
        if key not in self._values and len(self._values) >= MAX_METRICS:
            raise Refusal("metric cardinality limit reached")
        self._values[key] = value
        return value

    def snapshot(self) -> dict[str, Any]:
        rows = [{"name": n, "labels": l, "value": v} for (n, l), v in sorted(self._values.items())]
        return {"schema": "UC/METRICS/1", "count": len(rows), "metrics": rows}


@dataclass(order=True)
class _Queued:
    priority: int
    seq: int
    key: str
    payload: Any


class WorkQueue:
    """Bounded priority queue with idempotency keys and deterministic ordering."""
    def __init__(self, capacity: int = 256):
        self.capacity = _nonnegative_int(capacity, "queue capacity", MAX_QUEUE)
        if not self.capacity:
            raise Refusal("queue capacity must be positive")
        self._seq = 0
        self._heap: list[_Queued] = []
        self._keys: set[str] = set()

    def submit(self, key: str, payload: Any, priority: int = 100) -> dict[str, Any]:
        _token(key, "idempotency key", 96)
        priority = _nonnegative_int(priority, "priority", 1000000)
        _canonical_payload(payload)
        if key in self._keys:
            return {"accepted": False, "duplicate": True, "key": key, "depth": len(self._heap)}
        if len(self._heap) >= self.capacity:
            raise Refusal("work queue backpressure: capacity reached", {"capacity": self.capacity})
        self._seq += 1
        heapq.heappush(self._heap, _Queued(priority, self._seq, key, payload)); self._keys.add(key)
        return {"accepted": True, "duplicate": False, "key": key, "depth": len(self._heap)}

    def take(self) -> dict[str, Any] | None:
        if not self._heap:
            return None
        item = heapq.heappop(self._heap); self._keys.remove(item.key)
        return {"key": item.key, "priority": item.priority, "payload": item.payload, "depth": len(self._heap)}

    @property
    def depth(self) -> int:
        return len(self._heap)


def validate_feature_flags(value: Any) -> dict[str, bool]:
    if not isinstance(value, dict) or len(value) > MAX_FLAGS:
        raise Refusal("feature flag set out of bounds")
    out = {}
    for k, v in value.items():
        _token(k, "feature flag", 96)
        if not isinstance(v, bool):
            raise Refusal("feature flag values must be boolean", {"flag": k})
        out[k] = v
    return dict(sorted(out.items()))


def validate_quotas(value: Any) -> dict[str, int]:
    allowed = {"cpu_ms", "wall_ms", "memory_bytes", "storage_bytes", "network_bytes", "processes", "open_files", "queue_depth"}
    if not isinstance(value, dict) or len(value) > MAX_QUOTAS or set(value) - allowed:
        raise Refusal("quota policy fields invalid")
    out = {}
    for k, v in value.items():
        out[k] = _nonnegative_int(v, k)
    return dict(sorted(out.items()))


def hardware_capabilities() -> dict[str, Any]:
    """Best-effort local facts only; no privileged feature probing."""
    machine = platform.machine() or "unknown"
    system = platform.system() or "unknown"
    cores = os.cpu_count() or 1
    memory = None
    if hasattr(os, "sysconf"):
        try:
            pages = os.sysconf("SC_PHYS_PAGES"); size = os.sysconf("SC_PAGE_SIZE")
            if isinstance(pages, int) and isinstance(size, int) and pages > 0 and size > 0:
                memory = pages * size
        except (ValueError, OSError):
            pass
    return {"schema": "UC/HARDWARE_CAPABILITIES/1", "os": system, "architecture": machine,
            "logical_cpu_count": int(cores), "physical_memory_bytes": memory,
            "numa_qualified": False, "gpu_qualified": False, "virtualization_qualified": False}


def health_snapshot(root: str) -> dict[str, Any]:
    rootp = Path(root)
    checks = {
        "root_exists": rootp.is_dir(),
        "manifest_present": (rootp / "MANIFEST.json").is_file(),
        "version_present": (rootp / "VERSION").is_file(),
        "ship_package_present": (rootp / "ship" / "unikernel" / "__init__.py").is_file(),
    }
    return {"schema": "UC/HEALTH/1", "live": True, "ready": all(checks.values()), "checks": checks,
            "network_probe_performed": False}


def compatibility_matrix() -> dict[str, Any]:
    return {
        "schema": "UC/COMPATIBILITY_MATRIX/1",
        "candidate": "UC-2.8.0",
        "qualified": [{"os": "Linux", "arch": "x86_64", "surface": "ship-layer local tests"}],
        "unqualified": [
            {"os": "Windows", "arch": "x86_64", "reason": "native execution not observed in this build environment"},
            {"os": "Linux", "arch": "aarch64", "reason": "ARM64 toolchain/runtime not observed"},
            {"surface": "hypervisor guest", "reason": "bootable unikernel guest backend absent"},
            {"surface": "multi-host", "reason": "federation/consensus deliberately absent"},
        ],
    }

class TraceRecorder:
    """Bounded in-process trace recorder; not a distributed tracing backend."""
    def __init__(self, max_spans: int = 4096):
        self.max_spans = _nonnegative_int(max_spans, "max_spans", 100000)
        if not self.max_spans:
            raise Refusal("max_spans must be positive")
        self._seq = 0
        self._open: dict[str, dict[str, Any]] = {}
        self._done: list[dict[str, Any]] = []

    def start(self, name: str, parent: str | None = None) -> str:
        _token(name, "span name", 96)
        if parent is not None and parent not in self._open and all(s["id"] != parent for s in self._done):
            raise Refusal("trace parent does not exist")
        if len(self._open) + len(self._done) >= self.max_spans:
            raise Refusal("trace span budget reached")
        self._seq += 1
        sid = f"s{self._seq:08d}"
        self._open[sid] = {"id": sid, "name": name, "parent": parent, "start_ns": time.monotonic_ns()}
        return sid

    def finish(self, span_id: str, outcome: str = "ok") -> dict[str, Any]:
        _token(span_id, "span id", 32); _token(outcome, "span outcome", 32)
        if span_id not in self._open:
            raise Refusal("trace span is not open")
        rec = self._open.pop(span_id); end = time.monotonic_ns()
        out = {"schema": "UC/TRACE_SPAN/1", "id": rec["id"], "name": rec["name"], "parent": rec["parent"],
               "duration_ns": max(0, end - rec["start_ns"]), "outcome": outcome}
        self._done.append(out); return dict(out)

    def snapshot(self) -> dict[str, Any]:
        return {"schema": "UC/TRACE/1", "open": len(self._open), "completed": [dict(x) for x in self._done]}


def structured_log(event: str, level: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    _token(event, "log event", 96); _token(level, "log level", 16)
    if level not in {"debug", "info", "warning", "error", "critical"}:
        raise Refusal("unsupported log level")
    fields = fields or {}
    if not isinstance(fields, dict) or len(fields) > 64:
        raise Refusal("structured log fields out of bounds")
    _canonical_payload(fields)
    return {"schema": "UC/LOG_EVENT/1", "event": event, "level": level, "fields": fields}


def capacity_plan(request: dict[str, int], capacity: dict[str, int]) -> dict[str, Any]:
    req = validate_quotas(request); cap = validate_quotas(capacity)
    missing = [k for k in req if k not in cap]
    exceeded = {k: {"requested": req[k], "capacity": cap[k]} for k in req if k in cap and req[k] > cap[k]}
    return {"schema": "UC/CAPACITY_PLAN/1", "admitted": not missing and not exceeded,
            "requested": req, "capacity": cap, "missing_capacity_fields": missing, "exceeded": exceeded}


def validate_retention_policy(value: Any) -> dict[str, int]:
    allowed = {"max_items", "max_bytes", "max_age_seconds"}
    if not isinstance(value, dict) or not value or set(value) - allowed:
        raise Refusal("retention policy fields invalid")
    out = {k: _nonnegative_int(v, k) for k, v in value.items()}
    if all(v == 0 for v in out.values()):
        raise Refusal("retention policy cannot disable every bound")
    return dict(sorted(out.items()))
