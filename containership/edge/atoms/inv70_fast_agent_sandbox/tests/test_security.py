"""C023 / C044 / C045 / C048 / C049 trust-control tests."""
import importlib
import io
import time
import unittest

import _path
sec = importlib.import_module(_path.PKG + ".security")

K = b"k" * 32


def store():
    s = sec.TrustStore()
    s.add("c1", K, "caller")
    s.add("a1", b"a" * 32, "artifact")
    s.add("n1", b"n" * 32, "attest:node")
    s.add("cp1", b"p" * 32, "attest:control-plane")
    return s


class Clock(sec.Clock):
    def __init__(self, t=1_000_000.0):
        super().__init__(lambda: self.t)
        self.t = t


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.s, self.c = store(), Clock()
        self.a = sec.Authenticator(self.s, self.c)

    def tok(self, **kw):
        args = dict(subject="svc", tenant="t1", capabilities={"x"}, audience="inv70", ttl_s=60,
                    now=self.c.t, token_id="j1")
        args.update(kw)
        return sec.issue_token(self.s, "c1", **args)

    def test_valid(self):
        p = self.a.authenticate(self.tok())
        self.assertEqual((p.tenant, p.capabilities), ("t1", frozenset({"x"})))

    def test_rejections(self):
        good = self.tok()
        body, sig = good.split(".")
        cases = [None, "", "a.b.c", "x" * 5000, body + "." + sig[:-2] + "AA", body[:-2] + "." + sig]
        for t in cases:
            with self.subTest(t=str(t)[:20]), self.assertRaises(sec.AuthError):
                self.a.authenticate(t)

    def test_replay_expiry_audience_revocation(self):
        t = self.tok(token_id="r")
        self.a.authenticate(t)
        with self.assertRaisesRegex(sec.AuthError, "replayed"):
            self.a.authenticate(t)
        t2 = self.tok(token_id="e")
        self.c.t += 200
        with self.assertRaisesRegex(sec.AuthError, "expired"):
            self.a.authenticate(t2)
        with self.assertRaisesRegex(sec.AuthError, "audience"):
            self.a.authenticate(self.tok(token_id="aud", audience="other"))
        t3 = self.tok(token_id="rv")
        self.s.revoke("c1")
        with self.assertRaisesRegex(sec.AuthError, "revoked"):
            self.a.authenticate(t3)

    def test_key_purpose_confusion(self):
        # an artifact-signing key cannot mint caller tokens
        with self.assertRaisesRegex(sec.AuthError, "purpose"):
            sec.issue_token(self.s, "a1", subject="s", tenant="t", capabilities=(), audience="inv70",
                            ttl_s=60, now=self.c.t, token_id="z")

    def test_lifetime_bounds(self):
        with self.assertRaises(ValueError):
            self.tok(ttl_s=10_000)

    def test_c048_fail_closed(self):
        t = self.tok(token_id="f")
        self.s.available = False
        with self.assertRaisesRegex(sec.AuthError, "trust unavailable"):
            self.a.authenticate(t)
        self.s.available = True
        self.c.healthy = False
        with self.assertRaisesRegex(sec.AuthError, "time unavailable"):
            self.a.authenticate(t)


