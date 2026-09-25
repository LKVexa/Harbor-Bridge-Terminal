"""Collector adapters: Wasm (24), microVM (25), host (26), network (27).

Each adapter maps a *source-native* record shape into ``signals.Record`` with
the boundary set and provenance attached.  The Wasm and microVM mappers are
written against documented shapes (a WASI-style component log/metric record;
Firecracker's ``metrics`` JSON flush) and exercised with fixtures only -- no
Wasm runtime or hypervisor exists in this archive, so their live-integration
checks stay BLOCKED.  The host collector reads the real host it runs on.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import sys
import time
from typing import Any, Iterable

from .errors import Malformed
from .signals import Record, Resource, TraceContext, parse_traceparent


def _res(base: Resource, boundary: str, instance: str) -> Resource:
    return Resource(base.tenant, base.environment, base.site, base.workload, boundary, instance)


# ------------------------------------------------------------------ Wasm (24)

def from_wasm(component: str, instance: str, rec: dict, *, base: Resource) -> Record:
    """rec: {"type": "log"|"metric"|"span", "at": int, ...}; ``traceparent``
    propagated across the component boundary if present and valid."""
    if not isinstance(rec, dict) or rec.get("type") not in ("log", "metric", "span"):
        raise Malformed("unknown wasm record type")
    res = _res(base, "wasm", f"{component}/{instance}")
    tc = parse_traceparent(rec.get("traceparent"))
    attrs = {"wasm.component": component}
    if rec["type"] == "log":
        return Record("log", "wasm.log", res, rec["at"], {"severity": rec.get("level", "INFO").upper(),
                      "text": str(rec.get("message", ""))[:4096]},
                      tc.trace_id if tc else None, tc.parent_id if tc else None, attrs)
    if rec["type"] == "metric":
        return Record("metric", "wasm." + rec["name"], res, rec["at"], {"value": rec["value"]}, attributes=attrs)
    return Record("span", "wasm." + rec["name"], res, rec["at"], {"end": rec["end"]},
                  tc.trace_id if tc else None, rec.get("span_id"), attrs)


# ------------------------------------------------------------------ microVM (25)

def from_firecracker_metrics(vm_id: str, host: str, flush: dict, *, base: Resource, at: int) -> list[Record]:
    """Flatten a Firecracker metrics flush ({"api_server": {...}, "vcpu": {...}})
    into metric records carrying guest/host correlation attributes."""
    if not isinstance(flush, dict):
        raise Malformed("flush must be an object")
    res = _res(base, "microvm", vm_id)
    out = []
    for group, vals in sorted(flush.items()):
        if not isinstance(vals, dict):
            continue
        for k, v in sorted(vals.items()):
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            out.append(Record("metric", f"microvm.{group}.{k}"[:256], res, at, {"value": v},
                              attributes={"microvm.id": vm_id, "host.name": host}))
    return out


def microvm_lifecycle(vm_id: str, event: str, *, base: Resource, at: int) -> Record:
    if event not in ("created", "started", "paused", "resumed", "snapshotted", "stopped", "crashed"):
        raise Malformed("unknown lifecycle event")
    return Record("event", "microvm.lifecycle", _res(base, "microvm", vm_id), at, {"event": event})


# ------------------------------------------------------------------ host (26)

def collect_host(*, base: Resource, at: int | None = None, root: str = "/") -> list[Record]:
    """Portable host sample using only the stdlib.  Linux adds /proc-derived
    memory and process counts; other platforms report what the stdlib offers
    and say which signals were unavailable (absence, never zero)."""
    at = int(time.time()) if at is None else at
    res = _res(base, "host", os.uname().nodename if hasattr(os, "uname") else os.environ.get("COMPUTERNAME", "host"))
    out: list[Record] = []
    unavailable = []
    out.append(Record("metric", "host.cpu.count", res, at, {"value": os.cpu_count() or 0}))
    if hasattr(os, "getloadavg"):
        out.append(Record("metric", "host.load.1m", res, at, {"value": os.getloadavg()[0]}))
    else:
        unavailable.append("host.load.1m")
    du = shutil.disk_usage(root)
    out.append(Record("metric", "host.disk.used_bytes", res, at, {"value": du.used}))
    out.append(Record("metric", "host.disk.free_bytes", res, at, {"value": du.free}))
    if sys.platform.startswith("linux") and os.path.exists("/proc/meminfo"):
        with open("/proc/meminfo") as fh:
            mi = {ln.split(":")[0]: int(ln.split()[1]) * 1024 for ln in fh if ln.split()[1:2] and ln.split()[1].isdigit()}
        if "MemAvailable" in mi:
            out.append(Record("metric", "host.mem.available_bytes", res, at, {"value": mi["MemAvailable"]}))
        out.append(Record("metric", "host.process.count", res, at,
                          {"value": sum(1 for d in os.listdir("/proc") if d.isdigit())}))
    else:
        unavailable += ["host.mem.available_bytes", "host.process.count"]
    out.append(Record("event", "host.collector.coverage", res, at, {"unavailable": unavailable}))
    return out


# ------------------------------------------------------------------ network (27)

def _pseudonymize(ip: str, tenant: str, salt: bytes) -> str:
    return "ip:" + hashlib.sha256(salt + tenant.encode() + b"|" + ip.encode()).hexdigest()[:16]


def from_flow(flow: dict, *, base: Resource, salt: bytes, owner_of: dict[str, str]) -> Record:
    """Flow record -> tenant-safe network record.

    Endpoints are attributed to a tenant through ``owner_of`` (ip -> tenant,
    from the IPAM/control plane).  A flow is only attributed to ``base.tenant``
    if that tenant owns at least one endpoint; foreign endpoints are
    pseudonymised with a per-tenant salt so two tenants cannot join on them.
    """
    need = ("src", "dst", "proto", "bytes", "packets", "at")
    if not isinstance(flow, dict) or any(k not in flow for k in need):
        raise Malformed("flow record incomplete")
    t = base.tenant
    if owner_of.get(flow["src"]) != t and owner_of.get(flow["dst"]) != t:
        raise Malformed("flow not attributable to tenant")
    body = {
        "src": flow["src"] if owner_of.get(flow["src"]) == t else _pseudonymize(flow["src"], t, salt),
        "dst": flow["dst"] if owner_of.get(flow["dst"]) == t else _pseudonymize(flow["dst"], t, salt),
        "proto": flow["proto"], "bytes": int(flow["bytes"]), "packets": int(flow["packets"]),
        "policy_verdict": flow.get("verdict", "unknown"),
    }
    return Record("event", "network.flow", _res(base, "network", flow.get("iface", "unknown")), flow["at"], body)


def from_dns(q: dict, *, base: Resource) -> Record:
    if not isinstance(q.get("qname"), str) or len(q["qname"]) > 253:
        raise Malformed("qname invalid")
    return Record("event", "network.dns", _res(base, "network", q.get("resolver", "unknown")), q["at"],
                  {"qname": q["qname"].lower().rstrip("."), "rcode": q.get("rcode", "NOERROR"), "latency_ms": q.get("latency_ms")})
