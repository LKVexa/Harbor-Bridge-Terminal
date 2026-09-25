"""Items 2-4, 16-18, 30-31, 36-37, 39-43, 63: engine, adapter, runtime, telemetry."""
import copy
import json
import threading
import unittest
import urllib.request

from hkit import ADMIN, build, hardened_pod, request

from inv03_container_hardening.hardening.admission import (
    WEBHOOK_CONFIGURATION, extract_pod_spec, make_server, review)
from inv03_container_hardening.hardening.integrations import (
    Rollout, VerdictGate, check_image_provenance, check_node_attestation, ids_finding_to_action)
from inv03_container_hardening.hardening.runtime import parse_runsc_version
from inv03_container_hardening.hardening.telemetry import (
    ALERT_RULES, RETENTION_POLICY, StructuredLogger, parse_traceparent, redact)


def admission_review(obj, op="CREATE", ns="team-a"):
    return {"apiVersion": "admission.k8s.io/v1", "kind": "AdmissionReview",
            "request": {"uid": "u-1", "operation": op, "namespace": ns, "object": obj}}


def deployment(pod):
    return {"kind": "Deployment", "metadata": {"name": "api"}, "spec": {"template": {"spec": pod}}}


SCOPE = {"environment": "prod", "site": "eu1", "default_deny": {"team-a": True}}


class Runtime(unittest.TestCase):
    def test_item02_version_parse_and_minimum(self):
        self.assertEqual(parse_runsc_version("runsc version release-20240807.0\nspec: 1.1"), (20240807, 0))
        self.assertIsNone(parse_runsc_version("runc 1.1.12"))
        eng, ft, _ = build()
        eng.runtimes.report("old", "runsc", "runsc version release-20230101.0", True, int(ft.t))
        self.assertFalse(eng.runtimes.check("gvisor", "old")[0])
        self.assertIn("node-1", eng.runtimes.inventory())

    def test_item04_fail_closed_runtime_selection(self):
        eng, ft, _ = build()
        self.assertTrue(eng.decide(request(node="node-1"))["admit"])
        self.assertEqual(eng.decide(request(node="node-9"))["reason"], "SANDBOX_RUNTIME_UNAVAILABLE")
        eng.runtimes.report("node-2", "runsc", "runsc version release-20240807.0", False, int(ft.t))
        self.assertFalse(eng.decide(request(node="node-2"))["admit"])
        # silent downgrade on a node is refused even if the new version is above the floor
        eng.runtimes.report("node-1", "runsc", "runsc version release-20240201.0", True, int(ft.t))
        self.assertFalse(eng.decide(request(node="node-1"))["admit"])


class Adapter(unittest.TestCase):
    def setUp(self):
        self.eng, *_ = build()

    def test_item03_all_workload_kinds_extracted(self):
        pod = hardened_pod()
        objs = {
            "Pod": {"kind": "Pod", "spec": pod},
            "CronJob": {"kind": "CronJob", "spec": {"jobTemplate": {"spec": {"template": {"spec": pod}}}}},
        }
        for k in ("Deployment", "StatefulSet", "DaemonSet", "Job", "ReplicaSet", "ReplicationController"):
            objs[k] = {"kind": k, "spec": {"template": {"spec": pod}}}
        for k, o in objs.items():
            self.assertEqual(extract_pod_spec(o), (k, pod), k)

    def test_item03_review_allows_and_denies(self):
        ok = review(self.eng, admission_review(deployment(hardened_pod())), SCOPE)
        self.assertTrue(ok["response"]["allowed"], ok)
        self.assertEqual(ok["response"]["uid"], "u-1")
        bad_pod = hardened_pod()
        bad_pod["hostNetwork"] = True
        no = review(self.eng, admission_review(deployment(bad_pod)), SCOPE)
        self.assertFalse(no["response"]["allowed"])
        self.assertIn("host-namespaces", no["response"]["status"]["message"])
        # namespace without default-deny is refused (item 15 wiring)
        self.assertFalse(review(self.eng, admission_review(deployment(hardened_pod()), ns="team-b"), SCOPE)
                         ["response"]["allowed"])

    def test_item03_malformed_reviews_deny(self):
        for body in (None, {}, {"apiVersion": "admission.k8s.io/v1beta1"},
                     admission_review({"kind": "Unknown"}), admission_review({"kind": "Deployment"})):
            self.assertFalse(review(self.eng, body, SCOPE)["response"]["allowed"], body)

    def test_item03_webhook_configuration_fails_closed(self):
        w = WEBHOOK_CONFIGURATION["webhooks"][0]
        self.assertEqual(w["failurePolicy"], "Fail")
        self.assertIn("pods/ephemeralcontainers", w["rules"][0]["resources"])

    def test_item03_http_server_end_to_end(self):
        srv = make_server(self.eng, "127.0.0.1", 0, SCOPE)
        t = threading.Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            base = f"http://127.0.0.1:{srv.server_address[1]}"
            body = json.dumps(admission_review(deployment(hardened_pod()))).encode()
            r = urllib.request.urlopen(urllib.request.Request(base + "/validate", body,
                                                              {"Content-Type": "application/json"}))
            self.assertTrue(json.loads(r.read())["response"]["allowed"])
            r = urllib.request.urlopen(urllib.request.Request(base + "/validate", b"{not json",
                                                              {"Content-Type": "application/json"}))
            self.assertFalse(json.loads(r.read())["response"]["allowed"])
            self.assertEqual(urllib.request.urlopen(base + "/readyz").status, 200)
            self.assertIn(b"inv03_decisions_total", urllib.request.urlopen(base + "/metrics").read())
        finally:
            srv.shutdown()
            srv.server_close()


