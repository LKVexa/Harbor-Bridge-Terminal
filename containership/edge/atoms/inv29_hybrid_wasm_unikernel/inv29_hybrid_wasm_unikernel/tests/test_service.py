"""Service wiring: readiness logic, version/release correlation, latency and
gauge emission, control-file enforcement (MC079-MC083, MC087, MC089)."""
import io
import json
import pathlib
import tempfile
import unittest
import urllib.error
import urllib.request

import _fixtures as F
from inv29_hybrid_wasm_unikernel import deps as D
from inv29_hybrid_wasm_unikernel.service import Service


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kr = F.keyring()
        self.log = io.StringIO()
        self.svc = Service.build(self.kr, F.policy(), signing_key_id=F.SIGN_KEY, state_dir=pathlib.Path(self.tmp.name),
                                 release="sha256:" + "c" * 64, log_stream=self.log, clock=F.Clock())

    def tearDown(self):
        self.tmp.cleanup()

    def test_submit_emits_latency_gauges_and_release_tagged_logs(self):
        doc = self.svc.submit(F.request(self.kr), traceparent="00-" + "a" * 32 + "-" + "b" * 16 + "-01")
        self.assertEqual(doc["state"], "ADMITTED")
        text = self.svc.metrics.exposition()
        self.assertIn("inv29_admission_latency_ms_count 1", text)
        self.assertIn('inv29_hybrid_instances{state="ADMITTED"} 1.0', text)
        self.assertIn("inv29_replay_cache_fill_ratio", text)
        self.assertIn("inv29_min_layer_count 2.0", text)
        lines = [json.loads(l) for l in self.log.getvalue().splitlines()]
        self.assertTrue(all(l["release"] == "sha256:" + "c" * 64 for l in lines))
        self.assertIn("a" * 32, {l["trace_id"] for l in lines})

    def test_readiness_is_false_without_dependencies_or_when_disabled(self):
        ok, detail = self.svc.ready()
        if D.pk_core_status().state != D.AVAILABLE:
            self.assertFalse(ok)
            self.assertTrue(any("pk_core" in r for r in detail["reasons"]))
        self.svc.control.write("drill", "test")
        self.svc.control.apply(self.svc.admitter)
        self.assertTrue(any("emergency" in r for r in self.svc.ready()[1]["reasons"]))
        doc = self.svc.submit(F.request(self.kr))
        self.assertEqual(doc["error"]["code"], "INV29-E-DISABLED")

    def test_version_endpoint_tracks_policy_generation(self):
        srv = self.svc.serve(port=0)
        url = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            v1 = json.load(urllib.request.urlopen(url + "/version", timeout=5))
            self.svc.admitter.set_policy(F.policy(generation=7))
            v2 = json.load(urllib.request.urlopen(url + "/version", timeout=5))
            self.assertEqual((v1["policy_generation"], v2["policy_generation"]), (1, 7))
            self.assertEqual(v2["release"], "sha256:" + "c" * 64)
            with self.assertRaises(urllib.error.HTTPError) as cm:
                urllib.request.urlopen(url + "/readyz", timeout=5)
            self.assertEqual(cm.exception.code, 503)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
