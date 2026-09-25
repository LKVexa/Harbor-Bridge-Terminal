"""PLN-04 execution-plane admission controller (MC-005, MC-029, MC-037).

Order of checks — every one happens *before* any VMM side effect:

1. schema validation of ``PK_MICROVM_ADMISSION/1``;
2. authentication + capability ``microvm:create`` for the request tenant;
3. operator controls (freeze / quarantine / degraded mode);
4. idempotency: a known operation key returns its recorded result, a key
   reused with a different request is rejected;
5. device model + host readiness + artifact approval (``readiness`` hook);
6. quotas: fleet instance cap, per-tenant cap, vCPU/memory headroom;
7. bounded queueing with per-tenant fairness and deadlines; overload is
   rejected with ``OVERLOADED`` (retryable) instead of unbounded growth.
"""
from __future__ import annotations

import collections
import threading
import time
from dataclasses import dataclass
from typing import Callable

from ..errors import Inv24Error
from ..observability.explain import DecisionRecord
from ..resilience.controls import ControlPlane
from ..resilience.lease import OperationJournal, request_digest
from ..runtime import MINIMAL_DEVICE_MODEL
from ..schemas import validate
from ..security.identity import TokenAuthority


@dataclass(frozen=True, slots=True)
class Capacity:
    max_instances: int
    max_instances_per_tenant: int
    vcpus_total: int
    memory_mib_total: int
    queue_depth: int
    per_tenant_queue_depth: int


