"""LegacyPollService: the v4.3.0 production front door for INV-14.

Order of checks (validation/authorization before any allocation or wait -- xx.19):
  1. lifecycle/policy   -> PK_POLL_DRAINING / _DISABLED / _QUARANTINED / _FAILED_STATE
  2. identity           -> capability token verified for this owner (PK_POLL_TOKEN_*)
  3. consumer governance (optional ConsumerGate) -> PK_POLL_UNREGISTERED_CONSUMER ...
  4. admission          -> PK_POLL_OVERLOADED / PK_POLL_TENANT_QUOTA
  5. PollSet.poll       -> v4.2.0 semantics unchanged (+ optional cancellation)
Every refusal is audited (fail closed if the audit sink is down), logged,
counted, and returned as PK_POLL_ERROR/1.  Every success/timeout carries a child
traceparent and the correlation id.  Slots and lifecycle in-flight counts are
released in ``finally``.
"""
from __future__ import annotations

import datetime as _dt
import secrets
import time

try:
    from .polling import PollSet, PollValidationError, ForeignPollable, PollCancelled, _StructuredPollError
    from .errors import Inv14Error
    from .identity import Verifier, IdentityError, tenant_of
    from .admission import AdmissionController, AdmissionRefused
    from .lifecycle import Lifecycle, LifecycleError
    from .audit import AuditSink, AuditError
    from .telemetry import Telemetry
    from .tracing import child_context
    from .pollog import StructLogger
    from .governance import GovernanceError
except ImportError:
    from polling import PollSet, PollValidationError, ForeignPollable, PollCancelled, _StructuredPollError
    from errors import Inv14Error
    from identity import Verifier, IdentityError, tenant_of
    from admission import AdmissionController, AdmissionRefused
    from lifecycle import Lifecycle, LifecycleError
    from audit import AuditSink, AuditError
    from telemetry import Telemetry
    from tracing import child_context
    from pollog import StructLogger
    from governance import GovernanceError

VERSION = "4.3.0"
PROCESS_EPOCH = secrets.token_hex(6)  # new per process start (restart forensics, RST/15.11)
_REASON = {IdentityError: ("identity", "poll.refused.identity"),
           LifecycleError: ("policy", "poll.refused.policy"),
           GovernanceError: ("policy", "poll.refused.policy"),
           AdmissionRefused: ("admission", "poll.refused.admission"),
           ForeignPollable: ("foreign_owner", "poll.refused.foreign_owner"),
           PollValidationError: ("invalid", "poll.refused.invalid")}


