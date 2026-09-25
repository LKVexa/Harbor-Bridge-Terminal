"""Application-plane service facade: wires every v4.3 control around the v4.2 resolver.

Request pipeline (each step fail-closed, in this order)::

    payload bound -> authenticate -> plane enabled/frozen -> admission (quota/concurrency/shed)
    -> idempotency -> deadline checkpoint -> version check -> entitlement
    -> signed catalogue snapshot (fresh, or degraded under lease)
    -> constraint merge (platform > tenant > application) -> explainable selection
    -> resolve (v4.2 resolver, unchanged semantics) -> fenced durable publish -> audit + telemetry
"""
from __future__ import annotations

import json
import time
from typing import Any, Mapping

from .admission import AdmissionController, AdmissionPolicy
from .audit import AuditLedger
from .catalogue import CatalogueClient
from .config import validate as validate_config
from .context import IdempotencyCache, RequestContext
from .errors import PlaneError, to_public
from .observability import Health, Metrics, StructuredLogger, TraceContext, Watchdog
from .policy import POLICY_VERSION, Constraints, EntitlementPolicy, merge, select
from .resolver import ResolutionError, _digest, resolve_document
from .store import RevisionStore
from .trust import KeyRing, authenticate
from . import versioning

AUDIENCE = "pln-02"


