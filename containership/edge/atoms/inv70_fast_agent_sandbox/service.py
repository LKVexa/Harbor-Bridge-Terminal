"""INV-70 production entry point: the governed PK_FASTBOX_RUN handler.

Order of controls for one request (each step is a lifecycle transition, C015):

  version negotiation (C027) -> mode gate (C056) -> authenticate (C023)
  -> idempotency / duplicate check (C025, C058) -> admission + breaker (C054)
  -> program validation + capability intersection (C019 security first)
  -> isolated execution with wall-clock pre-emption (C025, C031)
  -> result mapping to stable reason codes -> audit (C049), metrics/logs/trace (C072-C074)
  -> explain record (C077) linked to release lineage + config digest (C078)
"""
from __future__ import annotations

import json
import os
import time

from . import __version__
from .config import ConfigStore
from .executor import InlineExecutor, ProcessExecutor, WasmBackend
from .resilience import (Admission, CircuitBreaker, DEGRADED_RULES, IdempotencyCache, Mode, derive_mode)
from .runtime import validate_program
from .security import (ArtifactPolicy, AuditLog, AuthError, Authenticator, Clock, TrustStore, canonical,
                       verify_artifact)
from .semantics import Lifecycle, State, VersionError, downgrade_result, negotiate
from .telemetry import DiagnosticChannel, Metrics, StructuredLog, TraceContext, tenant_pseudonym

# Stable PK_FASTBOX_RESULT reason codes (C031 trap mapping; C080 classification).
REASON_CODES = {
    "out of fuel": ("FB-R001", "guest"), "out of memory": ("FB-R002", "guest"),
    "value too large": ("FB-R003", "guest"), "stack underflow": ("FB-R004", "guest"),
    "type error": ("FB-R005", "guest"), "arithmetic error": ("FB-R006", "guest"),
    "invalid instruction": ("FB-R010", "request"), "invalid value": ("FB-R011", "request"),
    "invalid jump target": ("FB-R012", "request"), "invalid capability": ("FB-R013", "request"),
    "invalid program": ("FB-R014", "request"), "program too large": ("FB-R015", "request"),
    "invalid module": ("FB-R016", "request"),
    "capability denied": ("FB-S001", "security"), "capability unbound": ("FB-S002", "config"),
    "capability invalid": ("FB-S003", "config"), "unauthenticated": ("FB-S010", "security"),
    "token expired": ("FB-S011", "security"), "token replayed": ("FB-S012", "security"),
    "wrong audience": ("FB-S013", "security"), "unknown or revoked key": ("FB-S014", "security"),
    "key purpose mismatch": ("FB-S015", "security"), "key expired": ("FB-S016", "security"),
    "artifact unsigned": ("FB-S030", "security"), "artifact signature invalid": ("FB-S031", "security"),
    "artifact digest mismatch": ("FB-S032", "security"), "artifact denied": ("FB-S033", "security"),
    "artifact version not approved": ("FB-S034", "security"), "artifact provenance invalid": ("FB-S035", "security"),
    "artifact sbom missing": ("FB-S036", "security"),
    "trust unavailable": ("FB-S020", "dependency"), "time unavailable": ("FB-S021", "dependency"),
    "audit unavailable": ("FB-S022", "dependency"),
    "host error": ("FB-H001", "host"), "host lookup error": ("FB-H002", "host"),
    "host call timeout": ("FB-H003", "host"), "host call budget exceeded": ("FB-H004", "host"),
    "deadline exceeded": ("FB-T001", "timeout"), "cancelled": ("FB-T002", "caller"),
    "overloaded": ("FB-C001", "capacity"), "circuit open": ("FB-C002", "capacity"),
    "halted": ("FB-C003", "degraded"), "draining": ("FB-C004", "degraded"),
    "idempotency conflict": ("FB-D001", "request"), "duplicate in flight": ("FB-D002", "request"),
    "unsupported version": ("FB-V001", "request"),
    "worker crashed": ("FB-I001", "infrastructure"), "backend unavailable": ("FB-I002", "infrastructure"),
    "pc out of range": ("FB-I003", "infrastructure"),
}


def reason_code(reason: str) -> tuple[str, str]:
    base = reason.split(":")[0].strip()
    return REASON_CODES.get(base, ("FB-X999", "unclassified"))


_TERMINAL_FOR_CLASS = {"timeout": State.TIMED_OUT, "caller": State.CANCELLED, "infrastructure": State.FAILED}

