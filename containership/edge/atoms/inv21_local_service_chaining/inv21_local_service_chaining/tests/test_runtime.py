"""Standalone runtime tests for INV-21 core chaining behavior.

These tests stub only the pk_core base classes so the local-chain primitive is
actually exercised even when the repository is audited without the sibling
pk_core package installed.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import types
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
PKG = "inv21_local_service_chaining"


def load_component():
    pkg = types.ModuleType(PKG)
    pkg.__path__ = [str(PKG_DIR)]
    sys.modules[PKG] = pkg

    contract_mod = types.ModuleType(f"{PKG}.contract")
    contract_mod.ELEMENT_ID = "INV-21"
    contract_mod.ELEMENT_NAME = "Local service chaining"
    contract_mod.build = lambda: None
    sys.modules[f"{PKG}.contract"] = contract_mod

    pk_core = types.ModuleType("pk_core")
    checklist = types.ModuleType("pk_core.checklist")
    component_base = types.ModuleType("pk_core.component")
    checklist.ChecklistItem = object
    checklist.Finding = object
    component_base.Component = object
    sys.modules["pk_core"] = pk_core
    sys.modules["pk_core.checklist"] = checklist
    sys.modules["pk_core.component"] = component_base

    spec = importlib.util.spec_from_file_location(f"{PKG}.component", PKG_DIR / "component.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


m = load_component()


class RuntimeTest(unittest.TestCase):
    def setUp(self):
        self.res = m.Residency("host-1")
        self.res.place("svc", "acme", lambda ch, req, path, tenant, tid: ("ok", req, path, tenant, tid))

    def test_local_dispatch_and_trace(self):
        ch = m.Chainer(self.res, capability_checker=lambda *_: True)
        out = ch.call("svc", "acme", {"x": 1}, trace_id="trace-1")
        self.assertEqual(out[0], "ok")
        self.assertEqual(ch.hops_local, 1)
        self.assertEqual(ch.trace, [("svc", "trace-1")])
        self.assertEqual(ch.decisions[-1].route, "local")

    def test_remote_dispatch_injection(self):
        calls = []
        ch = m.Chainer(self.res, capability_checker=lambda *_: True,
                       remote_dispatch=lambda *args: calls.append(args) or "net")
        self.assertEqual(ch.call("remote", "acme", 1), "net")
        self.assertEqual(calls[0][0:3], ("remote", "acme", 1))
        self.assertEqual(ch.hops_remote, 1)

    def test_cross_tenant_is_refused_before_handler(self):
        ch = m.Chainer(self.res, capability_checker=lambda *_: True)
        with self.assertRaises(m.CrossTenantChain):
            ch.call("svc", "other", {})
        self.assertEqual(ch.hops_local, 0)
        self.assertEqual(ch.cross_tenant_refused, 1)

    def test_capability_is_rechecked_every_hop(self):
        checks = []
        ch = m.Chainer(self.res, capability_checker=lambda *a: checks.append(a[0]) or False)
        with self.assertRaises(m.CapabilityRefused):
            ch.call("svc", "acme", {})
        self.assertEqual(checks, ["svc"])
        self.assertEqual(ch.capability_refused, 1)

    def test_cycle_and_depth_bounds(self):
        cyc = m.Residency("h")
        cyc.place("a", "t", lambda ch, req, path, tenant, tid: ch.call("a", tenant, req, path=path, trace_id=tid))
        ch = m.Chainer(cyc, capability_checker=lambda *_: True)
        with self.assertRaises(m.ChainCycle):
            ch.call("a", "t", {})

        deep = m.Residency("h")
        deep.place("a", "t", lambda ch, req, path, tenant, tid: ch.call("b", tenant, req, path=path, trace_id=tid))
        deep.place("b", "t", lambda ch, req, path, tenant, tid: ch.call("c", tenant, req, path=path, trace_id=tid))
        deep.place("c", "t", lambda *_: "bad")
        ch2 = m.Chainer(deep, max_depth=2, capability_checker=lambda *_: True)
        with self.assertRaises(m.ChainTooDeep):
            ch2.call("a", "t", {})
        self.assertEqual(ch2.depth_exceeded, 1)

    def test_residency_snapshot_cannot_mutate_authority(self):
        snapshot = self.res.table
        snapshot["svc"] = ("evil", lambda *_: None)
        self.assertEqual(self.res.resolve("svc").tenant, "acme")

    def test_telemetry_is_bounded(self):
        ch = m.Chainer(self.res, capability_checker=lambda *_: True, max_telemetry_events=2)
        for _ in range(4):
            ch.call("svc", "acme", {})
        self.assertEqual(len(ch.trace), 2)
        self.assertEqual(len(ch.decisions), 2)

    def test_invalid_configuration_rejected(self):
        for value in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                m.Chainer(self.res, max_depth=value)
        with self.assertRaises(ValueError):
            m.Residency("")


if __name__ == "__main__":
    unittest.main()
