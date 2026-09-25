"""Governed data-plane service: the production composition of every PLN-06 control.

Request path (precedence order from :mod:`precedence`)::

    authenticate -> emergency/freeze/quarantine gates -> authorize(transfer.submit)
    -> signed label + digest (integrity) -> residency admission -> capacity
    -> authorize(transport.use.<tier>) -> journal(admitted) -> audit
    -> adapter selection -> bounded retry send -> receiver verification
    -> PLN-03 hand-off -> journal(completed) -> release capacity

Every refusal is audited, logged and counted; failures release capacity.
"""
from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Iterable, Mapping

from . import integrity, precedence
from .data_plane import Backpressure, DataPlane, InvalidRequest, _StructuredError
from .integrations import DistributedRuntime, PolicyClient, verified_locality
from .lifecycle import TERMINAL, TransferJournal
from .metadata import VERSION
from .observability import MetricsRegistry, StructuredLogger, Tracer, explain, hash_label, process_resources
from .resilience import FailoverController, FailoverRefused, RetryExhausted, RetryPolicy, StallDetector, call_with_retry
from .security import (
    AuditLedger,
    Authenticator,
    AuthorizationDenied,
    Authorizer,
    KeyRing,
    KeyUnavailable,
    LabelAuthority,
    Principal,
)
from .transports import TransportAdapter, select_adapter


class AdmissionFrozen(_StructuredError, RuntimeError):
    code = "PK_ADMISSION_FROZEN"
    retryable = True


class DestinationQuarantined(_StructuredError, PermissionError):
    code = "PK_DESTINATION_QUARANTINED"


