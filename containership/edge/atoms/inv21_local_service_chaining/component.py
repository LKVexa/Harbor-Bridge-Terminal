"""INV-21 - Local service chaining: pk_core component adapter.

The runtime lives in stdlib-only modules (``chain``, ``context``, ``policy``,
``residency``, ``transport`` ...). This module binds it to the pk_core
checklist/assessment framework and re-exports the 4.x public names.
"""
from __future__ import annotations

from pk_core.checklist import ChecklistItem, Finding
from pk_core.component import Component

from .contract import ELEMENT_ID, ELEMENT_NAME, build

from .chain import DEFAULT_MAX_DEPTH, DEFAULT_MAX_TELEMETRY_EVENTS, CapabilityChecker, Chainer, Hop, RemoteDispatch  # noqa: F401
from .errors import (CapabilityRefused, ChainCycle, ChainError, ChainTooDeep,  # noqa: F401
                     CrossTenantChain)
from .residency import Placement, Residency  # noqa: F401
from .telemetry import DecisionEvent  # noqa: F401


def _verify(condition, message="behavioural check failed"):
    """Fail a behavioural check even under ``python -O``."""
    if not condition:
        raise AssertionError(message)


class LocalServiceChainingComponent(Component):
    """Master-applied component for INV-21."""

    element_id = ELEMENT_ID
    element_name = ELEMENT_NAME

    def build_contract(self):
        return build()

    @staticmethod
    def _allow(*_args) -> bool:
        return True

    def assess_implementation(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_implementation(items)
        res = Residency("host-1")
        res.place("b", "acme", lambda ch, req, path, tenant, tid: ("local", "b", req))
        remote = []
        ch = Chainer(res, capability_checker=self._allow,
                     remote_dispatch=lambda c, t, r, p, tid: remote.append((c, t, tid)) or ("remote", c, r))
        _verify(ch.call("b", "acme", {"n": 1})[0] == "local")
        _verify(ch.call("elsewhere", "acme", {"n": 1})[0] == "remote")
        _verify(ch.hops_local == 1 and ch.hops_remote == 1 and remote == [("elsewhere", "acme", "t-0")])
        findings[0] = self.satisfied(
            items[0],
            "Co-resident calls dispatch directly and non-resident calls hand off through an injected remote dispatcher; both paths pass through the per-hop capability hook.",
            *self._evidence("component.py::Chainer.call"))
        return findings

    def assess_resilience(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_resilience(items)
        res = Residency("host-1")

        def recurse(ch, req, path, tenant, tid):
            return ch.call("b", tenant, req, path=path, trace_id=tid)

        res.place("b", "acme", recurse)
        ch = Chainer(res, capability_checker=self._allow)
        cycled = False
        try:
            ch.call("b", "acme", {})
        except ChainCycle:
            cycled = True
        _verify(cycled and ch.cycles_refused == 1)

        res2 = Residency("host-1")
        n = {"i": 0}

        def descend(chain, req, path, tenant, tid):
            n["i"] += 1
            return chain.call(f"s{n['i']}", tenant, req, path=path, trace_id=tid)

        for i in range(8):
            res2.place(f"s{i}", "acme", descend)
        ch2 = Chainer(res2, max_depth=3, capability_checker=self._allow)
        deep = False
        try:
            ch2.call("s0", "acme", {})
        except ChainTooDeep:
            deep = True
        _verify(deep and ch2.depth_exceeded == 1)
        findings[1] = self.satisfied(
            items[1],
            f"Cycles are refused and local recursion is bounded at {ch2.max_depth}; telemetry is bounded as well, preventing unbounded diagnostic memory growth.",
            *self._evidence("component.py::Chainer.call"))
        return findings

    def assess_security(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_security(items)
        res = Residency("host-1")
        res.place("b", "other-tenant", lambda ch, req, path, tenant, tid: ("local", "b", req))
        ch = Chainer(res, capability_checker=self._allow)
        crossed = False
        try:
            ch.call("b", "acme", {})
        except CrossTenantChain:
            crossed = True
        _verify(crossed and ch.hops_local == 0 and ch.cross_tenant_refused == 1)

        own = Residency("host-1")
        own.place("b", "acme", lambda *_: "should-not-run")
        denied = Chainer(own, capability_checker=lambda *_: False)
        refused = False
        try:
            denied.call("b", "acme", {})
        except CapabilityRefused:
            refused = True
        _verify(refused and denied.capability_refused == 1 and denied.hops_local == 0)
        findings[2] = self.satisfied(
            items[2],
            "Locality is not authority: cross-tenant calls are refused before dispatch and an injected per-hop capability policy can independently refuse same-tenant calls.",
            *self._evidence("component.py::Chainer._authorize"))
        return findings

    def assess_observability(self, items: list[ChecklistItem]) -> list[Finding]:
        findings = super().assess_observability(items)
        res = Residency("host-1")
        res.place("c", "acme", lambda ch, req, path, tenant, tid: ("local", "c", req))
        res.place("b", "acme", lambda ch, req, path, tenant, tid: ch.call("c", tenant, req, path=path, trace_id=tid))
        ch = Chainer(res, capability_checker=self._allow)
        ch.call("b", "acme", {}, trace_id="t-7")
        _verify([t for _, t in ch.trace] == ["t-7", "t-7"])
        _verify([d.route for d in ch.decisions] == ["local", "local"])
        findings[0] = self.satisfied(
            items[0],
            "Trace context survives each local hop and a bounded structured decision ledger records route, reason, depth, tenant and duration for every automated routing decision.",
            *self._evidence("component.py::DecisionEvent"))
        return findings


COMPONENT = LocalServiceChainingComponent
