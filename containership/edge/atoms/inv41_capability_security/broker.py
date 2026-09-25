"""Instrumented capability broker (REQ-BRK-*).

Wraps one Authority with admission control, audit, metrics, structured logs,
trace spans, decision-reason records, lineage, health/readiness and
quarantine.  Every decision passes through the same path so no instrumented
call can be allowed that the core primitives would deny, and any failure in
the instrumentation path is a denial (fail closed), never an allow.
"""
from __future__ import annotations

import hashlib
import secrets
import threading
import time
from typing import Final, Iterable, Mapping

from . import __version__
from .audit import AuditChain, AuditUnavailable
from .capabilities import (
    Authority, CapabilityError, CrossAuthority, Forged, Holder, Membrane, Reference, Revoked,
)
from .errors import Degraded, code_for, describe
from .resilience import Admission
from .telemetry import HEALTH_SCHEMA, REASON_SCHEMA, Metrics, StructuredLogger, Tracer, parse_traceparent

LIFECYCLE: Final[dict] = {
    "initializing": {"ready", "failed"},
    "ready": {"degraded", "quiesced", "failed", "terminated"},
    "degraded": {"ready", "quiesced", "failed", "terminated"},
    "quiesced": {"ready", "terminated"},
    "failed": {"terminated"},
    "terminated": set(),
}
REQUIRED_DEPENDENCIES: Final[tuple] = ("audit",)
OPTIONAL_DEPENDENCIES: Final[tuple] = ("identity", "policy", "key", "time", "telemetry")


class IllegalTransition(RuntimeError):
    pass


def _opaque(value: str) -> str:
    """Stable, non-reversible identifier for logs/telemetry."""
    return hashlib.sha256(value.encode()).hexdigest()[:16]


