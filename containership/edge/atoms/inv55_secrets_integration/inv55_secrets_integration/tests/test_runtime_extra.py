"""TLS / mTLS transport, failover, bootstrap (checklist #32, #41, #44, #55, #58)."""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import ssl
import subprocess
import tempfile
import unittest

import _support as S
from fake_vault import FakeVault
from inv55_secrets_integration.runtime.errors import INV55Error
from inv55_secrets_integration.runtime.failover import FailoverProvider
from inv55_secrets_integration.runtime.provider import InMemoryProvider
from inv55_secrets_integration.runtime.vault import StaticTokenAuth, VaultKV2Provider

OPENSSL = shutil.which("openssl")


def _pki(d):
    def run(*a):
        subprocess.run(["openssl", *a], cwd=d, check=True, capture_output=True)
    run("req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", "ca.key", "-out", "ca.pem", "-days", "2", "-subj", "/CN=inv55-test-ca")
    for name, san in (("server", "IP:127.0.0.1,DNS:localhost"), ("wrong", "DNS:not-this-host.example"), ("client", "DNS:client")):
        run("req", "-newkey", "rsa:2048", "-nodes", "-keyout", f"{name}.key", "-out", f"{name}.csr", "-subj", f"/CN={name}")
        pathlib.Path(d, f"{name}.ext").write_text(f"subjectAltName={san}\n")
        run("x509", "-req", "-in", f"{name}.csr", "-CA", "ca.pem", "-CAkey", "ca.key", "-CAcreateserial",
            "-out", f"{name}.pem", "-days", "2", "-extfile", f"{name}.ext")
    return {k: os.path.join(d, k) for k in ("ca.pem", "server.pem", "server.key", "wrong.pem", "wrong.key", "client.pem", "client.key")}


@unittest.skipIf(OPENSSL is None, "openssl CLI absent - MANDATORY test; a skip fails the production gate")
class TLS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.f = _pki(cls.d)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def server_ctx(self, cert="server", require_client=False):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(self.f[f"{cert}.pem"], self.f[f"{cert}.key"])
        if require_client:
            ctx.verify_mode = ssl.CERT_REQUIRED
            ctx.load_verify_locations(self.f["ca.pem"])
        return ctx

    def adapter(self, fv, **kw):
        return VaultKV2Provider(f"https://127.0.0.1:{fv.port}", auth=StaticTokenAuth("root-test-token"), **kw)

    def test_tls_hostname_verified(self):
        with FakeVault(ssl_context=self.server_ctx()) as fv:
            a = self.adapter(fv, ca_file=self.f["ca.pem"])
            a.write("acme/x", "v", cas=None, timeout_s=3)
            self.assertEqual(a.read("acme/x", timeout_s=3).value._reveal(), "v")
            with self.assertRaises(INV55Error):                       # unknown CA
                self.adapter(fv).read("acme/x", timeout_s=3)
        with FakeVault(ssl_context=self.server_ctx("wrong")) as fv:   # valid CA, wrong SAN
            with self.assertRaises(INV55Error) as c:
                self.adapter(fv, ca_file=self.f["ca.pem"]).read("acme/x", timeout_s=3)
            self.assertEqual(c.exception.code, "INV55-E-PROVIDER-UNAVAILABLE")

    def test_mtls_client_certificate_required(self):
        with FakeVault(ssl_context=self.server_ctx(require_client=True)) as fv:
            with self.assertRaises(INV55Error):
                self.adapter(fv, ca_file=self.f["ca.pem"]).read("acme/x", timeout_s=3)
            ok = self.adapter(fv, ca_file=self.f["ca.pem"], client_cert=(self.f["client.pem"], self.f["client.key"]))
            ok.write("acme/x", "v", cas=None, timeout_s=3)
            self.assertEqual(ok.read("acme/x", timeout_s=3).version, 1)


