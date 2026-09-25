"""Unit tests for components 4, 6, 12, 16-21, 25-27 (negative paths and contracts)."""
from __future__ import annotations

import hashlib
import random
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import _path  # noqa: F401
from gap08_ota_lifecycle_rollback import compat, config, errors, schema
from gap08_ota_lifecycle_rollback.admission import AdmissionController, AdmissionLimits, TokenBucket
from gap08_ota_lifecycle_rollback.artifact import ArtifactVerifier, verify_content
from gap08_ota_lifecycle_rollback.common import FakeClock, KeyRing, sign_envelope
from gap08_ota_lifecycle_rollback.distribution import ChunkManifest, fetch
from gap08_ota_lifecycle_rollback.harness import COMPAT, MEAS, build_world
from gap08_ota_lifecycle_rollback.health import GatePolicy, HealthGateAdapter
from gap08_ota_lifecycle_rollback.identity import DeviceRegistry
from gap08_ota_lifecycle_rollback.retry import BackoffPolicy, CircuitBreaker, retry_call
from gap08_ota_lifecycle_rollback.secrets_boundary import SecretRef, assert_no_secrets, find_secrets, redact
from gap08_ota_lifecycle_rollback.transport import SimNodeSupervisor, make_command
from gap08_ota_lifecycle_rollback.windows import MaintenancePolicy, Window


class HealthEvidence(unittest.TestCase):
    def setUp(self):
        self.w = build_world()
        self.nodes = ["n001", "n002"]
        self.applied = self.w.clock.now()
        self.w.clock.advance(120)

    def ev(self, **kw):
        return self.w.evidence("r1", "wave-1", self.nodes, applied_at=self.applied, **kw)

    def evaluate(self, env, **kw):
        return self.w.health.evaluate(env, rollout_id=kw.get("rid", "r1"), cohort=kw.get("cohort", "wave-1"),
                                      nodes=self.nodes, applied_at=self.applied)

    def test_accepts_fresh_bound_evidence_once(self):
        env = self.ev()
        self.assertTrue(self.evaluate(env).healthy)
        with self.assertRaises(errors.EvidenceRejected):
            self.evaluate(env)  # replay

    def test_rejections(self):
        cases = {
            "wrong rollout": dict(rid="r2"),
            "wrong cohort": dict(cohort="wave-2"),
        }
        for name, kw in cases.items():
            with self.subTest(name), self.assertRaises(errors.EvidenceRejected):
                self.evaluate(self.ev(), **kw)
        bad_bodies = {
            "stale": dict(observed_at=self.w.clock.now() - 10_000),
            "future": dict(observed_at=self.w.clock.now() + 600),
            "predates change": dict(window_start=self.applied - 10),
            "low coverage": dict(sampled_nodes=["n001"], healthy_nodes=["n001"]),
            "outside cohort": dict(sampled_nodes=["n001", "n002", "n999"]),
            "contradictory": dict(healthy_nodes=[], verdict="healthy"),
            "bool verdict": dict(verdict=True),
            "schema": dict(schema="PK_HEALTH/0"),
        }
        for name, over in bad_bodies.items():
            with self.subTest(name), self.assertRaises(errors.EvidenceRejected):
                self.evaluate(self.ev(**over))

    def test_unsigned_or_wrong_source_key(self):
        env = self.ev()
        env["body"]["verdict"] = "healthy"
        env["body"]["healthy_nodes"] = self.nodes
        env["signature"] = "0" * 64
        with self.assertRaises(errors.EvidenceRejected):
            self.evaluate(env)
        forged = sign_envelope(self.w.ring, "gap07-k1", self.ev()["body"])  # valid key, wrong source
        with self.assertRaises(errors.EvidenceRejected):
            self.evaluate(forged)

    def test_unhealthy_verdict_is_a_decision_not_an_error(self):
        self.assertFalse(self.evaluate(self.ev(healthy=False)).healthy)