class Broker:
    def __init__(self, authority: Authority, *, audit: AuditChain, lineage: Mapping[str, str] | None = None,
                 max_concurrent: int = 64, max_queue: int = 256, success_sample_every: int = 1) -> None:
        if not isinstance(authority, Authority):
            raise TypeError("Broker requires an Authority")
        self._authority = authority
        self.audit = audit
        self.metrics = Metrics()
        self.log = StructuredLogger(component_version=__version__, success_sample_every=success_sample_every)
        self.tracer = Tracer()
        self.admission = Admission(max_concurrent, max_queue)
        self.reasons: list = []
        self.lineage = dict(lineage or {"release": __version__, "source_revision": "UNPINNED",
                                        "config_digest": "NONE", "instance": secrets.token_hex(4)})
        self.dependencies = {d: "healthy" for d in REQUIRED_DEPENDENCIES + OPTIONAL_DEPENDENCIES}
        self._state = "initializing"
        self._quarantined = False
        self._lock = threading.Lock()
        self.selfcheck_passed = False
        self.audit.emit("authority.created", outcome="success", reason="BOOTSTRAP",
                        authority=_opaque(authority.authority_id), resources=len(authority.policy))
        self.metrics.set_gauge("inv41_active_authorities", 1)
        self.transition("ready")

    # ---- lifecycle -------------------------------------------------------------------
    @property
    def state(self) -> str:
        return self._state

    def transition(self, new: str) -> None:
        with self._lock:
            if new not in LIFECYCLE.get(self._state, set()):
                raise IllegalTransition(f"{self._state} -> {new}")
            self._state = new

    def set_dependency(self, name: str, status: str) -> None:
        if name not in self.dependencies or status not in ("healthy", "degraded", "unavailable"):
            raise ValueError("unknown dependency/status")
        self.dependencies[name] = status
        bad = [d for d in REQUIRED_DEPENDENCIES if self.dependencies[d] != "healthy"]
        self.metrics.set_gauge("inv41_degraded_dependencies", sum(1 for s in self.dependencies.values() if s != "healthy"))
        if bad and self._state == "ready":
            self.transition("degraded")
        elif not bad and self._state == "degraded":
            self.transition("ready")

    def quarantine(self, reason_code: str = "OPERATOR") -> None:
        """Freeze the whole authority domain: every subsequent use is denied."""
        self._quarantined = True
        try:
            self.audit.emit("quarantine", outcome="success", reason=reason_code, authority=_opaque(self._authority.authority_id))
        finally:
            if self._state in ("ready", "degraded"):
                self.transition("quiesced")

    # ---- decision path ---------------------------------------------------------------
    def _decide(self, op: str, fn, *, resource: str | None, operation: str | None, traceparent: str | None,
                priority: bool = False):
        ctx = parse_traceparent(traceparent)
        cid = ctx["trace_id"]
        t0 = time.perf_counter()
        outcome, code, reason, result, raised = "success", None, "ALLOW", None, None
        try:
            if self._quarantined:
                raise Degraded("authority domain quarantined")
            if self._state not in ("ready",) and not priority:
                raise Degraded(f"broker {self._state}")
            with self.admission(priority=priority):
                with self.tracer.span(f"inv41.{op}", ctx, op=op):
                    result = fn()
        except CapabilityError as exc:
            raised = exc
        except (ValueError, TypeError) as exc:
            raised = exc
        except Exception as exc:  # internal fault: deny
            raised = exc
        if raised is not None:
            d = describe(raised)
            outcome, code, reason = d["outcome"], d["code"], type(raised).__name__.upper()
            result = None
        latency = time.perf_counter() - t0
        record = {"schema": REASON_SCHEMA, "op": op, "outcome": outcome, "code": code, "reason": reason,
                  "authority": _opaque(self._authority.authority_id),
                  "resource": _opaque(resource) if isinstance(resource, str) else None,
                  "operation_class": operation if isinstance(operation, str) and len(operation) <= 64 else None,
                  "config_digest": self.lineage.get("config_digest"), "release": self.lineage.get("release"),
                  "dependencies": dict(self.dependencies), "correlation_id": cid, "at": time.time()}
        self.reasons.append(record)
        del self.reasons[:-10_000]
        label_op = op if op in ("grant", "bind", "attenuate", "wrap", "revoke", "use") else "use"
        self.metrics.observe("inv41_operation_latency_seconds", latency, op=label_op)
        audit_type = {"grant": "grant", "bind": "bind", "attenuate": "attenuate", "wrap": "wrap", "revoke": "revoke"}.get(op)
        if op == "use":
            audit_type = "use.allowed" if outcome == "success" else "use.denied"
        if isinstance(raised, CrossAuthority):
            audit_type = "cross_authority.attempt"
            self.metrics.inc("inv41_cross_authority_total")
        elif isinstance(raised, Forged):
            audit_type = "reference.invalid" if op != "use" else audit_type
            self.metrics.inc("inv41_invalid_references_total")
        if outcome == "retryable":
            self.metrics.inc("inv41_overload_rejections_total")
        try:
            self.audit.emit(audit_type or "use.denied", outcome=outcome, reason=reason, correlation_id=cid,
                            resource=record["resource"] or "", code=code or "")
        except AuditUnavailable:
            # Mandatory audit: an unauditable allow becomes a denial.
            if raised is None:
                raised = Degraded("audit unavailable; action denied")
                record["outcome"], record["code"] = "degraded", "INV41-E022"
        self.log.log("warning" if raised else "info", op, record["outcome"], reason, cid, code=code)
        if raised is not None:
            if op == "use":
                self.metrics.inc("inv41_uses_denied_total", outcome=record["outcome"])
            raise raised
        counter = {"grant": "inv41_grants_total", "bind": "inv41_binds_total", "attenuate": "inv41_attenuations_total",
                   "wrap": "inv41_wraps_total", "revoke": "inv41_revocations_total", "use": "inv41_uses_allowed_total"}[op]
        self.metrics.inc(counter)
        return result

    # ---- public operations -----------------------------------------------------------
    def grant(self, resource: str, operations: Iterable[str] | None = None, *, traceparent: str | None = None) -> Reference:
        return self._decide("grant", lambda: self._authority.grant(resource, operations),
                            resource=resource, operation=None, traceparent=traceparent)

    def bind_holder(self, name: str, held: Mapping[str, Reference] | None = None, *, traceparent: str | None = None) -> Holder:
        return self._decide("bind", lambda: self._authority.bind_holder(name, held),
                            resource=None, operation=None, traceparent=traceparent)

    def use(self, holder: Holder, alias: str, operation: str, *, traceparent: str | None = None) -> dict:
        def _do():
            if not isinstance(holder, Holder):
                raise Forged("not a holder")
            ref = holder.held.get(alias) if isinstance(alias, str) else None
            if ref is not None:
                ref._assert_authority(self._authority._authority_id, self._authority._authority_seal)
            return holder.use(alias, operation)
        return self._decide("use", _do, resource=alias if isinstance(alias, str) else None,
                            operation=operation, traceparent=traceparent)

    def attenuate(self, reference: Reference, operations: Iterable[str], *, traceparent: str | None = None) -> Reference:
        def _do():
            if not isinstance(reference, Reference):
                raise Forged("not a reference")
            reference._assert_authority(self._authority._authority_id, self._authority._authority_seal)
            return reference.attenuate(operations)
        return self._decide("attenuate", _do, resource=getattr(reference, "resource", None), operation=None,
                            traceparent=traceparent)

    def wrap(self, membrane: Membrane, reference: Reference, *, traceparent: str | None = None) -> Reference:
        def _do():
            if not isinstance(reference, Reference):
                raise Forged("not a reference")
            reference._assert_authority(self._authority._authority_id, self._authority._authority_seal)
            return membrane.wrap(reference)
        return self._decide("wrap", _do, resource=getattr(reference, "resource", None), operation=None,
                            traceparent=traceparent)

    def revoke(self, membrane: Membrane, *, traceparent: str | None = None) -> dict:
        # Priority lane: revocation proceeds under overload, degradation and quarantine.
        if self._quarantined or self._state != "ready":
            result = membrane.revoke()
            self.audit.emit("revoke", outcome="success", reason="PRIORITY", killed=result["references_killed"])
            self.metrics.inc("inv41_revocations_total")
            return result
        return self._decide("revoke", membrane.revoke, resource=None, operation=None, traceparent=traceparent,
                            priority=True)

    # ---- health / explain ------------------------------------------------------------
    def health(self) -> dict:
        ready = self._state == "ready" and not self._quarantined and self.selfcheck_passed
        return {"schema": HEALTH_SCHEMA, "live": self._state not in ("failed", "terminated"), "ready": ready,
                "state": self._state, "quarantined": self._quarantined,
                "status_code": 200 if ready else 503, "version": __version__,
                "config_digest": self.lineage.get("config_digest"), "lineage": dict(self.lineage),
                "dependencies": dict(self.dependencies), "selfcheck": self.selfcheck_passed,
                "degraded_reason": None if ready else ("quarantined" if self._quarantined else self._state)}

    def explain(self, correlation_id: str) -> list:
        """Read-only historical explanation: the reason records for one correlation id."""
        return [dict(r, kind="historical") for r in self.reasons if r["correlation_id"] == correlation_id]
