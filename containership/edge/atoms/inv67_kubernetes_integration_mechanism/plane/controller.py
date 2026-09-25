"""Kubernetes controller/reconciler for ``WasmWorkload`` (items 11, 7, 30).

Level-triggered and idempotent. One reconcile pass for a key:

  deletion?  -> cancel downstream (journalled, fenced) -> drop finalizer
  finalizer? -> add it before any side effect
  new generation -> identity -> authorization -> translate -> certify ->
                    artifact verify -> freeze/quarantine -> admission ->
                    journal intent -> place (circuit breaker, fencing,
                    idempotency key = attempt id) -> journal done -> status
  same generation -> observe downstream -> project status (stale -> Unknown)

Every refusal happens before an irreversible side effect and lands in status
as a stable code. Retryable errors requeue with bounded full-jitter backoff;
terminal errors do not retry until the generation changes.
"""
from __future__ import annotations

import heapq
import logging
import random
import threading
import time
from dataclasses import dataclass, field

from .. import translator
from . import compat
from .artifact import verify_image
from .audit import AuditLog
from .authz import CONTROLLER_SA, Policy, Principal, default_policy
from .config import ConfigStore, digest as cfg_digest
from .downstream import envelope
from .identity import IdentityMapper
from .journal import Journal
from .kube import ApiError
from .leader import Elector
from .lifecycle import POD_PHASE, TERMINAL, PlaneError, State, attempt_id, aggregate_units
from .observability import Health, Metrics, Tracer, get_logger, log
from .resilience import Admission, Backoff, CircuitBreaker, Switchboard
from .status import set_condition

FINALIZER = "inv67.linearfinance.org/runtime-cleanup"


@dataclass(order=True)
class _Item:
    due: float
    key: tuple = field(compare=False)