class ArtifactVerification(unittest.TestCase):
    def setUp(self):
        self.w = build_world()

    def test_rejections(self):
        v = self.w.verifier
        for name, over in {"wrong subject": dict(subject="v3"), "expired": dict(expires_at=self.w.clock.now() - 1),
                           "not yet valid": dict(verified_at=self.w.clock.now() + 600),
                           "downgrade": dict(algorithm="md5"), "no digest": dict(digest="v2"),
                           "not verified": dict(verified=False)}.items():
            with self.subTest(name), self.assertRaises(errors.EvidenceRejected):
                v.admit(self.w.verification(**over), bundle="v2")
        v.revoked_digests.add(self.w.digest)
        with self.assertRaises(errors.EvidenceRejected):
            v.admit(self.w.verification(), bundle="v2")

    def test_untrusted_signer_and_content_mismatch(self):
        other = KeyRing()
        other.add("gap07-k1")
        env = sign_envelope(other, "gap07-k1", self.w.verification()["body"])
        with self.assertRaises(errors.EvidenceRejected):
            self.w.verifier.admit(env, bundle="v2")
        art = self.w.verifier.admit(self.w.verification(), bundle="v2")
        p = Path(tempfile.mkdtemp()) / "a.bin"
        p.write_bytes(self.w.payload)
        verify_content(art, p)
        p.write_bytes(self.w.payload[:-1] + b"X")
        with self.assertRaises(errors.ArtifactMismatch):
            verify_content(art, p)


