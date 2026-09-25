"""Wire adapter (remote boundary) and a simulated network link (C018, C023-C025,
C044, C046, C055, C057, C058, C089).

The core primitive never touches a network.  This adapter is the *only* place
where a future crosses a trust boundary; it adds, in this order (C019):

  authentication -> authorization/capability -> tenant isolation -> version
  -> size limits -> epoch fencing -> idempotency -> state machine

Distributed semantics: the endpoint that created a future is its single
authoritative owner.  Writers hold an ownership *epoch*; ``fence()`` (failover)
raises the epoch so a stale writer is rejected with STALE_EPOCH, preventing two
owners from resolving one future (split brain).  A restarted endpoint has a new
boot epoch, so pre-restart futures are gone (not durable) and pre-restart
messages are rejected rather than resurrected.
"""
from __future__ import annotations

import base64
import collections
import json
import hashlib
import threading
from typing import Any, Callable

from . import wire
from .auth import Authenticator
from .errors import ErrorRecord, FutureError, Rejected, from_exception
from .runtime import Runtime
from .telemetry import TraceContext

_VT = {"str": str, "int": int, "float": float, "bool": bool, "bytes": str, "object": dict}


class RemoteEndpoint:
    """Server side of the PK_FUTURE/1 wire contract."""

    def __init__(self, runtime: Runtime, authenticator: Authenticator, *, idempotency_max: int = 10_000):
        self.rt = runtime
        self.auth = authenticator
        self.boot_epoch = runtime.epoch
        self._futs: dict[str, dict] = {}
        # released futures move to a bounded ring so the registry never grows without bound (C067)
        self._released: "collections.OrderedDict[str, dict]" = collections.OrderedDict()
        self._released_max = idempotency_max
        self._idem: dict[str, tuple[str, bytes]] = {}
        self._idem_max = idempotency_max
        self._lock = threading.Lock()
        self.handled = 0

    # -- helpers ---------------------------------------------------------
    def _resp(self, ok: bool, body: dict | None = None, err: ErrorRecord | None = None) -> bytes:
        doc = {"ok": ok}
        if ok:
            doc["result"] = body or {}
        else:
            doc["error"] = err.to_dict() if err else None
        return wire.encode(doc)

    def _owned(self, fid: str, sub: str, epoch: int | None = None) -> dict:
        rec = self._futs.get(fid) or self._released.get(fid)
        if rec is None or rec["tenant"] != sub:
            raise Rejected("unknown future", code="PERMISSION_DENIED")   # no cross-tenant oracle
        if epoch is not None:
            if epoch < rec["epoch"]:
                raise Rejected("stale ownership epoch", code="STALE_EPOCH",
                               details={"offered": epoch, "current": rec["epoch"]})
            if epoch != rec["epoch"]:
                raise Rejected("unknown ownership epoch", code="STALE_EPOCH")
        return rec

    def handle(self, op: str, blob: bytes, token: str, *, traceparent: str | None = None) -> bytes:
        """Single entry point; always returns an encoded response, never raises."""
        self.handled += 1
        trace = TraceContext.parse(traceparent)
        try:
            need = {"create": "create", "resolve": "resolve", "abandon": "abandon",
                    "take": "receive", "inspect": "inspect", "fence": "administer"}.get(op)
            if need is None:
                raise Rejected("unknown operation", code="INVALID_ARGUMENT")
            try:
                claims = self.auth.verify(token, need)        # authenticate before any parsing of state
            except Rejected as exc:
                self.rt.audit.append("auth.failure", target=op, result="denied", code=exc.code)
                self.rt.metrics.inc("inv18_rejections_total", code=exc.code)
                self.rt._decide("AUTHN_REJECTED" if exc.code != "PERMISSION_DENIED" else "AUTHZ_REJECTED", exc.code)
                raise
            sub = claims["sub"]
            limit = self.rt.config.values()["max_payload_bytes"]
            return getattr(self, "_op_" + op)(blob, sub, limit, trace)
        except FutureError as exc:
            return self._resp(False, err=exc.record())
        except Exception as exc:  # noqa: BLE001 - never leak tracebacks across the boundary
            return self._resp(False, err=from_exception(exc))

    def _idempotent(self, key: str, blob: bytes, fn: Callable[[], bytes]) -> bytes:
        d = hashlib.sha256(blob).hexdigest()
        with self._lock:
            hit = self._idem.get(key)
        if hit is not None:
            if hit[0] != d:
                raise Rejected("idempotency key reused with a different body", code="REPLAY_DETECTED")
            return hit[1]
        resp = fn()
        with self._lock:
            self._idem[key] = (d, resp)
            while len(self._idem) > self._idem_max:
                self._idem.pop(next(iter(self._idem)))
        return resp

    def _retire(self, fid: str) -> None:
        if fid in self._futs and fid not in self.rt._entries:
            with self._lock:
                rec = self._futs.pop(fid, None)
                if rec is not None:
                    self._released[fid] = rec
                    while len(self._released) > self._released_max:
                        self._released.popitem(last=False)

    @property
    def live(self) -> int:
        return len(self._futs)

    # -- operations -----------------------------------------------------
    def _op_create(self, blob, sub, limit, trace):
        doc = wire.decode(blob, "PK_FUTURE/1", max_bytes=limit)
        if doc.get("tenant", sub) != sub:
            raise Rejected("tenant must match authenticated subject", code="PERMISSION_DENIED")
        rcap, qcap = self.rt.create(_VT[doc["value_type"]], tenant=sub, trace=trace)
        fid = rcap.future_id
        with self._lock:
            self._futs[fid] = {"tenant": sub, "resolver": rcap, "receiver": qcap, "epoch": doc["epoch"] or 1,
                               "value_type": doc["value_type"]}
        return self._resp(True, {"schema": "PK_FUTURE/1", "future_id": fid, "value_type": doc["value_type"],
                                 "epoch": self._futs[fid]["epoch"], "traceparent": trace.header()})

    def _op_resolve(self, blob, sub, limit, trace):
        doc = wire.decode(blob, "PK_FUTURE_RESOLVE/1", max_bytes=limit)

        def run() -> bytes:
            rec = self._owned(doc["future_id"], sub, doc["epoch"])
            try:
                if doc["outcome"] == "ok":
                    v = doc["value"]
                    if rec["value_type"] == "float" and isinstance(v, int) and not isinstance(v, bool):
                        v = float(v)
                    self.rt.resolve(rec["resolver"], v)
                else:
                    err = ErrorRecord.from_dict(doc["error"])
                    self.rt.resolve_error(rec["resolver"], f"{err.code}: {err.message}"[:4096])
            except FutureError as exc:
                return self._resp(False, err=exc.record())
            except (TypeError, ValueError) as exc:
                return self._resp(False, err=from_exception(exc))
            return self._resp(True, {"future_id": doc["future_id"]})
        return self._idempotent(doc["idempotency_key"], blob, run)

    def _op_abandon(self, blob, sub, limit, trace):
        doc = wire.decode(blob, "PK_FUTURE_ABANDON/1", max_bytes=limit)

        def run() -> bytes:
            rec = self._owned(doc["future_id"], sub, doc["epoch"])
            done = self.rt.abandon(rec["resolver"])
            self._retire(doc["future_id"])
            return self._resp(True, {"future_id": doc["future_id"], "abandoned": done})
        return self._idempotent(doc["idempotency_key"], blob, run)

    def _op_take(self, blob, sub, limit, trace):
        doc = wire.decode(blob, "PK_FUTURE/1", max_bytes=limit)
        rec = self._owned(doc["future_id"], sub)
        try:
            out = self.rt.take(rec["receiver"])
        finally:
            self._retire(doc["future_id"])
        if out is None:
            return self._resp(True, {"pending": True})
        tag, val = out
        return self._resp(True, {"outcome": tag, "value" if tag == "ok" else "error_message": val})

    def _op_inspect(self, blob, sub, limit, trace):
        doc = wire.decode(blob, "PK_FUTURE/1", max_bytes=limit)
        rec = self._owned(doc["future_id"], sub)
        return self._resp(True, self.rt.inspect(rec["receiver"]))

    def _op_fence(self, blob, sub, limit, trace):
        """Failover: raise the ownership epoch; the previous owner is fenced."""
        doc = wire.decode(blob, "PK_FUTURE/1", max_bytes=limit)
        rec = self._owned(doc["future_id"], sub)          # administer is tenant-scoped too
        if doc["epoch"] <= rec["epoch"]:
            raise Rejected("new epoch must be greater", code="STALE_EPOCH")
        rec["epoch"] = doc["epoch"]
        self.rt.audit.append("ownership.fence", actor=sub, target=doc["future_id"], epoch=doc["epoch"])
        return self._resp(True, {"future_id": doc["future_id"], "epoch": doc["epoch"]})


