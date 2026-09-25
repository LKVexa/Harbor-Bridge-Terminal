"""PDB evaluator (10), pod policy (11, 13-17), node health (12),
capacity/constraints/priority (18-20)."""
from __future__ import annotations

import unittest

import _support  # noqa: F401
from inv04_current_orchestration.runtime import objects as o
from inv04_current_orchestration.runtime.policy import (classify_for_drain, eviction_allowed, job_needs_replacement,
                                                        may_evict_from, node_state, pdb_status, quorum_safe,
                                                        stateful_order, termination_state, volume_blockers)
from inv04_current_orchestration.runtime.scheduling import place, plan_drain_capacity, preemption_candidates


def pods(n, workload="web", ready=True, ns="default"):
    return [o.make_pod(f"{workload}-{i}", workload, f"n{i}", ns=ns, ready=ready) for i in range(n)]


def pdb(**kw):
    return o.DisruptionBudget(o.Meta("b"), selector=(("app", "web"),), **kw)


class PdbTest(unittest.TestCase):
    def test_min_available_int_and_percent_round_up(self):
        ps = pods(4)
        self.assertEqual(pdb_status(pdb(min_available=3), ps).disruptions_allowed, 1)
        self.assertEqual(pdb_status(pdb(min_available="50%"), ps).desired_healthy, 2)
        self.assertEqual(pdb_status(pdb(min_available="51%"), ps).desired_healthy, 3)

    def test_max_unavailable_uses_controller_scale(self):
        ps = pods(3)
        st = pdb_status(pdb(max_unavailable=1, expected_pods=4), ps)  # one replica already missing
        self.assertEqual((st.expected, st.desired_healthy, st.disruptions_allowed), (4, 3, 0))
        self.assertEqual(pdb_status(pdb(max_unavailable="25%"), pods(4)).disruptions_allowed, 1)

    def test_exactly_one_field_and_value_validation(self):
        with self.assertRaises(ValueError):
            pdb_status(pdb(min_available=1, max_unavailable=1), pods(1))
        with self.assertRaises(ValueError):
            pdb_status(pdb(min_available="150%"), pods(1))
        with self.assertRaises(ValueError):
            pdb_status(pdb(min_available=True), pods(1))

    def test_selector_and_namespace_scoping(self):
        other_ns = pods(2, ns="other")
        self.assertEqual(pdb_status(pdb(min_available=1), other_ns).expected, 0)

    def test_eviction_decision_healthy_and_unhealthy_policies(self):
        ps = pods(2)
        self.assertEqual(eviction_allowed(ps[0], [pdb(min_available=2)], ps), (False, "disruption_budget"))
        self.assertTrue(eviction_allowed(ps[0], [pdb(min_available=1)], ps)[0])
        sick = ps[0].replace(ready=False)
        ps2 = [sick, ps[1]]
        self.assertEqual(eviction_allowed(sick, [pdb(min_available=2)], ps2)[1], "budget_unhealthy")
        self.assertTrue(eviction_allowed(sick, [pdb(min_available=2, unhealthy_pod_eviction_policy="AlwaysAllow")], ps2)[0])
        two = [pdb(min_available=0), o.DisruptionBudget(o.Meta("c"), selector=(("app", "web"),), min_available=0)]
        self.assertEqual(eviction_allowed(ps[0], two, ps), (False, "multiple_pdbs"))


class PodPolicyTest(unittest.TestCase):
    def test_classification_matrix(self):
        base = o.make_pod("p", "web", "n1")
        cases = {
            "mirror_static_pod": base.replace(mirror=True),
            "terminal_pod": base.replace(phase="Succeeded"),
            "daemonset_managed": o.make_pod("d", "ds", "n1", owner_kind="DaemonSet"),
            "unmanaged_pod": o.make_pod("u", "", "n1", owner_kind=""),
            "local_storage": base.replace(volumes=(o.Volume("data", local=True),)),
            "managed": base,
        }
        for reason, pod in cases.items():
            self.assertEqual(classify_for_drain(pod).reason, reason)
        self.assertEqual(classify_for_drain(cases["unmanaged_pod"]).action, "block")
        self.assertEqual(classify_for_drain(cases["unmanaged_pod"], force_unmanaged=True).action, "evict")
        self.assertEqual(classify_for_drain(cases["local_storage"], delete_emptydir_data=True).action, "evict")

    def test_statefulset_order_and_quorum(self):
        ss = [o.make_pod(f"db-{i}", "db", "n1", owner_kind="StatefulSet", ordinal=i) for i in range(3)]
        self.assertEqual([p.ordinal for p in stateful_order(ss)], [2, 1, 0])
        self.assertTrue(quorum_safe(ss, ss[0], 2))
        self.assertFalse(quorum_safe([ss[0], ss[1].replace(ready=False), ss[2]], ss[0], 2))

    def test_termination_lifecycle(self):
        p = o.make_pod("p", "web", "n1", grace_seconds=30)
        self.assertEqual(termination_state(p, 100), "running")
        import dataclasses
        dying = p.replace(meta=dataclasses.replace(p.meta, deletion_timestamp=100.0))
        self.assertEqual(termination_state(dying, 120), "terminating")
        self.assertEqual(termination_state(dying, 200), "stuck_terminating")
        fin = dying.replace(meta=dataclasses.replace(dying.meta, finalizers=("x",)))
        self.assertEqual(termination_state(fin, 200), "finalizer_blocked")

    def test_job_semantics(self):
        done = o.make_pod("j", "job", "n1", owner_kind="Job", phase="Succeeded")
        self.assertFalse(job_needs_replacement(done))
        self.assertTrue(job_needs_replacement(done.replace(phase="Running")))

    def test_volume_constraints(self):
        n_b = o.make_node("nb", zone="b")
        p = o.make_pod("p", "web", "na", volumes=(o.Volume("c1", zone="a"),))
        self.assertIn("c1:zone_mismatch", volume_blockers(p, n_b))
        rwop = o.make_pod("q", "web", "na", volumes=(o.Volume("c2", access_mode="ReadWriteOncePod"),))
        other = o.make_pod("r", "web", "na", volumes=(o.Volume("c2", access_mode="ReadWriteOncePod"),))
        self.assertIn("c2:rwop_in_use", volume_blockers(rwop, n_b, other_pods=[other]))


