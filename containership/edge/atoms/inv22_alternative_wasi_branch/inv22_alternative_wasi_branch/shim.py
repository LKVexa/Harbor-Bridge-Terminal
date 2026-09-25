"""PK_BRANCH_SHIM/1 typed translation service (MC-07, MC-14, MC-15, MC-17, MC-26).

* Requests/responses are typed JSON documents, not Python objects.
* Translators are registered per (interface, from, to, schema versions) and
  are pure functions over canonical JSON payloads.
* Divergent, unclassified or unregistered paths never produce an output.
* Every success names the shim id/version, both baselines and the matrix digest.
* Capability monotonicity: a translator result is re-checked so rights can
  never widen across the boundary.
* Deadlines, cancellation and a bounded admission semaphore guard every call.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from . import canonical
from .errors import Inv22Error, wrap
from .matrix import Matrix

CONTRACT = "PK_BRANCH_SHIM/1"
BRANCHES = ("standards", "fork")
_REQ_KEYS = {"contract", "interface", "operation", "source_branch", "target_branch",
             "encoding", "payload", "correlation_id", "deadline_ms"}
SHIM_LIMITS = canonical.Limits(max_bytes=65_536, max_depth=16, max_items=2_048, max_string=4_096)


@dataclass(frozen=True)
class Translator:
    shim_id: str
    version: str
    interface: str
    source: str
    target: str
    fn: Callable[[Any], Any]
    rights_of: Callable[[Any, str], frozenset] | None = None   # extracts rights for monotonicity checks


class Registry:
    def __init__(self) -> None:
        self._t: dict[tuple[str, str, str], Translator] = {}

    def register(self, t: Translator) -> None:
        key = (t.interface, t.source, t.target)
        if key in self._t:
            raise Inv22Error("INV22.VALIDATION.INVALID_INPUT", "ambiguous translator registration",
                             {"interface": t.interface})
        if t.source == t.target or t.source not in BRANCHES or t.target not in BRANCHES:
            raise Inv22Error("INV22.TRANSLATE.UNSUPPORTED_DIRECTION", "bad translator direction")
        self._t[key] = t

    def get(self, interface: str, source: str, target: str) -> Translator:
        t = self._t.get((interface, source, target))
        if t is None:
            raise Inv22Error("INV22.TRANSLATE.NO_TRANSLATOR", "no translator registered",
                             {"interface": interface, "direction": f"{source}->{target}"})
        return t

    def manifest(self) -> list[dict]:
        return [{"shim_id": t.shim_id, "version": t.version, "interface": t.interface,
                 "direction": f"{t.source}->{t.target}"} for t in sorted(self._t.values(), key=lambda t: (t.interface, t.source))]


class CancelToken:
    def __init__(self) -> None:
        self._e = threading.Event()

    def cancel(self) -> None:
        self._e.set()

    @property
    def cancelled(self) -> bool:
        return self._e.is_set()


def validate_request(req: Any) -> dict:
    if isinstance(req, (bytes, str)):
        req = canonical.loads(req, SHIM_LIMITS)
    else:
        canonical.dumps(req, SHIM_LIMITS)
    if not isinstance(req, dict):
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "request must be an object")
    canonical.require_supported(req.get("contract", ""), "PK_BRANCH_SHIM")
    missing = (_REQ_KEYS - {"deadline_ms"}) - set(req)
    if missing:
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "missing field", {"field": sorted(missing)[0]})
    if set(req) - _REQ_KEYS:
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "unknown field", {"field": sorted(set(req) - _REQ_KEYS)[0]})
    for k in ("interface", "operation", "correlation_id"):
        if not isinstance(req[k], str) or not req[k] or len(req[k]) > 128:
            raise Inv22Error("INV22.VALIDATION.SCHEMA", f"{k} must be a short non-empty string")
    for k in ("source_branch", "target_branch"):
        if req[k] not in BRANCHES:
            raise Inv22Error("INV22.TRANSLATE.UNSUPPORTED_DIRECTION", "unknown branch", {"branch": req[k]})
    if req["encoding"] != "json-canonical":
        raise Inv22Error("INV22.VALIDATION.SCHEMA", "unsupported payload encoding")
    d = req.get("deadline_ms")
    if d is not None and (not isinstance(d, int) or isinstance(d, bool) or not 1 <= d <= 60_000):
        raise Inv22Error("INV22.VALIDATION.LIMIT", "deadline_ms must be 1..60000")
    return req


class ShimService:
    """Bounded, fail-closed translation service."""

    def __init__(self, matrix: Matrix, registry: Registry, *, max_concurrency: int = 8,
                 default_deadline_ms: int = 2_000, metrics=None, clock=time.monotonic) -> None:
        self.matrix, self.registry = matrix, registry
        self._sem = threading.BoundedSemaphore(max_concurrency)
        self.default_deadline_ms = default_deadline_ms
        self.metrics = metrics
        self._clock = clock

    def _count(self, name: str, **labels) -> None:
        if self.metrics is not None:
            self.metrics.inc(name, **labels)

    def translate(self, request: Any, cancel: CancelToken | None = None) -> dict:
        cid = request.get("correlation_id") if isinstance(request, dict) else None
        try:
            return self._translate(request, cancel)
        except Exception as exc:  # every failure leaves as a structured error, with no payload
            err = wrap(exc, cid if isinstance(cid, str) else None)
            self._count("shim_refusals", code=err.code)
            return {"contract": CONTRACT, "status": "error", "error": err.to_dict()}

    def _translate(self, request: Any, cancel: CancelToken | None) -> dict:
        start = self._clock()
        req = validate_request(request)
        budget = (req.get("deadline_ms") or self.default_deadline_ms) / 1000.0
        if not self._sem.acquire(blocking=False):
            raise Inv22Error("INV22.RESOURCE.OVERLOADED", "translation capacity exhausted")
        try:
            iface, src, dst = req["interface"], req["source_branch"], req["target_branch"]
            kind = self.matrix.classification(iface)
            if src == dst or kind == "identical":
                out, used = req["payload"], {"shim_id": "identity", "version": "1"}
            elif kind == "divergent":
                raise Inv22Error("INV22.TRANSLATE.DIVERGENT", "interface semantics differ between branches",
                                 {"interface": iface})
            else:
                t = self.registry.get(iface, src, dst)
                entry = next(e for e in self.matrix.entries if e.interface == iface)
                if entry.shim_id != t.shim_id:
                    raise Inv22Error("INV22.TRANSLATE.NO_TRANSLATOR", "registered shim does not match matrix shim_id",
                                     {"interface": iface})
                if cancel is not None and cancel.cancelled:
                    raise Inv22Error("INV22.TIMEOUT.CANCELLED", "cancelled before translation")
                out = t.fn(req["payload"])
                if t.rights_of is not None and not t.rights_of(out, dst) <= t.rights_of(req["payload"], src):
                    raise Inv22Error("INV22.TRANSLATE.CAPABILITY_ESCALATION", "translation widened rights",
                                     {"interface": iface})
                used = {"shim_id": t.shim_id, "version": t.version}
            canonical.dumps(out, SHIM_LIMITS)
            if cancel is not None and cancel.cancelled:
                raise Inv22Error("INV22.TIMEOUT.CANCELLED", "cancelled during translation")
            if self._clock() - start > budget:
                raise Inv22Error("INV22.TIMEOUT.DEADLINE_EXCEEDED", "deadline exceeded")
            self._count("translations", interface=iface)
            return {"contract": CONTRACT, "status": "ok", "correlation_id": req["correlation_id"],
                    "interface": iface, "source_branch": src, "target_branch": dst,
                    "encoding": "json-canonical", "payload": out, "lossless": True,
                    "shim": used, "matrix_digest": self.matrix.digest,
                    "source_baseline": self.matrix.source_baseline["digest"],
                    "target_baseline": self.matrix.target_baseline["digest"]}
        finally:
            self._sem.release()


# --- reference translator: filesystem open-flags + rights -------------------
# Standards form (preview2-style flags records):
#   {"open": {"create","directory","exclusive","truncate"}, "rights": {"read","write"}}
# Fork form (preview1/WASIX-style bitmasks):
#   {"oflags": u16, "rights_base": u64}
# oflags bits: CREAT=1<<0, DIRECTORY=1<<1, EXCL=1<<2, TRUNC=1<<3
# rights bits: FD_READ=1<<1, FD_WRITE=1<<6
# The mapping is a total bijection on this domain; any other bit/flag is
# non-representable and refused.

OFLAGS = {"create": 1 << 0, "directory": 1 << 1, "exclusive": 1 << 2, "truncate": 1 << 3}
RIGHTS = {"read": 1 << 1, "write": 1 << 6}
_OMASK = sum(OFLAGS.values())
_RMASK = sum(RIGHTS.values())
FS_IFACE = "wasi:filesystem/types"
FS_SHIM_ID = "fs-open-flags"


def _nr(msg: str) -> Inv22Error:
    return Inv22Error("INV22.TRANSLATE.NOT_REPRESENTABLE", msg, {"interface": FS_IFACE})


def _flagset(value: Any, universe: dict, what: str) -> list[str]:
    if not isinstance(value, list) or len(set(value)) != len(value):
        raise _nr(f"{what} must be a list of unique flag names")
    bad = [v for v in value if v not in universe]
    if bad:
        raise _nr(f"unknown {what} flag")
    return sorted(value)


def fs_std_to_fork(p: Any) -> dict:
    if not isinstance(p, dict) or set(p) != {"open", "rights"}:
        raise _nr("standards payload must be {open, rights}")
    o = _flagset(p["open"], OFLAGS, "open")
    r = _flagset(p["rights"], RIGHTS, "rights")
    return {"oflags": sum(OFLAGS[f] for f in o), "rights_base": sum(RIGHTS[f] for f in r)}


def fs_fork_to_std(p: Any) -> dict:
    if not isinstance(p, dict) or set(p) != {"oflags", "rights_base"}:
        raise _nr("fork payload must be {oflags, rights_base}")
    o, r = p["oflags"], p["rights_base"]
    for v, mask, bits in ((o, _OMASK, 16), (r, _RMASK, 64)):
        if not isinstance(v, int) or isinstance(v, bool) or v < 0 or v >= (1 << bits):
            raise _nr("bitmask out of range")
        if v & ~mask:
            raise _nr("bitmask carries bits with no standards equivalent")
    return {"open": sorted(k for k, b in OFLAGS.items() if o & b),
            "rights": sorted(k for k, b in RIGHTS.items() if r & b)}


def fs_rights(p: Any, branch: str) -> frozenset:
    if branch == "standards":
        return frozenset(p.get("rights", ()))
    return frozenset(k for k, b in RIGHTS.items() if p.get("rights_base", 0) & b)


def default_registry() -> Registry:
    reg = Registry()
    reg.register(Translator(FS_SHIM_ID, "1.0.0", FS_IFACE, "standards", "fork", fs_std_to_fork, fs_rights))
    reg.register(Translator(FS_SHIM_ID, "1.0.0", FS_IFACE, "fork", "standards", fs_fork_to_std, fs_rights))
    return reg