class LegacyPollService:
    def __init__(self, *, verifier: Verifier, admission: AdmissionController, lifecycle: Lifecycle,
                 audit: AuditSink, telemetry: Telemetry | None = None, logger: StructLogger | None = None,
                 consumer_gate=None, pollset_kwargs: dict | None = None, today=_dt.date.today):
        self.verifier, self.admission, self.lifecycle, self.audit = verifier, admission, lifecycle, audit
        self.telemetry = telemetry or Telemetry()
        self.logger = logger or StructLogger()
        self.consumer_gate, self._today = consumer_gate, today
        self._psk = dict(pollset_kwargs or {})
        self._sets: dict = {}
        self._sets_lock = __import__("threading").Lock()

    MAX_POLL_SETS = 10_000

    def _pollset(self, owner: str) -> PollSet:
        with self._sets_lock:
            ps = self._sets.get(owner)
            if ps is None:
                if len(self._sets) >= self.MAX_POLL_SETS:
                    raise AdmissionRefused("poll-set registry full", code="PK_POLL_OVERLOADED")
                ps = self._sets[owner] = PollSet(owner, **self._psk)
            return ps

    def poll(self, owner: str, pollables, *, timeout_ticks: int, token: str, cancel=None,
             traceparent: str | None = None, tracestate: str | None = None, correlation_id: str | None = None,
             workload: str = "-") -> dict:
        cid = (correlation_id if isinstance(correlation_id, str) and 0 < len(correlation_id) <= 64
               else secrets.token_hex(8))
        tc = child_context(traceparent, tracestate)
        tenant = "-"
        entered = admitted = False
        t0 = time.monotonic()
        try:
            try:
                tenant = tenant_of(owner)
            except IdentityError:
                tenant = "-"
                raise
            self.lifecycle.enter()
            entered = True
            self.verifier.verify(token, owner=owner)
            if self.consumer_gate is not None:
                self.consumer_gate.check(owner.split("/")[1], self._today())
            self.admission.acquire(tenant)
            admitted = True
            result = self._pollset(owner).poll(pollables, timeout_ticks=timeout_ticks, cancel=cancel)
            outcome = "timeout" if result["timed_out"] else "ready"
            self.telemetry.record(tenant, outcome, latency_ms=(time.monotonic() - t0) * 1000)
            self.audit.append("poll.deprecated_use", correlation_id=cid,
                              details={"tenant": tenant, "outcome": outcome, "set_size": result["set_size"]})
            self.logger.log("INFO", "poll", "poll." + outcome, tenant=tenant, workload=workload,
                            correlation_id=cid, trace_id=tc.trace_id, set_size=result["set_size"],
                            duration_ms=round((time.monotonic() - t0) * 1000, 3), epoch=PROCESS_EPOCH)
            return dict(result, correlation_id=cid, trace=tc.as_dict())
        except PollCancelled as e:
            self.telemetry.record(tenant, "cancelled")
            self._audit_or_fail("poll.cancelled", cid, e)
            self.logger.log("INFO", "poll", "poll.cancelled", tenant=tenant, correlation_id=cid, trace_id=tc.trace_id)
            e.details.update(correlation_id=cid)
            raise
        except Exception as e:  # _StructuredPollError is a mixin, not a BaseException (defect D-01)
            if not isinstance(e, _StructuredPollError):
                raise
            reason, event = next(((r, ev) for cls, (r, ev) in _REASON.items() if isinstance(e, cls)),
                                 ("invalid", "poll.refused.invalid"))
            self.telemetry.record(tenant, "refused", reason)
            self._audit_or_fail(event, cid, e)
            self.logger.log("WARN", "poll", event, tenant=tenant, correlation_id=cid, trace_id=tc.trace_id,
                            code=e.code)
            e.details.update(correlation_id=cid)
            raise
        finally:
            if admitted:
                self.admission.release(tenant)
            if entered:
                self.lifecycle.exit()

    def _audit_or_fail(self, event, cid, err):
        try:
            self.audit.append(event, correlation_id=cid, details={"code": err.code})
        except AuditError as ae:
            raise ae from None

    def diagnostics(self) -> dict:
        """Operator diagnostics: versions and safe status only (no keys, no owners)."""
        try:
            from .core_probe import probe
        except ImportError:
            from core_probe import probe
        cp = probe()
        import hashlib, pathlib
        sd = pathlib.Path(__file__).resolve().parent / "schemas"
        digests = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:16] for p in sorted(sd.glob("*.json"))}
        any_ps = next(iter(self._sets.values()), None)
        return {"component": "INV-14", "version": VERSION, "process_epoch": PROCESS_EPOCH,
                "schema_digests": digests, "lifecycle_model": "PK_POLL_LIFECYCLE/1",
                "tick_seconds": self._psk.get("tick_seconds", 0.001), "clock": "monotonic", "schemas": ["PK_POLL/1", "PK_POLLABLE/1",
                "PK_POLL_ERROR/1", "PK_POLL_METRICS/1"], "lifecycle": self.lifecycle.state,
                "in_flight": self.lifecycle.in_flight(), "admission": self.admission.snapshot(),
                "pk_core": {"ok": cp["ok"], "code": cp["code"], "version": cp["core"].get("version")},
                "audit_head": self.audit.head[:16], "telemetry_series": self.telemetry.series_count(),
                "poll_sets": len(self._sets)}