class NodeHealthTest(unittest.TestCase):
    def test_states(self):
        n = o.make_node("n", last_heartbeat=100)
        self.assertEqual(node_state(n, 110), "ready")
        self.assertEqual(node_state(n.replace(unschedulable=True), 110), "cordoned")
        self.assertEqual(node_state(n.replace(ready="False"), 110), "not_ready")
        self.assertEqual(node_state(n, 200), "unreachable")
        self.assertEqual(node_state(n, 200, partition_fraction=0.9), "partitioned")
        self.assertEqual(node_state(None, 0), "deleted")
        self.assertFalse(may_evict_from("partitioned"))


class SchedulingTest(unittest.TestCase):
    def test_capacity_taints_selectors_affinity(self):
        small = o.make_node("a", allocatable={"cpu_m": 150, "memory_mi": 1000, "ephemeral_mi": 1000, "pods": 10})
        tainted = o.make_node("b", taints=(o.Taint("gpu", "true"),))
        labelled = o.make_node("c", labels={"disk": "ssd"})
        nodes = [small, tainted, labelled]
        p = o.make_pod("p", "web", "", requests={"cpu_m": 200, "memory_mi": 10})
        self.assertEqual(place(p, nodes, []).node, "c")
        sel = p.replace(node_selector=(("disk", "hdd"),))
        pl = place(sel, nodes, [])
        self.assertIsNone(pl.node)
        self.assertTrue(any("insufficient:cpu_m" in r for r in pl.reasons))
        tol = p.replace(tolerations=(o.Toleration("gpu", "Equal", "true", "NoSchedule"),), node_selector=())
        self.assertIn(place(tol, [small, tainted], []).node, {"b"})

    def test_anti_affinity_and_spread(self):
        nodes = [o.make_node("a", zone="z1"), o.make_node("b", zone="z1"), o.make_node("c", zone="z2")]
        existing = [o.make_pod("w0", "web", "a", anti_affinity_key="topology.kubernetes.io/zone")]
        p = o.make_pod("w1", "web", "", anti_affinity_key="topology.kubernetes.io/zone")
        self.assertEqual(place(p, nodes, existing).node, "c")
        s0 = [o.make_pod("s0", "api", "a"), o.make_pod("s1", "api", "b")]
        sp = o.make_pod("s2", "api", "", spread_key="topology.kubernetes.io/zone", max_skew=1)
        self.assertEqual(place(sp, nodes, s0).node, "c")

    def test_drain_capacity_plan_reports_unplaceable(self):
        nodes = [o.make_node("a", allocatable={"cpu_m": 100, "memory_mi": 100, "ephemeral_mi": 1, "pods": 1}),
                 o.make_node("b", allocatable={"cpu_m": 100, "memory_mi": 100, "ephemeral_mi": 1, "pods": 1})]
        ps = [o.make_pod("x", "web", "a"), o.make_pod("y", "web", "a")]
        assign, fails = plan_drain_capacity(ps, nodes, ps, "a")
        self.assertEqual(len(assign), 1)
        self.assertEqual(len(fails), 1)

    def test_preemption_respects_priority_and_budget_protection(self):
        node = o.make_node("a", allocatable={"cpu_m": 100, "memory_mi": 100, "ephemeral_mi": 1, "pods": 2})
        low = o.make_pod("low", "batch", "a", priority=1, requests={"cpu_m": 100})
        hi = o.make_pod("hi", "api", "", priority=100, requests={"cpu_m": 100})
        self.assertEqual([p.meta.name for p in preemption_candidates(hi, node, [low], [node])], ["low"])
        self.assertIsNone(preemption_candidates(hi, node, [low], [node], protected_uids={low.meta.uid}))
        self.assertIsNone(preemption_candidates(hi.replace(preemption_policy="Never"), node, [low], [node]))


class AdapterBoundaryTest(unittest.TestCase):
    def test_from_k8s_pod_conversion(self):
        obj = {"kind": "Pod", "metadata": {"name": "a", "namespace": "ns", "uid": "u1", "resourceVersion": "7",
                                           "ownerReferences": [{"kind": "ReplicaSet", "name": "web-rs", "uid": "o1", "controller": True}]},
               "spec": {"nodeName": "n1", "containers": [{"resources": {"requests": {"cpu": "250m", "memory": "1Gi"}}}],
                        "tolerations": [{"key": "k", "operator": "Exists"}]},
               "status": {"phase": "Running", "conditions": [{"type": "Ready", "status": "True"}]}}
        p = o.from_k8s_pod(obj)
        self.assertEqual((p.meta.key, p.node, p.request("cpu_m"), p.request("memory_mi"), p.meta.resource_version),
                         ("ns/a", "n1", 250, 1024, 7))
        self.assertTrue(p.ready)
        with self.assertRaises(ValueError):
            o.from_k8s_pod({"kind": "Node"})


if __name__ == "__main__":
    unittest.main()
