"""The hardened INV-60 control plane: every public operation passes
authenticate -> authorize -> admission/limits -> validate -> (verify signature)
-> lifecycle transition -> placement -> durable write -> audit -> telemetry,
and returns a ``Result`` envelope (never a raw exception).

Degraded modes (M46): ``normal``, ``read_only`` (no mutations), ``isolated``
(serve existing links only), ``frozen`` (operator freeze: no mutations, calls
allowed). Quarantine (M49) isolates a component or host immediately: its links
are suspended, calls refused with QUARANTINED, and placements avoid it.
"""
from __future__ import annotations

import threading
import time

from .. import runtime as rt
from . import placement as pl
from .authz import Authorizer
from .errors import FabricError, Result, result_from_exception
from .identity import TrustDomain
from .ledger import AuditLedger
from .lifecycle import component_machine, host_machine, link_machine
from .limits import Limiter
from .membership import FailureDetector, LeaseManager, PartitionState
from .resilience import CircuitBreaker, Deadline, IdempotencyStore
from .signing import TrustPolicy
from .store import StateStore
from .telemetry import DecisionLog, Logger, Metrics, TraceContext

AUDIENCE = "inv60-fabric"
MODES = ("normal", "read_only", "isolated", "frozen")
VERSION = "4.3.0"


