"""INV-68 packing service boundary.

This is the production boundary the 4.2.0 package lacked: it wraps the pure
engine with everything a caller-facing component must own.

=========================  =======================================================
Concern                    Mechanism (component / checklist)
=========================  =======================================================
protocol + versions        ``PK_PACK/1`` negotiation, 4.2.0 requests accepted (MC-07, C027)
payload/queue/concurrency  config ``limits`` + :class:`resilience.Admission` (MC-07/18, C028, C054)
deadline / cancellation    :class:`resilience.Deadline` checked between phases (MC-07, C025)
idempotency                ``(tenant, idempotency_key)`` -> request digest + response (MC-07, C025)
authn / authz / tenancy    :class:`auth.Authorizer` (MC-06, C023/C024/C042-C046)
quotas / fairness          per-tenant request-rate + batch-size quotas (MC-05, C017)
capacity source            circuit breaker + staleness bound (MC-18/19, C051, C053, C055)
freeze / disable           audited operator control, state preserved (MC-20, C059)
audit                      hash-chained ``PK_PACK_AUDIT/1`` records (MC-15, C049)
telemetry                  RED/USE metrics, structured logs, traceparent (MC-26, C072-C076)
health / readiness         :meth:`status` ``PK_PACK_STATUS/1`` incl. stall detection (MC-17/25, C051/C052/C071)
explain                    :func:`explain.explain` over every decision (MC-27, C077/C078)
=========================  =======================================================

The engine result is unchanged: the service calls ``pack_detailed`` with the
*active configuration's* headroom and CPU ratio, so a response is fully
determined by ``(request, config digest, capacity snapshot)``.
"""
from __future__ import annotations

import collections
import hashlib
import json
import threading
import time
import uuid
from typing import Any, Callable, Mapping

from . import __version__
from .audit import AuditLog, AuditUnavailable
from .auth import Authorizer, Principal
from .config import ConfigStore, PackingConfig, canonical
from .errors import PackError
from .explain import explain
from .packing import capacity_report, fragmentation, lower_bound, pack_detailed
from .resilience import Admission, CircuitBreaker, Deadline
from .telemetry import Metrics, StructuredLogger, child_traceparent

SUPPORTED_PROTOCOLS = ("PK_PACK/1",)
STATUS_SCHEMA = "PK_PACK_STATUS/1"
RESPONSE_SCHEMA = "PK_PACK_SERVICE_RESPONSE/1"
_REQUEST_KEYS = {"protocol", "tenant", "idempotency_key", "host_capacity", "headroom", "workloads",
                 "correlation_id", "lineage"}
IDEMPOTENCY_TTL_S = 600
IDEMPOTENCY_MAX = 4096
FUTURE_SKEW_S = 30.0  # capacity observed "in the future" beyond this is treated as untrustworthy


def request_digest(request: Mapping[str, Any]) -> str:
    body = {k: v for k, v in request.items() if k not in ("correlation_id",)}
    return hashlib.sha256(canonical(body)).hexdigest()


