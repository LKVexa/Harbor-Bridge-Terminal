import json
import os
import unittest
import urllib.error
import urllib.request

from gap07_artifact_provenance_signing.policy import PolicyBundle, evaluate
from gap07_artifact_provenance_signing.service import make_server, serve_in_thread
from gap07_artifact_provenance_signing.tests.fixtures import Env, T0

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Gap13Conformance(unittest.TestCase):
    def test_fixture_contract(self):
        e = Env()
        with open(os.path.join(HERE, "fixtures", "gap13", "policy_bundle.example.json")) as fh:
            body = json.load(fh)["body"]
        with open(os.path.join(HERE, "fixtures", "gap13", "query_allow.example.json")) as fh:
            q = json.load(fh)
        b = PolicyBundle.from_signed(e.cfg("policy-bundle", body), e.authorities, now=T0 + 100)
        d = evaluate(b, q["facts"])
        self.assertEqual({k: d[k] for k in q["expected"]}, q["expected"])
        facts = dict(q["facts"], kind="grant")
        self.assertEqual(evaluate(b, facts)["reason_code"], "POLICY_DENY")
        facts = dict(q["facts"], signatures=[dict(q["facts"]["signatures"][0], profile="reference")])
        self.assertEqual(evaluate(b, facts)["reason_code"], "SIGNER_UNTRUSTED")

    def test_incompatible_adapter_version_refused(self):
        e = Env()
        with open(os.path.join(HERE, "fixtures", "gap13", "policy_bundle.example.json")) as fh:
            body = json.load(fh)["body"]
        from gap07_artifact_provenance_signing.errors import GapError
        with self.assertRaises(GapError) as cm:
            PolicyBundle.from_signed(e.cfg("policy-bundle", dict(body, adapter_version=2)), e.authorities, now=T0)
        self.assertEqual(cm.exception.code, "POLICY_INVALID")
        bad_rule = dict(body["rules"][0], require=dict(body["rules"][0]["require"], future_field=True))
        with self.assertRaises(GapError):
            PolicyBundle.from_signed(e.cfg("policy-bundle", dict(body, rules=[bad_rule])), e.authorities, now=T0)


class HttpService(unittest.TestCase):
    def test_endpoints(self):
        e = Env()
        srv = make_server(e.ctl, port=0)
        serve_in_thread(srv)
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        try:
            def post(obj):
                req = urllib.request.Request(base + "/admit", data=json.dumps(obj).encode(), method="POST", headers={"Content-Type": "application/json"})
                try:
                    with urllib.request.urlopen(req, timeout=10) as r:
                        return r.status, json.loads(r.read())
                except urllib.error.HTTPError as err:
                    return err.code, json.loads(err.read())
            st, d = post(e.full_request())
            self.assertEqual((st, d["outcome"]), (200, "allow"))
            st, d = post(e.full_request(site="site-b"))
            self.assertEqual((st, d["code"]), (403, "TENANT_MISMATCH"))
            with urllib.request.urlopen(base + "/readyz", timeout=5) as r:
                self.assertTrue(json.loads(r.read())["ready"])
            with urllib.request.urlopen(base + "/metrics", timeout=5) as r:
                text = r.read().decode()
            self.assertIn('gap07_admission_total{code="ALLOW",kind="code",outcome="allow"} 1', text)
            self.assertIn('gap07_ready{dependency="trust"} 1', text)
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