class AdmissionController:
    def __init__(self, *, authority: TokenAuthority, journal: OperationJournal, controls: ControlPlane,
                 capacity: Capacity, launcher: Callable[[dict], dict],
                 readiness: Callable[[], None] = lambda: None, node: str = "node-0",
                 permitted_devices: frozenset[str] = MINIMAL_DEVICE_MODEL,
                 release: dict | None = None, policy: dict | None = None,
                 on_decision: Callable[[DecisionRecord], None] | None = None,
                 clock=time.monotonic) -> None:
        if not permitted_devices <= MINIMAL_DEVICE_MODEL:
            raise Inv24Error("DEVICE_OUTSIDE_MODEL", "permitted devices exceed the minimal model")
        self.authority, self.journal, self.controls, self.capacity = authority, journal, controls, capacity
        self.launcher, self.readiness, self.node, self.permitted = launcher, readiness, node, permitted_devices
        self.release, self.policy = release or {}, policy or {}
        self.on_decision = on_decision or (lambda d: None)
        self.clock = clock
        self._lock = threading.Condition()
        self._running: dict[str, dict] = {}                       # instance -> request
        self._queues: dict[str, collections.deque] = collections.defaultdict(collections.deque)
        self._rr: collections.deque[str] = collections.deque()    # tenant round-robin
        self._queued = 0
        self._inflight = 0

    # -- accounting ------------------------------------------------------
    def _usage(self, tenant: str | None = None) -> tuple[int, int, int]:
        reqs = [r for r in self._running.values() if tenant is None or r["tenant"] == tenant]
        return len(reqs), sum(r["vcpus"] for r in reqs), sum(r["memory_mib"] for r in reqs)

    def release_instance(self, instance: str) -> None:
        with self._lock:
            self._running.pop(instance, None)
            self._lock.notify_all()

    def _decide(self, req: dict, outcome: str, code: str | None, reasons: list[str]) -> None:
        self.on_decision(DecisionRecord("admission", outcome, code, reasons,
                                        {k: req.get(k) for k in ("operation_key", "tenant", "workload", "vcpus", "memory_mib", "devices", "environment", "site")},
                                        self.policy, self.release, {"node": self.node, "site": req.get("site"), "environment": req.get("environment")}))

    # -- public API ------------------------------------------------------
    def admit(self, req: dict) -> dict:
        try:
            result = self._admit(req)
        except Inv24Error as exc:
            self._decide(req if isinstance(req, dict) else {}, "rejected", exc.code, [str(exc)])
            raise
        self._decide(req, "accepted", None, ["all admission checks passed"])
        return result

    def _admit(self, req: dict) -> dict:
        validate(req, "PK_MICROVM_ADMISSION/1")
        principal = self.authority.verify(req["capability_token"])
        principal.require("microvm:create", tenant=req["tenant"])
        instance = f"{req['workload']}"
        self.controls.check_admission(tenant=req["tenant"], node=self.node, instance=instance)
        digest = request_digest(req)
        prior = self.journal.lookup(req["operation_key"], digest)
        if prior is not None and prior["state"] == "done":
            return {**prior["result"], "idempotent_replay": True}
        if prior is not None and prior["state"] == "pending":
            raise Inv24Error("LEASE_HELD", "operation pending; awaiting completion or reconciliation")
        outside = set(req["devices"]) - self.permitted
        if outside:
            raise Inv24Error("DEVICE_OUTSIDE_MODEL", f"devices not permitted here: {sorted(outside)}")
        self.readiness()
        deadline = self.clock() + req["deadline_ms"] / 1000
        self._enqueue_and_wait(req, deadline)
        try:
            with self._lock:
                self._check_quota(req)
                self._running[instance] = req   # reserve before side effect
            self.journal.record(req["operation_key"], digest, "pending", {"instance": instance})
            if self.clock() > deadline:
                raise Inv24Error("TIMEOUT", "deadline elapsed before launch")
            try:
                result = self.launcher(req)
            except BaseException:
                self.release_instance(instance)
                self.journal.record(req["operation_key"], digest, "failed", {"instance": instance})
                raise
            self.journal.record(req["operation_key"], digest, "done", result)
            return result
        finally:
            with self._lock:
                self._inflight -= 1
                self._lock.notify_all()

    def _check_quota(self, req: dict) -> None:
        c = self.capacity
        n, cpu, mem = self._usage()
        tn, _, _ = self._usage(req["tenant"])
        if req["workload"] in self._running:
            raise Inv24Error("DUPLICATE_OPERATION", "workload already has a running instance")
        if n + 1 > c.max_instances:
            raise Inv24Error("QUOTA_EXCEEDED", "fleet instance cap reached")
        if tn + 1 > c.max_instances_per_tenant:
            raise Inv24Error("QUOTA_EXCEEDED", "tenant instance cap reached")
        if cpu + req["vcpus"] > c.vcpus_total or mem + req["memory_mib"] > c.memory_mib_total:
            raise Inv24Error("QUOTA_EXCEEDED", "host vCPU/memory headroom exhausted")

    def _enqueue_and_wait(self, req: dict, deadline: float) -> None:
        tenant = req["tenant"]
        ticket = object()
        with self._lock:
            if self._queued >= self.capacity.queue_depth:
                raise Inv24Error("OVERLOADED", "admission queue full")
            if len(self._queues[tenant]) >= self.capacity.per_tenant_queue_depth:
                raise Inv24Error("OVERLOADED", "tenant admission queue full")
            self._queues[tenant].append(ticket)
            if tenant not in self._rr:
                self._rr.append(tenant)
            self._queued += 1
            dispatched = False
            try:
                # fairness: only the head ticket of the tenant at the head of the
                # round-robin may dispatch; one launch in flight per controller.
                while not (self._rr and self._rr[0] == tenant and self._queues[tenant][0] is ticket
                           and self._inflight == 0):
                    remaining = deadline - self.clock()
                    if remaining <= 0:
                        raise Inv24Error("TIMEOUT", "deadline elapsed while queued")
                    self._lock.wait(min(remaining, 0.05))
                self._inflight += 1
                dispatched = True
            finally:
                self._queues[tenant].remove(ticket)
                self._queued -= 1
                if dispatched:
                    self._rr.popleft()               # rotate this tenant to the back
                    if self._queues[tenant]:
                        self._rr.append(tenant)
                elif not self._queues[tenant] and tenant in self._rr:
                    self._rr.remove(tenant)
                self._lock.notify_all()

    def stats(self) -> dict:
        with self._lock:
            n, cpu, mem = self._usage()
            return {"running": n, "vcpus": cpu, "memory_mib": mem, "queued": self._queued,
                    "tenants_queued": len(self._rr)}

    def reconcile(self, live_instances: set[str]) -> dict:
        """After restart: drop reservations for instances that are not live; report pending ops."""
        with self._lock:
            dead = [i for i in self._running if i not in live_instances]
            for i in dead:
                self._running.pop(i)
        return {"dropped": dead, "pending_ops": [r["key"] for r in self.journal.pending()]}