class Fabric:
    def __init__(self, *, trust: TrustDomain, policy: TrustPolicy, state_dir=None, ledger_path=None,
                 limits=None, clock=time.time, mono=time.monotonic, ledger_mac_key=None, controller_id="ctl-1",
                 voters=("v1", "v2", "v3")):
        self.trust, self.policy = trust, policy
        self.authz = Authorizer(clock=clock)
        self.limiter = Limiter(limits, clock=mono)
        self.ledger = AuditLedger(ledger_path, mac_key=ledger_mac_key, clock=clock)
        self.store = StateStore(state_dir) if state_dir else None
        self.metrics, self.log, self.decisions = Metrics(), Logger(), DecisionLog()
        self.detector = FailureDetector(clock=mono)
        self.leases = LeaseManager(list(voters), clock=mono)
        self.partition = PartitionState(clock=mono)
        self.idem = IdempotencyStore(clock=clock)
        self.breakers: dict[str, CircuitBreaker] = {}
        self.mono = mono
        self.controller_id = controller_id
        self.mode = "normal"
        self.lattice = rt.Lattice([])
        self.hosts: dict[str, pl.HostInfo] = {}
        self.host_sm: dict = {}
        self.comp_sm: dict = {}
        self.comp_meta: dict = {}
        self.link_sm: dict = {}
        self.verified: dict[str, dict] = {}
        self.quarantined: set = set()
        self.epoch = None
        self._mutex = threading.RLock()  # serialization boundary for control-plane mutations (M10/M71)
        if self.store:
            self._reconstruct()

    # ---------------------------------------------------------------- plumbing
    def _run(self, operation: str, token: str, action: str, resource: str, tenant: str, body, *,
             session="", mutating=True, traceparent=None, deadline: Deadline | None = None, endpoint=None) -> Result:
        trace = TraceContext.parse(traceparent)
        started = self.mono()
        box = {"result": None, "principal": None, "trace": trace}
        try:
            if deadline:
                deadline.check("ingress")
            pr = self.trust.authenticate(token, AUDIENCE, session=session, endpoint=endpoint)
            box["principal"] = pr
            self.authz.require(pr, action, resource, tenant)
            if mutating and self.mode in ("read_only", "frozen") and action not in ("control.quarantine", "control.freeze"):
                raise FabricError("QUARANTINED" if self.mode == "frozen" else "UNAVAILABLE",
                                  f"fabric in {self.mode} mode; mutations refused")
            if mutating and action not in ("control.quarantine", "control.freeze"):
                self.partition.require_new_authority()
            self.limiter.rate(pr.tenant)
            if mutating:
                with self._mutex:
                    body(box)
            else:
                body(box)
            if box["result"] is None:
                box["result"] = Result("OK")
        except Exception as exc:  # noqa: BLE001 - public boundary: always a Result
            box["result"] = result_from_exception(exc)
            sec = box["result"].code in ("UNAUTHENTICATED", "PERMISSION_DENIED", "REPLAY_DETECTED",
                                          "NOT_LINKED", "SIGNATURE_INVALID", "DIGEST_MISMATCH")
            self.log.log("warn", f"{operation}.refused", trace=trace, security=sec,
                         code=box["result"].code, target=resource)
            self.decisions.record(operation, resource, "refused", [box["result"].message],
                                  rules=[box["result"].detail.get("rule", "-")], trace=trace)
        r: Result = box["result"]
        r.principal = box["principal"].id if box["principal"] else None
        r.target = resource
        r.detail.setdefault("trace_id", trace.trace_id)
        self.metrics.inc("operations", operation=operation, code=r.code)
        self.metrics.observe("operation_seconds", self.mono() - started, operation=operation)
        self.ledger.append(f"op.{operation}", r.principal, {"code": r.code, "target": resource, "tenant": tenant,
                                                              "operation_id": r.operation_id})
        return r

    def _persist(self, op, **kw):
        if self.store:
            self.store.apply(op, **kw)

    def _authority(self):
        """Hold the controller lease; writes are fenced by its epoch (M48)."""
        lease = self.leases.acquire(self.controller_id, self.leases.voters if self.partition.connected_to_control else [])
        self.epoch = lease.epoch
        self.leases.check_fence(lease.epoch)

    # ---------------------------------------------------------------- membership
    def join_host(self, token, host: str, *, region="default", dedicated_tenant=None, capacity=64,
                  session="", traceparent=None) -> Result:
        def _body(box):
            pr = box["principal"]
            if pr.kind == "host" and not pr.id.endswith("/host/" + host):
                raise FabricError("PERMISSION_DENIED", "a host may only enrol itself")
            self.limiter.check_count("max_hosts", len(self.hosts))
            sm = self.host_sm.get(host) or host_machine(host)
            sm.fire("join"); sm.fire("admit")
            self._authority()
            self.host_sm[host] = sm
            self.hosts[host] = pl.HostInfo(host, region=region, dedicated_tenant=dedicated_tenant, capacity=capacity,
                                           attested=bool(pr.attestation.get("verified")) if pr.kind == "host" else True)
            if host not in self.lattice.hosts:
                self.lattice.add_host(host)
            self.detector.heartbeat(host)
            self._persist("host.put", name=host, record={"region": region, "dedicated": dedicated_tenant,
                                                        "capacity": capacity, "state": "active"})
            self.metrics.set("hosts", len(self.hosts), state="active")
        box_result = self._run("join", token, "membership.join", host, "*", session=session, traceparent=traceparent, body=_body)
        return box_result

    def heartbeat(self, host: str, progress: int | None = None) -> None:
        self.detector.heartbeat(host, progress)
        sm = self.host_sm.get(host)
        if sm and sm.state == "suspect":
            sm.fire("heartbeat")
            self.hosts[host].state = "active"

    def sweep(self) -> list[Result]:
        """Failure detector sweep: suspect -> lost -> failover (residency-aware)."""
        with self._mutex:
            return self._sweep()

    def _sweep(self) -> list[Result]:
        out = []
        for host, status in self.detector.sweep().items():
            sm = self.host_sm.get(host)
            if not sm or sm.state in ("lost", "removed", "quarantined"):
                continue
            if status in ("suspect", "stalled") and sm.state == "active":
                sm.fire("miss")
                self.hosts[host].state = "suspect"
                self.decisions.record("membership", host, "suspect", [f"detector status {status}"])
            elif status == "lost":
                out.append(self._failover(host))
        return out

    def _failover(self, host: str) -> Result:
        try:
            self._authority()
        except FabricError as e:
            return Result(e.code, str(e), target=host)
        self.host_sm[host].fire("declare_lost")
        self.hosts[host].state = "lost"
        moved = [c for c, h in self.lattice.instances.items() if h == host]
        per = []
        survivors = [h for h in self.hosts.values() if h.id != host]
        for comp in moved:
            meta = self.comp_meta[comp]
            try:
                rec = pl.resolve(survivors, pl.Request(comp, meta["tenant"], meta["app"], tuple(meta["regions"])))
                self.lattice.instances[comp] = rec["chosen"]
                self.hosts[rec["chosen"]].placed.append((meta["tenant"], meta["app"], comp))
                self.comp_sm[comp].fire("reschedule"); self.comp_sm[comp].fire("ready")
                self._persist("component.put", name=comp, record={**meta, "host": rec["chosen"], "state": "running"})
                self.decisions.record("failover", comp, "moved", [f"{host} lost"], rules=[pl.PRECEDENCE_VERSION],
                                      extra={"to": rec["chosen"]})
                per.append(Result("OK", target=comp, detail={"to": rec["chosen"]}))
            except FabricError as e:
                self.lattice.instances.pop(comp, None)
                self.comp_sm[comp].fire("fail")
                self._persist("component.put", name=comp, record={**meta, "host": None, "state": "failed"})
                self.decisions.record("failover", comp, "failed", [str(e)])
                per.append(Result(e.code, str(e), target=comp))
        self.lattice.hosts = [h for h in self.lattice.hosts if h != host]
        self.hosts[host].placed.clear()
        self.lattice.failovers += sum(1 for r in per if r.code == "OK")
        self.metrics.inc("failovers", len(moved))
        self._persist("host.put", name=host, record={"state": "lost"})
        self.ledger.append("failover", self.controller_id, {"host": host, "moved": len(moved)})
        code = "OK" if all(r.code == "OK" for r in per) else ("PARTIAL" if any(r.code == "OK" for r in per) else
                                                             ("NO_ELIGIBLE_TARGET" if per else "OK"))
        return Result(code, target=host, per_target=per)

    # ---------------------------------------------------------------- artifacts / lifecycle
    def push(self, token, name: str, data: bytes, envelope: dict, *, tenant: str, session="") -> Result:
        def _body(box):
            self.limiter.check_payload(len(data), kind="artifact")
            self.limiter.check_count("max_registry_entries", len(self.lattice.registry))
            va = self.policy.verify(name, data, envelope)        # signature + provenance (M35)
            ref = self.lattice.push(va.data)                      # exactly the verified bytes
            if ref != va.ref:
                raise FabricError("DIGEST_MISMATCH", "verified digest differs from stored digest")
            self.verified[ref] = {**va.record(), "name": name, "tenant": tenant}
            self.ledger.append("artifact.verified", box["principal"].id, va.record())
            box["result"] = Result("OK", value=ref)
        box_result = self._run("push", token, "artifact.push", name, tenant, session=session, body=_body)
        return box_result

    def start(self, token, component: str, ref: str, *, tenant: str, app="", regions=(), session="",
              idempotency_key=None, traceparent=None) -> Result:
        req = {"op": "start", "component": component, "ref": ref, "tenant": tenant, "app": app, "regions": list(regions)}
        if idempotency_key:
            prior = self.idem.lookup(idempotency_key, req)
            if prior is not None:
                return prior
        def _body(box):
            if component in self.quarantined:
                raise FabricError("QUARANTINED", f"{component} is quarantined")
            info = self.verified.get(ref)
            if info is None:
                raise FabricError("SIGNATURE_INVALID", "artifact was not admitted through signature verification")
            if info["tenant"] != tenant:
                raise FabricError("PERMISSION_DENIED", "artifact belongs to another tenant")
            count = sum(1 for c, m in self.comp_meta.items() if m["tenant"] == tenant and c in self.lattice.instances)
            self.limiter.check_count("max_components_per_tenant", count)
            sm = self.comp_sm.get(component) or component_machine(component)
            if sm.state in ("running", "degraded", "starting"):
                raise FabricError("ALREADY_EXISTS", f"{component} already {sm.state}")
            self._authority()
            rec = pl.resolve([h for h in self.hosts.values() if h.id not in self.quarantined],
                             pl.Request(component, tenant, app, tuple(regions)))
            # runtime.start re-hashes the stored bytes at the instantiate boundary
            self.lattice.start(component, ref)
            self.lattice.instances[component] = rec["chosen"]
            sm.fire("stage"); sm.fire("start"); sm.fire("ready")
            self.comp_sm[component] = sm
            meta = {"tenant": tenant, "app": app, "regions": list(regions), "ref": ref}
            self.comp_meta[component] = meta
            self.hosts[rec["chosen"]].placed.append((tenant, app, component))
            self._persist("component.put", name=component, record={**meta, "host": rec["chosen"], "state": "running"})
            self.decisions.record("placement", component, "placed", [rec["tie_break"]], rules=[rec["policy"]],
                                  trace=box["trace"], extra={"host": rec["chosen"]})
            self.metrics.set("instances", len(self.lattice.instances))
            box["result"] = Result("OK", value=rec["chosen"], detail={"host": rec["chosen"]})
        box_result = self._run("start", token, "component.start", component, tenant, session=session, traceparent=traceparent, body=_body)
        if idempotency_key and box_result.code == "OK":
            self.idem.store(idempotency_key, req, box_result)
        return box_result

    def stop(self, token, component: str, *, tenant: str, session="") -> Result:
        def _body(box):
            sm = self.comp_sm.get(component)
            if sm is None or sm.state in ("stopped", "absent"):
                box["result"] = Result("OK", message="already stopped")  # idempotent
            else:
                if self.comp_meta[component]["tenant"] != tenant:
                    raise FabricError("PERMISSION_DENIED", "cross-tenant stop")
                sm.fire("stop")
                host = self.lattice.stop(component)
                for (c, l), lsm in list(self.link_sm.items()):
                    if c == component and lsm.state == "granted":
                        lsm.fire("revoke"); self.authz.revoke(c, l)
                        self._persist("link.del", component=c, link=l)
                if host in self.hosts:
                    self.hosts[host].placed = [p for p in self.hosts[host].placed if p[2] != component]
                sm.fire("stopped")
                self._persist("component.del", name=component)
        box_result = self._run("stop", token, "component.stop", component, tenant, session=session, body=_body)
        return box_result

    def link(self, token, component: str, link: str, provider, *, tenant: str, grantee: str,
             interface="wasi:keyvalue/store@0.2.0", operations=("get", "set"), ttl_s=3600.0, session="") -> Result:
        def _body(box):
            meta = self.comp_meta.get(component)
            if meta is None or component not in self.lattice.instances:
                raise FabricError("NOT_FOUND", f"{component} not running")
            if meta["tenant"] != tenant:
                raise FabricError("PERMISSION_DENIED", "cross-tenant link")
            n = sum(1 for (c, _), s in self.link_sm.items() if c == component and s.state == "granted")
            self.limiter.check_count("max_links_per_component", n)
            lsm = self.link_sm.get((component, link)) or link_machine(f"{component}/{link}")
            lsm.fire("grant")
            self.link_sm[(component, link)] = lsm
            self.lattice.link(component, link, provider)
            g = self.authz.grant(component, link, tenant, grantee, interface, operations, ttl_s)
            self._persist("link.put", component=component, link=link,
                          record={"grant": g.id, "interface": interface, "ops": sorted(operations), "grantee": grantee})
            box["result"] = Result("OK", value=g.id)
        box_result = self._run("link", token, "link.grant", f"{component}/{link}", tenant, session=session, body=_body)
        return box_result

    def unlink(self, token, component, link, *, tenant, session="") -> Result:
        def _body(box):
            lsm = self.link_sm.get((component, link))
            if lsm is None or lsm.state != "granted":
                box["result"] = Result("OK", message="already revoked")
            else:
                lsm.fire("revoke")
                self.authz.revoke(component, link)
                self.lattice.unlink(component, link)
                self._persist("link.del", component=component, link=link)
        box_result = self._run("unlink", token, "link.revoke", f"{component}/{link}", tenant, session=session, body=_body)
        return box_result

    def call(self, token, component: str, link: str, operation: str, *args, tenant: str, session="",
             deadline: Deadline | None = None, traceparent=None, payload_size: int = 0) -> Result:
        deadline = deadline or Deadline.after(5.0, self.mono)
        def _body(box):
            if self.mode == "isolated" and not self.partition.may_serve_existing():
                raise FabricError("PARTITIONED", "isolated serving window elapsed")
            if not self.partition.may_serve_existing():
                raise FabricError("PARTITIONED", "isolation serving window elapsed")
            if component in self.quarantined:
                raise FabricError("QUARANTINED", f"{component} quarantined")
            host = self.lattice.instances.get(component)
            if host in self.quarantined:
                raise FabricError("QUARANTINED", f"host {host} quarantined")
            self.limiter.check_payload(payload_size)
            self.authz.check_capability(box["principal"], component, link, operation, tenant)
            br = self.breakers.setdefault(f"{component}/{link}", CircuitBreaker(clock=self.mono))
            br.before()
            self.limiter.acquire(tenant)
            try:
                deadline.check("provider")
                t0 = self.mono()
                try:
                    value = self.lattice.call(component, link, operation, *args)
                except (rt.NotLinked, LookupError):
                    raise
                except Exception as e:  # provider fault
                    br.failure()
                    raise FabricError("PROVIDER_ERROR", f"provider raised {type(e).__name__}") from None
                br.success()
                self.metrics.observe("call_seconds", self.mono() - t0, host=host)
                deadline.check("response")
            finally:
                self.limiter.release(tenant)
            box["result"] = Result("OK", value=value)
        box_result = self._run("call", token, "component.call", f"{component}/{link}", tenant, session=session, mutating=False, traceparent=traceparent, deadline=deadline, body=_body)
        return box_result

    # ---------------------------------------------------------------- emergency controls (M49/M46)
    def quarantine(self, token, target: str, *, reason: str, session="") -> Result:
        def _body(box):
            self.quarantined.add(target)
            if target in self.comp_sm:
                self.comp_sm[target].fire("quarantine")
                for (c, l), s in self.link_sm.items():
                    if c == target and s.state == "granted":
                        self.authz.revoke(c, l); s.fire("revoke")
            if target in self.host_sm:
                self.host_sm[target].fire("quarantine")
                self.hosts[target].state = "quarantined"
            self.ledger.append("control.quarantine", box["principal"].id, {"target": target, "reason": reason})
        box_result = self._run("quarantine", token, "control.quarantine", target, "*", session=session, body=_body)
        return box_result

    def set_mode(self, token, mode: str, *, session="") -> Result:
        def _body(box):
            if mode not in MODES:
                raise FabricError("INVALID_ARGUMENT", f"mode must be one of {MODES}")
            self.mode = mode
            self.ledger.append("control.mode", box["principal"].id, {"mode": mode})
        box_result = self._run("mode", token, "control.freeze", mode, "*", session=session, body=_body)
        return box_result

    # ---------------------------------------------------------------- status (M58)
    def status(self) -> dict:
        from . import config as cfgmod
        return {"schema": "inv60.status/1", "version": VERSION, "mode": self.mode,
                "ready": self.mode != "frozen" and bool(self.hosts) and self.partition.connected_to_control,
                "live": True, "partition": self.partition.mode(),
                "hosts": {h: sm.state for h, sm in sorted(self.host_sm.items())},
                "components": {c: sm.state for c, sm in sorted(self.comp_sm.items())},
                "links": sum(1 for s in self.link_sm.values() if s.state == "granted"),
                "quarantined": sorted(self.quarantined), "lease_epoch": self.epoch,
                "ledger_head": list(self.ledger.head), "config_schema": cfgmod.CONFIG_SCHEMA_VERSION,
                "dependencies": {"identity": self.trust.issuer_available and self.trust.revocation_source_available,
                                 "policy": self.authz.policy_available, "state_store": self.store is not None},
                "limits": self.limiter.usage()}

    # ---------------------------------------------------------------- restart (M47)
    def _reconstruct(self) -> None:
        s = self.store.state
        for h, rec in s["hosts"].items():
            if rec.get("state") == "active":
                self.hosts[h] = pl.HostInfo(h, region=rec.get("region", "default"),
                                            dedicated_tenant=rec.get("dedicated"), capacity=rec.get("capacity", 64))
                self.host_sm[h] = host_machine(h, "active")
                self.lattice.add_host(h)
                self.detector.heartbeat(h)
        for c, rec in s["components"].items():
            self.comp_meta[c] = {k: rec[k] for k in ("tenant", "app", "regions", "ref")}
            st = rec.get("state", "failed")
            if st == "running" and rec.get("host") in self.hosts:
                self.lattice.instances[c] = rec["host"]
                self.hosts[rec["host"]].placed.append((rec["tenant"], rec["app"], c))
                self.comp_sm[c] = component_machine(c, "running")
            else:
                self.comp_sm[c] = component_machine(c, "failed")
        # links are runtime authority bound to live provider objects; after restart they
        # are reconstructed as *revoked* and must be re-granted (fail closed).
        for key in s["links"]:
            c, l = key.split("|", 1)
            self.link_sm[(c, l)] = link_machine(f"{c}/{l}", "revoked")
