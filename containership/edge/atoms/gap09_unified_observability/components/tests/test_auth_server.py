"""Components 05 (mTLS), 06 (KMS guard), 07 (policy bundle), 08 (query
principal binding), 19 (network service)."""
import base64
import http.client
import json
import os
import shutil
import ssl
import subprocess
import unittest

from fixtures import PK_GW, PK_POLICY, SK_GW, SK_POLICY, make_stack, sample, seed, signed, tmpdir
from gap09_unified_observability.components import ed25519
from gap09_unified_observability.components.auth import (EnvelopeGuard, PolicyBundle, QueryAuthenticator,
                                                         client_tls_context, principal_from_peercert, server_tls_context)
from gap09_unified_observability.components.canonical import canonical_bytes
from gap09_unified_observability.components.controls import HealthModel
from gap09_unified_observability.components.errors import (DependencyUnavailable, Expired, Unauthenticated, Unauthorized,
                                                           Unverifiable)
from gap09_unified_observability.components.server import make_server
from gap09_unified_observability.components.signals import Catalogue


def policy_doc(version=1, issued=0, expires=10**6, grants=None):
    return {"format": "GAP09-POLICY/1", "version": version, "issued_at": issued, "expires_at": expires,
            "grants": grants or {"svc-dash": {"tenants": ["t1"]}}}


def psign(doc, sk=SK_POLICY):
    return ed25519.sign(sk, canonical_bytes(doc)).hex()


def token(principal="svc-dash", issued=990, expires=1500, audience="gap09-query", sk=SK_GW):
    t = {"format": "GAP09-QTOKEN/1", "principal": principal, "audience": audience, "issued_at": issued,
         "expires_at": expires, "nonce": "abc"}
    return t, ed25519.sign(sk, canonical_bytes(t)).hex()


class TestPolicyAndPrincipal(unittest.TestCase):
    def setUp(self):
        self.pb = PolicyBundle(signer_key=PK_POLICY)
        d = policy_doc(); self.pb.load(d, psign(d), now=1000)
        self.qa = QueryAuthenticator(issuer_keys={"gw1": PK_GW}, audience="gap09-query", policy=self.pb)

    def test_policy_fail_closed(self):
        pb = PolicyBundle(signer_key=PK_POLICY)
        with self.assertRaises(DependencyUnavailable):
            pb.scope_for("svc-dash", now=1)                     # nothing loaded
        d = policy_doc()
        with self.assertRaises(Unverifiable):
            pb.load(d, psign(d, seed("rogue")), now=1000)       # wrong signer
        pb.load(d, psign(d), now=1000)
        with self.assertRaises(Unverifiable):
            pb.load(d, psign(d), now=1000)                      # replay / downgrade
        with self.assertRaises(Expired):
            pb.scope_for("svc-dash", now=10**6)                 # expiry boundary
        with self.assertRaises(Unauthorized):
            pb.scope_for("nobody", now=1000)

    def test_token_binding(self):
        t, s = token()
        principal, scope = self.qa.authenticate(t, "gw1", s, now=1000)
        self.assertEqual(principal, "svc-dash")
        self.qa.authorize(scope, tenant="t1", environment="prod", site="s1", workload="w1")
        with self.assertRaises(Unauthorized):
            self.qa.authorize(scope, tenant="t2", environment="prod", site="s1", workload="w1")
        for bad, kid in ((token(audience="other"), "gw1"), (token(sk=seed("x")), "gw1"), (token(), "gw9"),
                         (token(issued=0, expires=2000), "gw1"), (token(expires=1000), "gw1")):
            with self.assertRaises((Unauthenticated, Expired)):
                self.qa.authenticate(bad[0], kid, bad[1], now=1000)
        t, s = token(); t["principal"] = "svc-admin"             # tampered principal
        with self.assertRaises(Unauthenticated):
            self.qa.authenticate(t, "gw1", s, now=1000)


class TestKMSGuard(unittest.TestCase):
    def test_refuses_plaintext_without_provider(self):
        g = EnvelopeGuard(None)
        with self.assertRaises(DependencyUnavailable):
            g.seal(b"x", purpose="wal")
        self.assertEqual(g.seal(b"x", purpose="public_metrics"), b"x")