class Lifecycle(unittest.TestCase):
    def test_item16_17_drift_and_quarantine(self):
        eng, *_ = build()
        req = request()
        self.assertTrue(eng.decide(req)["admit"])
        wl = req["workload"]
        self.assertFalse(eng.reconcile(wl, req["pod"], "runsc")["drift"])
        mutated = copy.deepcopy(req["pod"])
        mutated["containers"][0]["securityContext"]["privileged"] = True
        r = eng.reconcile(wl, mutated, "runsc")
        self.assertTrue(r["drift"])
        self.assertEqual([s["op"] for s in r["action"]["steps"]][:3], ["label", "network_isolate", "freeze"])
        self.assertTrue(eng.reconcile(wl, req["pod"], "runc")["drift"])  # handler swapped after admission
        self.assertTrue(eng.reconcile("never/seen", req["pod"], "runsc")["drift"])

    def test_item18_emergency_deny_all(self):
        eng, *_ = build()
        eng.set_emergency(ADMIN, True, "INC-7 container escape suspected")
        d = eng.decide(request())
        self.assertEqual((d["admit"], d["reason"]), (False, "EMERGENCY_DENY_ALL"))
        eng.set_emergency(ADMIN, False, "INC-7 contained")
        self.assertTrue(eng.decide(request())["admit"])
        self.assertEqual([e["kind"] for e in eng.ledger.events()].count("emergency.toggle"), 2)


