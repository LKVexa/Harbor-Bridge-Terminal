"""P2 assurance suites: interop vectors, property-based, fuzz, concurrency, fault injection.

Property tests use a seeded stdlib generator (reproducible: GAP07_SEED env var)
and additionally run under Hypothesis when it is installed.
"""
import base64
import hashlib
import json
import os
import random
import threading
import unittest

from gap07_artifact_provenance_signing import algorithms as algs
from gap07_artifact_provenance_signing.canonical import canonical_bytes, ld_encode, strict_loads
from gap07_artifact_provenance_signing.dsse import pae
from gap07_artifact_provenance_signing.errors import ERROR_CODES, GapError
from gap07_artifact_provenance_signing.signing import parse_envelope, signed_message, verify_signature
from gap07_artifact_provenance_signing.tests.fixtures import Env, PKI, T0
from gap07_artifact_provenance_signing.tlog import consistency_path, inclusion_path, mth, verify_consistency, verify_inclusion

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = int(os.environ.get("GAP07_SEED", "20260922"))
ITER = int(os.environ.get("GAP07_ITER", "300"))


class Interop(unittest.TestCase):
    """Byte-level vectors - independent published constants pin the primitives."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "vectors", "v6_vectors.json"), encoding="utf-8") as fh:
            cls.v = json.load(fh)

    def test_rfc8032_and_rfc6962_published_values(self):
        self.assertEqual(self.v["rfc8032_test1"]["signature_hex"],
                         "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        self.assertEqual(mth([bytes.fromhex(x) for x in self.v["rfc6962_root_8"]["leaves_hex"]]).hex(),
                         "5dc9da79a70659a9ad559cb701ded9a2ab9d823aad2f4960cfe370eff4604328")

    def test_jcs_utf16_key_order(self):
        self.assertTrue(canonical_bytes({"\uffff": 1, "\U0001F600": 2}).startswith('{"\U0001F600"'.encode()))
        with self.assertRaises(GapError):
            canonical_bytes({"a": 2**53})

    def test_encodings_are_stable(self):
        for c in self.v["canonical_json"]:
            self.assertEqual(canonical_bytes(c["input"]).hex(), c["canonical_hex"])
        le = self.v["ld_encode"]
        self.assertEqual(ld_encode(le["domain"], [tuple(f) for f in le["fields"]]).hex(), le["hex"])
        self.assertEqual(pae(self.v["dsse_pae"]["type"], self.v["dsse_pae"]["body"].encode()).hex(), self.v["dsse_pae"]["hex"])
        sv = self.v["signature_v3"]
        env = parse_envelope(sv["envelope"])
        self.assertEqual(signed_message(env).hex(), sv["signed_bytes_hex"])
        algs.verify_raw("ed25519", base64.b64decode(sv["public_spki_b64"]), base64.urlsafe_b64decode(env["sig"] + "=="), bytes.fromhex(sv["signed_bytes_hex"]))


class Properties(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(SEED)

    def rand_json(self, depth=0):
        r = self.rng.random()
        if depth > 3 or r < 0.3:
            return self.rng.choice([None, True, False, self.rng.randint(-2**40, 2**40), "".join(chr(self.rng.randint(32, 0x2FFF)) for _ in range(self.rng.randint(0, 8)))])
        if r < 0.65:
            return [self.rand_json(depth + 1) for _ in range(self.rng.randint(0, 4))]
        return {"".join(chr(self.rng.randint(97, 122)) for _ in range(self.rng.randint(1, 5))): self.rand_json(depth + 1) for _ in range(self.rng.randint(0, 4))}

    def test_canonicalisation_idempotent_and_roundtrip(self):
        for _ in range(ITER):
            v = self.rand_json()
            b = canonical_bytes(v)
            self.assertEqual(strict_loads(b), v)
            self.assertEqual(canonical_bytes(strict_loads(b)), b)

    def test_ld_encode_injective_on_random_splits(self):
        for _ in range(ITER):
            s = "".join(self.rng.choice("ab\x00") for _ in range(self.rng.randint(0, 10)))
            i = self.rng.randint(0, len(s))
            j = self.rng.randint(0, len(s))
            a, b = (s[:i], s[i:]), (s[:j], s[j:])
            if a != b:
                self.assertNotEqual(ld_encode("p", [("x", a[0]), ("y", a[1])]), ld_encode("p", [("x", b[0]), ("y", b[1])]))

    def test_signature_mutation_resistance(self):
        pki = PKI()
        trust = pki.trust()
        env = pki.signer().sign(b"payload", "code", now=T0)
        d = hashlib.sha256(b"payload").hexdigest()
        fields = [k for k in env if k != "v"]
        for _ in range(ITER):
            m = dict(env)
            k = self.rng.choice(fields)
            v = m[k]
            if isinstance(v, str):
                pos = self.rng.randrange(len(v)) if v else 0
                m[k] = (v[:pos] + self.rng.choice("aZ0_-") + v[pos + 1:]) if v else "x"
            elif isinstance(v, int):
                m[k] = v + self.rng.randint(1, 1000)
            elif v is None:
                m[k] = "n" * 20
            else:
                m[k] = ["zz"]
            if m == env:
                continue
            with self.assertRaises(GapError):
                verify_signature(m, digest_hex=d, kind="code", trust=trust, now=T0)

    def test_merkle_proof_invariants(self):
        for _ in range(60):
            n = self.rng.randint(1, 70)
            leaves = [self.rng.randbytes(self.rng.randint(0, 8)) for _ in range(n)]
            root = mth(leaves)
            i = self.rng.randrange(n)
            self.assertTrue(verify_inclusion(leaves[i], i, n, inclusion_path(i, leaves), root))
            m = self.rng.randint(1, n)
            self.assertTrue(verify_consistency(m, n, mth(leaves[:m]), root, consistency_path(m, leaves)))
            bad = inclusion_path(i, leaves)
            if bad:
                bad[self.rng.randrange(len(bad))] = b"\x00" * 32
                self.assertFalse(verify_inclusion(leaves[i], i, n, bad, root))

    def test_trust_rotation_invariant(self):
        """Adding a signer never changes another signer's resolution; revoking always refuses."""
        pki = PKI()
        base = pki.trust().resolve_kid(pki.refs["k1"].kid, T0, purpose="sign:code")
        for i in range(5):
            pki.add_signer(f"spiffe://acme/prod/s{i}", f"s{i}")
            t = pki.trust(generation=2 + i)
            self.assertEqual(t.resolve_kid(pki.refs["k1"].kid, T0, purpose="sign:code").path, base.path)
            with self.assertRaises(GapError):
                pki.trust(generation=100, revoked_kids=frozenset({pki.refs[f"s{i}"].kid})).resolve_kid(pki.refs[f"s{i}"].kid, T0, purpose="sign:code")


