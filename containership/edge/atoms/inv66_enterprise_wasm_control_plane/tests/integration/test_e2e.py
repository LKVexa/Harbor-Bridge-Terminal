"""End-to-end over real sockets (MC-019/020/021/049/052/056).

Stub peers run as real HTTP servers in-process: an INV-63 deployment manager speaking
``PK_ECP_DELIVER/1`` and a GAP-13 policy engine speaking the OPA data API.  The
control plane is driven over HTTP and HTTPS/mTLS.  What this suite does NOT cover —
a real IdP, OPA, OCI registry, wadm or wasmCloud lattice — is listed in
``release/compatibility.json`` as OPEN_EXTERNAL.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from tests.support import EcpError, Estate
from inv66_enterprise_wasm_control_plane.production.adapters import GitOpsIngestor, HttpDeploymentManager
from inv66_enterprise_wasm_control_plane.production.http_api import Server
from inv66_enterprise_wasm_control_plane.production.policy_engine import ExternalPolicy, HttpPolicyClient


class StubPeer:
    def __init__(self, handler_fn):
        state = self.state = {"requests": [], "mode": "ok", "apps": {}}

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                return

            def _handle(self):
                n = int(self.headers.get("Content-Length") or 0)
                body = json.loads(self.rfile.read(n) or b"null")
                state["requests"].append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body,
                                          "method": self.command})
                status, out = handler_fn(state, self.path, dict(self.headers), body)
                data = json.dumps(out).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            do_PUT = do_POST = _handle
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


def inv63(state, path, headers, body):
    if state["mode"] == "down":
        return 503, {"error": "unavailable"}
    if state["mode"] == "refuse":
        return 422, {"error": "bad manifest"}
    key = {k.lower(): v for k, v in headers.items()}.get("idempotency-key")
    if key in state["apps"]:
        return 409, {"revision": state["apps"][key]}
    state["apps"][key] = f"rev-{len(state['apps']) + 1}"
    return 200, {"revision": state["apps"][key]}


def opa(state, path, headers, body):
    comps = body["input"]["components"]
    deny = [f"{c['name']}: blocked by org policy" for c in comps if c["name"].startswith("blocked")]
    return 200, {"result": {"allow": not deny, "reasons": deny, "policy_version": "org-2026.09"}}


def call(url, method="GET", body=None, token=None, headers=None, ctx=None):
    h = {"Content-Type": "application/json", **(headers or {})}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if r.headers.get("Content-Type", "").startswith("application/json") else raw.decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class EndToEndTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dm = StubPeer(inv63)
        cls.opa = StubPeer(opa)

    @classmethod
    def tearDownClass(cls):
        cls.dm.stop()
        cls.opa.stop()

    def setUp(self):
        self.dm.state.update(mode="ok", requests=[], apps={})
        self.opa.state["requests"] = []
        ext = ExternalPolicy(HttpPolicyClient(self.opa.url + "/v1/data/inv66/admit"), expected_version="org-2026.09")
        self.e = Estate(deployer=HttpDeploymentManager(self.dm.url), external_policy=ext)
        s = self.e.service
        pol = dict(self.e.config()["policy"], engine="external", external_endpoint=self.opa.url)
        gen = s.stage_config(self.e.config(policy=pol), self.e.principal("sec1"), source_repo="git", source_rev="e2e")
        s.approve_config(gen, self.e.principal("sec2"))
        s.approve_config(gen, self.e.principal("root", groups=["platform-admins"]))
        s.activate_config(gen, self.e.principal("root", groups=["platform-admins"]), expected_active=s.config.active.generation)
        self.srv = Server(s).start()

    def tearDown(self):
        self.srv.stop()

    def test_full_admission_path_over_http(self):
        tp = "00-" + "c" * 32 + "-" + "d" * 16 + "-01"
        st, d = call(self.srv.url + "/v1/admit", "POST", self.e.request("api", key="e2e-1"), self.e.token("ops"),
                     {"traceparent": tp})
        self.assertEqual(st, 200, d)
        self.assertTrue(d["admitted"])
        self.assertEqual(d["state"], "delivered")
        self.assertEqual(d["trace_id"], "c" * 32)
        put = self.dm.state["requests"][0]
        self.assertEqual(put["method"], "PUT")
        self.assertEqual(put["headers"]["idempotency-key"], d["decision_id"])
        self.assertIn("c" * 32, put["headers"]["traceparent"])  # context propagated to INV-63
        self.assertIn("c" * 32, self.opa.state["requests"][0]["headers"]["traceparent"])  # and to GAP-13
        # replay of the same idempotent request: same decision, no second delivery
        st, d2 = call(self.srv.url + "/v1/admit", "POST", self.e.request("api", key="e2e-1") | {"request_id": d["request_id"]},
                      self.e.token("ops"))
        # Ed25519 signatures are deterministic, so the rebuilt body is byte-identical -> idempotent replay
        self.assertEqual((st, d2["idempotent_replay"], d2["decision_id"]), (200, True, d["decision_id"]))
        self.assertEqual(len([r for r in self.dm.state["requests"] if r["method"] == "PUT"]), 1)
        # external policy denial
        st, d3 = call(self.srv.url + "/v1/admit", "POST", self.e.request("blocked-svc"), self.e.token("ops"))
        self.assertFalse(d3["admitted"])
        self.assertTrue(any("blocked by org policy" in r["message"] for r in d3["reasons"]))
        # explain + inventory + audit + metrics + health
        st, ex = call(f"{self.srv.url}/v1/explain/{d['decision_id']}", token=self.e.token("auditor"))
        self.assertEqual(ex["policy_external"]["policy_version"], "org-2026.09")
        self.assertEqual(ex["config"]["activation"]["approvers"], ["root", "sec2"])
        st, inv = call(self.srv.url + "/v1/inventory?tenant=payments", token=self.e.token("auditor"))
        self.assertEqual([i["state"] for i in inv["items"]], ["delivered"])
        st, m = call(self.srv.url + "/metrics")
        self.assertIn('ecp_admissions_total{outcome="admitted"}', m)
        st, h = call(self.srv.url + "/readyz")
        self.assertEqual((st, h["ready"]), (200, True))

    def test_http_errors_are_typed_envelopes(self):
        st, env = call(self.srv.url + "/v1/admit", "POST", self.e.request("api"))
        self.assertEqual((st, env["code"]), (401, "ECP_UNAUTHENTICATED"))
        st, env = call(self.srv.url + "/v1/admit", "POST", self.e.request("api"), self.e.token("dev"))
        self.assertEqual((st, env["code"]), (403, "ECP_FORBIDDEN"))
        st, env = call(self.srv.url + "/version", headers={"Accept-Protocol": "PK_ECP_ADMIT/9"})
        self.assertEqual((st, env["code"]), (409, "ECP_UNSUPPORTED_VERSION"))
        req = urllib.request.Request(self.srv.url + "/v1/admit", data=b"[" * 100000 + b"]" * 100000, method="POST",
                                     headers={"Content-Type": "application/json"})
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(json.loads(cm.exception.read())["code"], "ECP_SCHEMA_INVALID")
        st, env = call(self.srv.url + "/nope")
        self.assertEqual(env["code"], "ECP_NOT_FOUND")

    def test_deployment_manager_outage_and_refusal(self):
        self.dm.state["mode"] = "down"
        st, d = call(self.srv.url + "/v1/admit", "POST", self.e.request("api"), self.e.token("ops"))
        self.assertEqual(d["state"], "delivery_pending")
        self.dm.state["mode"] = "ok"
        self.e.service.delivery_breaker.state = "closed"
        self.assertEqual(list(self.e.service.redeliver_pending().values()), ["delivered"])
        self.dm.state["mode"] = "refuse"
        st, d = call(self.srv.url + "/v1/admit", "POST", self.e.request("api2"), self.e.token("ops"))
        self.assertEqual(d["state"], "rejected")

    def test_policy_engine_outage_fails_closed(self):
        self.opa.stop()
        try:
            st, d = call(self.srv.url + "/v1/admit", "POST", self.e.request("api"), self.e.token("ops"))
            self.assertFalse(d["admitted"])
            self.assertIn("ECP_DEPENDENCY_UNAVAILABLE", [r["code"] for r in d["reasons"]])
        finally:
            type(self).opa = StubPeer(opa)

    def test_gitops_ingestion_goes_through_admission(self):
        repo = Path(tempfile.mkdtemp(prefix="inv66-git-"))
        (repo / "apps").mkdir()
        for n in ("api", "web"):
            (repo / "apps" / f"{n}.json").write_text(json.dumps({"app": n, "components": [self.e.component(n)]}))
        if shutil.which("git"):
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.email=a@b", "-c", "user.name=t", "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "desired"], check=True)
            rev = None
        else:  # pragma: no cover
            rev = "f" * 40
        ing = GitOpsIngestor(repo, "https://git.acme.example/estate", tenant="payments", lattice="prod")
        reqs = ing.requests(rev)
        out = [self.e.service.admit(r, self.e.token("ops")) for r in reqs]
        self.assertTrue(all(d["admitted"] for d in out))
        ex = self.e.service.explain(out[0]["decision_id"], self.e.principal("auditor"))
        self.assertEqual(ex["source"]["repo"], "https://git.acme.example/estate")
        self.assertEqual(len(ex["source"]["rev"]), 40)
        again = [self.e.service.admit(r, self.e.token("ops")) for r in reqs]  # re-sync is idempotent
        self.assertTrue(all(d["idempotent_replay"] for d in again))


def _mk_certs(d: Path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    now = dt.datetime.now(dt.timezone.utc)

    def key():
        return ec.generate_private_key(ec.SECP256R1())

    def write(name, k, c):
        (d / f"{name}.key").write_bytes(k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                                        serialization.NoEncryption()))
        (d / f"{name}.pem").write_bytes(c.public_bytes(serialization.Encoding.PEM))
    ca_k = key()
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "inv66-test-ca")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_k.public_key())
          .serial_number(1).not_valid_before(now - dt.timedelta(minutes=1)).not_valid_after(now + dt.timedelta(hours=1))
          .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True).sign(ca_k, hashes.SHA256()))
    write("ca", ca_k, ca)
    for name, sans in (("server", [x509.DNSName("localhost"), x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1"))]),
                       ("client", [x509.UniformResourceIdentifier("spiffe://acme.example/ns/payments/sa/deployer")]),
                       ("rogue", [x509.UniformResourceIdentifier("spiffe://acme.example/ns/payments/sa/deployer")])):
        k = key()
        signer_k, issuer = (ca_k, ca.subject)
        if name == "rogue":  # self-signed, not from our CA
            signer_k, issuer = k, x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "rogue")])
        c = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
             .issuer_name(issuer).public_key(k.public_key()).serial_number(x509.random_serial_number())
             .not_valid_before(now - dt.timedelta(minutes=1)).not_valid_after(now + dt.timedelta(hours=1))
             .add_extension(x509.SubjectAlternativeName(sans), critical=False).sign(signer_k, hashes.SHA256()))
        write(name, k, c)


class MutualTlsTest(unittest.TestCase):
    def test_mtls_peer_identity_admission(self):
        d = Path(tempfile.mkdtemp(prefix="inv66-tls-"))
        _mk_certs(d)
        e = Estate()
        sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sctx.minimum_version = ssl.TLSVersion.TLSv1_2
        sctx.load_cert_chain(d / "server.pem", d / "server.key")
        sctx.load_verify_locations(d / "ca.pem")
        sctx.verify_mode = ssl.CERT_REQUIRED
        srv = Server(e.service, tls=sctx).start()
        try:
            cctx = ssl.create_default_context(cafile=str(d / "ca.pem"))
            cctx.load_cert_chain(d / "client.pem", d / "client.key")
            st, dec = call(srv.url + "/v1/admit", "POST", e.request("api", lattice="staging"), ctx=cctx)
            self.assertEqual(st, 200, dec)
            self.assertTrue(dec["admitted"])
            self.assertEqual((dec["principal"]["auth_method"], dec["principal"]["subject"]), ("mtls", "payments/deployer"))
            rogue = ssl.create_default_context(cafile=str(d / "ca.pem"))
            rogue.load_cert_chain(d / "rogue.pem", d / "rogue.key")
            with self.assertRaises((ssl.SSLError, urllib.error.URLError, ConnectionError, OSError)):
                call(srv.url + "/healthz", ctx=rogue)
            plain = ssl.create_default_context(cafile=str(d / "ca.pem"))  # no client cert at all
            with self.assertRaises((ssl.SSLError, urllib.error.URLError, ConnectionError, OSError)):
                call(srv.url + "/healthz", ctx=plain)
            srv.reload_tls(str(d / "server.pem"), str(d / "server.key"))  # rotation path is callable live
            st, _ = call(srv.url + "/healthz", ctx=cctx)
            self.assertEqual(st, 200)
        finally:
            srv.stop()


if __name__ == "__main__":
    unittest.main()
