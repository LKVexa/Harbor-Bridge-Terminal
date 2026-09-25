"""MC02 / MC16 / MC17 / MC36 / MC39 / MC40 / MC58(local) — distribution client against
a local fake registry (real HTTP, real sockets; no external network)."""
import tempfile
import unittest
from pathlib import Path

from inv02_container_substrate.distribution import AuthError, DistributionClient, OfflineMiss, StaticCredentials, TLSPolicy, split_host
from inv02_container_substrate.registry import IntegrityError, ValidationError
from inv02_container_substrate.resilience import RetryPolicy
from inv02_container_substrate.store import ContentStore
from inv02_container_substrate.tests.fixtures import FakeRegistry, make_image, sha


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ContentStore(Path(self.tmp.name) / "s")
        self.img = make_image([[("a", "file", b"A" * 5000)], [("b", "file", b"B" * 7000)]])

    def tearDown(self):
        self.tmp.cleanup()

    def client(self, reg, **kw):
        kw.setdefault("tls", TLSPolicy(insecure_hosts=frozenset({reg.host})))
        kw.setdefault("retry_policy", RetryPolicy(max_attempts=4, base_delay_s=0.001, retry_on=(ConnectionError, TimeoutError)))
        return DistributionClient(self.store, **kw)

    def pull_all(self, c, name, ref):
        d, raw, mt = c.resolve(f"{name}:{ref}" if not ref.startswith("sha256:") else f"{name}@{ref}")
        import json
        m = json.loads(raw)
        for desc in [m["config"]] + m["layers"]:
            c.fetch_blob(name, desc["digest"], desc["size"])
        return d

    def test_pull_with_bearer_auth(self):
        reg = FakeRegistry(token="tok-123", basic=("u", "p"))
        try:
            reg.add_image("team/app", "1.0", self.img)
            c = self.client(reg, credentials=StaticCredentials({reg.host: ("u", "p")}))
            d = self.pull_all(c, f"{reg.host}/team/app", "1.0")
            self.assertEqual(d, self.img["digest"])
            self.assertEqual(self.store.get_tag(f"{reg.host}/team/app:1.0"), d)
            for b in self.img["layers"]:
                self.assertEqual(self.store.get(sha(b)), b)
            self.assertIn("StaticCredentials(hosts=", repr(c.creds))
            self.assertNotIn("'p'", repr(c.creds))
        finally:
            reg.close()

    def test_bad_credentials(self):
        reg = FakeRegistry(token="t", basic=("u", "p"))
        try:
            reg.add_image("team/app", "1.0", self.img)
            c = self.client(reg, credentials=StaticCredentials({reg.host: ("u", "wrong")}))
            with self.assertRaises(AuthError):
                c.resolve(f"{reg.host}/team/app:1.0")
        finally:
            reg.close()

    def test_digest_mismatch_and_corrupt_blob_rejected(self):
        reg = FakeRegistry()
        try:
            reg.add_image("x", "1", self.img)
            other = make_image([[("z", "file", b"z")]])
            reg.manifests[("x", other["digest"])] = reg.manifests[("x", "1")]  # serves wrong manifest
            c = self.client(reg)
            with self.assertRaises(IntegrityError):
                c.resolve(f"{reg.host}/x@{other['digest']}")
            reg.corrupt.add(sha(self.img["layers"][0]))
            with self.assertRaises(IntegrityError):
                c.fetch_blob(f"{reg.host}/x", sha(self.img["layers"][0]), len(self.img["layers"][0]))
            self.assertFalse(self.store.has(sha(self.img["layers"][0])))
        finally:
            reg.close()

    def test_retry_on_5xx_and_resume_after_truncation(self):
        reg = FakeRegistry()
        try:
            reg.add_image("x", "1", self.img)
            reg.fail_next = 2
            c = self.client(reg)
            c.resolve(f"{reg.host}/x:1")
            layer = self.img["layers"][1]
            reg.truncate_once.add(sha(layer))
            c.fetch_blob(f"{reg.host}/x", sha(layer), len(layer))
            self.assertEqual(self.store.get(sha(layer)), layer)
            ranged = [h for p, h in reg.requests if p.endswith(sha(layer)) and "Range" in h]
            self.assertTrue(ranged, "second attempt should resume with a Range request")
        finally:
            reg.close()

    def test_mirror_fallback_digest_only(self):
        primary, mirror = FakeRegistry(), FakeRegistry()
        try:
            primary.add_image("x", "1", self.img)
            mirror.add_image("x", None, self.img)
            tls = TLSPolicy(insecure_hosts=frozenset({primary.host, mirror.host}))
            c = self.client(primary, tls=tls, mirrors={primary.host: [mirror.host]})
            c.resolve(f"{primary.host}/x@{self.img['digest']}")
            self.assertTrue(any("manifests" in p for p, _ in mirror.requests))
            n = len(mirror.requests)
            c.resolve(f"{primary.host}/x:1")  # tags never come from mirrors
            self.assertEqual(len(mirror.requests), n)
        finally:
            primary.close()
            mirror.close()

    def test_offline_mode(self):
        reg = FakeRegistry()
        try:
            reg.add_image("x", "1", self.img)
            name = f"{reg.host}/x"
            self.pull_all(self.client(reg), name, "1")
        finally:
            reg.close()
        off = DistributionClient(self.store, offline=True)
        d, _, _ = off.resolve(f"{name}:1")
        self.assertEqual(d, self.img["digest"])
        with self.assertRaises(OfflineMiss):
            off.resolve(f"{name}:2")
        with self.assertRaises(OfflineMiss):
            off.fetch_blob(name, sha(b"nope"), 4)

    def test_tls_policy(self):
        with self.assertRaises(ValidationError):
            TLSPolicy(insecure_hosts=frozenset({"registry.example.com"})).scheme_for("registry.example.com")
        self.assertEqual(TLSPolicy().scheme_for("registry.example.com"), "https")
        ctx = TLSPolicy().context()
        import ssl
        self.assertGreaterEqual(ctx.minimum_version, ssl.TLSVersion.TLSv1_2)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_split_host(self):
        self.assertEqual(split_host("alpine"), ("docker.io", "library/alpine"))
        self.assertEqual(split_host("user/app"), ("docker.io", "user/app"))
        self.assertEqual(split_host("localhost:5000/app"), ("localhost:5000", "app"))
        self.assertEqual(split_host("ghcr.io/o/r"), ("ghcr.io", "o/r"))


if __name__ == "__main__":
    unittest.main()
