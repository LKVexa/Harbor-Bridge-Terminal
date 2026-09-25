"""Multi-signal event model (20), W3C trace-context propagation (21),
causal-context graph (22) and the signal catalogue registry (23).
"""
from __future__ import annotations

import math
import re
import threading
from dataclasses import dataclass, field
from typing import Any

from ..runtime import MAX_TEXT
from .errors import Malformed, QuotaExceeded

KINDS = ("metric", "log", "span", "profile", "event")
BOUNDARIES = ("wasm", "microvm", "host", "network", "control_plane")
SEVERITIES = ("TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL")


def _txt(v: Any, name: str, maxlen: int = MAX_TEXT) -> str:
    if not isinstance(v, str) or not v or len(v) > maxlen or v != v.strip():
        raise Malformed(f"{name} invalid")
    return v


@dataclass(frozen=True)
class Resource:
    tenant: str
    environment: str
    site: str
    workload: str
    boundary: str
    instance: str = ""

    def __post_init__(self) -> None:
        for n in ("tenant", "environment", "site", "workload"):
            _txt(getattr(self, n), n)
        if self.boundary not in BOUNDARIES:
            raise Malformed("unknown boundary")


@dataclass(frozen=True)
class Record:
    """One telemetry record of any kind, sharing provenance + causal context."""
    kind: str
    name: str
    resource: Resource
    at: int
    body: dict = field(default_factory=dict)
    trace_id: str | None = None
    span_id: str | None = None
    attributes: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise Malformed("unknown record kind")
        _txt(self.name, "name")
        if isinstance(self.at, bool) or not isinstance(self.at, int) or not (0 <= self.at < 2**63):
            raise Malformed("timestamp invalid")
        if self.trace_id is not None and not _TRACE_RE.fullmatch(self.trace_id or ""):
            raise Malformed("trace_id invalid")
        if self.span_id is not None and not _SPAN_RE.fullmatch(self.span_id or ""):
            raise Malformed("span_id invalid")
        v = self.body.get("value")
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)):
            raise Malformed("value must be finite")


# -------------------------------------------------------------- W3C trace context

_TRACE_RE = re.compile(r"[0-9a-f]{32}")
_SPAN_RE = re.compile(r"[0-9a-f]{16}")
_TP_RE = re.compile(r"([0-9a-f]{2})-([0-9a-f]{32})-([0-9a-f]{16})-([0-9a-f]{2})")
_TS_KEY = re.compile(r"[a-z][a-z0-9_\-*/]{0,255}|[a-z0-9][a-z0-9_\-*/]{0,240}@[a-z][a-z0-9_\-*/]{0,13}")


@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    parent_id: str
    sampled: bool
    tracestate: tuple = ()

    def traceparent(self) -> str:
        return f"00-{self.trace_id}-{self.parent_id}-{'01' if self.sampled else '00'}"

    def child(self, span_id: str) -> "TraceContext":
        if not _SPAN_RE.fullmatch(span_id) or span_id == "0" * 16:
            raise Malformed("span id invalid")
        return TraceContext(self.trace_id, span_id, self.sampled, self.tracestate)

    def headers(self) -> dict:
        h = {"traceparent": self.traceparent()}
        if self.tracestate:
            h["tracestate"] = ",".join(f"{k}={v}" for k, v in self.tracestate)
        return h


def parse_traceparent(header: str | None, tracestate: str | None = None) -> TraceContext | None:
    """W3C Trace Context level 1.  Invalid input -> None (start a new trace);
    never raises on hostile headers.  Future versions (>00) are parsed by the
    version-00 prefix rule; version ff is invalid."""
    if not isinstance(header, str) or len(header) > 512:
        return None
    h = header.strip().lower() if header.strip() == header.strip().lower() else None
    if h is None:
        return None
    m = _TP_RE.match(h)
    if not m:
        return None
    ver, tid, pid, flags = m.groups()
    if ver == "ff" or (ver == "00" and len(h) != 55) or (ver != "00" and len(h) > 55 and h[55] != "-"):
        return None
    if tid == "0" * 32 or pid == "0" * 16:
        return None
    ts: list = []
    if isinstance(tracestate, str) and len(tracestate) <= 8192:
        seen = set()
        for member in tracestate.split(","):
            member = member.strip()
            if not member:
                continue
            k, sep, v = member.partition("=")
            if not sep or not _TS_KEY.fullmatch(k) or not v or len(v) > 256 or k in seen:
                ts = []  # invalid tracestate is discarded wholesale, traceparent kept
                break
            seen.add(k)
            ts.append((k, v))
            if len(ts) > 32:
                ts = []
                break
    return TraceContext(tid, pid, bool(int(flags, 16) & 1), tuple(ts))


# -------------------------------------------------------------- causal graph (22)


