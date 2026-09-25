import base64
import copy
import hashlib
import json
import os
import tempfile
import unittest

from gap07_artifact_provenance_signing import algorithms as algs
from gap07_artifact_provenance_signing import dsse
from gap07_artifact_provenance_signing.canonical import b64u_encode, canonical_bytes
from gap07_artifact_provenance_signing.errors import GapError
from gap07_artifact_provenance_signing.tests.fixtures import Env, T0
from gap07_artifact_provenance_signing.tlog import (CheckpointCache, LocalTransparencyLog, LogKey, compare_views, verify_checkpoint,
                                                    verify_inclusion_evidence)

H = hashlib.sha256(b"artifact").hexdigest()


class Attestations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = Env()
        cls.trust = cls.e.pki.trust()

    def verify(self, env, policy=None, digest=H):
        return dsse.verify_envelope(env, artifact_digest=digest, trust=self.trust, now=T0,
                                    policy=policy or dsse.AttestationPolicy(builder_ids=frozenset({"https://ci.acme/builder@v1"})))

    def code(self, env, **kw):
        with self.assertRaises(GapError) as cm:
            self.verify(env, **kw)
        return cm.exception.code

    def test_valid(self):
        va = self.verify(self.e.slsa(H))
        self.assertEqual(va.evidence()["builder_id"], "https://ci.acme/builder@v1")
        self.assertEqual(hashlib.sha256(va.original_payload).hexdigest(), va.payload_sha256)

    def test_pae_matches_spec(self):
        self.assertEqual(dsse.pae("http://example.com/HelloWorld", b"hello world"),
                         b"DSSEv1 29 http://example.com/HelloWorld 11 hello world")

    def test_negatives(self):
        self.assertEqual(self.code(self.e.slsa(H), digest="0" * 64), "ATTESTATION_SUBJECT")
        self.assertEqual(self.code(self.e.slsa(H, builder="https://evil/builder")), "ATTESTATION_BUILDER")
        self.assertEqual(self.code(self.e.slsa(H), policy=dsse.AttestationPolicy(predicate_types=frozenset({"x"}))), "ATTESTATION_PREDICATE")
        env = self.e.slsa(H)
        st = json.loads(base64.b64decode(env["payload"]))
        st["predicate"]["buildDefinition"]["externalParameters"]["evil"] = 1
        env2 = dict(env, payload=base64.b64encode(canonical_bytes(st)).decode())
        self.assertEqual(self.code(env2), "SIGNATURE_INVALID")  # altered parameters break the signature
        st2 = json.loads(base64.b64decode(env["payload"]))
        st2["subject"].append(dict(st2["subject"][0]))
        signed = dsse.make_envelope(canonical_bytes(st2), [(self.e.pki.refs["k1"].kid, lambda m: self.e.pki.custody.sign(self.e.pki.refs["k1"], m, request_id="t"))])
        self.assertEqual(self.code(signed), "ATTESTATION_SUBJECT")
        st3 = json.loads(base64.b64decode(env["payload"]))
        del st3["predicate"]["buildDefinition"]["resolvedDependencies"]
        signed = dsse.make_envelope(canonical_bytes(st3), [(self.e.pki.refs["k1"].kid, lambda m: self.e.pki.custody.sign(self.e.pki.refs["k1"], m, request_id="t"))])
        self.assertEqual(self.code(signed), "ATTESTATION_MATERIALS")
        self.assertEqual(self.code(dict(env, payloadType="application/json")), "ATTESTATION_INVALID")
        self.assertEqual(self.code(dict(env, payload=env["payload"] + "=")), "ENVELOPE_MALFORMED")
        bad = dict(env, signatures=[{"keyid": "acme/site-a/prod/software:none@1", "sig": env["signatures"][0]["sig"]}])
        self.assertEqual(self.code(bad), "SIGNER_UNTRUSTED")
        self.assertEqual(self.code(env, policy=dsse.AttestationPolicy(threshold=2)), "THRESHOLD_UNMET")
        self.assertEqual(self.code(env, policy=dsse.AttestationPolicy(external_parameter_keys=frozenset())), "ATTESTATION_MATERIALS")

    def test_uri_normalisation_duplicate(self):
        self.assertEqual(dsse._normalize_uri("HTTPS://Git.Acme:443/app.git/"), dsse._normalize_uri("https://git.acme/app"))

    def test_conflicting_provenance(self):
        a = self.verify(self.e.slsa(H))
        b = copy.copy(a)
        b.predicate = json.loads(json.dumps(a.predicate))
        b.predicate["buildDefinition"]["externalParameters"]["ref"] = "refs/heads/other"
        with self.assertRaises(GapError) as cm:
            dsse.check_no_conflicts([a, b])
        self.assertEqual(cm.exception.code, "ATTESTATION_CONFLICT")


