import json, unittest, urllib.error, urllib.request
from inv65_capability_providers.tests.helpers import World
from inv65_capability_providers.host.server import ProviderHost
from inv65_capability_providers.schemas import check


class HostHttp(unittest.TestCase):
    def setUp(self):
        self.w = World()
        self.h = ProviderHost(self.w.svc, host="127.0.0.1", port=0, insecure_loopback_for_tests=True)
        self.base = "http://%s:%d" % self.h.start()

    def tearDown(self):
        self.h.stop()

    def req(self, path, body=None, token=None, ctype="application/json", raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        r = urllib.request.Request(self.base + path, data=data, method="POST" if data is not None else "GET")
        if data is not None:
            r.add_header("Content-Type", ctype)
        if token:
            r.add_header("Authorization", "Bearer " + token)
        try:
            with urllib.request.urlopen(r, timeout=5) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def test_full_link_call_unlink_over_http(self):
        w = self.w
        st, b = self.req("/v1/link", {"link_name": "primary", "config": {"bucket": "hb", "user": "u"},
                                      "decision": w.decision("link.create", "primary")}, w.token())
        self.assertEqual(st, 200, b)
        st, b = self.req("/v1/call", {"link_name": "primary", "op": "get", "payload": {"key": "k"},
                                      "decision": w.decision("call", "primary", ["get"])}, w.token())
        self.assertEqual((st, json.loads(b)["result"]["bucket"]), (200, "hb"))
        st, b = self.req("/v1/unlink", {"link_name": "primary", "decision": w.decision("link.revoke", "primary")}, w.token())
        self.assertEqual(json.loads(b), {"revoked": True})
        st, b = self.req("/v1/call", {"link_name": "primary", "op": "get", "decision": w.decision("call", "primary", ["get"])}, w.token())
        env = json.loads(b); check(env, "pk_provider_error")
        self.assertEqual((st, env["code"]), (404, "PK_PROVIDER_NO_LINK"))

    def test_boundary_rejections(self):
        self.assertEqual(self.req("/v1/call", {"link_name": "x", "op": "get"})[0], 401)
        self.assertEqual(self.req("/v1/call", raw=b"{nope", token=self.w.token())[0], 400)
        self.assertEqual(self.req("/v1/call", {"a": 1}, ctype="text/plain")[0], 400)
        self.assertEqual(self.req("/v1/call", raw=b"[1]", token=self.w.token())[0], 400)
        self.assertEqual(self.req("/v1/call", raw=b"x" * 70000)[0], 400)

    def test_probes_and_metrics(self):
        self.assertEqual(self.req("/livez")[0], 200)
        st, b = self.req("/readyz"); check(json.loads(b), "pk_provider_health"); self.assertEqual(st, 200)
        self.w.backend.up = False
        self.assertEqual(self.req("/readyz")[0], 503)
        self.assertIn("pk_links", self.req("/metrics")[1])
