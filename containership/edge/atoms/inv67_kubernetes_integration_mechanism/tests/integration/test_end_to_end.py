"""Adjacent-layer integration (item 49) and the final-gate representative flow:
create -> identity/authz -> compat -> translate -> place -> status -> delete."""
import unittest

import _support as S

State = S.lifecycle.State


class EndToEnd(unittest.TestCase):
    def test_full_lifecycle(self):
        h = S.Harness()
        h.kube.apply(S.workload())
        h.settle(3)
        o = h.obj()
        self.assertIn(S.controller.FINALIZER, o["metadata"]["finalizers"])
        st = o["status"]
        self.assertEqual(st["state"], "Placed")
        self.assertEqual(st["observedGeneration"], 1)
        self.assertEqual(st["identity"]["tenant"], "tenant-a")
        app = st["appId"]
        self.assertEqual(h.rt.launches, 1)
        h.rt.advance(app, State.RUNNING)
        h.ctrl.queue.add(("team-a", "web"))
        h.settle(2)
        o = h.obj()
        self.assertEqual(o["status"]["phase"], "Running")
        ready = S.status.get_condition(o["status"]["conditions"], "Ready")
        self.assertEqual(ready["status"], "True")
        # delete -> downstream cancel -> finalizer removed -> object gone
        h.kube.delete("team-a", "web")
        h.settle(3)
        with self.assertRaises(S.kube.ApiError):
            h.obj()
        self.assertEqual(h.rt.placements[app]["state"], "Cancelled")
        ok, _ = S.audit.AuditLog.verify(h.audit.records, h.audit.head)
        self.assertTrue(ok)
        actions = [r["action"] for r in h.audit.records]
        self.assertIn("runtime.place", actions)
        self.assertIn("runtime.cancel", actions)

    def test_idempotent_reconcile_no_duplicate_launch(self):
        h = S.Harness()
        h.kube.apply(S.workload())
        for _ in range(5):
            h.settle(3)
            h.ctrl.resync()
        self.assertEqual(h.rt.launches, 1)

    def test_new_generation_replaces_placement(self):
        h = S.Harness()
        h.kube.apply(S.workload())
        h.settle(3)
        first = h.obj()["status"]["attemptId"]
        w = S.workload()
        w["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"]["cpu"] = "500m"
        h.kube.apply(w)
        h.settle(3)
        st = h.obj()["status"]
        self.assertEqual(st["observedGeneration"], 2)
        self.assertNotEqual(st["attemptId"], first)
        self.assertEqual(h.rt.launches, 2)

    def test_unsupported_workload_refused_before_side_effect(self):
        h = S.Harness()
        h.kube.apply(S.workload(hostNetwork=True))
        h.settle(3)
        st = h.obj()["status"]
        self.assertEqual(st["state"], "Blocked")
        self.assertEqual(st["lastError"]["code"], "PK_K8S_UNSUPPORTED_FIELD")
        self.assertEqual(h.rt.launches, 0)
        self.assertTrue(any(e["type"] == "Warning" for e in h.kube.events))

    def test_multi_unit_partial_failure_aggregates_failed(self):
        h = S.Harness()
        cs = [{"name": n, "image": S.IMAGE, "resources": {}} for n in ("a", "b")]
        h.kube.apply(S.workload(containers=cs))
        h.settle(3)
        app = h.obj()["status"]["appId"]
        h.rt.advance(app, State.RUNNING)
        h.rt.advance(app, State.FAILED, unit="b")
        h.ctrl.queue.add(("team-a", "web"))
        h.settle(2)
        self.assertEqual(h.obj()["status"]["phase"], "Failed")


if __name__ == "__main__":
    unittest.main()
