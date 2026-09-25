"""INV-64 integration boundary: the authenticated, authorized, bounded submit/validate API.

This is the executable form of the controls the 4.2.0 archive left to "the
calling control plane". One request travels a fixed pipeline; each stage fails
closed with a stable ``PK_APP_ERROR/1`` code, and *no semantic processing
happens before authentication and authorization* (REQ-SEC-1):

    envelope schema -> version negotiation -> authenticate -> tenant bind ->
    authorize -> deadline -> admission -> idempotency -> parse/validate ->
    secret & tenancy checks -> canonicalize -> register -> decision/audit/telemetry

Request ``PK_APP_SUBMIT_REQUEST/1`` and response ``PK_APP_SUBMIT_RESPONSE/1``
are defined in ``schema/`` and INTERFACES.md. Credentials and the TLS channel
binding arrive as transport metadata, never inside the manifest.
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from typing import Callable

from . import __version__
from .audit import AuditLog, AuditUnavailable
from .auth import Authenticator
from .authz import Authorizer
from .errors import Inv64Error, error_envelope, outcome_for
from .explain import DecisionLog
from .manifest import (MAX_MANIFEST_BYTES, DuplicateKeyError, ManifestDepthError, ManifestTooLargeError,
                       ManifestValidationError, canonical, parse_manifest_json, validate_issues)
from .semantics import AdmissionController, Deadline, IdempotencyStore, negotiate
from .telemetry import Metrics, StructuredLog, child_traceparent
from .tenancy import ISOLATION_PROFILE, SharedResources, TenantRegistry, check_manifest_tenancy

REQUEST_FORMAT = "PK_APP_SUBMIT_REQUEST/1"
RESPONSE_FORMAT = "PK_APP_SUBMIT_RESPONSE/1"
STATUS_FORMAT = "PK_APP_STATUS/1"
SPEC_VERSION = "INV64-SPEC/1.0"
CONTRACT_VERSIONS = {"manifest": "PK_APP_MANIFEST/1", "validate": "PK_APP_VALIDATE/1",
                     "canonical": "PK_APP_CANONICAL/1", "error": "PK_APP_ERROR/1",
                     "request": REQUEST_FORMAT, "response": RESPONSE_FORMAT, "status": STATUS_FORMAT,
                     "decision": "PK_APP_DECISION/1", "audit": "PK_APP_AUDIT/1", "telemetry": "PK_APP_TELEMETRY/1"}
OAM_BASELINE = "oam-dev/spec@v0.3.0 (3104d27a0ecb55cac84755950e53371aa3e1d2b2), conceptual profile"
OP_CAPABILITY = {"submit": "app.submit", "validate": "app.validate", "canonicalize": "app.canonicalize"}
MAX_ISSUES_RETURNED = 1_000
_REQ_FIELDS = {"format": str, "version": str, "operation": str, "tenant": str, "environment": str, "site": str,
               "app": str, "manifest_json": str}


_BUILD_DIGEST: str | None = None


def build_digest() -> str:
    """SHA-256 over the package's own .py/.json files (computed once per process)."""
    global _BUILD_DIGEST
    if _BUILD_DIGEST is None:
        import hashlib
        from pathlib import Path
        root = Path(__file__).resolve().parent
        h = hashlib.sha256()
        for p in sorted(root.rglob("*")):
            if p.suffix in (".py", ".json") and "__pycache__" not in p.parts and "evidence" not in p.parts \
                    and "tests" not in p.parts:
                h.update(p.relative_to(root).as_posix().encode() + b"\0" + hashlib.sha256(p.read_bytes()).digest())
        _BUILD_DIGEST = h.hexdigest()
    return _BUILD_DIGEST