class WorkQueue:
    """Deduplicating delayed queue: a key is queued at most once; the earliest
    due time wins; a key is never processed concurrently."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.heap: list[_Item] = []
        self.due: dict[tuple, float] = {}
        self.processing: set[tuple] = set()
        self.dirty: dict[tuple, float] = {}   # key -> earliest requested delay while processing
        self._lock = threading.Lock()

    def add(self, key, delay=0.0):
        with self._lock:
            t = self.clock() + delay
            if key in self.processing:
                # Keep the *requested delay*: re-adding with delay 0 here once turned
                # every backoff requeue into an immediate hot loop.
                self.dirty[key] = min(delay, self.dirty.get(key, delay))
                return
            if key in self.due and self.due[key] <= t:
                return
            self.due[key] = t
            heapq.heappush(self.heap, _Item(t, key))

    def pop_due(self):
        with self._lock:
            now = self.clock()
            while self.heap and self.heap[0].due <= now:
                it = heapq.heappop(self.heap)
                if self.due.get(it.key) != it.due:
                    continue
                del self.due[it.key]
                self.processing.add(it.key)
                return it.key
            return None

    def done(self, key):
        with self._lock:
            self.processing.discard(key)
            if key in self.dirty:
                delay = self.dirty.pop(key)
                self.due[key] = self.clock() + delay
                heapq.heappush(self.heap, _Item(self.due[key], key))

    def __len__(self):
        return len(self.due)


class Controller:
    def __init__(self, kube, runtime, *, config: ConfigStore, identity: IdentityMapper, elector: Elector,
                 verifier=None, policy: Policy | None = None, journal: Journal | None = None,
                 audit: AuditLog | None = None, clock=time.monotonic, seed: int = 0, logger=None):
        self.kube, self.rt, self.cfgs, self.idm, self.elector = kube, runtime, config, identity, elector
        self.verifier, self.policy = verifier, policy or default_policy()
        self.principal = Principal(CONTROLLER_SA, (), "tokenreview")
        self.journal, self.audit = journal or Journal(), audit or AuditLog()
        self.clock = clock
        c = config.active
        self.backoff = Backoff(c["retry"]["base"], c["retry"]["cap"], c["retry"]["maxAttempts"], random.Random(seed))  # noqa: S311 - jitter
        self.breaker = CircuitBreaker(c["circuit"]["threshold"], c["circuit"]["resetAfter"], clock)
        self.admission = Admission(c["maxInflight"], c["tenantInflight"], c["defaultTenantInflight"],
                                   c["tenantRatePerSec"], c["tenantBurst"], clock)
        self.switch = Switchboard()
        self.queue = WorkQueue(clock)
        self.attempts: dict[tuple, int] = {}
        self.rv = "0"
        self.metrics, self.tracer = Metrics(), Tracer()
        self.health = Health("4.3.0", clock=clock)
        self.health.config_digest = cfg_digest(c)
        self.health.capabilities = sorted(c["certifiedFeatures"])
        self.health.checks["config"] = lambda: bool(self.cfgs.active)
        self.health.checks["breaker"] = lambda: self.breaker.state != CircuitBreaker.OPEN
        self.log = logger or get_logger("inv67.controller")
        self.last_seen_downstream: dict[str, float] = {}
        # Pre-register every counter the alerts/dashboards use: an absent series makes
        # rate()-based alerts silently never fire.
        for name in ("inv67_translated_total", "inv67_status_syncs_total", "inv67_watch_relists_total",
                     "inv67_finalized_total", "inv67_journal_replays_total"):
            self.metrics.inc(name, v=0)
        for reason in ("DownstreamUnavailable", "CircuitOpen", "Overloaded", "QuotaExceeded", "NotLeader", "Frozen", "ApiError"):
            self.metrics.inc("inv67_requeues_total", {"reason": reason}, v=0)
        self.metrics.set("inv67_queue_depth", 0)
        self.metrics.set("inv67_leader", 0)

    # ---------------- event intake ----------------
    def resync(self):
        items, self.rv = self.kube.list()
        for o in items:
            self.queue.add((o["metadata"]["namespace"], o["metadata"]["name"]))

    def pump(self):
        """Pull watch events since the last resourceVersion; relist on 410 Gone."""
        try:
            evs = self.kube.events_since(self.rv)
        except ApiError as e:
            if e.status == 410:
                self.metrics.inc("inv67_watch_relists_total")
                self.resync()
                return
            raise
        for _, o in evs:
            self.rv = max(self.rv, o["metadata"]["resourceVersion"], key=int)
            self.queue.add((o["metadata"]["namespace"], o["metadata"]["name"]))

    def replay_journal(self):
        """Crash recovery: re-drive intents that never recorded ``done``."""
        for e in self.journal.pending():
            if e["op"] == "place":
                self.queue.add(tuple(e["payload"]["key"]))
            elif e["op"] == "cancel":
                self.queue.add(tuple(e["payload"]["key"]))
        self.metrics.inc("inv67_journal_replays_total", v=len(self.journal.pending()))

    # ---------------- main loop ----------------
    MAX_PER_PASS = 10_000

    def run_once(self) -> int:
        """Process every key currently due (bounded per pass). Returns number processed."""
        n = 0
        if not self.elector.try_acquire_or_renew():
            self.metrics.set("inv67_leader", 0)
            self.health.progressed()
            return 0
        self.metrics.set("inv67_leader", 1)
        try:
            self.pump()
        except (ApiError, PlaneError) as e:
            log(self.log, logging.WARNING, "watch pump failed", error=str(e))
        while n < self.MAX_PER_PASS:
            key = self.queue.pop_due()
            if key is None:
                break
            n += 1
            try:
                self.reconcile(*key)
            finally:
                self.queue.done(key)
        self.metrics.set("inv67_queue_depth", len(self.queue))
        self.health.progressed()
        return n

    def _requeue(self, key, err: PlaneError | ApiError):
        a = self.attempts.get(key, 0) + 1
        self.attempts[key] = a
        try:
            d = self.backoff.delay(min(a, self.backoff.max_attempts))
        except PlaneError:
            d = self.backoff.cap
        self.metrics.inc("inv67_requeues_total", {"reason": getattr(err, "reason", "ApiError")})
        self.queue.add(key, d)

    # ---------------- reconcile ----------------
    def reconcile(self, ns: str, name: str):
        key = (ns, name)
        t0 = time.perf_counter()
        with self.tracer.span("reconcile", ns=ns, name=name):
            try:
                if self.elector.token is None or not self.elector.is_leader():
                    raise PlaneError("INV67_NOT_LEADER", "not leader")
                try:
                    obj = self.kube.get(ns, name)
                except ApiError as e:
                    if e.status == 404:
                        self.attempts.pop(key, None)
                        return
                    raise
                if obj["metadata"].get("deletionTimestamp"):
                    self._finalize(obj)
                elif FINALIZER not in obj["metadata"].get("finalizers", []):
                    obj["metadata"].setdefault("finalizers", []).append(FINALIZER)
                    self.kube.update(obj)
                    self.queue.add(key)
                else:
                    self._sync(obj)
                self.attempts.pop(key, None)
            except PlaneError as e:
                if e.retryable:
                    self._requeue(key, e)
                else:
                    raise
            except ApiError as e:
                self._requeue(key, e)
            finally:
                self.metrics.observe("inv67_reconcile_seconds", time.perf_counter() - t0)

    def _finalize(self, obj):
        md = obj["metadata"]
        if FINALIZER in md.get("finalizers", []):
            app_id = obj.get("status", {}).get("appId")
            if app_id:
                jkey = f"{md['uid']}/cancel"
                self.journal.intent(jkey, "cancel", {"key": [md["namespace"], md["name"]], "appId": app_id})
                self.breaker.call(self.rt.cancel, app_id, self.elector.token)
                self.journal.done(jkey, "cancel")
                self.audit.append(self.principal.subject, "runtime.cancel", f"{md['namespace']}/{md['name']}", "ok",
                                  appId=app_id)
            md["finalizers"] = [f for f in md["finalizers"] if f != FINALIZER]
            self.kube.update(obj)
            self.metrics.inc("inv67_finalized_total")

    def _write_status(self, obj, **fields):
        for _ in range(5):
            st = dict(obj.get("status") or {})
            conds = st.get("conditions", [])
            for (t, s, r, m) in fields.pop("_conds", []):
                conds = set_condition(conds, t, s, r, m, obj["metadata"]["generation"])
            st.update(fields)
            st["conditions"] = conds
            obj["status"] = st
            try:
                self.kube.update_status(obj)
                self.metrics.inc("inv67_status_syncs_total")
                return
            except ApiError as e:
                if e.status != 409:
                    raise
                obj = self.kube.get(obj["metadata"]["namespace"], obj["metadata"]["name"])
                fields["_conds"] = []
        raise PlaneError("INV67_CONFLICT", "status write kept conflicting")

    def _refuse(self, obj, err_dict, state: State):
        self._write_status(obj, observedGeneration=obj["metadata"]["generation"], state=state.value,
                           phase=POD_PHASE[state], lastError=err_dict,
                           _conds=[("Accepted", False, err_dict.get("reason", err_dict.get("code")), err_dict["message"]),
                                   ("Ready", False, "Refused", err_dict["message"])])
        self.kube.record_event(obj, "Warning", err_dict.get("reason", "Refused"), err_dict["message"])
        self.metrics.inc("inv67_refused_total", {"reason": err_dict.get("reason", err_dict["code"])})
        self.audit.append(self.principal.subject, "workload.refuse",
                          f"{obj['metadata']['namespace']}/{obj['metadata']['name']}", "refused", code=err_dict["code"])

    def _sync(self, obj):
        md, st = obj["metadata"], obj.get("status") or {}
        gen = md["generation"]
        if st.get("observedGeneration") == gen and st.get("appId") and st.get("state") != State.BLOCKED.value:
            return self._observe(obj)
        if st.get("observedGeneration") == gen and st.get("state") in (State.BLOCKED.value, State.FAILED.value) \
                and st.get("lastError", {}).get("retryable") is False:
            return  # terminal for this generation
        cfg = self.cfgs.active
        # 1. identity + authorization (fail closed)
        try:
            ident = self.idm.map(md["namespace"], md["name"], md["uid"])
            if cfg["watchNamespaces"] and md["namespace"] not in cfg["watchNamespaces"]:
                raise PlaneError("INV67_UNAUTHORIZED", "namespace not in watch scope")
            self.policy.check(self.principal, "update", "wasmworkloads/status", md["namespace"])
        except PlaneError as e:
            return self._refuse(obj, e.to_dict(), State.BLOCKED)
        # 2. translate (the v4.2 strict boundary)
        tmpl = (obj.get("spec") or {}).get("template") or {}
        tmd = tmpl.get("metadata") or {}
        pod = {"apiVersion": "v1", "kind": "Pod",
               "metadata": {"name": md["name"], "namespace": md["namespace"],
                            "labels": tmd.get("labels", {}), "annotations": tmd.get("annotations", {})},
               "spec": tmpl.get("spec")}
        extra = set(tmd) - {"labels", "annotations"}
        try:
            if extra:
                raise translator.Unsupported("template metadata", details=[
                    translator.RefusalDetail(f"spec.template.metadata.{k}", "field is outside the supported translation subset")
                    for k in sorted(extra)])
            req = translator.translate(pod)
        except translator.TranslationError as e:
            d = e.to_dict()
            d.update(reason="UnsupportedField" if isinstance(e, translator.Unsupported) else "InvalidSpec",
                     retryable=False)
            return self._refuse(obj, d, State.BLOCKED)
        self.metrics.inc("inv67_translated_total")
        # 3. compatibility, artifacts, safety switches
        try:
            compat.certify(req, cfg["certifiedFeatures"])
            for u in req["units"]:
                verify_image(u["image"], allowed_registries=cfg["allowedRegistries"],
                             require_digest=cfg["requireImageDigest"], require_signature=cfg["requireSignature"],
                             verifier=self.verifier)
            self.switch.check_launch(f"{md['namespace']}/{md['name']}", md["namespace"])
        except PlaneError as e:
            if e.retryable:          # frozen: hold, don't mark terminal
                self._write_status(obj, state=State.QUEUED.value, phase="Pending", lastError=e.to_dict(),
                                   _conds=[("Progressing", False, e.reason, str(e))])
                raise
            return self._refuse(obj, e.to_dict(), State.BLOCKED)
        # 4. admission + placement
        attempt = st.get("attempt", 0) + 1 if st.get("observedGeneration") == gen else 1
        aid = attempt_id(md["uid"], gen, attempt)
        key_ = [md["namespace"], md["name"]]
        pend = next((e for e in self.journal.pending()
                     if e["op"] == "place" and e["payload"]["key"] == key_ and e["payload"]["gen"] == gen), None)
        if pend:
            aid = pend["payload"]["attemptId"]   # replay with the original idempotency key
        self.admission.acquire(ident.tenant)
        try:
            fence = self.elector.token
            if fence is None:
                raise PlaneError("INV67_NOT_LEADER", "lost leadership before placement")
            env = envelope(req, ident.to_dict(), aid, fence)
            self.journal.intent(aid, "place", {"key": [md["namespace"], md["name"]], "gen": gen, "attemptId": aid})
            app_id = self.breaker.call(self.rt.place, env)
            self.journal.done(aid, "place")
        except PlaneError as e:
            if e.retryable:
                self._write_status(obj, state=State.DEGRADED.value, phase="Unknown", attempt=attempt, lastError=e.to_dict(),
                                   _conds=[("Degraded", True, e.reason, str(e))])
            raise
        finally:
            self.admission.release(ident.tenant)
        self.last_seen_downstream[app_id] = self.clock()
        self.audit.append(self.principal.subject, "runtime.place", f"{md['namespace']}/{md['name']}", "ok",
                          appId=app_id, attemptId=aid, generation=gen)
        self._write_status(obj, observedGeneration=gen, appId=app_id, attempt=attempt, attemptId=aid,
                           state=State.PLACED.value, phase="Pending", lastError=None, identity=ident.to_dict(),
                           _conds=[("Accepted", True, "Translated", "translated and admitted"),
                                   ("Progressing", True, "Placed", "placement accepted by runtime"),
                                   ("Degraded", False, "Healthy", ""),
                                   ("Ready", False, "Starting", "waiting for runtime")])

    def _observe(self, obj):
        st = obj["status"]
        app_id = st["appId"]
        try:
            ob = self.breaker.call(self.rt.observe, app_id)
        except PlaneError as e:
            age = self.clock() - self.last_seen_downstream.get(app_id, self.clock())
            if age > self.cfgs.active["staleObservationSec"] and st.get("state") != State.UNKNOWN.value:
                self._write_status(obj, state=State.UNKNOWN.value, phase="Unknown", lastError=e.to_dict(),
                                   _conds=[("Ready", None, "StaleObservation", f"no runtime observation for {age:.0f}s"),
                                           ("Degraded", True, "DownstreamUnavailable", str(e))])
            raise
        self.last_seen_downstream[app_id] = self.clock()
        if not ob.get("found") or ob.get("key") != st.get("attemptId"):
            # Runtime lost/replaced our placement: re-place under a new attempt.
            self._write_status(obj, state=State.DEGRADED.value, phase="Unknown", appId=None,
                               _conds=[("Degraded", True, "PlacementLost", "runtime has no record of current attempt")])
            self.queue.add((obj["metadata"]["namespace"], obj["metadata"]["name"]))
            return
        new = aggregate_units([State(s) for s in ob["units"].values()])
        if new.value != st.get("state"):
            ready = new is State.RUNNING or new is State.SUCCEEDED
            self._write_status(obj, state=new.value, phase=POD_PHASE[new],
                               _conds=[("Ready", ready, new.value, f"runtime reports {new.value}"),
                                       ("Degraded", False, "Healthy", ""),
                                       ("Progressing", new not in TERMINAL and not ready, new.value, "")])