class AttestationTests(unittest.TestCase):
    def test_roles_measurement_expiry(self):
        s, c = store(), Clock()
        att = sec.make_attestation(s, "n1", role="node", identity="node-7", measurement="m1", now=c.t)
        self.assertEqual(sec.verify_attestation(s, c, att, role="node", expected_measurements={"m1"}), "node-7")
        with self.assertRaisesRegex(sec.AuthError, "measurement"):
            sec.verify_attestation(s, c, att, role="node", expected_measurements={"m2"})
        with self.assertRaises(sec.AuthError):   # node key used as control-plane
            sec.verify_attestation(s, c, att, role="control-plane", expected_measurements={"m1"})
        att["statement"]["id"] = "evil"
        with self.assertRaisesRegex(sec.AuthError, "invalid"):
            sec.verify_attestation(s, c, att, role="node", expected_measurements={"m1"})
        att2 = sec.make_attestation(s, "cp1", role="control-plane", identity="cp", measurement="m", now=c.t, ttl_s=10)
        c.t += 11
        with self.assertRaisesRegex(sec.AuthError, "expired"):
            sec.verify_attestation(s, c, att2, role="control-plane", expected_measurements={"m"})


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.s, self.c = store(), Clock()
        self.pol = sec.ArtifactPolicy(approved_versions={"guest": {"1.0"}})
        self.blob = b"\0asm\1\0\0\0"
        self.m = sec.make_manifest(self.s, "a1", name="guest", version="1.0", content=self.blob, builder="inv70-ci",
                                   source_revision="abc123", sbom=[{"name": "x", "version": "1"}], now=self.c.t)

    def test_ok(self):
        self.assertEqual(sec.verify_artifact(self.s, self.c, self.pol, self.m, self.blob)["version"], "1.0")

    def test_each_gate(self):
        with self.assertRaisesRegex(sec.AuthError, "digest"):
            sec.verify_artifact(self.s, self.c, self.pol, self.m, self.blob + b"x")
        self.pol.denied_digests.add(self.m["manifest"]["digest"])
        with self.assertRaisesRegex(sec.AuthError, "denied"):
            sec.verify_artifact(self.s, self.c, self.pol, self.m, self.blob)
        self.pol.denied_digests.clear()
        self.pol.approved_versions["guest"] = {"2.0"}
        with self.assertRaisesRegex(sec.AuthError, "version"):
            sec.verify_artifact(self.s, self.c, self.pol, self.m, self.blob)
        self.pol.approved_versions["guest"] = {"1.0"}
        m2 = sec.make_manifest(self.s, "a1", name="guest", version="1.0", content=self.blob, builder="laptop",
                               source_revision="abc", sbom=[{}], now=self.c.t)
        with self.assertRaisesRegex(sec.AuthError, "provenance"):
            sec.verify_artifact(self.s, self.c, self.pol, m2, self.blob)
        m3 = sec.make_manifest(self.s, "a1", name="guest", version="1.0", content=self.blob, builder="inv70-ci",
                               source_revision="abc", sbom=[], now=self.c.t)
        with self.assertRaisesRegex(sec.AuthError, "sbom"):
            sec.verify_artifact(self.s, self.c, self.pol, m3, self.blob)
        self.m["manifest"]["version"] = "1.0 "
        with self.assertRaisesRegex(sec.AuthError, "signature"):
            sec.verify_artifact(self.s, self.c, self.pol, self.m, self.blob)


class AuditTests(unittest.TestCase):
    def test_chain_detects_tamper_reorder_delete_truncate(self):
        log = sec.AuditLog(K)
        for i in range(5):
            log.append("e", i=i)
        head = log.sealed_head()
        self.assertEqual(sec.AuditLog.verify(log.entries, K, head), (True, "ok"))
        e = [dict(x) for x in log.entries]
        e[2]["i"] = 99
        self.assertFalse(sec.AuditLog.verify(e, K)[0])
        e = [dict(x) for x in log.entries]
        e[1], e[2] = e[2], e[1]
        self.assertFalse(sec.AuditLog.verify(e, K)[0])
        e = [dict(x) for x in log.entries]
        del e[3]
        self.assertFalse(sec.AuditLog.verify(e, K)[0])
        self.assertEqual(sec.AuditLog.verify(log.entries[:4], K, head), (False, "truncation detected"))
        self.assertFalse(sec.AuditLog.verify(log.entries, b"z" * 32)[0])

    def test_sink_failure_fails_closed(self):
        class Bad(io.StringIO):
            def write(self, s):
                raise OSError("disk full")
        log = sec.AuditLog(K, sink=Bad())
        with self.assertRaisesRegex(sec.AuthError, "audit unavailable"):
            log.append("e")
        self.assertEqual((len(log.entries), log.write_failures), (0, 1))


if __name__ == "__main__":
    unittest.main()