class ApplicationModelService:
    def __init__(self, *, authenticator: Authenticator, authorizer: Authorizer, audit: AuditLog,
                 metrics: Metrics | None = None, log: StructuredLog | None = None,
                 decisions: DecisionLog | None = None, admission: AdmissionController | None = None,
                 idempotency: IdempotencyStore | None = None, registry: TenantRegistry | None = None,
                 shared: SharedResources | None = None, config_store=None, clock: Callable[[], float] = time.time,
                 release_id: str = f"inv64-{__version__}"):
        self.authn = authenticator
        self.authz = authorizer
        self.audit = audit
        self.metrics = metrics or Metrics()
        self.log = log or StructuredLog(metrics=self.metrics)
        self.decisions = decisions or DecisionLog(versions={"release": __version__, "spec": SPEC_VERSION},
                                                  lineage={"release_id": release_id})
        self.admission = admission or AdmissionController(metrics=self.metrics)
        self.idem = idempotency or IdempotencyStore(clock=clock)
        self.registry = registry or TenantRegistry()
        self.shared = shared or SharedResources()
        self.config_store = config_store
        self.clock = clock
        self._deps: dict[str, dict] = {}
        self._dep_lock = threading.Lock()
        self.degraded_reasons: set[str] = set()
        self.blocked_reasons: set[str] = set()
        # one audit ledger and one metrics registry for every boundary (MC-18/MC-24 wiring)
        for part in (self.authn, self.authz):
            if getattr(part, "_audit", None) is None:
                part._audit = audit
            if getattr(part, "_metrics", None) is None:
                part._metrics = self.metrics

    # ------------------------------------------------------------------ API
    def handle(self, request: dict, *, token: str | None, source: str = "unknown",
               channel_binding: str | None = None, traceparent: str | None = None,
               cancel=None) -> dict:
        t0 = self.clock()
        cid = str(uuid.uuid4())
        tp_out, trace_id, span_id = child_traceparent(traceparent)
        op = request.get("operation") if isinstance(request, dict) else None
        op = op if op in OP_CAPABILITY else "invalid"
        principal = None
        ctx = {"cid": cid, "trace_id": trace_id, "span_id": span_id, "op": op, "tenant": None}
        try:
            if "emergency.disabled" in self.blocked_reasons:
                raise Inv64Error("service.disabled")
            self._check_envelope(request)
            negotiate([request["version"]])
            principal = self.authn.authenticate(token, source=source, channel_binding=channel_binding,
                                                correlation_id=cid)
            ctx["tenant"] = principal.tenant
            self.authz.require(principal, OP_CAPABILITY[op], tenant=request["tenant"],
                               environment=request["environment"], site=request["site"],
                               resource=f"apps/{request['app']}")
            deadline = Deadline.for_operation(op, request.get("deadline_ms"), clock=self.clock,
                                              inbound_expires_at_ms=request.get("deadline_at_ms"))
            with self.admission.admit(request["tenant"]):
                if op == "submit":
                    raw = request["manifest_json"].encode("utf-8")
                    digest = IdempotencyStore.request_digest(json.dumps(
                        {k: request.get(k) for k in ("operation", "tenant", "environment", "site", "app")},
                        sort_keys=True).encode() + b"\x00" + raw)
                    with self.idem.claim(request["tenant"], request.get("idempotency_key"), digest) as (replayed, h):
                        if replayed:
                            resp = dict(h["response"], replayed=True, correlation_id=cid, traceparent=tp_out)
                            return self._finish(ctx, resp, t0)
                        resp = self._process(request, principal, deadline, cancel, ctx, tp_out)
                        if resp["error"] is None or not resp["error"]["retryable"]:
                            h["response"] = {k: v for k, v in resp.items() if k not in ("correlation_id", "traceparent")}
                        return self._finish(ctx, resp, t0)
                resp = self._process(request, principal, deadline, cancel, ctx, tp_out)
                return self._finish(ctx, resp, t0)
        except Inv64Error as exc:
            return self._finish(ctx, self._error_response(exc.code, cid, tp_out, exc.details), t0)
        except AuditUnavailable:
            return self._finish(ctx, self._error_response("internal", cid, tp_out, {"reason": "audit unavailable"}), t0)
        except Exception as exc:  # defect: never leak internals, never report success
            self.log.emit("ERROR", op, outcome="defect", code="internal", correlation_id=cid,
                          detail={"exception": type(exc).__name__})
            return self._finish(ctx, self._error_response("internal", cid, tp_out, {}), t0)

    # -------------------------------------------------------------- stages
    @staticmethod
    def _check_envelope(req) -> None:
        if not isinstance(req, dict) or req.get("format") != REQUEST_FORMAT:
            raise Inv64Error("request.invalid", details={"field": "format"})
        for k, t in _REQ_FIELDS.items():
            if not isinstance(req.get(k), t):
                raise Inv64Error("request.invalid", details={"field": k})
        for k in ("tenant", "environment", "site", "app"):
            v = req[k]
            if not (0 < len(v) <= 128) or not all(c.isalnum() or c in "._-" for c in v):
                raise Inv64Error("request.invalid", details={"field": k})
        if req["operation"] not in OP_CAPABILITY:
            raise Inv64Error("request.invalid", details={"field": "operation"})
        allowed = set(_REQ_FIELDS) | {"idempotency_key", "deadline_ms", "deadline_at_ms"}
        unknown = set(req) - allowed
        if unknown:  # unknown request fields are refused, not ignored (no parser differential)
            raise Inv64Error("request.invalid", details={"unknown_fields": sorted(unknown)[:16]})
        if len(req["manifest_json"].encode("utf-8")) > MAX_MANIFEST_BYTES:
            raise Inv64Error("manifest.too_large")

    def _process(self, req, principal, deadline: Deadline, cancel, ctx, tp_out) -> dict:
        cid = ctx["cid"]
        if cancel:
            cancel.check()
        deadline.check()
        raw = req["manifest_json"]
        self.metrics.inc("inv64_bytes_decoded_total", len(raw.encode("utf-8")), operation=req["operation"])
        try:
            manifest = parse_manifest_json(raw)
            issues = []
        except ManifestValidationError as exc:
            manifest, issues = None, list(exc.issues)
        except DuplicateKeyError:
            raise Inv64Error("manifest.duplicate_key")
        except ManifestTooLargeError:
            raise Inv64Error("manifest.too_large")
        except ManifestDepthError:
            raise Inv64Error("manifest.too_deep")
        except (ValueError, UnicodeError):
            raise Inv64Error("manifest.parse")
        deadline.check()
        if manifest is not None:
            check_manifest_tenancy(manifest, req["tenant"], self.shared)
        issue_dicts = [{"code": i.code, "path": i.path, "message": i.message} for i in issues]
        issue_dicts.sort(key=lambda d: (d["path"], d["code"]))
        result = {"valid": not issues, "issue_count": len(issue_dicts),
                  "issues": issue_dicts[:MAX_ISSUES_RETURNED], "truncated": len(issue_dicts) > MAX_ISSUES_RETURNED,
                  "canonical": None}
        if issues:
            codes = {i["code"] for i in issue_dicts}
            self.decisions.record("validation", "rejected", codes=codes, tenant=req["tenant"], correlation_id=cid)
            self.audit.append("app." + req["operation"], actor=principal.subject, tenant=req["tenant"],
                              outcome="rejected", resource=f"apps/{req['app']}", reason="manifest.invalid",
                              correlation_id=cid, issue_codes=sorted(codes))
            err = error_envelope("manifest.invalid", cid, {"issue_count": len(issue_dicts)})
            return self._response(cid, tp_out, "rejected_before_activation", result, err)
        digest = canonical(manifest)
        result["canonical"] = {"form": "PK_APP_CANONICAL/1", "algorithm": "sha256", "digest": digest,
                               "precondition": "validated"}
        if req["operation"] == "submit":
            deadline.check()
            # audit first (fail closed): nothing becomes registered without its audit record
            self.audit.append("app.submit", actor=principal.subject, tenant=req["tenant"], outcome="accepted",
                              resource=f"apps/{req['app']}", correlation_id=cid, digest=digest,
                              fail_closed=True)
            try:
                self.registry.put(req["tenant"], req["environment"], req["app"],
                                  {"digest": digest, "actor": principal.subject, "ts": self.clock()})
            except Inv64Error as exc:
                self.audit.append("app.submit", actor=principal.subject, tenant=req["tenant"], outcome="reverted",
                                  resource=f"apps/{req['app']}", correlation_id=cid, reason=exc.code)
                raise
        self.decisions.record(req["operation"], "accepted", tenant=req["tenant"], correlation_id=cid,
                              inputs={"manifest_digest": digest},
                              providers=[p.get("name") for p in manifest.get("providers", [])])
        return self._response(cid, tp_out, "success", result, None)

    def _response(self, cid, tp_out, outcome, result, error) -> dict:
        return {"format": RESPONSE_FORMAT, "correlation_id": cid, "traceparent": tp_out, "outcome": outcome,
                "result": result, "error": error, "replayed": False}

    def _error_response(self, code, cid, tp_out, details) -> dict:
        return self._response(cid, tp_out, outcome_for(code), None, error_envelope(code, cid, details))

    def _finish(self, ctx, resp: dict, t0: float) -> dict:
        op = ctx["op"]
        code = resp["error"]["code"] if resp.get("error") else None
        dur = (self.clock() - t0) * 1000
        self.metrics.inc("inv64_requests_total", operation=op, outcome=resp["outcome"])
        self.metrics.observe("inv64_latency_ms", dur, operation=op)
        if code:
            self.metrics.inc("inv64_rejections_total", operation=op, code=code)
            if code == "deadline.exceeded":
                self.metrics.inc("inv64_timeouts_total", operation=op)
            if code == "request.cancelled":
                self.metrics.inc("inv64_cancellations_total", operation=op)
            if not code.startswith(("manifest", "request")) and code != "internal" and not resp.get("result"):
                self.decisions.record("boundary", "rejected", codes=[code], tenant=ctx["tenant"],
                                      correlation_id=ctx["cid"])
        self.log.emit("INFO" if not code else "WARN", op, outcome=resp["outcome"], code=code,
                      tenant=ctx["tenant"], trace_id=ctx["trace_id"], span_id=ctx["span_id"],
                      correlation_id=ctx["cid"], duration_ms=round(dur, 3))
        return resp

    # ----------------------------------------------------- emergency disable
    def emergency_disable(self, *, actor: str, reason: str) -> None:
        """Refuse every request (``service.disabled``) until re-enabled; audited fail-closed."""
        self.audit.append("service.emergency_disable", actor=actor, outcome="disabled", reason=reason, fail_closed=True)
        self.blocked_reasons.add("emergency.disabled")

    def emergency_enable(self, *, actor: str, reason: str) -> None:
        self.audit.append("service.emergency_enable", actor=actor, outcome="enabled", reason=reason, fail_closed=True)
        self.blocked_reasons.discard("emergency.disabled")

    # --------------------------------------------------------------- status
    def register_dependency(self, name: str, probe: Callable[[], bool], *, required: bool = True,
                            ttl_s: float = 5.0) -> None:
        with self._dep_lock:
            self._deps[name] = {"probe": probe, "required": required, "ttl": ttl_s, "state": "unknown",
                                "checked": None, "last_success": None, "last_failure": None}

    def _eval_dep(self, name: str, d: dict) -> None:
        now = self.clock()
        if d["checked"] is not None and now - d["checked"] < d["ttl"]:
            return  # bounded evaluation: cached result, no dependency storm
        try:
            ok = bool(d["probe"]())
        except Exception:
            ok = False
        d["checked"] = now
        if ok:
            d["state"], d["last_success"] = "healthy", now
        else:
            d["state"], d["last_failure"] = "unhealthy", now
            self.metrics.inc("inv64_dependency_failures_total", dependency=name)

    def status(self, *, include_detail: bool = True, viewer=None) -> dict:
        """Status document. ``viewer`` (a Principal) must hold ``status.inspect`` for the full
        detail; without it (or when denied) only live/ready/state and reason codes are returned."""
        if viewer is not None:
            d = self.authz.decide(viewer, "status.inspect", tenant=viewer.tenant, environment="*", site="*",
                                  resource="status")
            include_detail = include_detail and d.allowed
        reasons: list[dict] = []
        deps = {}
        with self._dep_lock:
            for name, d in self._deps.items():
                self._eval_dep(name, d)
                stale = d["checked"] is not None and self.clock() - d["checked"] > 10 * d["ttl"]
                state = "stale" if stale else d["state"]
                deps[name] = {"state": state, "required": d["required"], "last_success": d["last_success"],
                              "last_failure": d["last_failure"]}
                if state != "healthy":
                    reasons.append({"code": f"dependency.{state}", "dependency": name,
                                    "severity": "blocked" if d["required"] else "degraded",
                                    "runbook": "ops/RUNBOOK.md#dependency-outage"})
        if self.authz.policy is None:
            reasons.append({"code": "policy.missing", "severity": "blocked", "runbook": "ops/RUNBOOK.md#policy"})
        cfg = self.config_store.status() if self.config_store is not None else None
        if cfg is not None:
            if cfg["pending"]:
                reasons.append({"code": "config.activation_in_progress", "severity": "degraded",
                                "runbook": "ops/RUNBOOK.md#activation"})
            if cfg["active"] is None:
                reasons.append({"code": "config.none_active", "severity": "blocked",
                                "runbook": "ops/RUNBOOK.md#activation"})
        for r in sorted(self.degraded_reasons):
            reasons.append({"code": r, "severity": "degraded", "runbook": "ops/RUNBOOK.md#degraded"})
        for r in sorted(self.blocked_reasons):
            reasons.append({"code": r, "severity": "blocked", "runbook": "ops/RUNBOOK.md#blocked"})
        if getattr(self.audit, "dropped", 0):
            reasons.append({"code": "audit.events_dropped", "severity": "degraded", "runbook": "ops/INCIDENT_RESPONSE.md#audit"})
        blocked = any(r["severity"] == "blocked" for r in reasons)
        degraded = any(r["severity"] == "degraded" for r in reasons)
        pol = self.authz.policy
        if not include_detail:
            return {"format": STATUS_FORMAT, "live": True, "ready": not blocked,
                    "state": "blocked" if blocked else "degraded" if degraded else "ready",
                    "reasons": [{"code": r["code"], "severity": r["severity"], "runbook": r["runbook"]} for r in reasons],
                    "versions": {"component": __version__}, "capabilities": sorted(OP_CAPABILITY),
                    "isolation_profile": ISOLATION_PROFILE, "dependencies": {}}
        out = {
            "format": STATUS_FORMAT, "live": True, "ready": not blocked,
            "state": "blocked" if blocked else "degraded" if degraded else "ready",
            "reasons": reasons,
            "versions": {"component": __version__, "build_digest": build_digest(), "spec": SPEC_VERSION,
                         "contracts": CONTRACT_VERSIONS,
                         "oam_baseline": OAM_BASELINE,
                         "policy": pol.version if pol else None, "policy_digest": pol.digest if pol else None},
            "capabilities": sorted(OP_CAPABILITY), "isolation_profile": ISOLATION_PROFILE,
            "config": cfg,
            "dependencies": deps,
            "inflight": self.admission.inflight,
        }
        return out
