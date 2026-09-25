"""Durable, fenced, idempotent GAP-11 controller.

Components realised here (see docs/TRACEABILITY.md for per-check evidence):
  GAP11-P0-01 durable lease state (via LeaseStore), GAP11-P0-02 fencing (every
  mutation carries the leader epoch as a store fence), GAP11-P0-04 lease TTL /
  heartbeat / orphan reconciliation, GAP11-P0-05 idempotency + replay store,
  GAP11-P0-15 workload lifecycle hooks, GAP11-P1-21 hot-plug reconciliation,
  GAP11-P1-31 usage accounting, GAP11-P1-32 operator quarantine/drain controls.

Placement decisions reuse the audited v4.2.0 ``allocator.AcceleratorPool`` on a
transient view rebuilt from durable truth, so the selection rules that were
audited (kind/generation/memory/features, declared partitions, tenant security
epoch, quarantine, best fit) are not re-implemented.
"""
from __future__ import annotations

import secrets
import threading
from typing import Any, Callable, Iterable

from ._core import allocator as core
from .common import ControlError, Telemetry, digest, tenant_hash, utc_iso
from .election import FENCE_RESOURCE, LeaderElector
from .store import LeaseStore, Provenance

# ---------------------------------------------------------------- state machines
DEVICE_STATES = ("CLEAN", "DIRTY", "SCRUBBING", "QUARANTINED", "MISSING")
DEVICE_TRANSITIONS = {
    ("CLEAN", "DIRTY"), ("DIRTY", "DIRTY"), ("DIRTY", "SCRUBBING"), ("CLEAN", "SCRUBBING"),
    ("SCRUBBING", "CLEAN"), ("SCRUBBING", "QUARANTINED"), ("QUARANTINED", "SCRUBBING"),
    ("CLEAN", "QUARANTINED"), ("DIRTY", "QUARANTINED"),
    ("CLEAN", "MISSING"), ("DIRTY", "MISSING"), ("QUARANTINED", "MISSING"), ("SCRUBBING", "MISSING"),
    ("MISSING", "QUARANTINED"),  # a device that reappears is never trusted until scrubbed
}
LEASE_STATES = ("ACTIVE", "SUSPECT", "RELEASED", "RECLAIMED")
LEASE_TRANSITIONS = {
    ("ACTIVE", "RELEASED"), ("ACTIVE", "SUSPECT"), ("SUSPECT", "ACTIVE"), ("SUSPECT", "RELEASED"),
    ("ACTIVE", "RECLAIMED"), ("SUSPECT", "RECLAIMED"),
}
TERMINAL_LEASE_STATES = {"RELEASED", "RECLAIMED"}


def check_transition(table: set[tuple[str, str]], old: str, new: str) -> None:
    if (old, new) not in table:
        raise ControlError("ILLEGAL_TRANSITION", f"{old} -> {new}", old=old, new=new)


LIVENESS_ALIVE, LIVENESS_DEAD, LIVENESS_UNKNOWN = "alive", "dead", "unknown"


def _serialized(fn):
    """One mutation at a time inside a controller process. Across processes/controllers
    the store's CAS + fence is the guard; inside one process this lock removes
    self-inflicted STALE_REVISION between benign concurrent requests (found by the
    soak test: a release racing an allocate on the same device key failed spuriously
    and leaked the lease to a client that did not retry)."""
    import functools

    @functools.wraps(fn)
    def wrapper(self, *a, **k):
        with self._mu:
            return fn(self, *a, **k)
    return wrapper


