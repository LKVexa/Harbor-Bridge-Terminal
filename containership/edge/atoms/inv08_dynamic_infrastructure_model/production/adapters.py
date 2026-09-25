"""Components 26 & 28 - adjacent-layer adapter contracts and the provider
adapter interface, with in-memory contract doubles.

NOTHING here talks to a real cloud, hypervisor, BMC, edge site, INV-06,
INV-68, PLN-05 or INV-32 implementation.  Every live integration/qualification
is BLOCKED on the missing real system; the doubles implement the contract so
the controller and tests can exercise it deterministically.

Provider contract ``PK_DYN_PROVIDER/1``
---------------------------------------
Operations (all carry ``idempotency_key`` and ``fence`` token):
  create(node_id, spec) / drain(node_id) / delete(node_id) / list() / capabilities()
Normalized node view: {"node_id", "state": PROVISIONING|RUNNING|DRAINING|DELETED,
  "kind", "provider", "location"}.  Unknown provider states normalize to
  ``UNKNOWN`` (never guessed).  Provider exceptions are translated with
  ``core.wrap_provider_error``; ``ProviderTransient`` -> retryable, anything
  else -> terminal.  A repeated idempotency key returns the first result.
  A fence lower than the highest seen -> ``INV08.FENCE.STALE``.

Adjacent-layer contracts (from contract.py dependencies)
--------------------------------------------------------
* INV-06 Traditional IaC (upstream): ``PK_DYN_ADJ_INV06/1`` static inventory import
  {"schema","nodes":[{"node_id","pinned":bool}]} - pinned nodes are never reclaimed.
* PLN-05 Elasticity plane (upstream): ``PK_DYN_ADJ_PLN05/1`` demand signal
  {"schema","pool","demand">=0,"min_nodes","max_nodes","ts"} (bounds must satisfy model.Pool).
* INV-68 Resource packing (downstream): ``PK_DYN_ADJ_INV68/1`` pool membership export
  {"schema","pool","nodes":[...],"epoch"} and busy-flag feedback {"node_id","busy"}.
* INV-32 Elastic virtualization (peer): ``PK_DYN_ADJ_INV32/1`` host capacity hint
  {"schema","host","free_slots">=0}.
Field semantics beyond what contract.py states are ASSUMPTIONS pending the
peers' published interface specs (hence PARTIAL).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Protocol

from .core import Inv08Error, Outcome, wrap_provider_error
from .leader import FenceGate

PROVIDER_SCHEMA = "PK_DYN_PROVIDER/1"
KINDS = ("cloud", "hypervisor", "baremetal", "edge")
NORMAL_STATES = ("PROVISIONING", "RUNNING", "DRAINING", "DELETED", "UNKNOWN")
CAPABILITY_KEYS = ("create", "drain", "delete", "list", "max_nodes", "supports_drain",
                   "provision_seconds", "intermittent")


class ProviderTransient(Exception):
    """Raised by provider doubles for failures that a retry may fix."""


class ProviderAdapter(Protocol):
    name: str
    kind: str

    def capabilities(self) -> dict: ...
    def create(self, node_id: str, spec: dict, *, idempotency_key: str, fence: int) -> dict: ...
    def drain(self, node_id: str, *, idempotency_key: str, fence: int) -> dict: ...
    def delete(self, node_id: str, *, idempotency_key: str, fence: int) -> dict: ...
    def list(self) -> dict[str, dict]: ...


_NATIVE_STATE = {
    "cloud": {"pending": "PROVISIONING", "running": "RUNNING", "stopping": "DRAINING", "terminated": "DELETED"},
    "hypervisor": {"defining": "PROVISIONING", "active": "RUNNING", "shutting_down": "DRAINING", "undefined": "DELETED"},
    "baremetal": {"imaging": "PROVISIONING", "deployed": "RUNNING", "evacuating": "DRAINING", "released": "DELETED"},
    "edge": {"joining": "PROVISIONING", "ready": "RUNNING", "cordoned": "DRAINING", "gone": "DELETED"},
}

_DEFAULT_CAPS = {
    "cloud": {"max_nodes": 1000, "supports_drain": True, "provision_seconds": 60, "intermittent": False},
    "hypervisor": {"max_nodes": 64, "supports_drain": True, "provision_seconds": 20, "intermittent": False},
    "baremetal": {"max_nodes": 16, "supports_drain": True, "provision_seconds": 900, "intermittent": False},
    "edge": {"max_nodes": 8, "supports_drain": False, "provision_seconds": 120, "intermittent": True},
}


def normalize_state(kind: str, native: str) -> str:
    return _NATIVE_STATE.get(kind, {}).get(native, "UNKNOWN")


def normalize_capabilities(raw: dict) -> dict:
    missing = [k for k in CAPABILITY_KEYS if k not in raw]
    if missing:
        raise Inv08Error("INV08.PROVIDER.CAPABILITIES", f"capability keys missing: {missing}",
                         outcome=Outcome.TERMINAL_FAILURE, details={"missing": missing})
    out = {k: raw[k] for k in CAPABILITY_KEYS}
    for k in ("create", "drain", "delete", "list", "supports_drain", "intermittent"):
        if not isinstance(out[k], bool):
            raise Inv08Error("INV08.PROVIDER.CAPABILITIES", f"{k} must be bool",
                             outcome=Outcome.TERMINAL_FAILURE)
    if isinstance(out["max_nodes"], bool) or not isinstance(out["max_nodes"], int) or out["max_nodes"] < 0:
        raise Inv08Error("INV08.PROVIDER.CAPABILITIES", "max_nodes must be int >= 0",
                         outcome=Outcome.TERMINAL_FAILURE)
    return out


@dataclass
class InMemoryProvider:
    """Contract double for one provider of the given ``kind``.

    Kind-specific behaviour modelled: cloud quota (max_nodes), hypervisor host
    capacity, bare-metal finite inventory (named slots), edge intermittent
    connectivity (``online`` flag) and no drain support (drain == cordon)."""
    name: str
    kind: str
    location: str = "test-site"
    max_nodes: int | None = None
    online: bool = True
    native: dict[str, str] = field(default_factory=dict)       # node_id -> native state
    calls: list[tuple[str, str]] = field(default_factory=list)
    fail_next: list[BaseException] = field(default_factory=list)  # fault injection hook
    _idem: dict[str, dict] = field(default_factory=dict)
    gate: FenceGate = field(init=False)

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"unknown provider kind {self.kind!r}")
        if self.max_nodes is None:
            self.max_nodes = _DEFAULT_CAPS[self.kind]["max_nodes"]
        self.gate = FenceGate(f"provider:{self.name}")

    # ------------------------------------------------------------ plumbing
    def _native(self, normal: str) -> str:
        return {v: k for k, v in _NATIVE_STATE[self.kind].items()}[normal]

    def _enter(self, op: str, node_id: str, key: str | None, fence: int | None) -> dict | None:
        self.calls.append((op, node_id))
        if fence is not None:
            self.gate.admit(fence)
        if self.fail_next:
            exc = self.fail_next.pop(0)
            raise wrap_provider_error(self.name, exc, retryable=isinstance(exc, ProviderTransient))
        if self.kind == "edge" and not self.online:
            raise wrap_provider_error(self.name, ProviderTransient("edge site unreachable"), retryable=True)
        if key is not None and key in self._idem:
            return self._idem[key]
        return None

    def _view(self, node_id: str) -> dict:
        return {"node_id": node_id, "state": normalize_state(self.kind, self.native[node_id]),
                "kind": self.kind, "provider": self.name, "location": self.location}

    # ------------------------------------------------------------ contract
    def capabilities(self) -> dict:
        self._enter("capabilities", "", None, None)
        caps = dict(_DEFAULT_CAPS[self.kind], max_nodes=self.max_nodes,
                    create=True, drain=True, delete=True, list=True)
        return normalize_capabilities(caps)

    def create(self, node_id: str, spec: dict, *, idempotency_key: str, fence: int) -> dict:
        prior = self._enter("create", node_id, idempotency_key, fence)
        if prior is not None:
            return prior
        live = [n for n, s in self.native.items() if normalize_state(self.kind, s) != "DELETED"]
        if node_id in self.native and normalize_state(self.kind, self.native[node_id]) != "DELETED":
            raise Inv08Error("INV08.PROVIDER.CONFLICT", f"{node_id} already exists",
                             outcome=Outcome.OPERATOR_REQUIRED,
                             remediation="adopt or delete the existing node explicitly",
                             details={"node_id": node_id})
        if len(live) >= self.max_nodes:
            raise wrap_provider_error(self.name, RuntimeError("capacity/quota exhausted"), retryable=False)
        self.native[node_id] = self._native("RUNNING")
        res = self._view(node_id)
        self._idem[idempotency_key] = res
        return res

    def drain(self, node_id: str, *, idempotency_key: str, fence: int) -> dict:
        prior = self._enter("drain", node_id, idempotency_key, fence)
        if prior is not None:
            return prior
        if node_id not in self.native or normalize_state(self.kind, self.native[node_id]) == "DELETED":
            res = {"node_id": node_id, "state": "DELETED", "kind": self.kind,
                   "provider": self.name, "location": self.location}
        else:
            self.native[node_id] = self._native("DRAINING")
            res = self._view(node_id)
        self._idem[idempotency_key] = res
        return res

    def delete(self, node_id: str, *, idempotency_key: str, fence: int) -> dict:
        prior = self._enter("delete", node_id, idempotency_key, fence)
        if prior is not None:
            return prior
        if node_id in self.native:
            self.native[node_id] = self._native("DELETED")
        res = {"node_id": node_id, "state": "DELETED", "kind": self.kind,
               "provider": self.name, "location": self.location}
        self._idem[idempotency_key] = res
        return res

    def list(self) -> dict[str, dict]:
        self._enter("list", "", None, None)
        return {n: self._view(n) for n in sorted(self.native)
                if normalize_state(self.kind, self.native[n]) != "DELETED"}


def make_provider(kind: str, name: str | None = None, **kw) -> InMemoryProvider:
    return InMemoryProvider(name=name or f"{kind}-double", kind=kind, **kw)


# =================================================================== adjacent layers

ADJ_SCHEMAS = {
    "INV-06": "PK_DYN_ADJ_INV06/1",
    "PLN-05": "PK_DYN_ADJ_PLN05/1",
    "INV-68": "PK_DYN_ADJ_INV68/1",
    "INV-32": "PK_DYN_ADJ_INV32/1",
}


def _bad(layer: str, msg: str) -> Inv08Error:
    return Inv08Error("INV08.ADAPTER.INVALID", f"{layer}: {msg}", outcome=Outcome.TERMINAL_FAILURE,
                      remediation="peer sent a message outside the versioned contract",
                      details={"layer": layer})


def _schema(layer: str, msg: dict) -> None:
    if not isinstance(msg, dict):
        raise _bad(layer, "message must be an object")
    want = ADJ_SCHEMAS[layer]
    got = msg.get("schema")
    if not isinstance(got, str) or got.split("/")[0] != want.split("/")[0]:
        raise _bad(layer, f"schema {got!r} is not {want}")
    if got != want:
        raise Inv08Error("INV08.ADAPTER.UNSUPPORTED_VERSION", f"{layer}: {got} unsupported (want {want})",
                         outcome=Outcome.OPERATOR_REQUIRED, details={"layer": layer, "got": got})


def _num(layer: str, v, name: str, minimum: float = 0) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < minimum:
        raise _bad(layer, f"{name} must be a finite number >= {minimum}")
    return v


def parse_inv06_inventory(msg: dict) -> dict[str, bool]:
    _schema("INV-06", msg)
    nodes = msg.get("nodes")
    if not isinstance(nodes, list):
        raise _bad("INV-06", "nodes must be a list")
    out: dict[str, bool] = {}
    for n in nodes:
        if not isinstance(n, dict) or not isinstance(n.get("node_id"), str) or not n["node_id"] \
                or not isinstance(n.get("pinned"), bool):
            raise _bad("INV-06", f"bad node entry {n!r}")
        if n["node_id"] in out:
            raise _bad("INV-06", f"duplicate node {n['node_id']}")
        out[n["node_id"]] = n["pinned"]
    return out


def parse_pln05_demand(msg: dict) -> dict:
    _schema("PLN-05", msg)
    for k in ("pool", "demand", "min_nodes", "max_nodes", "ts"):
        if k not in msg:
            raise _bad("PLN-05", f"missing {k}")
    if not isinstance(msg["pool"], str) or not msg["pool"]:
        raise _bad("PLN-05", "pool must be a non-empty string")
    for k in ("min_nodes", "max_nodes"):
        if isinstance(msg[k], bool) or not isinstance(msg[k], int) or msg[k] < 0:
            raise _bad("PLN-05", f"{k} must be int >= 0")
    if msg["min_nodes"] > msg["max_nodes"]:
        raise _bad("PLN-05", "min_nodes > max_nodes")
    return {"pool": msg["pool"], "demand": _num("PLN-05", msg["demand"], "demand"),
            "min_nodes": msg["min_nodes"], "max_nodes": msg["max_nodes"],
            "ts": _num("PLN-05", msg["ts"], "ts")}


def export_inv68_membership(pool_name: str, pool, epoch: int) -> dict:
    return {"schema": ADJ_SCHEMAS["INV-68"], "pool": pool_name, "epoch": epoch,
            "nodes": [{"node_id": n, "busy": s["busy"]} for n, s in sorted(pool.nodes.items())]}


def apply_inv68_busy(pool, msg: dict) -> None:
    _schema("INV-68", msg)
    node_id, busy = msg.get("node_id"), msg.get("busy")
    if not isinstance(node_id, str) or not isinstance(busy, bool):
        raise _bad("INV-68", "busy feedback needs node_id:str and busy:bool")
    if node_id not in pool.nodes:
        raise Inv08Error("INV08.ADAPTER.UNKNOWN_NODE", f"INV-68: unknown node {node_id}",
                         outcome=Outcome.RETRYABLE_FAILURE, details={"node_id": node_id})
    pool.set_busy(node_id, busy)


def parse_inv32_hint(msg: dict) -> dict:
    _schema("INV-32", msg)
    if not isinstance(msg.get("host"), str) or not msg["host"]:
        raise _bad("INV-32", "host must be a non-empty string")
    fs = msg.get("free_slots")
    if isinstance(fs, bool) or not isinstance(fs, int) or fs < 0:
        raise _bad("INV-32", "free_slots must be int >= 0")
    return {"host": msg["host"], "free_slots": fs}


class AdjacentLayerDouble:
    """In-memory peer that records every message exchanged (contract double)."""

    def __init__(self, layer: str) -> None:
        if layer not in ADJ_SCHEMAS:
            raise ValueError(layer)
        self.layer = layer
        self.outbox: list[dict] = []
        self.inbox: list[dict] = []

    def emit(self, **fields) -> dict:
        msg = {"schema": ADJ_SCHEMAS[self.layer], **fields}
        self.outbox.append(msg)
        return msg

    def receive(self, msg: dict) -> None:
        _schema(self.layer, msg)
        self.inbox.append(msg)