class Identity(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.ring = KeyRing()
        self.reg = DeviceRegistry(self.ring, clock=self.clock)
        for n in ("a", "b"):
            self.reg.enroll(n, self.ring.add(f"k-{n}"), MEAS)
        self.sup = {n: SimNodeSupervisor(n, self.ring, f"k-{n}", dict(MEAS), "v1", clock=self.clock) for n in "ab"}

    def cmd(self, node):
        return make_command(rollout_id="r", node=node, op="query", fence=1, target_version=None, digest=None,
                            nonce=self.reg.issue_nonce(node), issued_at=0, deadline=self.clock.now() + 60)

    def test_valid_then_replay_rejected(self):
        c = self.cmd("a")
        ack = self.sup["a"].handle(c)
        self.reg.verify_ack(ack, command=c)
        with self.assertRaises(errors.IdentityRejected):
            self.reg.verify_ack(ack, command=c)

    def test_cross_node_replay_and_attestation(self):
        ca, cb = self.cmd("a"), self.cmd("b")
        ack_a = self.sup["a"].handle(ca)
        with self.assertRaises(errors.IdentityRejected):
            self.reg.verify_ack(ack_a, command=cb)
        self.sup["b"].measurements = {"boot": "evil", "runtime": "b" * 64}
        with self.assertRaises(errors.IdentityRejected):
            self.reg.verify_ack(self.sup["b"].handle(cb), command=cb)

    def test_rotation_and_revocation(self):
        self.ring.add("k-a2")
        self.reg.rotate("a", "k-a2")
        c = self.cmd("a")
        with self.assertRaises((errors.IdentityRejected, PermissionError)):   # old key revoked
            self.reg.verify_ack(self.sup["a"].handle(c), command=c)
        self.reg.revoke("b")
        with self.assertRaises(errors.IdentityRejected):
            self.reg.issue_nonce("b")


class RetryBreakerAdmission(unittest.TestCase):
    def test_retry_bounded_and_nonidempotent_single_attempt(self):
        clk = FakeClock()
        calls = []

        def boom():
            calls.append(1)
            raise errors.DependencyUnavailable("x")
        with self.assertRaises(errors.Timeout):
            retry_call(boom, idempotent=True, policy=BackoffPolicy(0.1, 1, 4, 100), clock=clk,
                       rng=random.Random(1))
        self.assertEqual(len(calls), 4)
        calls.clear()
        with self.assertRaises(errors.Timeout):
            retry_call(boom, idempotent=False, clock=clk)
        self.assertEqual(len(calls), 1)
        with self.assertRaises(errors.Unauthorized):  # never retried
            retry_call(lambda: (_ for _ in ()).throw(errors.Unauthorized("no")), idempotent=True, clock=clk)

    def test_full_jitter_within_cap(self):
        p, rng = BackoffPolicy(0.5, 8, 10, 100), random.Random(3)
        for a in range(10):
            d = p.delay(a, rng)
            self.assertTrue(0 <= d <= min(8, 0.5 * 2 ** a))

    def test_breaker_opens_and_half_opens(self):
        clk = FakeClock()
        b = CircuitBreaker(failure_threshold=2, reset_timeout_s=10, clock=clk)
        b.failure("site0")
        b.failure("site0")
        with self.assertRaises(errors.CircuitOpen):
            b.before("site0")
        b.before("site1")  # other cohorts unaffected
        clk.advance(10)
        b.before("site0")  # half-open probe
        b.success("site0")
        self.assertEqual(b.state("site0"), "closed")

    def test_recovery_lane_not_starved(self):
        a = AdmissionController(AdmissionLimits(max_inflight_commands=10, reserved_recovery_slots=4))
        a.acquire_commands(6, recovery=False)
        with self.assertRaises(errors.Overloaded):
            a.acquire_commands(1, recovery=False)
        a.acquire_commands(4, recovery=True)  # rollback still admitted at saturation

    def test_token_bucket(self):
        clk = FakeClock()
        b = TokenBucket(2, 2, clk)
        self.assertEqual(b.take(), 0)
        self.assertEqual(b.take(), 0)
        self.assertGreater(b.take(), 0)
        clk.advance(1)
        self.assertEqual(b.take(), 0)


class Windows(unittest.TestCase):
    def test_window_crossing_midnight_and_recovery_exempt(self):
        mp = MaintenancePolicy(site_offsets_min={"s": 0},
                               default_windows=[Window(frozenset({0}), 22 * 60, 2 * 60)])  # Mon 22:00-Tue 02:00
        mon_23 = datetime(2026, 9, 21, 23, 0, tzinfo=timezone.utc).timestamp()
        tue_01 = datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc).timestamp()
        tue_03 = datetime(2026, 9, 22, 3, 0, tzinfo=timezone.utc).timestamp()
        mp.check("s", mon_23)
        mp.check("s", tue_01)
        with self.assertRaises(errors.PolicyDenied):
            mp.check("s", tue_03)
        mp.check("s", tue_03, recovery=True)
        mp.blackouts.append((mon_23 - 10, mon_23 + 10, "trading close"))
        with self.assertRaises(errors.PolicyDenied):
            mp.check("s", mon_23)


class ConfigSecretsCompat(unittest.TestCase):
    def test_config_provenance_and_rollback(self):
        ring = KeyRing()
        ring.add("cfg")
        cs = config.ConfigStore(ring, "cfg")
        with self.assertRaises(errors.Unauthorized):
            cs.propose(author="a", approver="a")
        with self.assertRaises(errors.ValidationFailed):
            cs.propose(author="a", approver="b", base={"gate": {"min_coverage": 2}})
        with self.assertRaises(errors.ValidationFailed):
            cs.propose(author="a", approver="b", base={"unknown": 1})
        r1 = cs.propose(author="a", approver="b")
        r2 = cs.propose(author="a", approver="b", base={"lease": {"ttl_s": 15}},
                        overlays={"site:site0": {"gate": {"settle_s": 120}}})
        self.assertEqual(r2["body"]["parent"], r1["body"]["digest"])
        schema.validate(r2["body"], "PK_CONFIG/1")
        cs.activate(2)
        self.assertEqual(cs.effective(site="site0")["gate"]["settle_s"], 120)
        cs.rollback()
        self.assertEqual(cs.effective()["lease"]["ttl_s"], 30)
        r2["body"]["base"]["lease"]["ttl_s"] = 1  # tamper
        with self.assertRaises(errors.IntegrityFailure):
            cs.activate(2)

    def test_secrets_boundary(self):
        doc = {"mtls": SecretRef("vault://ota/mtls", "3").to_dict(), "db_password": "hunter2",
               "nested": [{"api_key": "abc"}], "pem": "-----BEGIN RSA PRIVATE KEY-----..."}
        self.assertEqual(len(find_secrets(doc)), 3)
        with self.assertRaises(errors.ValidationFailed):
            assert_no_secrets(doc, where="test")
        red = redact(doc)
        self.assertEqual(red["db_password"], "***REDACTED***")
        self.assertEqual(red["mtls"]["secret_ref"], "vault://ota/mtls")
        self.assertNotIn("material", repr(KeyRing()))

    def test_compat_matrix(self):
        self.assertTrue(compat.check(COMPAT)["compatible"])
        with self.assertRaises(errors.Incompatible):
            compat.check({**COMPAT, "arch": "armv7l", "node_runtime": "df-fabric-1.x"})
        with self.assertRaises(errors.Incompatible):
            compat.check({k: v for k, v in COMPAT.items() if k != "arch"})