class Controller:
    def __init__(self, store: LeaseStore, elector: LeaderElector, *, telemetry: Telemetry | None = None,
                 lease_ttl: float = 30.0, grace: float = 15.0, idem_retention: float = 86_400.0,
                 audit: Callable[[dict[str, Any]], None] | None = None,
                 scrub_executor: Any | None = None) -> None:
        self.store = store
        self.elector = elector
        self.clock = store.clock
        self.tel = telemetry or Telemetry(self.clock)
        self.ttl = lease_ttl
        self.grace = grace
        self.idem_retention = idem_retention
        self.audit = audit or (lambda ev: None)
        self.scrub_executor = scrub_executor
        self.maintenance = False
        self._mu = threading.RLock()
        self._inflight_scrubs: set[str] = set()

    # ------------------------------------------------------------ helpers
    def _prov(self, request_id: str, actor: str, reason: str) -> Provenance:
        return Provenance(request_id, actor, self.elector.require(), reason)

    def _commit(self, ops: list[dict[str, Any]], pre: dict[str, int], request_id: str, actor: str, reason: str) -> int:
        prov = self._prov(request_id, actor, reason)
        rev = self.store.commit(ops, pre=pre, prov=prov, fence=(FENCE_RESOURCE, prov.controller_epoch))
        self.audit({"action": reason, "request_id": request_id, "actor": actor,
                    "controller_epoch": prov.controller_epoch, "revision": rev,
                    "keys": sorted({op["key"] for op in ops})})
        return rev

    def _idem(self, request_id: str, payload: dict[str, Any]) -> tuple[str, int, dict[str, Any] | None]:
        if not isinstance(request_id, str) or not (8 <= len(request_id) <= 128):
            raise ControlError("SCHEMA_INVALID", "request_id must be 8..128 chars")
        key = f"idem/{request_id}"
        cur = self.store.get(key)
        pd = digest(payload)
        if cur is None:
            return key, 0, None
        rev, rec = cur
        if rec["expires"] < self.clock.monotonic():
            return key, rev, None  # retention elapsed: treated as new, overwritten by CAS
        if rec["payload"] != pd:
            self.tel.emit("idempotency", "conflict", code="IDEMPOTENCY_CONFLICT", severity="WARN", request_id=request_id)
            raise ControlError("IDEMPOTENCY_CONFLICT", request_id=request_id)
        self.tel.emit("idempotency", "replay", code="DUPLICATE_REQUEST", request_id=request_id)
        return key, rev, rec["result"]

    def _idem_op(self, key: str, payload: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        return {"op": "put", "key": key, "value": {"payload": digest(payload), "result": result,
                                                    "expires": self.clock.monotonic() + self.idem_retention}}

    def _guard_mutation(self) -> None:
        if self.maintenance:
            raise ControlError("MAINTENANCE_MODE")
        self.elector.require()

    def devices(self) -> dict[str, tuple[int, dict[str, Any]]]:
        return {k[4:]: v for k, v in self.store.scan("dev/").items()}

    def leases(self, *, include_terminal: bool = False) -> dict[str, tuple[int, dict[str, Any]]]:
        out = {k[6:]: v for k, v in self.store.scan("lease/").items()}
        if not include_terminal:
            out = {k: v for k, v in out.items() if v[1]["state"] not in TERMINAL_LEASE_STATES}
        return out

    # ------------------------------------------------------------ inventory
    @_serialized
    def upsert_device(self, record: dict[str, Any], *, request_id: str, actor: str) -> dict[str, Any]:
        """Insert/refresh an inventory record from the (attested) inventory adapter."""
        self._guard_mutation()
        # Validate with the audited core model (raises on contradictory declarations).
        core.Accelerator(record["device"], record["generation"], record["memory_gb"],
                         frozenset(record.get("features", ())),
                         partitions=tuple(core.PartitionSpec(p["name"], p.get("memory_gb"), frozenset(p["features"]) if p.get("features") is not None else None)
                                          for p in record.get("partitions", ())),
                         kind=record.get("kind", "generic"))
        key = f"dev/{record['device']}"
        cur = self.store.get(key)
        static = {k: record[k] for k in ("device", "generation", "memory_gb") }
        static.update(kind=record.get("kind", "generic").lower(), features=sorted(record.get("features", ())),
                      partitions=list(record.get("partitions", ())), node=record.get("node", "node-0"),
                      topology=record.get("topology", {}), stable_id=record.get("stable_id", record["device"]))
        if cur is None:
            value = {**static, "state": "CLEAN", "security_tenant": None, "draining": False,
                     "health": "ok", "thermal_ok": True, "present": True}
            self._commit([{"op": "put", "key": key, "value": value}], {key: 0}, request_id, actor, "DEVICE_REGISTER")
            return value
        rev, value = cur
        changed_capability = any(value.get(k) != static[k] for k in ("kind", "generation", "memory_gb", "features", "partitions"))
        active = [l for l in self.leases().values() if l[1]["device"] == record["device"]]
        new = {**value, **static, "present": True}
        if value["state"] == "MISSING":
            check_transition(DEVICE_TRANSITIONS, "MISSING", "QUARANTINED")
            new["state"] = "QUARANTINED"
        if changed_capability and active:
            # Capability changed under a live lease: never silently re-shape; quarantine for review.
            new["draining"] = True
            self.tel.emit("inventory", "capability_changed_under_lease", code="AMBIGUOUS_EVIDENCE", severity="WARN", device=record["device"])
        self._commit([{"op": "put", "key": key, "value": new}], {key: rev}, request_id, actor, "DEVICE_REFRESH")
        return new

    @_serialized
    def mark_missing(self, device: str, *, request_id: str, actor: str) -> None:
        self._guard_mutation()
        rev, value = self._device(device)
        check_transition(DEVICE_TRANSITIONS, value["state"], "MISSING")
        leases = [(lid, l) for lid, l in self.leases().items() if l[1]["device"] == device]
        ops = [{"op": "put", "key": f"dev/{device}", "value": {**value, "state": "MISSING", "present": False}}]
        pre = {f"dev/{device}": rev}
        for lid, (lrev, l) in leases:
            check_transition(LEASE_TRANSITIONS, l["state"], "SUSPECT")
            ops.append({"op": "put", "key": f"lease/{lid}", "value": {**l, "state": "SUSPECT", "suspect_reason": "DEVICE_MISSING"}})
            pre[f"lease/{lid}"] = lrev
        self._commit(ops, pre, request_id, actor, "DEVICE_MISSING")
        self.tel.emit("inventory", "device_missing", code="DEVICE_MISSING", severity="ERROR", device=device)

    def _device(self, device: str) -> tuple[int, dict[str, Any]]:
        cur = self.store.get(f"dev/{device}")
        if cur is None:
            raise ControlError("LEASE_NOT_FOUND", f"no device {device}")
        return cur

    # ------------------------------------------------------------ allocation
    def _view(self, *, exclude: Iterable[str] = (), eligible: Callable[[dict[str, Any]], bool] | None = None) -> core.AcceleratorPool:
        leases = self.leases()
        devices = []
        for name, (_, d) in sorted(self.devices().items()):
            if name in exclude or not d["present"] or d["draining"] or d["health"] != "ok" or not d["thermal_ok"]:
                continue
            if d["state"] in ("SCRUBBING", "MISSING"):
                continue
            if eligible is not None and not eligible(d):
                continue
            acc = core.Accelerator(d["device"], d["generation"], d["memory_gb"], frozenset(d["features"]),
                                   partitions=tuple(core.PartitionSpec(p["name"], p.get("memory_gb"),
                                                    frozenset(p["features"]) if p.get("features") is not None else None)
                                                    for p in d["partitions"]), kind=d["kind"])
            acc.security_tenant = d["security_tenant"]
            acc.quarantined = d["state"] == "QUARANTINED"
            acc.scrubbed = d["state"] == "CLEAN"
            for lid, (_, l) in leases.items():
                if l["device"] == d["device"]:
                    acc.leases[lid] = core.AllocationLease(lid, l["tenant"], l["workload"], l["partition"])
            devices.append(acc)
        return core.AcceleratorPool(devices)

    @_serialized
    def allocate(self, request: dict[str, Any], *, request_id: str, actor: str,
                 eligible: Callable[[dict[str, Any]], bool] | None = None) -> dict[str, Any]:
        self._guard_mutation()
        payload = {"op": "allocate", **request}
        ikey, irev, prior = self._idem(request_id, payload)
        if prior is not None:
            return prior
        view = self._view(eligible=eligible)
        try:
            res = view.allocate(tenant=request["tenant"], workload=request["workload"],
                                memory_gb=request.get("memory_gb", 0), kind=request.get("kind"),
                                generation=request.get("generation"), features=request.get("features", ()),
                                partition=request.get("partition"))
        except core.ScrubRequired as exc:
            raise ControlError("DEVICE_QUARANTINED" if exc.details.get("quarantined") else "CAPACITY_EXHAUSTED",
                               str(exc), scrub_required=True, **{k: v for k, v in exc.details.items() if k != "previous_tenant"}) from exc
        except core.UndeclaredPartition as exc:
            raise ControlError("CONSTRAINT_UNSATISFIED", str(exc), partition=request.get("partition")) from exc
        except core.NoMatchingAccelerator as exc:
            raise ControlError("CAPACITY_EXHAUSTED", str(exc)) from exc
        drev, dev = self._device(res["device"])
        new_state = "DIRTY"
        check_transition(DEVICE_TRANSITIONS, dev["state"], new_state) if dev["state"] != "QUARANTINED" else None
        now = self.clock.monotonic()
        lease = {"lease_id": res["lease_id"], "device": res["device"], "tenant": request["tenant"],
                 "workload": request["workload"], "partition": res["partition"], "memory_gb": res["memory_gb"],
                 "state": "ACTIVE", "expires": now + self.ttl, "created": utc_iso(self.clock.wall()),
                 "created_mono": now, "epoch": self.elector.epoch, "request_id": request_id}
        result = {"schema": "PK_ACCELERATOR_ALLOCATION/1", **{k: res[k] for k in ("lease_id", "device", "partition", "kind", "generation", "memory_gb")},
                  "tenant": request["tenant"], "workload": request["workload"], "ttl_seconds": self.ttl,
                  "fencing_token": self.elector.epoch}
        ops = [
            {"op": "put", "key": f"dev/{res['device']}", "value": {**dev, "state": new_state, "security_tenant": request["tenant"]}},
            {"op": "put", "key": f"lease/{res['lease_id']}", "value": lease},
            {"op": "put", "key": f"usage/{res['lease_id']}", "value": {"lease_id": res["lease_id"], "device": res["device"],
             "partition": res["partition"], "tenant": request["tenant"], "start": lease["created"], "start_mono": now, "end": None, "seconds": None}},
            self._idem_op(ikey, payload, result),
        ]
        self._commit(ops, {f"dev/{res['device']}": drev, f"lease/{res['lease_id']}": 0, f"usage/{res['lease_id']}": 0, ikey: irev},
                     request_id, actor, "ALLOCATE")
        self.tel.emit("allocator", "allocate", lease_id=res["lease_id"], device=res["device"], request_id=request_id,
                      tenant_hash=tenant_hash(request["tenant"]), controller_epoch=self.elector.epoch)
        return result

    @_serialized
    def allocate_gang(self, requests: list[dict[str, Any]], *, request_id: str, actor: str,
                      order: Callable[[list[str]], list[str]] | None = None) -> dict[str, Any]:
        """All-or-nothing multi-device reservation in ONE store transaction (GAP11-P1-17)."""
        self._guard_mutation()
        payload = {"op": "allocate_gang", "requests": requests}
        ikey, irev, prior = self._idem(request_id, payload)
        if prior is not None:
            return prior
        view = self._view()
        chosen = []
        try:
            for r in requests:
                res = view.allocate(tenant=r["tenant"], workload=r["workload"], memory_gb=r.get("memory_gb", 0),
                                    kind=r.get("kind"), generation=r.get("generation"), features=r.get("features", ()),
                                    partition=r.get("partition"))
                chosen.append((r, res))
        except core.AcceleratorSchedulingError as exc:
            # nothing was persisted: the transient view is discarded (rollback is free)
            raise ControlError("CAPACITY_EXHAUSTED", f"gang not satisfiable: {exc}", members=len(requests), placed=len(chosen)) from exc
        gang_id = secrets.token_hex(8)
        now = self.clock.monotonic()
        ops, pre, members = [], {ikey: irev}, []
        devs: dict[str, tuple[int, dict[str, Any]]] = {}
        for r, res in chosen:
            if res["device"] not in devs:
                devs[res["device"]] = self._device(res["device"])
            rev, d = devs[res["device"]]
            devs[res["device"]] = (rev, {**d, "state": "DIRTY", "security_tenant": r["tenant"]})
            lease = {"lease_id": res["lease_id"], "device": res["device"], "tenant": r["tenant"], "workload": r["workload"],
                     "partition": res["partition"], "memory_gb": res["memory_gb"], "state": "ACTIVE",
                     "expires": now + self.ttl, "created": utc_iso(self.clock.wall()), "created_mono": now,
                     "epoch": self.elector.epoch, "request_id": request_id, "gang_id": gang_id}
            ops.append({"op": "put", "key": f"lease/{res['lease_id']}", "value": lease})
            pre[f"lease/{res['lease_id']}"] = 0
            members.append({"lease_id": res["lease_id"], "device": res["device"], "partition": res["partition"]})
        for name, (rev, d) in devs.items():
            ops.append({"op": "put", "key": f"dev/{name}", "value": d})
            pre[f"dev/{name}"] = self._device(name)[0]
        result = {"schema": "PK_ACCELERATOR_GANG/1", "gang_id": gang_id, "members": members, "fencing_token": self.elector.epoch}
        ops.append(self._idem_op(ikey, payload, result))
        self._commit(ops, pre, request_id, actor, "ALLOCATE_GANG")
        return result

    @_serialized
    def release(self, lease_id: str, *, request_id: str, actor: str, tenant: str | None = None,
                reason: str = "RELEASE") -> dict[str, Any]:
        self._guard_mutation()
        payload = {"op": "release", "lease_id": lease_id}
        ikey, irev, prior = self._idem(request_id, payload)
        if prior is not None:
            return prior
        cur = self.store.get(f"lease/{lease_id}")
        if cur is None:
            raise ControlError("LEASE_NOT_FOUND", lease_id=lease_id)
        lrev, lease = cur
        if tenant is not None and lease["tenant"] != tenant:
            # cross-tenant release: indistinguishable from not-found to avoid an existence oracle
            raise ControlError("LEASE_NOT_FOUND", lease_id=lease_id)
        target = "RECLAIMED" if reason == "RECLAIM" else "RELEASED"
        check_transition(LEASE_TRANSITIONS, lease["state"], target)
        drev, dev = self._device(lease["device"])
        urev, usage = self.store.get(f"usage/{lease_id}") or (0, None)
        now = self.clock.monotonic()
        result = {"schema": "PK_ACCELERATOR_RELEASE/1", "lease_id": lease_id, "device": lease["device"],
                  "partition": lease["partition"], "released": True, "scrub_required_for_tenant_change": True,
                  "outcome": target}
        ops = [{"op": "put", "key": f"lease/{lease_id}", "value": {**lease, "state": target, "ended": utc_iso(self.clock.wall())}},
               # security_tenant remains until a verified scrub; device stays DIRTY
               {"op": "put", "key": f"dev/{lease['device']}", "value": {**dev, "state": dev["state"] if dev["state"] in ("QUARANTINED", "MISSING") else "DIRTY"}},
               self._idem_op(ikey, payload, result)]
        pre = {f"lease/{lease_id}": lrev, f"dev/{lease['device']}": drev, ikey: irev}
        if usage is not None:
            ops.append({"op": "put", "key": f"usage/{lease_id}", "value": {**usage, "end": utc_iso(self.clock.wall()),
                        "seconds": round(now - usage["start_mono"], 6)}})
            pre[f"usage/{lease_id}"] = urev
        self._commit(ops, pre, request_id, actor, reason)
        self.tel.emit("allocator", "release", lease_id=lease_id, device=lease["device"], request_id=request_id, outcome=target)
        return result

    # ------------------------------------------------------------ TTL / heartbeat
    @_serialized
    def heartbeat(self, lease_id: str, *, tenant: str, request_id: str, actor: str) -> dict[str, Any]:
        self._guard_mutation()
        cur = self.store.get(f"lease/{lease_id}")
        if cur is None or cur[1]["tenant"] != tenant:
            raise ControlError("LEASE_NOT_FOUND", lease_id=lease_id)
        rev, lease = cur
        now = self.clock.monotonic()
        if lease["state"] in TERMINAL_LEASE_STATES:
            raise ControlError("LEASE_EXPIRED", lease_id=lease_id)
        new = {**lease, "expires": now + self.ttl}
        if lease["state"] == "SUSPECT" and lease.get("suspect_reason") != "DEVICE_MISSING":
            check_transition(LEASE_TRANSITIONS, "SUSPECT", "ACTIVE")
            new["state"] = "ACTIVE"
            new.pop("suspect_reason", None)
        self._commit([{"op": "put", "key": f"lease/{lease_id}", "value": new}], {f"lease/{lease_id}": rev}, request_id, actor, "HEARTBEAT")
        return {"lease_id": lease_id, "expires_in": self.ttl, "state": new["state"]}

    @_serialized
    def reconcile(self, liveness: Callable[[dict[str, Any]], str], *, actor: str = "reconciler") -> dict[str, list[str]]:
        """Deterministic orphan reconciliation. Only unambiguous evidence is destructive.

        expired + workload dead      -> RECLAIMED (device stays DIRTY until scrub)
        expired + workload alive     -> lease renewed on the workload's behalf
        expired + liveness unknown   -> SUSPECT; reclaimed only after ``grace`` more
                                        seconds of *continued* unknown, never earlier
        SCRUBBING device not being scrubbed by this process (its runner crashed or a
        previous leader died mid-scrub) -> QUARANTINED (outcome unknown, fail closed);
        an in-flight scrub of this process is left alone (found by the barrier test)
        """
        self._guard_mutation()
        now = self.clock.monotonic()
        report: dict[str, list[str]] = {"reclaimed": [], "renewed": [], "suspect": [], "quarantined": [], "untouched": []}
        for lid, (rev, lease) in sorted(self.leases().items()):
            if lease["expires"] > now:
                report["untouched"].append(lid)
                continue
            state = liveness(lease)
            rid = f"reconcile-{lid}-{int(now * 1000)}"
            if state == LIVENESS_DEAD:
                self.release(lid, request_id=rid, actor=actor, reason="RECLAIM")
                report["reclaimed"].append(lid)
            elif state == LIVENESS_ALIVE:
                new = {**lease, "expires": now + self.ttl, "state": "ACTIVE"}
                new.pop("suspect_reason", None)
                self._commit([{"op": "put", "key": f"lease/{lid}", "value": new}], {f"lease/{lid}": rev}, rid, actor, "RENEW_ON_LIVENESS")
                report["renewed"].append(lid)
            else:
                if lease["state"] == "SUSPECT" and now >= lease.get("suspect_since", now) + self.grace and lease.get("suspect_reason") != "DEVICE_MISSING":
                    self.release(lid, request_id=rid, actor=actor, reason="RECLAIM")
                    report["reclaimed"].append(lid)
                elif lease["state"] == "ACTIVE":
                    check_transition(LEASE_TRANSITIONS, "ACTIVE", "SUSPECT")
                    self._commit([{"op": "put", "key": f"lease/{lid}", "value": {**lease, "state": "SUSPECT", "suspect_since": now, "suspect_reason": "LIVENESS_UNKNOWN"}}],
                                 {f"lease/{lid}": rev}, rid, actor, "SUSPECT")
                    self.tel.emit("reconciler", "suspect", code="AMBIGUOUS_EVIDENCE", severity="WARN", lease_id=lid)
                    report["suspect"].append(lid)
                else:
                    report["suspect"].append(lid)
        for name, (rev, d) in sorted(self.devices().items()):
            if d["state"] == "SCRUBBING" and name not in self._inflight_scrubs:
                # SCRUBBING that this live controller is not running = its runner died
                self._commit([{"op": "put", "key": f"dev/{name}", "value": {**d, "state": "QUARANTINED", "quarantine_reason": "SCRUB_OUTCOME_UNKNOWN"}}],
                             {f"dev/{name}": rev}, f"reconcile-scrub-{name}-{int(now*1000)}", actor, "QUARANTINE")
                report["quarantined"].append(name)
        return report

    # ------------------------------------------------------------ lifecycle hooks (P0-15)
    @_serialized
    def on_workload_event(self, event: dict[str, Any], *, actor: str = "lifecycle") -> dict[str, Any]:
        """Authoritative workload hooks: start/exit/crash/evict/restart."""
        kind = event["event"]
        lid = event["lease_id"]
        rid = event["event_id"]
        if kind in ("exit", "crash", "evict"):
            return self.release(lid, request_id=rid, actor=actor, tenant=event.get("tenant"),
                                reason="RELEASE" if kind == "exit" else "RECLAIM")
        if kind in ("start", "restart"):
            return self.heartbeat(lid, tenant=event["tenant"], request_id=rid, actor=actor)
        raise ControlError("SCHEMA_INVALID", f"unknown lifecycle event {kind!r}")

    # ------------------------------------------------------------ scrub (P0-08 integration)
    def scrub(self, device: str, *, request_id: str, actor: str) -> dict[str, Any]:
        """Begin (serialized) -> executor runs WITHOUT the controller lock (scrubs take
        minutes; other devices keep being served) -> end (serialized). The SCRUBBING
        state excludes the device from placement for the whole window."""
        begun = self._scrub_begin(device, request_id=request_id, actor=actor)
        if "result" in begun:
            return begun["result"]
        try:
            evidence = self.scrub_executor.scrub(begun["device"])
            return self._scrub_end(device, evidence, request_id=request_id, actor=actor, payload=begun["payload"])
        finally:
            self._inflight_scrubs.discard(device)

    @_serialized
    def _scrub_begin(self, device: str, *, request_id: str, actor: str) -> dict[str, Any]:
        self._guard_mutation()
        if self.scrub_executor is None:
            raise ControlError("DEPENDENCY_UNAVAILABLE", "no scrub executor bound")
        payload = {"op": "scrub", "device": device}
        ikey, irev, prior = self._idem(request_id, payload)
        if prior is not None:
            return {"result": prior}
        rev, d = self._device(device)
        if any(l[1]["device"] == device for l in self.leases().values()):
            raise ControlError("ILLEGAL_TRANSITION", "active leases; release before scrubbing", device=device)
        check_transition(DEVICE_TRANSITIONS, d["state"], "SCRUBBING")
        self._commit([{"op": "put", "key": f"dev/{device}", "value": {**d, "state": "SCRUBBING"}}],
                     {f"dev/{device}": rev}, request_id + ":begin", actor, "SCRUB_BEGIN")
        self._inflight_scrubs.add(device)
        return {"device": d, "payload": payload}

    @_serialized
    def _scrub_end(self, device: str, evidence: dict[str, Any], *, request_id: str, actor: str,
                   payload: dict[str, Any]) -> dict[str, Any]:
        self._guard_mutation()
        ikey, irev, _ = self._idem(request_id, payload)
        ok = bool(evidence.get("verified"))
        final = "CLEAN" if ok else "QUARANTINED"
        rev, cur = self._device(device)
        if cur["state"] != "SCRUBBING":   # e.g. reconciled to QUARANTINED meanwhile: never overwrite
            raise ControlError("ILLEGAL_TRANSITION", "device left SCRUBBING during scrub", device=device, state=cur["state"])
        check_transition(DEVICE_TRANSITIONS, "SCRUBBING", final)
        new = {**cur, "state": final, "security_tenant": None if ok else cur["security_tenant"],
               "quarantine_reason": None if ok else evidence.get("code", "SCRUB_FAILED")}
        result = {"schema": "PK_SCRUB/1", "device": device, "completed": ok, "quarantined": not ok, "evidence": evidence}
        self._commit([{"op": "put", "key": f"dev/{device}", "value": new}, self._idem_op(ikey, payload, result)],
                     {f"dev/{device}": rev, ikey: irev}, request_id, actor, "SCRUB_END")
        self.tel.emit("scrub", "scrub", code="OK" if ok else evidence.get("code", "SCRUB_FAILED"),
                      severity="INFO" if ok else "ERROR", device=device, request_id=request_id)
        return result

    # ------------------------------------------------------------ operator controls (P1-32)
    @_serialized
    def set_draining(self, device: str, draining: bool, *, request_id: str, actor: str) -> None:
        self._guard_mutation()
        rev, d = self._device(device)
        self._commit([{"op": "put", "key": f"dev/{device}", "value": {**d, "draining": draining}}], {f"dev/{device}": rev},
                     request_id, actor, "DRAIN" if draining else "UNDRAIN")

    @_serialized
    def quarantine(self, device: str, *, request_id: str, actor: str, reason: str) -> None:
        self._guard_mutation()
        rev, d = self._device(device)
        check_transition(DEVICE_TRANSITIONS, d["state"], "QUARANTINED")
        self._commit([{"op": "put", "key": f"dev/{device}", "value": {**d, "state": "QUARANTINED", "quarantine_reason": reason}}],
                     {f"dev/{device}": rev}, request_id, actor, "QUARANTINE")

    @_serialized
    def set_health(self, device: str, *, health: str | None = None, thermal_ok: bool | None = None,
                   request_id: str, actor: str) -> None:
        self._guard_mutation()
        rev, d = self._device(device)
        new = dict(d)
        if health is not None:
            if health not in ("ok", "degraded", "failed"):
                raise ControlError("SCHEMA_INVALID", "health must be ok|degraded|failed")
            new["health"] = health
            if health == "failed" and d["state"] != "QUARANTINED" and ("QUARANTINED" in {s for (o, s) in DEVICE_TRANSITIONS if o == d["state"]}):
                new["state"] = "QUARANTINED"
                new["quarantine_reason"] = "HARDWARE_FAULT"
        if thermal_ok is not None:
            new["thermal_ok"] = bool(thermal_ok)
        self._commit([{"op": "put", "key": f"dev/{device}", "value": new}], {f"dev/{device}": rev}, request_id, actor, "HEALTH_UPDATE")

    def freeze(self, on: bool) -> None:
        """Maintenance freeze: reads keep working, every mutation is refused."""
        self.maintenance = bool(on)
        self.tel.emit("operator", "maintenance", code="MAINTENANCE_MODE" if on else "OK", detail=str(on))

    # ------------------------------------------------------------ accounting (P1-31)
    def usage_records(self) -> list[dict[str, Any]]:
        return [v for _, (_, v) in sorted(self.store.scan("usage/").items())]