class ApplicationPlaneService:
    def __init__(self, *, ring: KeyRing, catalogue: CatalogueClient, store: RevisionStore, audit: AuditLedger,
                 config: Mapping[str, Any] | None = None, holder: str = "pln02-controller") -> None:
        self.config = validate_config(config or {})
        self.config_digest = _digest(self.config)
        self.ring, self.catalogue, self.store, self.audit = ring, catalogue, store, audit
        self.admission = AdmissionController(AdmissionPolicy(**self.config["admission"]))
        self.entitlements = EntitlementPolicy({t: frozenset(c) for t, c in self.config["entitlements"].items()})
        self.idempotency = IdempotencyCache()
        self.metrics = Metrics()
        self.log = StructuredLogger()
        self.watchdog = Watchdog()
        self.health = Health("4.3.0", self.watchdog)
        self.health.register("catalogue", self._catalogue_health)
        self.health.register("store", lambda: ("fail", "disabled") if self.store.status()["disabled"] else ("ok", "writable"))
        self.epoch = self.store.acquire_epoch(holder)

    def _catalogue_health(self) -> tuple[str, str]:
        try:
            snap = self.catalogue.snapshot()
        except PlaneError as exc:
            return "fail", exc.code
        return ("degraded", "offline-cache") if snap.degraded else ("ok", f"generation {snap.generation}")

    # ------------------------------------------------------------------ resolve+publish
    def submit(self, ctx: RequestContext, token: str, application_name: str, raw_document: bytes,
               *, traceparent: str | None = None) -> dict:
        """Public entry point. Returns {"ok": True, ...} or {"ok": False, "error": PK_ERROR/1}."""
        trace = TraceContext.from_header(traceparent).child()
        started = time.perf_counter()
        wd = self.watchdog.start("submit")
        labels = ctx.labels()
        principal_sub = None
        try:
            self.admission.check_payload(len(raw_document))
            principal = authenticate(self.ring, token, audience=AUDIENCE)
            principal_sub = principal.subject
            with self.admission.admit(ctx.tenant):
                request_digest = _digest({"app": application_name, "doc": raw_document.decode("utf-8", "replace")})
                result = self.idempotency.run(ctx, request_digest,
                                              lambda: self._submit(ctx, principal, application_name, raw_document, trace))
            self.metrics.inc("application_revisions_total", labels)
            return {"ok": True, **result}
        except (PlaneError, ResolutionError) as exc:
            self.metrics.inc("resolution_rejections_total", {**labels, "code": exc.code})
            action = {"UNAUTHENTICATED": "authn_failure", "PERMISSION_DENIED": "authz_denied"}.get(exc.code, "resolve")
            self._audit(action, "refused", ctx, principal_sub, reason=exc.code, resource=application_name)
            self.log.log("warn", "submit_refused", code=exc.code, correlation_id=ctx.correlation_id,
                         trace_id=trace.trace_id, **labels)
            return {"ok": False, "error": to_public(exc, correlation_id=ctx.correlation_id)}
        except Exception as exc:  # defect: never leak internals
            self.metrics.inc("resolution_rejections_total", {**labels, "code": "INTERNAL"})
            self.log.log("error", "submit_internal", error_type=type(exc).__name__, correlation_id=ctx.correlation_id)
            return {"ok": False, "error": to_public(exc, correlation_id=ctx.correlation_id)}
        finally:
            self.watchdog.finish(wd)
            self.metrics.observe("resolution_seconds", time.perf_counter() - started, labels)

    def _submit(self, ctx: RequestContext, principal: Any, application_name: str, raw: bytes, trace: TraceContext) -> dict:
        self.store.check_writable(ctx.tenant, ctx.environment)
        ctx.checkpoint()
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise PlaneError("request is not UTF-8 JSON", code="INVALID_APPLICATION", details={"field": "$"}) from None
        if not isinstance(doc, dict):
            raise PlaneError("request must be an object", code="INVALID_APPLICATION", details={"field": "$"})
        app_constraints = doc.pop("constraints", None)
        versioning.check(doc.get("schema"))
        components = doc.get("components") if isinstance(doc.get("components"), list) else []
        self.entitlements.authorize_resolve(principal, ctx.tenant, [c for c in components if isinstance(c, dict)])

        snap = self.catalogue.snapshot()
        ctx.checkpoint()
        cons = self.config["constraints"]
        merged = merge(Constraints.from_doc(cons["platform"]),
                       Constraints.from_doc(cons["tenants"].get(ctx.tenant)),
                       Constraints.from_doc(app_constraints))
        flat, explain = {}, []
        wanted: dict[str, bool] = {}
        for c in components:
            if isinstance(c, dict) and isinstance(c.get("requires"), dict):
                for cap, req in c["requires"].items():
                    wanted[cap] = wanted.get(cap, False) or req is True
        for cap in sorted(wanted):
            cands = snap.doc["providers"].get(cap)
            if not cands:
                continue  # resolver reports UNSATISFIED_CAPABILITY / drops optional
            try:
                pid, record = select(cap, cands, merged)
            except PlaneError as exc:
                if exc.code == "NO_ELIGIBLE_PROVIDER" and not wanted[cap]:
                    explain.append({"capability": cap, "chosen": None, "rejected": exc.details.get("rejected")})
                    continue
                raise
            flat[cap] = pid
            explain.append(record)

        revision = resolve_document(doc, {"schema": "PK_PROVIDER_CATALOGUE/1", "providers": flat})
        ctx.checkpoint()
        provenance = {
            "tenant": ctx.tenant, "environment": ctx.environment, "site": ctx.site,
            "principal": principal.subject, "correlation_id": ctx.correlation_id, "trace_id": trace.trace_id,
            "catalogue_generation": snap.generation, "catalogue_digest": snap.digest, "catalogue_degraded": snap.degraded,
            "config_digest": self.config_digest, "policy_version": POLICY_VERSION,
            "explain": explain,
        }
        pub = self.store.publish(tenant=ctx.tenant, environment=ctx.environment, application=application_name,
                                 revision=revision, epoch=self.epoch, provenance=provenance)
        self._audit("publish", "ok", ctx, principal.subject, resource=f"{application_name}@{pub['revision'][:16]}")
        for cap, pid in flat.items():
            self.metrics.set("provider_bindings", 1, {"provider": pid, **ctx.labels()})
        return {"publication": pub, "revision": revision, "provenance": provenance}

    # ------------------------------------------------------------------ admin controls
    def admin(self, token: str, action: str, target: str = "*") -> dict:
        principal = authenticate(self.ring, token, audience=AUDIENCE)
        self.entitlements.authorize_admin(principal)
        ops = {
            "freeze": lambda: self.store.freeze(target, self.epoch),
            "unfreeze": lambda: self.store.unfreeze(target, self.epoch),
            "disable": lambda: self.store.set_disabled(True, self.epoch),
            "enable": lambda: self.store.set_disabled(False, self.epoch),
            "quarantine": lambda: self.store.quarantine(target, self.epoch),
            "release": lambda: self.store.release(target, self.epoch),
        }
        if action not in ops:
            raise PlaneError("unknown admin action", code="INVALID_APPLICATION", details={"field": "action"})
        ops[action]()
        self.audit.append({"action": action, "outcome": "ok", "actor": principal.subject, "resource": target})
        return self.store.status()

    def _audit(self, action: str, outcome: str, ctx: RequestContext, actor: str | None, **kw: Any) -> None:
        try:
            self.audit.append({"action": action, "outcome": outcome, "actor": actor or "unauthenticated",
                               "tenant": ctx.tenant, "correlation_id": ctx.correlation_id, **kw})
        except Exception:
            self.metrics.inc("audit_write_failures_total")
            raise