class GovernedDataPlane:
    def __init__(self, plane: DataPlane, *, keyring: KeyRing, authenticator: Authenticator,
                 labels: LabelAuthority, audit: AuditLedger, journal: TransferJournal,
                 adapters: Mapping[str, TransportAdapter], runtime: DistributedRuntime | None = None,
                 policy: PolicyClient | None = None, gravity_keys: KeyRing | None = None,
                 failover: FailoverController | None = None, retry: RetryPolicy | None = None,
                 logger: StructuredLogger | None = None, metrics: MetricsRegistry | None = None,
                 tracer: Tracer | None = None, stall_timeout: float = 60.0, lineage: Mapping[str, str] | None = None,
                 require_labels: bool = True):
        self.plane = plane
        self.keys = keyring
        self.authn = authenticator
        self.labels = labels
        self.audit = audit
        self.journal = journal
        self.adapters = dict(adapters)
        self.runtime = runtime
        self.policy = policy
        self.gravity_keys = gravity_keys
        self.failover_ctl = failover
        self.retry = retry or RetryPolicy(max_attempts=3, base_delay=0.001, max_delay=0.01, deadline_s=30)
        self.log = logger or StructuredLogger(node="local", release=VERSION)
        self.metrics = metrics or MetricsRegistry()
        self.tracer = tracer or Tracer(sample_rate=1.0)
        self.stalls = StallDetector(stall_timeout)
        self.lineage = dict(lineage or {"release": VERSION})
        self.require_labels = require_labels
        self._frozen: str | None = None
        self._disabled: str | None = None
        self._q_dest: dict[str, str] = {}
        self._q_transport: dict[str, str] = {}
        self._decisions: dict[str, dict[str, object]] = {}
        self._lock = threading.RLock()
        self.recovered = self._recover()

    # ------------------------------------------------------------ helpers
    def _principal(self, credential: Mapping[str, object], op: str) -> Principal:
        try:
            return self.authn.authenticate(credential)
        except _StructuredError as exc:
            self._refuse(None, op, exc)
            raise

    def _refuse(self, principal: Principal | None, op: str, exc: _StructuredError, **fields: object) -> None:
        event = {"PK_AUTHN_FAILED": "authn_failure", "PK_AUTHZ_DENIED": "authz_denied"}.get(exc.code, "refuse")
        try:
            self.audit.append(event, op=op, code=exc.code,
                              subject=None if principal is None else principal.subject, **fields)
        except KeyUnavailable:
            pass  # key outage already fails the request closed
        self.metrics.inc("pk06_refusals", code=exc.code, op=op)
        self.log.log("SECURITY" if event != "refuse" else "WARNING", "refused", operation=op,
                     tenant=None if principal is None else principal.tenant, code=exc.code)

    def _require(self, p: Principal, cap: str, op: str, tenant: str | None = None) -> None:
        try:
            Authorizer.require(p, cap, tenant=tenant)
        except AuthorizationDenied as exc:
            self._refuse(p, op, exc)
            raise

    def _recover(self) -> list[str]:
        """Crash recovery: capacity reservations are process-local, so any transfer that was
        non-terminal in the journal is reconciled to ``expired`` and audited."""
        expired = []
        for tid in self.journal.open_transfers():
            self.journal.transition(tid, "expired", reason="controller_restart")
            expired.append(tid)
        if expired:
            self.audit.append("restore", expired=len(expired), epoch=self.journal.epoch)
        return expired

    # ------------------------------------------------------------ data path
    def submit(self, credential: Mapping[str, object], *, workload: str, data: bytes, classification: str,
               destination: str, label: Mapping[str, object] | None = None, locality: str = "auto",
               gravity: Mapping[str, object] | None = None, traceparent: str | None = None,
               failover_candidates: Iterable[str] = (), control_verb: str | None = None) -> dict[str, object]:
        op = "transfer.submit"
        p = self._principal(credential, op)
        span = self.tracer.start("pk06.submit", traceparent, destination=destination)
        t0 = time.monotonic()
        tenant = p.tenant or ""
        digest = integrity.sha256_hex(data)
        tier_hint = [None]

        def sec() -> tuple[bool, str]:
            if self._disabled:
                return False, "emergency_disabled"
            if self._frozen:
                return False, "admission_frozen"
            if destination in self._q_dest:
                return False, "destination_quarantined"
            return True, "ok"

        def residency() -> tuple[bool, str]:
            return (self.plane.permitted(destination, classification), destination)

        def integ() -> tuple[bool, str]:
            if not self.require_labels:
                return True, "labels_not_required"
            if label is None:
                return False, "missing_signed_label"
            self.labels.verify(label, classification=classification, digest=digest, tenant=tenant)
            return True, "label_verified"

        try:
            self._require(p, op, op, tenant=tenant)
            if not tenant:
                raise AuthorizationDenied("submitting principal must be tenant-scoped")
            if self.policy is not None:
                self.policy.get()  # fails closed when authoritative policy is stale/unavailable
            if gravity is not None and self.gravity_keys is not None and locality == "auto":
                locality = verified_locality(gravity, self.gravity_keys, tenant=tenant, destination=destination)
            verdict = precedence.evaluate({"security": sec, "residency": residency, "integrity": integ})
            if not verdict.allowed:
                if verdict.decided_by == "residency":
                    # delegate to the runtime so refusal counters/structured error stay authoritative
                    self.plane.admit(tenant=tenant, workload=workload, size=len(data),
                                     classification=classification, destination=destination, locality=locality)
                why = verdict.reasons[-1].split(":", 2)[-1]
                if why == "destination_quarantined":
                    raise DestinationQuarantined("destination quarantined", destination=destination)
                if why in ("admission_frozen", "emergency_disabled"):
                    raise AdmissionFrozen(f"admission refused: {why}", retryable=why == "admission_frozen")
                raise InvalidRequest(f"refused by {verdict.decided_by}: {why}", reasons=list(verdict.reasons))
            decision = self.plane.admit(tenant=tenant, workload=workload, size=len(data),
                                        classification=classification, destination=destination,
                                        locality=locality, digest=digest)
            tier_hint[0] = decision["tier"]  # type: ignore[assignment, call-overload]
        except _StructuredError as exc:
            if exc.code not in ("PK_AUTHN_FAILED", "PK_AUTHZ_DENIED"):
                self._refuse(p, op, exc, destination=destination)
            self.tracer.end(span, "error", code=exc.code)
            raise
        tid = str(decision["transfer_id"] or f"inline-{uuid.uuid4().hex}")
        try:
            self._require(p, f"transport.use.{decision['tier']}", op, tenant=tenant)
        except AuthorizationDenied:
            self.plane.cancel(decision)
            self.tracer.end(span, "error", code="PK_AUTHZ_DENIED")
            raise
        if control_verb is not None:
            decision = {**decision, "control_verb": control_verb}
        self.journal.transition(tid, "admitted", tenant_hash=hash_label(tenant), tier=decision["tier"],
                                destination=destination, size=len(data), digest=digest)
        self.audit.append("admit", transfer=tid, tenant=hash_label(tenant), destination=destination,
                          classification=classification, tier=decision["tier"], digest=digest,
                          policy=decision["config_revision"])
        self.metrics.inc("pk06_admitted", tier=str(decision["tier"]))
        with self._lock:
            self._decisions[tid] = dict(decision)
        try:
            receipt = self._move(tid, decision, data)
        except _StructuredError as exc:
            candidates = list(failover_candidates)
            if candidates and self.failover_ctl is not None and exc.code in (
                    "PK_RETRY_EXHAUSTED", "PK_TRANSPORT_FAILED", "PK_DEADLINE_EXCEEDED", "PK_CIRCUIT_OPEN"):
                try:
                    alt = self.failover_ctl.choose(classification=classification, original=destination,
                                                   candidates=candidates)
                except FailoverRefused as fexc:
                    self._refuse(p, "failover", fexc, transfer=tid)
                    self.tracer.end(span, "error", code=fexc.code)
                    raise
                self.audit.append("failover", transfer=tid, frm=destination, to=alt["destination"])
                self.tracer.end(span, "error", code=exc.code, failover=alt["destination"])
                return self.submit(credential, workload=workload, data=data, classification=classification,
                                   destination=str(alt["destination"]), label=label, locality=locality,
                                   traceparent=Tracer.traceparent(span))
            self.tracer.end(span, "error", code=exc.code)
            raise
        self.metrics.observe("pk06_transfer_seconds", time.monotonic() - t0, tier=str(decision["tier"]))
        self.metrics.inc("pk06_bytes", len(data), tier=str(decision["tier"]))
        self.tracer.end(span, "ok", adapter=receipt["adapter"])
        self.log.log("INFO", "transfer_completed", operation=op, tenant=hash_label(tenant), workload=workload,
                     trace=span, transfer=tid, adapter=receipt["adapter"], size=len(data))  # type: ignore[arg-type]
        return {"transfer_id": tid, "decision": decision, "receipt": receipt,
                "traceparent": Tracer.traceparent(span), "state": "completed"}

    def _move(self, tid: str, decision: Mapping[str, object], data: bytes) -> dict[str, object]:
        try:
            adapter, choice = select_adapter(decision, self.adapters, excluded=frozenset(self._q_transport))
        except _StructuredError as exc:
            # no executable transport: fail the admitted transfer and release its reservation
            self.journal.transition(tid, "failed", code=exc.code, retryable=exc.retryable)
            self.audit.append("fail", transfer=tid, code=exc.code)
            self.plane.cancel(decision)
            raise
        with self._lock:
            self._decisions[tid]["adapter_choice"] = choice
        self.journal.transition(tid, "in_flight", adapter=adapter.name)
        self.stalls.progress(tid)
        try:
            receipt = call_with_retry(
                lambda dl: adapter.send(decision, data, deadline=time.monotonic() + max(0.001, dl - time.monotonic())),
                self.retry, clock=time.monotonic)
            rec = {"adapter": receipt.adapter, "bytes": receipt.bytes_moved, "copies": receipt.copies,
                   "manifest_root": receipt.manifest_root, "elapsed_s": receipt.elapsed_s, **receipt.extra}
            if self.runtime is not None and decision.get("tier") != "inline":
                call_with_retry(lambda _dl: self.runtime.handoff(decision, rec), self.retry)  # type: ignore[union-attr]
        except integrity.IntegrityMismatch as exc:
            self.journal.transition(tid, "quarantined", code=exc.code)
            self.audit.append("quarantine_payload", transfer=tid, code=exc.code)
            self.plane.cancel(decision)
            self.stalls.done(tid)
            raise
        except _StructuredError as exc:
            self.journal.transition(tid, "failed", code=exc.code, retryable=exc.retryable)
            self.audit.append("fail", transfer=tid, code=exc.code)
            self.plane.cancel(decision)
            self.stalls.done(tid)
            raise
        self.journal.transition(tid, "completed", root=rec["manifest_root"])
        self.audit.append("complete", transfer=tid, root=rec["manifest_root"], adapter=rec["adapter"])
        self.plane.complete(decision)
        self.stalls.done(tid)
        return rec

    def cancel(self, credential: Mapping[str, object], transfer_id: str) -> bool:
        p = self._principal(credential, "transfer.cancel")
        with self._lock:
            decision = self._decisions.get(transfer_id)
        if decision is None or self.journal.state.get(transfer_id, {}).get("state") in TERMINAL:
            return False
        cap = "transfer.complete" if decision["tenant"] == p.tenant else "transfer.complete.any"
        self._require(p, cap, "transfer.cancel")
        self.journal.transition(transfer_id, "cancelled", by=p.subject)
        self.audit.append("cancel", transfer=transfer_id, by=p.subject)
        return self.plane.cancel(decision)

    def reap_stalled(self) -> list[str]:
        """Stall detection: cancel transfers without progress beyond the stall timeout."""
        out = []
        for tid in self.stalls.stalled():
            decision = self._decisions.get(tid)
            if decision is not None and self.journal.state.get(tid, {}).get("state") not in TERMINAL:
                self.journal.transition(tid, "expired", reason="stall")
                self.audit.append("fail", transfer=tid, code="PK_STALLED")
                self.plane.cancel(decision)
                out.append(tid)
            self.stalls.done(tid)
        return out

    # ------------------------------------------------------------ operator controls (#27)
    def _admin(self, credential: Mapping[str, object], cap: str, op: str) -> Principal:
        p = self._principal(credential, op)
        self._require(p, cap, op)
        return p

    def freeze(self, credential: Mapping[str, object], reason: str) -> None:
        p = self._admin(credential, "control.freeze", "freeze")
        self._frozen = reason
        self.audit.append("freeze", by=p.subject, reason=reason)

    def unfreeze(self, credential: Mapping[str, object]) -> None:
        p = self._admin(credential, "control.freeze", "unfreeze")
        self._frozen = None
        self.audit.append("unfreeze", by=p.subject)

    def quarantine(self, credential: Mapping[str, object], *, destination: str | None = None,
                   transport: str | None = None, reason: str) -> None:
        p = self._admin(credential, "control.freeze", "quarantine")
        if destination:
            self._q_dest[destination] = reason
        if transport:
            self._q_transport[transport] = reason
        self.audit.append("quarantine", by=p.subject, destination=destination, transport=transport, reason=reason)

    def unquarantine(self, credential: Mapping[str, object], *, destination: str | None = None,
                     transport: str | None = None) -> None:
        p = self._admin(credential, "control.freeze", "unquarantine")
        self._q_dest.pop(destination or "", None)
        self._q_transport.pop(transport or "", None)
        self.audit.append("unquarantine", by=p.subject, destination=destination, transport=transport)

    def drain(self, credential: Mapping[str, object], timeout: float = 30.0) -> bool:
        p = self._admin(credential, "control.freeze", "drain")
        self._frozen = self._frozen or "draining"
        self.audit.append("drain", by=p.subject)
        end = time.monotonic() + timeout
        while self.plane.inflight and time.monotonic() < end:
            time.sleep(0.01)
        return self.plane.inflight == 0

    def emergency_disable(self, credential: Mapping[str, object], reason: str) -> None:
        p = self._admin(credential, "control.freeze", "emergency_disable")
        self._disabled = reason
        self.audit.append("emergency_disable", by=p.subject, reason=reason)

    def update_policy(self, credential: Mapping[str, object], residency: Mapping[str, Iterable[str]],
                      *, revision: str) -> None:
        p = self._admin(credential, "policy.update", "policy.update")
        self.plane.replace_residency({k: set(v) for k, v in residency.items()}, revision=revision, author=p.subject)
        self.audit.append("policy_update", by=p.subject, revision=revision)

    def sync_policy(self) -> str:
        """Pull authoritative GAP-13 policy and activate it."""
        if self.policy is None:
            raise InvalidRequest("no policy client configured")
        body = self.policy.refresh()
        if self.plane.config_snapshot()["revision"] != body["revision"]:
            self.plane.replace_residency({k: set(v) for k, v in body["residency"].items()},  # type: ignore[attr-defined, union-attr]
                                         revision=str(body["revision"]), author="gap13")
            self.audit.append("policy_update", by="gap13", revision=body["revision"])
        return str(body["revision"])

    # ------------------------------------------------------------ observability (#34, #35, #38)
    def health(self) -> dict[str, object]:
        deps: dict[str, dict[str, object]] = {}
        try:
            self.keys.sign(b"probe")
            deps["key_service"] = {"ok": True}
        except KeyUnavailable as exc:
            deps["key_service"] = {"ok": False, "code": exc.code}
        try:
            self.audit.verify()
            deps["audit_ledger"] = {"ok": True, "head": self.audit.head[:16]}
        except _StructuredError as exc:
            deps["audit_ledger"] = {"ok": False, "code": exc.code}
        if self.policy is not None:
            try:
                self.policy.get()
                deps["gap13_policy"] = {"ok": True, "degraded": self.policy.degraded}
            except _StructuredError as exc:
                deps["gap13_policy"] = {"ok": False, "code": exc.code}
        for name, a in self.adapters.items():
            deps[f"adapter:{name}"] = {"ok": a.available()}
        stalled = self.stalls.stalled()
        critical = ("key_service", "audit_ledger", "gap13_policy")
        ready = all(deps[d]["ok"] for d in critical if d in deps) and not self._disabled and not self._frozen
        base = self.plane.health()
        return {**base, "schema": "PK_DATA_PLANE_HEALTH/2", "healthy": ready or bool(self._frozen),
                "ready": ready, "frozen": self._frozen, "emergency_disabled": self._disabled,
                "quarantined": {"destinations": sorted(self._q_dest), "transports": sorted(self._q_transport)},
                "dependencies": deps, "stalled": len(stalled), "lineage": self.lineage,
                "degraded": [k for k, v in deps.items() if not v["ok"]]}

    def metrics_text(self) -> str:
        m = self.plane.metrics()
        self.metrics.set("pk06_inflight", float(m["inflight"]))  # type: ignore[arg-type]
        self.metrics.set("pk06_inflight_limit", float(m["inflight_limit"]))  # type: ignore[arg-type]
        self.metrics.set("pk06_backpressure_events", float(m["backpressure_events"]))  # type: ignore[arg-type]
        self.metrics.set("pk06_open_transfers", float(len(self.journal.open_transfers())))
        oldest = [time.time() - float(v["ts"]) for v in self.journal.open_transfers().values()]  # type: ignore[arg-type]
        self.metrics.set("pk06_backlog_oldest_seconds", max(oldest, default=0.0))
        self.metrics.set("pk06_health_ready", 1.0 if self.health()["ready"] else 0.0)
        self.metrics.set("pk06_metrics_overflowed", float(self.metrics.overflowed))
        for k, v in process_resources().items():
            self.metrics.set(f"pk06_process_{k}", v)
        return self.metrics.prometheus()

    def explain(self, credential: Mapping[str, object], transfer_id: str) -> dict[str, object]:
        p = self._admin(credential, "diagnostics.read", "explain")
        del p
        with self._lock:
            decision = self._decisions.get(transfer_id)
        if decision is None:
            raise InvalidRequest("unknown transfer", transfer_id=transfer_id)
        return explain(decision, policy_revision=str(decision["config_revision"]),
                       precedence=precedence.PRECEDENCE, adapter_choice=decision.get("adapter_choice"),  # type: ignore[arg-type]
                       lineage=self.lineage)


__all__ = ["GovernedDataPlane", "AdmissionFrozen", "DestinationQuarantined", "Backpressure", "RetryExhausted"]