class Link:
    """Simulated network between a client and an endpoint (partition, loss, reorder)."""

    def __init__(self, endpoint: RemoteEndpoint | None):
        self.endpoint = endpoint
        self.partitioned = False
        self.drop_responses = 0      # deliver the request but lose N responses
        self.delivered = 0

    def send(self, op: str, blob: bytes, token: str, traceparent: str | None = None) -> bytes:
        if self.partitioned or self.endpoint is None:
            raise Rejected("network partition", code="DEPENDENCY_UNAVAILABLE")
        resp = self.endpoint.handle(op, blob, token, traceparent=traceparent)
        self.delivered += 1
        if self.drop_responses > 0:
            self.drop_responses -= 1
            raise Rejected("response lost", code="TIMEOUT")
        return resp


class RemoteClient:
    """Producer/consumer client using retries + idempotency keys."""

    def __init__(self, link: Link, issuer: Authenticator, subject: str, caps: list[str], *, retry=None):
        from .retry import RetryPolicy
        self.link, self.issuer, self.sub, self.caps = link, issuer, subject, caps
        self.retry = retry or RetryPolicy(max_attempts=4, base_delay_s=0.0, max_total_s=5.0, seed=7,
                                          sleep=lambda s: None)
        self._n = 0
        self.trace = TraceContext.new()

    def _call(self, op: str, doc: dict) -> dict:
        blob = wire.encode(doc)

        def once():
            tok = self.issuer.issue(self.sub, self.caps)
            resp = self.link.send(op, blob, tok, self.trace.header())
            out = json.loads(resp)
            if not out["ok"] and out["error"]["retryable"] and out["error"]["code"] != "RESOURCE_EXHAUSTED":
                raise Rejected(out["error"]["message"], code=out["error"]["code"])
            return out
        return self.retry.call(once)

    def key(self) -> str:
        self._n += 1
        return f"{self.sub}.{self._n}"

    def create(self, value_type: str, epoch: int = 1) -> dict:
        return self._call("create", {"schema": "PK_FUTURE/1", "future_id": "new", "value_type": value_type,
                                     "epoch": epoch})

    def resolve(self, fid: str, value: Any, *, epoch: int = 1, key: str | None = None) -> dict:
        return self._call("resolve", {"schema": "PK_FUTURE_RESOLVE/1", "future_id": fid, "outcome": "ok",
                                      "value": value, "epoch": epoch, "idempotency_key": key or self.key()})

    def resolve_error(self, fid: str, err: ErrorRecord, *, epoch: int = 1, key: str | None = None) -> dict:
        return self._call("resolve", {"schema": "PK_FUTURE_RESOLVE/1", "future_id": fid, "outcome": "error",
                                      "error": err.to_dict(), "epoch": epoch,
                                      "idempotency_key": key or self.key()})

    def abandon(self, fid: str, *, epoch: int = 1, reason: str = "writer_dropped") -> dict:
        return self._call("abandon", {"schema": "PK_FUTURE_ABANDON/1", "future_id": fid, "epoch": epoch,
                                      "idempotency_key": self.key(), "reason": reason})

    def take(self, fid: str, value_type: str = "str") -> dict:
        return self._call("take", {"schema": "PK_FUTURE/1", "future_id": fid, "value_type": value_type,
                                   "epoch": 0})

    def fence(self, fid: str, epoch: int, value_type: str = "str") -> dict:
        return self._call("fence", {"schema": "PK_FUTURE/1", "future_id": fid, "value_type": value_type,
                                    "epoch": epoch})


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode()
