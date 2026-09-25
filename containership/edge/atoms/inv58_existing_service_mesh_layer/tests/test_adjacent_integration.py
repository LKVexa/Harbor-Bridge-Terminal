"""MC-007 / MC-028: adjacent-layer integration via contract test doubles.

INV-48 Service communication APIs (upstream: app retry policy)  -> reconcile
PLN-07 Security plane (upstream: issues SPIFFE identities)      -> identity
INV-59 Application authorization (downstream: consumes identity)
GAP-09 Unified observability (peer: one trace, both layers' retries)
The doubles implement only the documented contract of each neighbour
(docs/INTERFACES.md §Adjacent layers); live-topology runs are BLOCKED (see RTM).
"""
from __future__ import annotations

import unittest

from _support import CTRL_A, NODE, errors, make_service, telemetry


class INV48Double:
    """Emits app retry policies as INV-48 would: per route, attempts >= 1."""
    policies = {"orders->payments": 3, "cart->inventory": 1, "search->index": 5}


class PLN07Double:
    """Issues SPIFFE SVID SANs for workloads in a trust domain."""
    def __init__(self, td="estate.local"):
        self.td = td

    def issue(self, tenant, sa):
        return f"spiffe://{self.td}/ns/{tenant}/sa/{sa}"


class INV59Double:
    """Accepts only runtime identities; rejects anything else."""
    def __init__(self):
        self.grants = {"runtime:ns/alpha/sa/orders": {"payments:charge"}}

    def check(self, runtime_identity, action):
        if not runtime_identity.startswith("runtime:"):
            raise ValueError("INV-59 requires a mapped runtime identity")
        return action in self.grants.get(runtime_identity, set())


class GAP09Double:
    """Collects spans keyed by trace id from both layers."""
    def __init__(self):
        self.spans = []


class AdjacentIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.svc, self.clock, _ = make_service()

    def test_inv48_policies_reconciled_to_single_owner(self):
        mesh_retries = 3
        for route, app in INV48Double.policies.items():
            r = self.svc.reconcile(CTRL_A, "alpha", route, app, mesh_retries)
            self.assertLessEqual(r["effective_attempts"], r["budget"])
            self.assertFalse(r["app"] > 1 and r["mesh"] > 1)

    def test_pln07_identity_flows_to_inv59(self):
        pln, inv59 = PLN07Double(), INV59Double()
        mapped = self.svc.map_identity(NODE, "alpha", pln.issue("alpha", "orders"))["runtime_identity"]
        self.assertTrue(inv59.check(mapped, "payments:charge"))
        self.assertFalse(inv59.check(self.svc.map_identity(NODE, "alpha", pln.issue("alpha", "cron"))["runtime_identity"], "payments:charge"))

    def test_pln07_foreign_domain_never_reaches_inv59(self):
        pln = PLN07Double("other.domain")
        with self.assertRaises(errors.MeshError) as cm:
            self.svc.map_identity(NODE, "alpha", pln.issue("alpha", "orders"))
        self.assertEqual(cm.exception.code, "E_IDENTITY_UNMAPPABLE")

    def test_gap09_sees_one_trace_across_layers(self):
        gap = GAP09Double()
        upstream = telemetry.TraceContext.new()
        gap.spans.append(("app", upstream.trace_id))
        self.svc.reconcile(CTRL_A, "alpha", "orders->payments", 3, 3, traceparent=upstream.header())
        entry = self.svc.explain(CTRL_A, "alpha", "orders->payments")[-1]
        gap.spans.append(("inv58", entry["correlation_id"]))
        self.assertEqual({t for _, t in gap.spans}, {upstream.trace_id})

    def test_neighbour_failure_paths(self):
        with self.assertRaises(errors.MeshError):
            self.svc.reconcile(CTRL_A, "alpha", "orders->payments", 0, 3)  # malformed INV-48 policy
        self.svc.set_dependency("identity", False)  # PLN-07 outage
        with self.assertRaises(errors.MeshError) as cm:
            self.svc.map_identity(NODE, "alpha", PLN07Double().issue("alpha", "orders"))
        self.assertEqual(cm.exception.code, "E_DEPENDENCY_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()