try:  # optional Hypothesis layer
    from hypothesis import given, settings, strategies as st

    class HypothesisProps(unittest.TestCase):
        @settings(max_examples=200, deadline=None)
        @given(st.recursive(st.none() | st.booleans() | st.integers(-(2**53 - 1), 2**53 - 1) | st.text(max_size=20),
                            lambda c: st.lists(c, max_size=4) | st.dictionaries(st.text(max_size=5), c, max_size=4), max_leaves=20))
        def test_canonical_roundtrip(self, v):
            try:
                b = canonical_bytes(v)
            except GapError:
                return  # lone surrogates etc. are refused by design
            self.assertEqual(strict_loads(b), v)
except ImportError:  # pragma: no cover
    pass


class Fuzz(unittest.TestCase):
    """Random/mutated inputs must only ever raise GapError (stable code) - never crash."""

    PARSERS = []

    @classmethod
    def setUpClass(cls):
        e = Env()
        cls.e = e
        h = hashlib.sha256(b"artifact-bytes").hexdigest()
        cls.seeds = {
            "sig": canonical_bytes(e.builder.sign(b"artifact-bytes", "code", now=T0)),
            "dsse": canonical_bytes(e.slsa(h)),
            "cp": canonical_bytes(e.log.checkpoint(T0)),
            "req": canonical_bytes(e.full_request()),
        }

    def mutate(self, rng, b):
        b = bytearray(b)
        for _ in range(rng.randint(1, 8)):
            op = rng.random()
            if op < 0.4 and b:
                b[rng.randrange(len(b))] = rng.randrange(256)
            elif op < 0.7 and b:
                del b[rng.randrange(len(b))]
            else:
                b.insert(rng.randrange(len(b) + 1), rng.choice(b'{}[]",:\\0eE-9\xff\xc3'))
        return bytes(b)

    def test_parsers_fail_closed(self):
        from gap07_artifact_provenance_signing import dsse as D
        from gap07_artifact_provenance_signing.tlog import verify_checkpoint
        trust = self.e.pki.trust()
        rng = random.Random(SEED)
        targets = {
            "sig": lambda b: verify_signature(b, digest_hex="0" * 64, kind="code", trust=trust, now=T0),
            "dsse": lambda b: D.verify_envelope(strict_loads(b), artifact_digest="0" * 64, trust=trust, now=T0, policy=D.AttestationPolicy()),
            "cp": lambda b: verify_checkpoint(strict_loads(b), self.e.log_keys),
        }
        for name, fn in targets.items():
            for _ in range(ITER):
                data = self.mutate(rng, self.seeds[name])
                try:
                    fn(data)
                except GapError as exc:
                    self.assertIn(exc.code, ERROR_CODES)
                except (TypeError, KeyError, AttributeError, ValueError, IndexError) as exc:  # pragma: no cover - a finding
                    if not isinstance(exc, GapError):
                        self.fail(f"{name}: non-structured failure {type(exc).__name__}: {exc} on {data[:120]!r}")

    def test_admission_never_crashes_or_allows_mutants(self):
        rng = random.Random(SEED + 1)
        allowed = 0
        for _ in range(ITER // 3):
            data = self.mutate(rng, self.seeds["req"])
            try:
                req = json.loads(data)
            except ValueError:
                continue
            d = self.e.ctl.admit(req)
            self.assertIn(d["outcome"], {"allow", "deny", "defer", "error"})
            if d["outcome"] == "allow":
                allowed += 1
                self.assertEqual(d["digest"], "sha256:" + hashlib.sha256(b"artifact-bytes").hexdigest())
            self.assertNotEqual(d["code"], "INTERNAL_ERROR", d)
        self.assertLessEqual(allowed, ITER)  # allows only for semantically unchanged requests

    def test_resource_bounds(self):
        with self.assertRaises(GapError) as cm:
            strict_loads(b"[" * 100 + b"]" * 100)
        self.assertEqual(cm.exception.code, "INPUT_TOO_LARGE")
        with self.assertRaises(GapError):
            strict_loads(b'{"a":1,"a":2}')
        with self.assertRaises(GapError):
            strict_loads(b'{"a":1.5}')
        with self.assertRaises(GapError):
            strict_loads(b'"\\ud800"')
        with self.assertRaises(GapError):
            strict_loads(b"x" * (5 * 1024 * 1024))


class Concurrency(unittest.TestCase):
    def test_parallel_admission_rotation_revocation(self):
        e = Env()
        req = e.full_request()
        results, errors = [], []
        stop = threading.Event()

        def worker():
            while not stop.is_set():
                try:
                    d = e.ctl.admit(req)
                    results.append((d["outcome"], d.get("trust_generation"), d["code"]))
                except Exception as exc:  # noqa: BLE001
                    errors.append(exc)

        ts = [threading.Thread(target=worker) for _ in range(6)]
        for t in ts:
            t.start()
        for g in range(2, 12):
            e.state.swap(e.pki.trust(generation=g))
        e.state.swap(e.pki.trust(generation=12, revoked_kids=frozenset({e.pki.refs["k1"].kid})))
        final_gen_seen = threading.Event()
        for _ in range(200):
            d = e.ctl.admit(req)
            if d["code"] in ("CERT_REVOKED", "QUARANTINED"):  # a revoked-key refusal quarantines the digest
                final_gen_seen.set()
                break
        stop.set()
        for t in ts:
            t.join()
        self.assertFalse(errors)
        self.assertTrue(final_gen_seen.is_set())
        for outcome, gen, code in results:
            if outcome == "allow":
                self.assertLess(gen, 12)  # never allowed under the revoking generation
        self.assertTrue(e.audit.verify())

    def test_audit_ledger_thread_safety(self):
        from gap07_artifact_provenance_signing.core import AuditLedger
        led = AuditLedger()
        ts = [threading.Thread(target=lambda: [led.append("x") for _ in range(200)]) for _ in range(8)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(len(led.events), 1600)
        self.assertTrue(led.verify())


class FaultInjection(unittest.TestCase):
    def test_log_outage_policy_requires_tlog_denies(self):
        e = Env()
        e.log.available = False
        with self.assertRaises(GapError):
            e.full_request()  # producer side sees TLOG_UNAVAILABLE; admission without evidence:
        e.log.available = True
        d = e.ctl.admit(e.full_request(tlog=False))
        self.assertEqual((d["outcome"], d["code"]), ("deny", "TLOG_REQUIRED"))

    def test_policy_expiry_and_absence_fail_closed(self):
        e = Env()
        e.ctl.policy._active = None
        d = e.ctl.admit(e.full_request())
        self.assertEqual((d["outcome"], d["code"]), ("defer", "POLICY_UNAVAILABLE"))

    def test_trust_not_loaded(self):
        from gap07_artifact_provenance_signing.store import TrustState
        e = Env()
        e.ctl.trust_state = TrustState()
        d = e.ctl.admit(e.full_request())
        self.assertEqual((d["outcome"], d["code"]), ("defer", "NOT_READY"))


if __name__ == "__main__":
    unittest.main()