RELEASE_LINEAGE = {"component": "INV-70", "version": __version__,
                   "source_revision": os.environ.get("INV70_SOURCE_REVISION", "unrecorded")}


class Sandbox:
    def __init__(self, *, environment: str = "prod", trust: TrustStore, clock: Clock | None = None,
                 audit_key: bytes, audit_sink=None, log_sink=None, site: str = "local"):
        self.clock = clock or Clock()
        self.trust = trust
        self.audit = AuditLog(audit_key, sink=audit_sink)
        self.config = ConfigStore(environment, audit=self.audit)
        cfg = self.config.active
        self.auth = Authenticator(trust, self.clock)
        self.admission = Admission(cfg["max_concurrent"], cfg["rate_per_s"], max(1, cfg["rate_per_s"] // 5),
                                   cfg["per_tenant_concurrent"])
        self.breaker = CircuitBreaker()
        self.idem = IdempotencyCache()
        self.metrics = Metrics()
        self.log = StructuredLog(__version__, sink=log_sink)
        self.diag = DiagnosticChannel()
        self.site = site
        self.control_plane_ok = True
        self.draining = False
        self.explain_index: dict[str, dict] = {}
        self._executors = {"process": ProcessExecutor(warm=cfg["warm_workers"] if cfg["isolation"] == "process" else 0), "inline-dev": InlineExecutor()}
        self.wasm = WasmBackend()
        self.host_registry: dict = {}
        self.artifact_policy = ArtifactPolicy()

    # --------------------------------------------------------------- health / mode
    def mode(self) -> Mode:
        overload = self.admission.shed > 0 and self.breaker.state != "closed"
        return derive_mode(trust_ok=self.trust.available, time_ok=self.clock.healthy,
                           audit_ok=self.audit.write_failures == 0, control_plane_ok=self.control_plane_ok,
                           overload=overload, draining=self.draining)

    def health(self) -> dict:
        m = self.mode()
        return {"mode": m.value, "ready": DEGRADED_RULES[m]["admit"], "breaker": self.breaker.state,
                "config_digest": self.config.active_digest, "backend": self.config.active["backend"],
                "wasm_available": self.wasm.available, "lineage": RELEASE_LINEAGE}

    # --------------------------------------------------------------- main path
    def handle(self, request: dict, *, traceparent: str | None = None, cancel=None) -> dict:
        t0 = time.perf_counter()
        trace = TraceContext.from_header(traceparent)
        run_id = os.urandom(8).hex()
        life = Lifecycle(run_id)
        ctx = {"run_id": run_id, "trace": trace, "life": life, "tenant": None, "notes": [],
               "version": 2, "config_digest": self.config.active_digest}
        return self._handle(request, ctx, cancel, t0)

    def _finish(self, ctx, *, status, value=None, reason=None, fuel=0, t0, cache=None):
        life = ctx["life"]
        code, klass = ("FB-OK", "ok") if status == "ok" else reason_code(reason)
        target = State.SUCCEEDED if status == "ok" else (
            State.TRAPPED if life.state == State.RUNNING and klass in ("guest", "security", "host", "config")
            else _TERMINAL_FOR_CLASS.get(klass, State.REJECTED))
        if not life.terminal:
            if target in (State.SUCCEEDED, State.TRAPPED) and life.state != State.RUNNING:
                target = State.REJECTED
            life.to(target)
        elapsed_us = int((time.perf_counter() - t0) * 1e6)
        result = {"run_id": ctx["run_id"], "status": status, "value": value, "reason": reason,
                  "reason_code": code, "class": klass, "fuel": fuel, "state": life.state.value}
        tenant = ctx["tenant"] or "anonymous"
        self.metrics.inc("runs", status=status)
        if status != "ok":
            self.metrics.inc("terminations", reason=code)
        self.metrics.observe("fuel_used", max(0, fuel))
        self.metrics.observe("latency_us", elapsed_us, phase="total")
        self.log.emit("info" if status == "ok" else "warn", "run.finished", run_id=ctx["run_id"],
                      trace_id=ctx["trace"].trace_id, tenant=tenant_pseudonym(tenant), reason_code=code,
                      state=life.state.value, fuel=fuel, latency_us=elapsed_us)
        try:
            self.audit.append("run.finished", run_id=ctx["run_id"], tenant=tenant_pseudonym(tenant),
                              reason_code=code, state=life.state.value, config_digest=ctx["config_digest"])
        except AuthError:
            # A successful result is never released unaudited; a rejection stays a
            # rejection (its own reason) but is flagged.
            if status == "ok":
                result = {**result, "status": "error", "value": None, "reason": "audit unavailable",
                          "reason_code": REASON_CODES["audit unavailable"][0], "class": "dependency"}
            result["audit_failed"] = True
        self.explain_index[ctx["run_id"]] = {
            "run_id": ctx["run_id"], "trace_id": ctx["trace"].trace_id, "states": [s.value for s in life.history],
            "reason": reason, "reason_code": code, "class": klass, "notes": ctx["notes"],
            "config_digest": ctx["config_digest"], "lineage": RELEASE_LINEAGE, "site": self.site,
            "mode": self.mode().value, "elapsed_us": elapsed_us}
        if len(self.explain_index) > 10_000:
            self.explain_index.pop(next(iter(self.explain_index)))
        self.diag.record(tenant, run_id=ctx["run_id"], reason_code=code, fuel=fuel)
        if cache is not None:
            self.idem.finish(*cache, result, cacheable=klass in ("ok", "guest", "request", "security", "host"))
        return downgrade_result(result, ctx["version"])

    def _handle(self, req, ctx, cancel, t0):
        life = ctx["life"]
        if not isinstance(req, dict):
            return self._finish(ctx, status="error", reason="invalid program", t0=t0)
        try:
            ctx["version"] = negotiate("PK_FASTBOX_RUN", req.get("versions", [1]))
            negotiate("PK_FASTBOX_RESULT", req.get("result_versions", [ctx["version"]]))
        except VersionError:
            ctx["version"] = 2
            return self._finish(ctx, status="error", reason="unsupported version", t0=t0)
        mode = self.mode()
        rules = DEGRADED_RULES[mode]
        if not rules["admit"]:
            return self._finish(ctx, status="error", reason="halted" if mode == Mode.HALT else "draining", t0=t0)
        try:
            principal = self.auth.authenticate(req.get("token"))
        except AuthError as e:
            return self._finish(ctx, status="error", reason=e.code, t0=t0)
        ctx["tenant"] = principal.tenant
        life.to(State.AUTHENTICATED)

        cache = None
        key = req.get("idempotency_key")
        if key is not None:
            if type(key) is not str or not 1 <= len(key) <= 128:
                return self._finish(ctx, status="error", reason="invalid program", t0=t0)
            fp = IdempotencyCache.fingerprint(canonical([principal.tenant, repr(req.get("program")),
                                                          sorted(req.get("caps", []))]))
            scoped = f"{principal.tenant}:{key}"
            state, prior = self.idem.begin(scoped, fp)
            if state == "replay":
                ctx["notes"].append("idempotent replay")
                self.metrics.inc("idempotent_replays")
                return downgrade_result({**prior, "replayed": True}, ctx["version"])
            if state == "conflict":
                return self._finish(ctx, status="error", reason="idempotency conflict", t0=t0)
            if state == "inflight":
                return self._finish(ctx, status="error", reason="duplicate in flight", t0=t0)
            cache = (scoped, fp)

        if not self.breaker.allow():
            return self._finish(ctx, status="error", reason="circuit open", t0=t0, cache=cache)
        shed = self.admission.try_acquire(principal.tenant)
        if shed:
            return self._finish(ctx, status="error", reason=shed, t0=t0, cache=cache)
        try:
            life.to(State.ADMITTED)
            cfg = self.config.active
            try:
                program = None if cfg["backend"] == "wasm" else validate_program(req.get("program"),
                                           max_program_instructions=cfg["max_program_instructions"])
            except ValueError as e:
                return self._finish(ctx, status="error", reason=str(e), t0=t0, cache=cache)
            life.to(State.VALIDATED)
            requested = req.get("caps", [])
            if type(requested) not in (list, tuple) or not all(type(c) is str for c in requested):
                return self._finish(ctx, status="error", reason="invalid capability", t0=t0, cache=cache)
            # C019: security (token grant) wins over the caller's request.
            granted = frozenset(requested) & principal.capabilities
            for c in set(requested) - granted:
                ctx["notes"].append(f"capability {c} requested but not granted by token (security precedence)")
            if not rules["host_calls"]:
                granted = frozenset()
                ctx["notes"].append(f"host calls disabled in mode {mode.value}")
            scale = rules["budget_scale"]
            limits = {"fuel": max(1, int(cfg["fuel"] * scale)), "max_stack": cfg["max_stack"],
                      "max_memory_bytes": cfg["max_memory_bytes"], "max_value_bytes": cfg["max_value_bytes"],
                      "max_program_instructions": cfg["max_program_instructions"]}
            req_fuel = req.get("fuel")
            if type(req_fuel) is int and 0 < req_fuel < limits["fuel"]:
                limits["fuel"] = req_fuel   # callers may only tighten (C019 resource limits)
            if cancel is not None and cancel.cancelled:
                return self._finish(ctx, status="error", reason="cancelled", t0=t0, cache=cache)
            if cfg["backend"] == "wasm":
                # C031: production Wasm profile. Fails closed if the pinned engine is absent.
                execu, program = self.wasm, req.get("module", b"")
                if type(program) is not bytes:
                    return self._finish(ctx, status="error", reason="invalid module", t0=t0, cache=cache)
                # C045: digest, signature, provenance, SBOM and approved version before compilation.
                try:
                    m = verify_artifact(self.trust, self.clock, self.artifact_policy, req.get("manifest"), program)
                except AuthError as e:
                    return self._finish(ctx, status="error", reason=e.code, t0=t0, cache=cache)
                ctx["notes"].append(f"module {m['name']}@{m['version']} {m['digest']}")
            else:
                execu = self._executors[cfg["isolation"]]
            life.to(State.RUNNING)
            out = execu.execute(program, limits=limits, caps=granted, host=self.host_bindings(principal),
                                wall_clock_s=cfg["wall_clock_ms"] / 1000,
                                host_call_timeout_s=cfg["host_call_timeout_ms"] / 1000, cancel=cancel)
            infra = "trap" in out and reason_code(out["trap"])[1] == "infrastructure"
            self.breaker.record(not infra)
            if "trap" in out:
                return self._finish(ctx, status="trap", reason=out["trap"], fuel=out.get("fuel", 0), t0=t0, cache=cache)
            return self._finish(ctx, status="ok", value=out["ok"], fuel=out["fuel"], t0=t0, cache=cache)
        finally:
            self.admission.release(principal.tenant)

    # --------------------------------------------------------------- host capabilities
    def host_bindings(self, principal) -> dict:
        """Only capabilities registered by the embedding layer are bindable; there is
        no dynamic lookup into arbitrary Python objects."""
        return dict(self.host_registry)

    def register_capability(self, name: str, fn) -> None:
        if not callable(fn):
            raise ValueError("capability must be callable")
        self.host_registry = {**self.host_registry, name: fn}
        self.audit.append("capability.registered", name=name)

    # --------------------------------------------------------------- C077 explain
    def explain(self, run_id: str) -> str:
        e = self.explain_index.get(run_id)
        if e is None:
            return f"run {run_id}: no record (expired from the explain window or never seen)"
        lines = [f"Run {e['run_id']}  trace {e['trace_id']}",
                 f"  path:    {' -> '.join(e['states'])}",
                 f"  outcome: {e['reason_code']} ({e['class']})" + (f" - {e['reason']}" if e['reason'] else ""),
                 f"  mode:    {e['mode']}   site: {e['site']}   elapsed: {e['elapsed_us']} us",
                 f"  config:  {e['config_digest']}",
                 f"  release: INV-70 {e['lineage']['version']} @ {e['lineage']['source_revision']}"]
        for n in e["notes"]:
            lines.append(f"  note:    {n}")
        lines.append("  next:    " + NEXT_STEP.get(e["class"], "see RUNBOOK.md#triage"))
        return "\n".join(lines)

    def close(self):
        for e in self._executors.values():
            e.close()


NEXT_STEP = {
    "ok": "none",
    "guest": "guest exceeded or misused its budget; raise limits via config overlay only with owner approval",
    "request": "fix the caller's program/request; not retryable",
    "security": "inspect audit log for this run_id; do not retry without a valid grant",
    "config": "capability granted but not bound; check register_capability in the embedding layer",
    "host": "host capability failed or timed out; check the capability owner's service",
    "timeout": "run hit its wall-clock deadline; check guest loop or host latency",
    "capacity": "shed by admission/breaker; retry with backoff (RetryPolicy)",
    "degraded": "sandbox is in a degraded mode; see RUNBOOK.md#degraded-modes",
    "dependency": "trust/time/audit dependency down; sandbox is fail-closed; page on-call",
    "infrastructure": "worker/backend failure; breaker records it; see RUNBOOK.md#worker-crash",
}


def dumps_result(result: dict) -> str:
    return json.dumps(result, sort_keys=True, default=str)