class PackingService:
    def __init__(self, store: ConfigStore, authorizer: Authorizer, audit: AuditLog, *,
                 capacity_source: Callable[[str], Mapping[str, Any]] | None = None,
                 metrics: Metrics | None = None, logger: StructuredLogger | None = None,
                 clock: Callable[[], float] = time.time, monotonic: Callable[[], float] = time.monotonic,
                 epoch: int = 1, stall_after_s: float = 5.0):
        self.store = store
        self.auth = authorizer
        self.audit = audit
        self.capacity_source = capacity_source
        self.metrics = metrics or Metrics()
        if getattr(audit, "_metrics", None) is None:
            audit._metrics = self.metrics  # audit loss becomes visible as inv68_audit_dropped_total
        self.logger = logger or StructuredLogger(stream=_NullStream())
        self.clock = clock
        self.monotonic = monotonic
        self.epoch = epoch
        self.stall_after_s = stall_after_s
        self.breaker = CircuitBreaker("capacity-source", clock=monotonic)
        cfg = store.active()
        self._config = cfg
        limits = cfg.document["limits"] if cfg else {"max_concurrency": 1, "max_queue": 0}
        self.admission = Admission(limits["max_concurrency"], limits["max_queue"])
        self._lock = threading.Lock()
        self._idem: "collections.OrderedDict[tuple[str, str], tuple[float, str, dict]]" = collections.OrderedDict()
        self._rate: dict[str, collections.deque] = {}
        self._inflight: dict[str, float] = {}
        self._freeze_file = store.root / "FROZEN"
        self.frozen: dict | None = self._load_freeze()
        self.last_success: float | None = None
        self.last_error: str | None = None

    # ------------------------------------------------------------ config/control
    @property
    def config(self) -> PackingConfig | None:
        return self._config

    def activate_config(self, token: str, cfg: PackingConfig, *, expected_digest: str | None = None) -> dict:
        p = self.auth.authenticate(token)
        self.auth.require(p, "config:activate")
        entry = self.store.activate(cfg, actor=p.subject, epoch=self.epoch, expected_digest=expected_digest)
        self._apply(cfg)
        return entry

    def rollback_config(self, token: str) -> dict:
        p = self.auth.authenticate(token)
        self.auth.require(p, "config:rollback")
        entry = self.store.rollback(actor=p.subject, epoch=self.epoch)
        self._apply(self.store.active())
        return entry

    def _apply(self, cfg: PackingConfig | None) -> None:
        self._config = cfg
        if cfg:
            self.admission.reconfigure(cfg.limit("max_concurrency"), cfg.limit("max_queue"))
            self.metrics.set("inv68_config_info", 1, {"config_version": cfg.version})

    def freeze(self, token: str, reason: str) -> dict:
        p = self.auth.authenticate(token)
        self.auth.require(p, "control:freeze")
        try:
            self.audit.append("control.freeze", actor=p.subject, outcome="applied", reason=reason[:256],
                              fail_closed=True)
        except AuditUnavailable as exc:
            raise PackError("AUDIT_UNAVAILABLE") from exc
        self.frozen = {"by": p.subject, "reason": reason[:256], "at": self.clock()}
        self.store._write_atomic(self._freeze_file, json.dumps(self.frozen, sort_keys=True).encode())
        self.metrics.set("inv68_frozen", 1)
        return dict(self.frozen)

    def unfreeze(self, token: str, reason: str) -> None:
        p = self.auth.authenticate(token)
        self.auth.require(p, "control:freeze")
        # recovery criteria (MC-20 E): a verified configuration must be active and the audit chain intact
        cfg = self.store.active()
        if cfg is None:
            raise PackError("NOT_READY", "cannot unfreeze without a verified active configuration")
        try:
            self.audit.verify()
        except Exception as exc:  # AuditChainBroken or unreadable ledger
            raise PackError("AUDIT_UNAVAILABLE", "cannot unfreeze: audit chain does not verify") from exc
        self._apply(cfg)
        try:
            self.audit.append("control.unfreeze", actor=p.subject, outcome="applied", reason=reason[:256],
                              fail_closed=True)
        except AuditUnavailable as exc:
            raise PackError("AUDIT_UNAVAILABLE") from exc
        self.frozen = None
        try:
            self._freeze_file.unlink()
        except FileNotFoundError:
            pass
        self.metrics.set("inv68_frozen", 0)

    def _load_freeze(self) -> dict | None:
        """A freeze survives restart (persisted beside the config store); unreadable -> stay frozen."""
        if not self._freeze_file.exists():
            return None
        try:
            return json.loads(self._freeze_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {"by": "unknown", "reason": "freeze marker unreadable; failing closed", "at": None}

    # ------------------------------------------------------------ request path
    def _parse(self, raw: Any, cfg: PackingConfig) -> dict:
        max_bytes = cfg.limit("max_payload_bytes")
        if isinstance(raw, (bytes, bytearray, str)):
            size = len(raw.encode() if isinstance(raw, str) else raw)
            if size > max_bytes:
                raise PackError("PAYLOAD_TOO_LARGE", details={"bytes": size, "limit": max_bytes})
            try:
                raw = json.loads(raw, parse_constant=_reject_constant, parse_float=_finite_float)
            except RecursionError:
                raise PackError("INVALID_REQUEST", "request nesting too deep") from None
            except (ValueError, TypeError) as exc:
                raise PackError("INVALID_REQUEST", f"request is not valid JSON: {type(exc).__name__}") from None
        if not isinstance(raw, Mapping):
            raise PackError("INVALID_REQUEST", "request must be a JSON object")
        unknown = sorted(set(raw) - _REQUEST_KEYS)
        if unknown:
            raise PackError("INVALID_REQUEST", "unknown request field(s)", details={"fields": unknown[:10]})
        protocols = raw.get("protocol", ["PK_PACK/1"])  # 4.2.0 requests carry no protocol field
        if isinstance(protocols, str):
            protocols = [protocols]
        if not isinstance(protocols, list) or not any(p in SUPPORTED_PROTOCOLS for p in protocols):
            raise PackError("UNSUPPORTED_PROTOCOL", details={"supported": list(SUPPORTED_PROTOCOLS)})
        tenant = raw.get("tenant", "default")
        if not isinstance(tenant, str) or not 1 <= len(tenant) <= 128:
            raise PackError("INVALID_REQUEST", "tenant must be a 1..128 character string")
        workloads = raw.get("workloads")
        if not isinstance(workloads, list):
            raise PackError("INVALID_REQUEST", "workloads must be an array")
        if len(workloads) > cfg.limit("max_workloads"):
            raise PackError("PAYLOAD_TOO_LARGE", details={"workloads": len(workloads),
                                                          "limit": cfg.limit("max_workloads")})
        max_name = cfg.limit("max_name_length")
        for w in workloads:
            if isinstance(w, Mapping) and isinstance(w.get("name"), str) and len(w["name"]) > max_name:
                raise PackError("INVALID_REQUEST", "workload name exceeds max_name_length")
        headroom = raw.get("headroom", cfg.headroom)
        if isinstance(headroom, bool) or not isinstance(headroom, (int, float)):
            raise PackError("INVALID_REQUEST", "headroom must be a number")
        if headroom < cfg.headroom:
            # a caller may be more conservative than policy, never less (C019 precedence)
            raise PackError("INVALID_REQUEST", "request headroom may not be below the configured headroom",
                            details={"configured": cfg.headroom})
        key = raw.get("idempotency_key")
        if key is not None and (not isinstance(key, str) or not 8 <= len(key) <= 128):
            raise PackError("INVALID_REQUEST", "idempotency_key must be 8..128 characters")
        return dict(raw, tenant=tenant, headroom=float(headroom))

    def _capacity(self, req: Mapping[str, Any], cfg: PackingConfig) -> dict:
        if req.get("host_capacity") is not None:
            cap = req["host_capacity"]
            if not isinstance(cap, Mapping) or set(cap) - {"cpu", "mem"}:
                raise PackError("INVALID_REQUEST", "host_capacity must be {cpu, mem}")
            return {"cpu": cap.get("cpu"), "mem": cap.get("mem"), "source": "request", "age_s": 0.0,
                    "snapshot_id": None, "observed_at": None}
        if self.capacity_source is None:
            raise PackError("INVALID_REQUEST", "host_capacity is required when no capacity source is configured")
        snap = self.breaker.call(lambda: self.capacity_source(req["tenant"]))
        age = self.clock() - float(snap["observed_at"])
        if age > cfg.limit("capacity_staleness_s") or age < -FUTURE_SKEW_S:
            self.breaker.failure()
            raise PackError("STALE_CAPACITY", details={"age_s": round(age, 3),
                                                       "limit_s": cfg.limit("capacity_staleness_s")})
        return {"cpu": snap["cpu"], "mem": snap["mem"], "source": str(snap.get("source", "capacity-source")),
                "age_s": round(age, 3), "snapshot_id": str(snap.get("snapshot_id") or "")[:128] or None,
                "observed_at": float(snap["observed_at"])}

    def _quota(self, tenant: str, n_workloads: int, cfg: PackingConfig) -> None:
        quota = cfg.quota(tenant)
        if n_workloads > quota["max_workloads_per_request"]:
            raise PackError("QUOTA_EXCEEDED", details={"max_workloads_per_request": quota["max_workloads_per_request"]})
        now = self.monotonic()
        with self._lock:
            window = self._rate.setdefault(tenant, collections.deque())
            while window and now - window[0] > 60.0:
                window.popleft()
            if len(window) >= quota["max_requests_per_minute"]:
                raise PackError("QUOTA_EXCEEDED", details={"max_requests_per_minute": quota["max_requests_per_minute"]})
            window.append(now)

    def pack(self, raw: Any, token: str, *, traceparent: str | None = None, deadline: Deadline | None = None,
             principal: Principal | None = None) -> dict:
        started = self.monotonic()
        corr = str(uuid.uuid4())
        trace_id, span_id, tp = child_traceparent(traceparent)
        tenant = "unknown"
        code = "OK"
        request_id = corr
        admitted = False
        try:
            cfg = self._config
            if cfg is None:
                raise PackError("NOT_READY")
            deadline = deadline or Deadline(cfg.limit("request_timeout_ms"), clock=self.monotonic)
            p = principal or self.auth.authenticate(token)
            req = self._parse(raw, cfg)
            tenant = req["tenant"]
            corr = str(req.get("correlation_id") or corr)[:128]
            self.auth.require(p, "pack:submit", tenant)
            if self.frozen:
                raise PackError("FROZEN", details={"reason": self.frozen["reason"]})
            try:
                digest = request_digest(req)
            except (TypeError, ValueError):
                raise PackError("INVALID_REQUEST", "request contains non-finite or non-JSON values") from None
            key = req.get("idempotency_key")
            if key:
                hit = self._idem_get((tenant, key))
                if hit is not None:
                    if hit[0] != digest:
                        raise PackError("IDEMPOTENCY_CONFLICT")
                    self.metrics.inc("inv68_idempotent_replays_total")
                    return dict(hit[1], replayed=True)
            self._quota(tenant, len(req["workloads"]), cfg)
            self.admission.acquire(deadline)
            admitted = True
            with self._lock:
                self._inflight[request_id] = self.monotonic()
            deadline.check("capacity")
            cap = self._capacity(req, cfg)
            deadline.check("pack")
            try:
                result = pack_detailed(req["workloads"], cap["cpu"], cap["mem"], req["headroom"], cfg.cpu_overcommit)
                lb = lower_bound(req["workloads"], cap["cpu"], cap["mem"], req["headroom"], cfg.cpu_overcommit,
                                 placeable_only=True)
                frag = fragmentation(result.hosts, req["headroom"], cfg.cpu_overcommit)
                capacity = capacity_report(cap["cpu"], cap["mem"], req["headroom"], cfg.cpu_overcommit)
            except (TypeError, ValueError) as exc:
                raise PackError("INVALID_REQUEST", str(exc)) from None
            deadline.check("respond")
            outcome = "success" if not result.unplaced else "partial"
            response = {
                "schema": RESPONSE_SCHEMA,
                "protocol": "PK_PACK/1",
                "outcome": outcome,
                "tenant": tenant,
                "request_digest": digest,
                "correlation_id": corr,
                "traceparent": tp,
                "component_version": __version__,
                "config": cfg.identity(),
                "capacity_source": {k: cap[k] for k in ("source", "age_s", "snapshot_id", "observed_at")},
                "capacity": capacity,
                "lower_bound": lb,
                "hosts_used": len(result.hosts),
                "fragmentation": frag,
                "result": result.to_dict(),
                "lineage": req.get("lineage") or {},
            }
            response["explain"] = explain(result, config=cfg.identity(), capacity=capacity, lower_bound_hosts=lb,
                                          lineage=req.get("lineage"), tenant=tenant,
                                          capacity_source=response["capacity_source"])
            if key:
                self._idem_put((tenant, key), digest, response)
            self.metrics.set("inv68_hosts_used", len(result.hosts))
            self.metrics.inc("inv68_unplaced_total", len(result.unplaced), {"tenant": tenant})
            limit_mem = capacity["effective_mem"]
            self.metrics.set("inv68_mem_overcommit_hosts",
                             sum(1 for h in result.hosts if h.used["mem"] > limit_mem + 1e-9))
            self.metrics.set("inv68_stranded_cpu", frag["cpu"])
            self.metrics.set("inv68_stranded_mem", frag["mem"])
            self.metrics.set("inv68_efficiency_ratio", (len(result.hosts) / lb) if lb else 1.0)
            self.last_success = self.clock()
            try:
                self.audit.append("pack.decision", actor=p.subject, tenant=tenant, outcome=outcome,
                                  resource=digest, correlation_id=corr, hosts=len(result.hosts),
                                  unplaced=len(result.unplaced), config_digest=cfg.digest)
            except AuditUnavailable:
                pass  # pack decisions buffer/count loss; they are not security-policy changes
            return response
        except PackError as err:
            code = err.code
            err.correlation_id = corr
            self.last_error = code
            raise
        except Exception as exc:  # defect: never leak internals, always correlate
            code = "INTERNAL"
            self.last_error = code
            self.logger.log("error", "pack.internal", correlation_id=corr, trace_id=trace_id, span_id=span_id,
                            tenant=tenant, error=type(exc).__name__)
            raise PackError("INTERNAL", correlation_id=corr) from exc
        finally:
            if admitted:
                self.admission.release()
                with self._lock:
                    self._inflight.pop(request_id, None)
            elapsed_ms = (self.monotonic() - started) * 1000.0
            self.metrics.inc("inv68_requests_total", 1, {"tenant": tenant, "code": code})
            self.metrics.observe("inv68_request_latency_ms", elapsed_ms, {"tenant": tenant})
            self.metrics.set("inv68_in_flight", self.admission.in_flight)
            self.metrics.set("inv68_queue_depth", self.admission.waiting)
            self.logger.log("info" if code == "OK" else "warning", "pack.request", correlation_id=corr,
                            trace_id=trace_id, span_id=span_id, tenant=tenant, code=code,
                            elapsed_ms=round(elapsed_ms, 3))

    def _idem_get(self, key):
        with self._lock:
            hit = self._idem.get(key)
            if hit is None:
                return None
            ts, digest, response = hit
            if self.monotonic() - ts > IDEMPOTENCY_TTL_S:
                del self._idem[key]
                return None
            return digest, response

    def _idem_put(self, key, digest, response):
        with self._lock:
            self._idem[key] = (self.monotonic(), digest, response)
            self._idem.move_to_end(key)
            while len(self._idem) > IDEMPOTENCY_MAX:
                self._idem.popitem(last=False)

    # ------------------------------------------------------------ status
    def status(self) -> dict:
        now = self.monotonic()
        with self._lock:
            oldest = min(self._inflight.values(), default=None)
        stalled = oldest is not None and now - oldest > self.stall_after_s
        cfg = self._config
        deps = {
            "capacity_source": ("not_configured" if self.capacity_source is None else self.breaker.state),
            "audit": {"buffered": self.audit.buffered, "dropped": self.audit.dropped},
            "config_store": "recovered" if self.store.recovered_from else "ok",
        }
        if cfg is None:
            state = "not_ready"
        elif self.frozen:
            state = "frozen"
        elif stalled or self.breaker.state == CircuitBreaker.OPEN or self.audit.buffered or self.store.recovered_from:
            state = "degraded"
        else:
            state = "ok"
        return {
            "schema": STATUS_SCHEMA,
            "component": "INV-68",
            "version": __version__,
            "live": not stalled,
            "ready": state in ("ok", "degraded") and cfg is not None,
            "state": state,
            "frozen": self.frozen,
            "stalled": stalled,
            "config": cfg.identity() if cfg else None,
            "epoch": self.epoch,
            "dependencies": deps,
            "capabilities": sorted(["pack", "capacity", "fragmentation", "explain"] + (["capacity-source"] if self.capacity_source else [])),
            "admission": {"in_flight": self.admission.in_flight, "queued": self.admission.waiting,
                          "shed_total": self.admission.shed},
            "last_error": self.last_error,
        }


def _finite_float(text: str) -> float:
    value = float(text)
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("non-finite JSON number")
    return value


def _reject_constant(value: str):
    raise ValueError(f"non-finite JSON constant {value}")


class _NullStream:
    def write(self, _s: str) -> int:
        return 0