class Failover(unittest.TestCase):
    def test_failover_reads_only(self):
        clk = S.Clock(0)
        p, s = InMemoryProvider(), InMemoryProvider()
        p.write("t/x", "primary", cas=None, timeout_s=1)
        s.write("t/x", "replica", cas=None, timeout_s=1)
        f = FailoverProvider(p, s, failback_after_s=30, clock=clk)
        self.assertEqual(f.read("t/x", timeout_s=1).value._reveal(), "primary")
        p.available = False
        self.assertEqual(f.read("t/x", timeout_s=1).value._reveal(), "replica")
        self.assertEqual(f.active, "secondary")
        with self.assertRaises(INV55Error) as c:              # no split-brain write
            f.write("t/x", "new", cas=None, timeout_s=1)
        self.assertEqual(c.exception.code, "INV55-E-PROVIDER-UNAVAILABLE")
        self.assertEqual(s.metadata("t/x", timeout_s=1)["current_version"], 1)
        p.available = True
        f.read("t/x", timeout_s=1); clk.t = 10
        self.assertEqual(f.active, "secondary")               # not yet: needs 30 s healthy
        clk.t = 31
        self.assertEqual(f.read("t/x", timeout_s=1).value._reveal(), "primary")
        self.assertEqual([e[1] for e in f.events], ["secondary", "primary"])

    def test_denial_does_not_fail_over(self):
        p, s = InMemoryProvider(), InMemoryProvider()
        s.write("t/x", "replica", cas=None, timeout_s=1)
        f = FailoverProvider(p, s)
        with self.assertRaises(INV55Error) as c:
            f.read("t/x", timeout_s=1)
        self.assertEqual(c.exception.code, "INV55-E-DENIED")
        self.assertEqual(f.active, "primary")


class Bootstrap(unittest.TestCase):
    CFG = pathlib.Path(__file__).resolve().parents[1] / "deploy" / "config"

    def run_bs(self, *files):
        import importlib
        bs = importlib.import_module("inv55_secrets_integration.tools.bootstrap")
        lines = []
        code, steps = bs.run([str(self.CFG / f) for f in files], "alice", "test", out=lines.append)
        return code, steps

    def test_bootstrap_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            cfgp = os.path.join(d, "c.json")
            doc = json.loads((self.CFG / "base.json").read_text())
            doc["telemetry"]["audit_path"] = os.path.join(d, "audit.jsonl")
            pathlib.Path(cfgp).write_text(json.dumps(doc))
            import importlib
            bs = importlib.import_module("inv55_secrets_integration.tools.bootstrap")
            self.assertEqual(bs.run([cfgp], "alice", "t", out=lambda s: None)[0], 0)
            self.assertEqual(bs.run([cfgp], "alice", "t", out=lambda s: None)[0], 0)   # re-run: same result
            from inv55_secrets_integration.runtime.audit import verify_file
            self.assertEqual(verify_file(os.path.join(d, "audit.jsonl"))[1]["count"], 2)

    def test_production_example_stops_at_provider(self):
        code, steps = self.run_bs("production.example.json")
        self.assertEqual(code, 2)                      # config valid; trust-root files absent -> FAIL, never fake
        self.assertEqual(steps[0]["result"], "PASS")

    def test_site_overlay_and_locked_overlay(self):
        self.assertEqual(self.run_bs("base.json", "overlay.test.json", "overlay.site-edge-1.json")[0], 0)
        code, steps = self.run_bs("base.json", "overlay.staging.json")
        self.assertEqual(code, 0)


class AuditSink(unittest.TestCase):
    def test_unwritable_audit_sink_returns_no_grant(self):
        from inv55_secrets_integration.runtime.audit import AuditLog
        with tempfile.TemporaryDirectory() as d:
            log = AuditLog(os.path.join(d, "a.jsonl"))
            svc, prov, ver, clock, wall = S.seeded(audit=log)
            log.path = os.path.join(d, "missing-dir", "a.jsonl")      # sink disappears
            r = svc.handle("RESOLVE", S.req(), S.token(ver, wall))
            self.assertEqual(r["error"]["code"], "INV55-E-INTERNAL")
            self.assertNotIn("lease", r)
            self.assertEqual(svc.metrics.get("internal_errors", op="RESOLVE", kind="FileNotFoundError"), 1)


if __name__ == "__main__":
    unittest.main()
