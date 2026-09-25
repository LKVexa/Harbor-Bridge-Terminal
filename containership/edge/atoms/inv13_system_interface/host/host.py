"""End-to-end host: identity -> policy -> descriptors -> quotas -> providers -> audit/telemetry.

This is the integration surface exercised by tests/test_integration.py: every
guest-facing operation passes the control-plane guard, the descriptor check
(revocation/tenant/rights), quota admission, the concrete provider, then
metrics + durable audit.  Failures are ``Inv13Error`` with stable codes.
"""
from __future__ import annotations

import os
import time
from typing import Any

from .clocks import MonotonicClock, WallClock
from .control import ControlPlane
from .descriptors import DescriptorTable
from .errors import ErrorCode, Inv13Error
from .fs import Preopen
from .quotas import QuotaLedger
from .randomness import CsprngProvider
from .resources import ResourceTable
from .telemetry import Metrics, classify
from . import wit_surface


class Host:
    def __init__(self, *, policy, identity, audit, quotas: QuotaLedger, config=None) -> None:
        self.policy, self.identity, self.audit, self.quotas = policy, identity, audit, quotas
        self.descriptors = DescriptorTable()
        self.metrics = Metrics()
        self.control = ControlPlane(identity=identity, audit=audit, descriptors=self.descriptors, config=config)

    def instantiate(self, token: str, *, tenant: str, workload: str, world: str,
                    preopens: dict[str, tuple[str, set[str]]] | None = None) -> "HostInstance":
        preopens = preopens or {}
        err = None
        try:
            claims = self.identity.verify(token, role="runtime", workload=workload)
            caps = wit_surface.world_capabilities(world)
            decision = self.policy.enforce(tenant=tenant, workload=workload, world=world, capabilities=set(caps),
                                           preopens={k: v[0] for k, v in preopens.items()},
                                           rights={k: v[1] for k, v in preopens.items()})
            self.control.guard(workload)
            inst = HostInstance(self, tenant, workload, world, caps)
            prov = {"decision": decision.policy_digest + ":" + str(decision.rule_id), "actor": str(claims["sub"])}
            for cap in sorted(caps):
                inst.cap_desc[cap] = self.descriptors.mint(
                    tenant=tenant, workload=workload, capability=cap, scope={"world": world},
                    rights={"invoke"}, provenance=prov).id
            for logical, (host_root, rights) in preopens.items():
                self.quotas.acquire(tenant, workload, "preopens")
                d = self.descriptors.mint(tenant=tenant, workload=workload, capability="filesystem",
                                          scope={"logical": logical, "host_root": host_root},
                                          rights=set(rights), provenance=prov)
                inst.preopens[logical] = (d.id, Preopen(logical, host_root,
                                                        read_only=not ({"write", "create"} & set(rights))))
            self.audit.append(workload, "instantiate", "granted", {"world": world, "rule_id": decision.rule_id,
                                                                   "policy_digest": decision.policy_digest})
            return inst
        except Inv13Error as e:
            err = e
            self.audit.append(workload, "instantiate", "denied", {"world": world, "code": e.code.value})
            raise
        finally:
            self.metrics.inc("instantiations", op="instantiate", outcome=classify(err))


class HostInstance:
    def __init__(self, host: Host, tenant: str, workload: str, world: str, caps: frozenset[str]) -> None:
        self.host, self.tenant, self.workload, self.world, self.caps = host, tenant, workload, world, caps
        self.cap_desc: dict[str, str] = {}
        self.preopens: dict[str, tuple[str, Preopen]] = {}
        self.table = ResourceTable(capacity=host.quotas._wl["descriptors"])
        self._rand = CsprngProvider()
        self._mono, self._wall = MonotonicClock(), WallClock()

    def _gate(self, cap: str, op: str, *, mutation: bool = False) -> None:
        self.host.control.guard(self.workload, cap, mutation=mutation)
        if cap not in self.caps:
            raise Inv13Error(ErrorCode.CAP_NOT_GRANTED, cap)
        self.host.descriptors.check(self.cap_desc[cap], tenant=self.tenant, right="invoke")

    def _run(self, cap: str, op: str, fn, *, mutation: bool = False, detail: dict | None = None):
        t0, err = time.perf_counter_ns(), None
        try:
            self._gate(cap, op, mutation=mutation)
            return fn()
        except Inv13Error as e:
            err = e
            self.host.audit.append(self.workload, op, "denied", {**(detail or {}), "code": e.code.value})
            raise
        finally:
            self.host.metrics.inc("ops", capability=cap, op=op, outcome=classify(err))
            self.host.metrics.observe_us("op_latency", (time.perf_counter_ns() - t0) / 1000, op=op)

    # ---- filesystem
    def open(self, logical: str, path: str, flags: int = os.O_RDONLY) -> int:
        def go():
            if logical not in self.preopens:
                raise Inv13Error(ErrorCode.PREOPEN_NOT_FOUND)
            did, pre = self.preopens[logical]
            need = "write" if flags & (os.O_WRONLY | os.O_RDWR) else "read"
            self.host.descriptors.check(did, tenant=self.tenant, right=need)
            self.host.quotas.acquire(self.tenant, self.workload, "descriptors")
            try:
                fd = pre.open(path, flags)
            except BaseException:
                self.host.quotas.release(self.tenant, self.workload, "descriptors")
                raise
            def closer(f, t=self.tenant, w=self.workload):
                os.close(f)
                self.host.quotas.release(t, w, "descriptors")
            return self.table.push("fd", fd, on_drop=closer)
        return self._run("filesystem", "open", go, mutation=bool(flags & (os.O_WRONLY | os.O_RDWR)),
                         detail={"logical": logical, "path": path})

    def read(self, handle: int, n: int = 65536) -> bytes:
        return self._run("filesystem", "open", lambda: os.read(self.table.get(handle, "fd"), min(n, 1 << 20)))

    def write(self, handle: int, data: bytes) -> int:
        return self._run("filesystem", "open", lambda: os.write(self.table.get(handle, "fd"), data), mutation=True)

    def close(self, handle: int) -> None:
        self.table.drop(handle)

    # ---- other providers
    def random(self, n: int) -> bytes:
        return self._run("random", "random", lambda: self._rand.get(n))

    def monotonic(self) -> int:
        return self._run("monotonic-clock", "clock", self._mono.now)

    def shutdown(self) -> int:
        n = self.table.close_all()
        for _, pre in self.preopens.values():
            pre.close()
            self.host.quotas.release(self.tenant, self.workload, "preopens")
        self.preopens.clear()
        return n