class Transparency(unittest.TestCase):
    def setUp(self):
        self.k = algs.generate_private_key("ed25519")
        self.log = LocalTransparencyLog("log.acme", "lk1", "ed25519", algs.software_signer("ed25519", self.k))
        self.keys = {"lk1": LogKey("log.acme", "lk1", "ed25519", algs.spki(self.k.public_key()))}
        for i in range(10):
            self.log.append(b"entry-%d" % i)

    def ev(self, i, ts=T0):
        cp = self.log.checkpoint(ts)
        return {"index": i, "checkpoint": cp, "proof": self.log.prove_inclusion(i, cp["size"])}

    def test_inclusion(self):
        r = verify_inclusion_evidence(self.ev(3), entry=b"entry-3", log_keys=self.keys, now=T0, max_checkpoint_age_s=60)
        self.assertEqual(r["tree_size"], 10)

    def test_negative(self):
        def code(ev, entry=b"entry-3", keys=None, now=T0):
            with self.assertRaises(GapError) as cm:
                verify_inclusion_evidence(ev, entry=entry, log_keys=keys or self.keys, now=now, max_checkpoint_age_s=60)
            return cm.exception.code
        self.assertEqual(code(self.ev(3), entry=b"entry-4"), "TLOG_PROOF_INVALID")
        ev = self.ev(3)
        ev["proof"] = ev["proof"][:-1]
        self.assertEqual(code(ev), "TLOG_PROOF_INVALID")
        other = algs.generate_private_key("ed25519")
        self.assertEqual(code(self.ev(3), keys={"lk1": LogKey("log.acme", "lk1", "ed25519", algs.spki(other.public_key()))}), "TLOG_CHECKPOINT_INVALID")
        self.assertEqual(code(self.ev(3), now=T0 + 3600), "TLOG_CHECKPOINT_STALE")
        ev = self.ev(3)
        ev["checkpoint"] = dict(ev["checkpoint"], size=11)
        self.assertEqual(code(ev), "TLOG_CHECKPOINT_INVALID")
        self.log.available = False
        with self.assertRaises(GapError) as cm:
            self.log.checkpoint(T0)
        self.assertEqual(cm.exception.code, "TLOG_UNAVAILABLE")

    def test_cache_monotonic_consistency_and_corruption(self):
        events = []
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cp.json")
            cache = CheckpointCache(self.keys, path, on_security_event=lambda e, x: events.append(e))
            cp10 = self.log.checkpoint(T0)
            cache.observe(cp10, None)
            for i in range(5):
                self.log.append(b"more-%d" % i)
            cp15 = self.log.checkpoint(T0 + 10)
            cache.observe(cp15, self.log.prove_consistency(10, 15))
            with self.assertRaises(GapError) as cm:
                cache.observe(cp10, None)
            self.assertEqual(cm.exception.code, "TLOG_ROLLBACK")
            # equivocation: a different log with the same key produces a divergent tree
            fork = LocalTransparencyLog("log.acme", "lk1", "ed25519", algs.software_signer("ed25519", self.k))
            for i in range(16):
                fork.append(b"fork-%d" % i)
            with self.assertRaises(GapError):
                cache.observe(fork.checkpoint(T0 + 20), fork.prove_consistency(15, 16))
            self.assertIn("tlog.inconsistent", events)
            reloaded = CheckpointCache(self.keys, path)
            self.assertEqual(reloaded.trusted("log.acme")["size"], 15)
            with open(path, "r+b") as fh:
                fh.seek(20)
                fh.write(b"X")
            with self.assertRaises(GapError):
                CheckpointCache(self.keys, path)

    def test_split_view_monitor(self):
        a = self.log.checkpoint(T0)
        b = dict(a, root=b64u_encode(b"\x00" * 32))
        self.assertEqual(compare_views({"site-a": a, "site-b": b})[0]["event"], "tlog.split_view")


if __name__ == "__main__":
    unittest.main()
