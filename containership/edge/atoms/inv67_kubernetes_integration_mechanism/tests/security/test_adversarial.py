"""Adversarial security suite (item 29): each case must be refused before any
runtime side effect, with a stable code, and without leaking secrets."""
import json
import unittest

import _support as S


class Adversarial(unittest.TestCase):
    def run_case(self, wl, bindings=None, **cfg):
        h = S.Harness(cfg=cfg or None, bindings=bindings)
        h.kube.apply(wl)
        h.settle(3)
        md = wl["metadata"]
        return h, h.obj(md["name"], md["namespace"])["status"]

    def assert_refused(self, wl, code, **kw):
        h, st = self.run_case(wl, **kw)
        self.assertEqual(h.rt.launches, 0, st)
        self.assertEqual(st["lastError"]["code"], code, st)
        return h, st

    def test_privileged_hostpath_hostnetwork(self):
        wl = S.workload(hostNetwork=True, volumes=[{"name": "h", "hostPath": {"path": "/"}}])
        wl["spec"]["template"]["spec"]["containers"][0]["securityContext"] = {"privileged": True}
        _, st = self.assert_refused(wl, "PK_K8S_UNSUPPORTED_FIELD")
        self.assertIn("privileged", st["lastError"]["message"])

    def test_unsigned_or_unpinned_or_foreign_image(self):
        for img in ["registry.example.org/web:latest", "evil.io/web" + S.DIGEST, "registry.example.org/web@sha256:" + "b" * 64]:
            with self.subTest(img=img):
                self.assert_refused(S.workload(image=img), "INV67_ARTIFACT_UNVERIFIED")

    def test_cross_tenant_namespace_not_bound(self):
        self.assert_refused(S.workload(ns="kube-system"), "INV67_UNAUTHORIZED")

    def test_watch_scope_enforced(self):
        self.assert_refused(S.workload(ns="team-b"), "INV67_UNAUTHORIZED", watchNamespaces=["team-a"])

    def test_uncertified_feature(self):
        self.assert_refused(S.workload(), "INV67_INCOMPATIBLE", certifiedFeatures=["cpu"])

    def test_template_metadata_smuggling(self):
        wl = S.workload()
        wl["spec"]["template"]["metadata"]["ownerReferences"] = [{"name": "x"}]
        self.assert_refused(wl, "PK_K8S_UNSUPPORTED_FIELD")

    def test_env_secret_not_echoed_in_status_or_audit(self):
        wl = S.workload()
        wl["spec"]["template"]["spec"]["containers"][0]["env"] = [{"name": "PASSWORD", "value": "hunter2-VERY-SECRET"}]
        h, st = self.assert_refused(wl, "PK_K8S_UNSUPPORTED_FIELD")
        blob = json.dumps(st) + json.dumps(h.audit.records) + json.dumps(h.kube.events) + h.ctrl.metrics.render()
        self.assertNotIn("hunter2-VERY-SECRET", blob)

    def test_oversized_and_hostile_values(self):
        cases = [
            S.workload(containers=[{"name": "c", "image": S.IMAGE, "resources": {"requests": {"cpu": "9" * 200}}}]),
            S.workload(containers=[{"name": "c", "image": S.IMAGE, "resources": {"requests": {"cpu": "-1"}}}]),
            S.workload(containers=[{"name": "c", "image": S.IMAGE, "resources": {"requests": {"cpu": "1e400"}}}]),
            S.workload(containers="not-a-list"),
        ]
        for wl in cases:
            with self.subTest():
                h, st = self.run_case(wl)
                self.assertEqual(h.rt.launches, 0)
                self.assertEqual(st["state"], "Blocked")

    def test_frozen_blocks_launch_but_allows_delete(self):
        h = S.Harness()
        h.ctrl.switch.freeze("sev1")
        h.kube.apply(S.workload())
        h.settle(3, step=1)
        self.assertEqual(h.rt.launches, 0)
        self.assertEqual(h.obj()["status"]["lastError"]["code"], "INV67_FROZEN")
        h.kube.delete("team-a", "web")
        h.settle(3, step=40)
        with self.assertRaises(S.kube.ApiError):
            h.obj()

    def test_stale_leader_fencing(self):
        rt = S.downstream.InMemoryRuntime()
        rt.fence.admit(5)
        env = S.downstream.envelope({"units": []}, {"appId": "app-x"}, "k", 4)
        with self.assertRaises(S.lifecycle.PlaneError) as e:
            rt.place(env)
        self.assertEqual(e.exception.code, "INV67_NOT_LEADER")
        with self.assertRaises(S.lifecycle.PlaneError):
            rt.cancel("app-x", None)


if __name__ == "__main__":
    unittest.main()