class CausalGraph:
    """Bounded typed graph linking telemetry to workload instance, release
    lineage, node, network path and infrastructure.  Edges are typed; queries
    walk ancestry with a depth bound and never cross tenants."""

    EDGE_TYPES = frozenset({"runs_on", "deployed_by", "release_of", "routes_via", "part_of", "emitted_by", "caused"})

    def __init__(self, max_nodes: int = 100_000) -> None:
        self._nodes: dict[str, dict] = {}
        self._out: dict[str, set] = {}
        self._max = max_nodes
        self._lock = threading.Lock()

    def add_node(self, node_id: str, *, kind: str, tenant: str, **attrs: Any) -> None:
        with self._lock:
            if node_id not in self._nodes and len(self._nodes) >= self._max:
                raise QuotaExceeded("causal graph node bound")
            old = self._nodes.get(node_id)
            if old and old["tenant"] != tenant:
                raise Malformed("node id already bound to another tenant")
            self._nodes[node_id] = {"kind": kind, "tenant": tenant, **attrs}
            self._out.setdefault(node_id, set())

    def link(self, src: str, edge: str, dst: str) -> None:
        if edge not in self.EDGE_TYPES:
            raise Malformed("unknown edge type")
        with self._lock:
            a, b = self._nodes.get(src), self._nodes.get(dst)
            if a is None or b is None:
                raise Malformed("both endpoints must exist")
            if a["tenant"] != b["tenant"] and "*" not in (a["tenant"], b["tenant"]):
                raise Malformed("cross-tenant causal edge refused")
            self._out[src].add((edge, dst))

    def context(self, node_id: str, *, tenant: str, depth: int = 6) -> list[tuple[str, str, str]]:
        with self._lock:
            start = self._nodes.get(node_id)
            if start is None or start["tenant"] != tenant:
                return []
            out, frontier, seen = [], [node_id], {node_id}
            for _ in range(depth):
                nxt = []
                for n in frontier:
                    for edge, dst in sorted(self._out.get(n, ())):
                        if self._nodes[dst]["tenant"] not in (tenant, "*"):
                            continue
                        out.append((n, edge, dst))
                        if dst not in seen:
                            seen.add(dst)
                            nxt.append(dst)
                frontier = nxt
            return out


# -------------------------------------------------------------- catalogue (23)

CATALOGUE_KINDS = {"gauge": "metric", "counter": "metric", "histogram": "metric",
                   "log": "log", "trace": "span", "profile": "profile"}
# NOTE: PK_SIGNAL_CATALOGUE/1 has no kind for "event" records; recorded as
# finding F-03 (schema gap) rather than silently extending the v5 schema.
UNITS = frozenset({"1", "s", "ms", "us", "ns", "By", "KiBy", "MiBy", "%", "Cel", "W", "J", "Hz", "{request}", "{packet}", "{error}"})
LIFECYCLE = ("experimental", "stable", "deprecated", "removed")
_NAME = re.compile(r"[a-z][a-z0-9_.]{0,127}")


class Catalogue:
    """Signal registry: name, kind, unit, owner, description, lifecycle.

    Transitions only move forward (experimental->stable->deprecated->removed);
    a removed name is never re-registered with a different unit/kind (that is
    the classic silent semantic change)."""

    def __init__(self, audit=None) -> None:
        self._s: dict[str, dict] = {}
        self._lock = threading.Lock()
        self._audit = audit

    def register(self, name: str, *, kind: str, unit: str, owner: str, description: str, actor: str) -> dict:
        if not _NAME.fullmatch(name or ""):
            raise Malformed("signal name must match [a-z][a-z0-9_.]{0,127}")
        if kind not in CATALOGUE_KINDS:
            raise Malformed("unknown catalogue kind")
        if unit not in UNITS:
            raise Malformed("unit not in the approved UCUM subset")
        _txt(owner, "owner")
        _txt(description, "description", 1024)
        with self._lock:
            old = self._s.get(name)
            if old and (old["kind"], old["unit"]) != (kind, unit):
                raise Malformed("signal re-registered with different kind/unit")
            if old:
                return old
            rec = {"name": name, "kind": kind, "unit": unit, "owner": owner, "description": description,
                   "lifecycle": "experimental"}
            self._s[name] = rec
        if self._audit:
            self._audit.append("catalogue", {"action": "register", "name": name}, actor=actor)
        return rec

    def transition(self, name: str, to: str, *, actor: str) -> None:
        with self._lock:
            rec = self._s.get(name)
            if rec is None or to not in LIFECYCLE or LIFECYCLE.index(to) <= LIFECYCLE.index(rec["lifecycle"]):
                raise Malformed("illegal lifecycle transition")
            rec["lifecycle"] = to
        if self._audit:
            self._audit.append("catalogue", {"action": "transition", "name": name, "to": to}, actor=actor)

    def accepts(self, name: str, kind: str) -> bool:
        rec = self._s.get(name)
        return rec is not None and CATALOGUE_KINDS[rec["kind"]] == kind and rec["lifecycle"] in ("experimental", "stable", "deprecated")

    def document(self) -> dict:
        with self._lock:
            return {"schema": "PK_SIGNAL_CATALOGUE/1",
                    "signals": [{k: r[k] for k in ("name", "kind", "unit", "description")}
                                for r in sorted(self._s.values(), key=lambda r: r["name"])
                                if r["lifecycle"] != "removed"]}