class Integrations(unittest.TestCase):
    KEY = b"v" * 32

    def test_items30_31_36_verdicts(self):
        gate = VerdictGate({"scanner": self.KEY, "attestor": self.KEY}, max_age=60)
        pod = hardened_pod()
        img = pod["containers"][0]["image"]
        good = {img: VerdictGate.seal(self.KEY, "scanner", img, True, 1000)}
        self.assertEqual(check_image_provenance(pod, good, gate, 1010), [])
        self.assertTrue(check_image_provenance(pod, {}, gate, 1010))
        self.assertTrue(check_image_provenance(pod, good, gate, 2000))  # stale
        forged = {img: VerdictGate.seal(b"x" * 32, "scanner", img, True, 1000)}
        self.assertTrue(check_image_provenance(pod, forged, gate, 1010))
        pod["containers"][0]["image"] = "registry.example/app:latest"
        self.assertTrue(check_image_provenance(pod, good, gate, 1010))
        att = {"node-1": VerdictGate.seal(self.KEY, "attestor", "node-1", True, 1000)}
        self.assertTrue(check_node_attestation("node-1", att, gate, 1001)[0])
        self.assertFalse(check_node_attestation("node-2", att, gate, 1001)[0])

    def test_item37_ids_to_quarantine(self):
        eng, *_ = build()
        gate = VerdictGate({"ids": self.KEY})
        f = {"workload": "w", "verdict": VerdictGate.seal(self.KEY, "ids", "w", False, 1000)}
        out = ids_finding_to_action(eng, f, gate, 1001)
        self.assertTrue(out["accepted"] and out["intrusion"] and out["plan"])
        spoof = {"workload": "w", "verdict": VerdictGate.seal(b"z" * 32, "ids", "w", False, 1000)}
        self.assertFalse(ids_finding_to_action(eng, spoof, gate, 1001)["accepted"])

    def test_item63_rollout(self):
        r = Rollout()
        self.assertEqual([r.gate(0.01, 0.01, 0) for _ in range(5)],
                         ["ADVANCED", "ADVANCED", "ADVANCED", "ADVANCED", "COMPLETE"])
        r = Rollout()
        r.gate(0.01, 0.01, 0)
        self.assertEqual(r.gate(0.01, 0.2, 0), "ROLLED_BACK")
        self.assertEqual(r.percent(), 0)
        self.assertFalse(r.cohort_enabled("node-1"))
        r = Rollout()
        r.freeze()
        self.assertEqual(r.gate(0, 0, 0), "HELD")
        share = sum(Rollout(stage=2).cohort_enabled(f"n{i}") for i in range(2000)) / 2000
        self.assertAlmostEqual(share, 0.25, delta=0.05)


class Observability(unittest.TestCase):
    def test_items39_41_42_43_decision_is_explained_traced_metered(self):
        eng, *_ = build()
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        lineage = {"release": "api-1.4.2", "image_digests": ["sha256:" + "0" * 64],
                   "deployment_revision": 7, "node": None, "topology_ref": "tg://eu1/api"}
        d = eng.decide(request(traceparent=tp, lineage=lineage))
        self.assertEqual(d["trace"]["trace_id"], "a" * 32)
        self.assertNotEqual(d["trace"]["span_id"], "b" * 16)
        self.assertEqual(d["lineage"]["release"], "api-1.4.2")
        self.assertTrue(d["baseline_digest"].startswith("sha256:"))
        self.assertIn("inputs_digest", d["explain"])
        eng.decide(request(pod={"containers": [{"name": "x"}]}))
        text = eng.metrics.prometheus()
        self.assertIn('inv03_decisions_total{reason="ADMIT"} 1', text)
        self.assertIn('inv03_denials_total{control="sandbox-runtime"} 1', text)
        self.assertIn("inv03_eval_ms_count 2", text)
        self.assertEqual(len(eng.logger.sink), 2)

    def test_item40_redaction(self):
        log = StructuredLogger()
        rec = log.log("info", "x", token="abc", nested={"password": "p", "note": "Bearer eyJhbGciOi.xyz"},
                      aws="AKIAABCDEFGHIJKLMNOP")
        s = json.dumps(rec)
        for leak in ("abc", '"p"', "eyJhbGciOi", "AKIAABCDEFGHIJKLMNOP"):
            self.assertNotIn(leak, s)
        self.assertEqual(redact({"a": 1}), {"a": 1})

    def test_item41_traceparent_validation(self):
        self.assertIsNone(parse_traceparent("00-" + "0" * 32 + "-" + "1" * 16 + "-01"))
        self.assertIsNone(parse_traceparent("garbage"))
        self.assertIsNone(parse_traceparent(None))

    def test_items44_45_policy_and_alert_rules_are_data(self):
        self.assertIn("PROPOSED", RETENTION_POLICY["status"])
        classes = {r["class"] for r in ALERT_RULES}
        self.assertTrue({"attack_indicator", "dependency_failure", "software_defect",
                         "exception_expiry_risk"} <= classes)

    def test_audit_failure_converts_admit_to_deny(self):
        eng, *_ = build()
        eng.ledger.append = lambda *a, **k: (_ for _ in ()).throw(OSError("disk full"))
        d = eng.decide(request())
        self.assertEqual((d["admit"], d["reason"]), (False, "DEPENDENCY_FAILURE"))


if __name__ == "__main__":
    unittest.main()