class TestServer(unittest.TestCase):
    def setUp(self):
        self.ingest, self.reg, self.clock, _ = make_stack(tmpdir())
        pb = PolicyBundle(signer_key=PK_POLICY); d = policy_doc(); pb.load(d, psign(d), now=1000)
        qa = QueryAuthenticator(issuer_keys={"gw1": PK_GW}, audience="gap09-query", policy=pb)
        cat = Catalogue(); cat.register("cpu", kind="gauge", unit="%", owner="team-obs", description="CPU", actor="t")
        self.srv = make_server(ingest=self.ingest, store=self.ingest.store, authenticator=qa, catalogue=cat,
                               health=HealthModel("5.1.0", lambda: "0" * 64), clock=lambda: 1000)
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close()

    def _req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        data = json.dumps(body).encode() if body is not None else None
        c.request(method, path, body=data, headers={"Content-Type": "application/json", **(headers or {})})
        r = c.getresponse()
        out = (r.status, json.loads(r.read() or b"{}"), dict(r.getheaders()))
        c.close()
        return out

    def _sub(self, **over):
        a = signed([sample()], **over)
        fields = ("signal", "value", "tenant", "environment", "site", "workload", "at")
        a["samples"] = [{f: getattr(s, f) for f in fields} for s in a["samples"]]
        a["schema"] = "PK_SIGNAL_SUBMISSION/2"
        a["attestation"] = {"key_id": a.pop("key_id"), "profile": "GAP09-CSP/1"}
        return a

    def test_submit_query_catalogue_health(self):
        self.assertEqual(self._req("POST", "/v1/submit", self._sub())[0], 202)
        self.assertEqual(self._req("POST", "/v1/submit", self._sub())[1]["code"], "replay_detected")
        t, s = token()
        hdr = {"Authorization": f"GAP09 gw1:{s}", "X-GAP09-Token": base64.b64encode(json.dumps(t).encode()).decode()}
        q = {"tenant": "t1", "environment": "prod", "site": "s1", "workload": "w1", "signal": "cpu"}
        st, body, _ = self._req("POST", "/v1/query", q, hdr)
        self.assertEqual((st, body["value"], body["present"]), (200, 1.0, True))
        st, body, _ = self._req("POST", "/v1/query", {**q, "tenant": "t2"}, hdr)
        self.assertEqual((st, body["code"]), (403, "unauthorized"))           # self-declared tenant refused
        self.assertEqual(self._req("POST", "/v1/query", q)[0], 401)           # no credentials
        self.assertEqual(self._req("GET", "/v1/catalogue")[1]["signals"][0]["name"], "cpu")
        self.assertTrue(self._req("GET", "/v1/health")[1]["ready"])

    def test_malformed_and_throttle(self):
        self.assertEqual(self._req("POST", "/v1/submit", {"nope": 1})[1]["code"], "malformed")
        self.ingest.admission.max_inflight = 0
        st, body, headers = self._req("POST", "/v1/submit", self._sub(sid="t9"))
        self.assertEqual((st, body["code"]), (429, "throttled"))
        self.assertIn("Retry-After", headers)


OPENSSL = shutil.which("openssl")


@unittest.skipUnless(OPENSSL, "LANE openssl: openssl CLI not on PATH -- mTLS handshake check NOT_RUN")
class TestMTLS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = cls.d = tmpdir()
        def run(*a):
            subprocess.run([OPENSSL, *a], check=True, capture_output=True, cwd=d)
        run("req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes", "-keyout", "ca.key",
            "-out", "ca.pem", "-days", "2", "-subj", "/CN=gap09-test-ca")
        for n in ("server", "client", "rogue"):
            run("req", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256", "-nodes", "-keyout", f"{n}.key",
                "-out", f"{n}.csr", "-subj", f"/CN={'localhost' if n == 'server' else 'svc-' + n}")
        with open(os.path.join(d, "ext.cnf"), "w") as fh:
            fh.write("subjectAltName=DNS:localhost,IP:127.0.0.1\n")
        for n in ("server", "client"):
            run("x509", "-req", "-in", f"{n}.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial",
                "-out", f"{n}.pem", "-days", "2", "-extfile", "ext.cnf")
        run("req", "-x509", "-key", "rogue.key", "-out", "rogue.pem", "-days", "2", "-subj", "/CN=svc-rogue")

    def _serve(self):
        import socket, threading
        p = lambda n: os.path.join(self.d, n)
        ctx = server_tls_context(p("server.pem"), p("server.key"), p("ca.pem"))
        ls = socket.socket(); ls.bind(("127.0.0.1", 0)); ls.listen(4)
        seen = {}
        def loop():
            for _ in range(2):
                c, _ = ls.accept()
                try:
                    with ctx.wrap_socket(c, server_side=True) as s:
                        seen["principal"] = principal_from_peercert(s.getpeercert())
                        s.sendall(b"ok")
                except (ssl.SSLError, OSError) as exc:
                    seen["error"] = type(exc).__name__
        t = threading.Thread(target=loop, daemon=True); t.start()
        return ls, seen, t

    def test_mutual_tls(self):
        import socket
        p = lambda n: os.path.join(self.d, n)
        ls, seen, t = self._serve()
        port = ls.getsockname()[1]
        good = client_tls_context(p("client.pem"), p("client.key"), p("ca.pem"))
        with good.wrap_socket(socket.create_connection(("127.0.0.1", port)), server_hostname="localhost") as s:
            self.assertEqual(s.recv(2), b"ok")
        self.assertEqual(seen["principal"], "svc-client")
        bad = client_tls_context(p("rogue.pem"), p("rogue.key"), p("ca.pem"))
        with self.assertRaises((ssl.SSLError, ConnectionResetError, BrokenPipeError, OSError)):
            with bad.wrap_socket(socket.create_connection(("127.0.0.1", port)), server_hostname="localhost") as s:
                s.recv(2)
                s.sendall(b"x"); s.recv(2)
        t.join(5); ls.close()
        self.assertIn("error", seen)                         # self-signed client cert refused by server

    def test_principal_requires_cert(self):
        with self.assertRaises(Unauthenticated):
            principal_from_peercert(None)


if __name__ == "__main__":
    unittest.main()