class Distribution(unittest.TestCase):
    def test_resumable_verified_fetch_with_bad_source_and_budget(self):
        data = bytes(random.Random(5).getrandbits(8) for _ in range(10_000))
        m = ChunkManifest.build(data, 1024)
        schema.validate(m.to_dict(), "PK_CHUNK_MANIFEST/1")
        dest = Path(tempfile.mkdtemp()) / "art.bin"
        calls = {"n": 0}

        def flaky(i):
            calls["n"] += 1
            if calls["n"] == 5:
                raise ConnectionError("peer dropped")
            return data[i * 1024:(i + 1) * 1024]

        def corrupt(i):
            return b"x" * 1024
        with self.assertRaises(errors.DependencyUnavailable):
            fetch(m, dest, [flaky])                       # interrupted mid-transfer
        stats = fetch(m, dest, [corrupt, flaky])          # resumes, skips corrupt peer
        self.assertGreaterEqual(stats["reused"], 4)
        self.assertEqual(dest.read_bytes(), data)
        with self.assertRaises(errors.Overloaded):
            fetch(m, Path(tempfile.mkdtemp()) / "b.bin", [flaky], budget=TokenBucket(100, 2000, FakeClock()))


class ErrorsAndSchemas(unittest.TestCase):
    def test_error_envelope(self):
        try:
            try:
                raise errors.Timeout("node n1 silent", resource="n1")
            except errors.Timeout as inner:
                raise errors.DependencyUnavailable("supervisor down", resource="supervisor", cause=inner)
        except errors.Gap08Error as exc:
            d = exc.to_dict()
        schema.validate(d, "PK_ERROR/1")
        self.assertEqual(d["causes"][0]["code"], "GAP08-E004-TIMEOUT")
        self.assertEqual(len(errors.REGISTRY), len({s.code for s in errors.REGISTRY.values()}))

    def test_command_ack_verification_schemas(self):
        w = build_world()
        c = make_command(rollout_id="r", node="n001", op="query", fence=1, target_version=None, digest=None,
                         nonce=w.registry.issue_nonce("n001"), issued_at=0, deadline=w.clock.now() + 9)
        schema.validate(c, "PK_NODE_COMMAND/1")
        schema.validate(w.nodes["n001"].handle(c)["body"], "PK_NODE_ACK/1")
        schema.validate(w.verification()["body"], "PK_VERIFICATION/1")
        schema.validate(w.evidence("r", "wave-1", ["n001"])["body"], "PK_HEALTH_EVIDENCE/1")
        schema.validate(w.leases.acquire("x", "h").to_dict(), "PK_LEASE/1")
        w.sink.append({"event_hash": "a" * 64})
        schema.validate(w.sink.entries()[0], "PK_AUDIT_SEAL/1")
        with self.assertRaises(errors.ValidationFailed):
            schema.validate({**c, "op": "format_disk"}, "PK_NODE_COMMAND/1")


if __name__ == "__main__":
    unittest.main()
