"""MC-03/07/08/09/13/14/16/18/27/34 state, enrollment, policy and audit tests."""
import json
import tempfile
import unittest
from pathlib import Path

import _kit as k
from cryptography.hazmat.primitives import serialization

from gap06_device_identity_and_attestation.mc import audit, enrollment, keys, policy, replay, store
from gap06_device_identity_and_attestation.mc.errors import Gap06Error


def code(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except Gap06Error as e:
        return e.code
    return "NO_ERROR"


class DurableStoreTest(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_restart_preserves_state_and_chain(self):
        s = store.DurableStore(self.d)
        s.put("t", "a", 1)
        with s.transaction() as tx:
            tx.put("t", "b", 2)
            tx.delete("t", "a")
        s2 = store.DurableStore(self.d)
        self.assertEqual(s2.items("t"), {"b": 2})
        self.assertEqual(s2.generation, 2)

    def test_torn_tail_truncated(self):
        s = store.DurableStore(self.d)
        s.put("t", "a", 1)
        with open(self.d / "wal.log", "ab") as f:
            f.write(b"deadbeef {\"gen\":2,\"op")
        s2 = store.DurableStore(self.d)
        self.assertEqual(s2.generation, 1)
        s2.put("t", "c", 3)
        self.assertEqual(store.DurableStore(self.d).items("t"), {"a": 1, "c": 3})

    def test_mid_log_corruption_detected(self):
        s = store.DurableStore(self.d)
        s.put("t", "a", 1)
        s.put("t", "b", 2)
        lines = (self.d / "wal.log").read_text().splitlines()
        lines[0] = lines[0].replace('"a",1', '"a",9')
        (self.d / "wal.log").write_text("\n".join(lines) + "\n")
        self.assertEqual(code(store.DurableStore, self.d), "E_STATE_CORRUPT")

    def test_transaction_atomic_on_exception(self):
        s = store.DurableStore(self.d)
        with self.assertRaises(RuntimeError):
            with s.transaction() as tx:
                tx.put("t", "x", 1)
                raise RuntimeError
        self.assertEqual(s.items("t"), {})
        self.assertEqual(store.DurableStore(self.d).items("t"), {})

    def test_cas_conflict(self):
        s = store.DurableStore(self.d)
        g = s.generation
        s.put("t", "a", 1)
        self.assertEqual(code(lambda: s.transaction(expect_generation=g).__enter__()), "E_CONFLICT")

    def test_snapshot_backup_restore_floor(self):
        s = store.DurableStore(self.d)
        s.put("t", "a", 1)
        b = self.d / "backup.json"
        s.backup(b)
        s.put("t", "b", 2)
        s.snapshot()
        self.assertEqual(store.DurableStore(self.d).items("t"), {"a": 1, "b": 2})
        self.assertEqual(code(store.DurableStore.restore, b, self.d / "r", min_generation=2), "E_POLICY_ROLLBACK")
        r = store.DurableStore.restore(b, self.d / "r2", min_generation=1)
        self.assertEqual(r.items("t"), {"a": 1})


class ReplayTest(unittest.TestCase):
    def test_restart_does_not_reopen_replay(self):
        d = Path(tempfile.mkdtemp())
        b = replay.ChallengeBook(store.DurableStore(d), ttl=30)
        n = b.issue("n1", 0.0, audience="a")
        b.consume(n, "n1", 1.0, audience="a")
        b2 = replay.ChallengeBook(store.DurableStore(d), ttl=30)
        self.assertEqual(code(b2.consume, n, "n1", 2.0, audience="a"), "E_REPLAY")

    def test_bounded_retention_and_post_prune_replay(self):
        b = replay.ChallengeBook(store.DurableStore(tempfile.mkdtemp(), fsync=False), ttl=10, skew_margin=1)
        n = b.issue("n1", 0.0, audience="a")
        b.consume(n, "n1", 1.0, audience="a")
        for i in range(50):
            b.issue("n1", 20.0 + i, audience="a")
        self.assertLessEqual(len(b.store.items("challenges")), 12)  # bounded by ttl window
        self.assertEqual(code(b.consume, n, "n1", 80.0, audience="a"), "E_UNISSUED_CHALLENGE")

    def test_capacity_audience_and_cross_node(self):
        b = replay.ChallengeBook(store.DurableStore(tempfile.mkdtemp(), fsync=False), ttl=10, max_outstanding=2)
        n = b.issue("n1", 0, audience="a")
        b.issue("n1", 0, audience="a")
        self.assertEqual(code(b.issue, "n1", 0, audience="a"), "E_OVERLOADED")
        self.assertEqual(code(b.consume, n, "n2", 1, audience="a"), "E_UNISSUED_CHALLENGE")
        self.assertEqual(code(b.consume, n, "n1", 1, audience="b"), "E_UNISSUED_CHALLENGE")
        self.assertEqual(code(b.consume, n, "n1", 11, audience="a"), "E_CHALLENGE_EXPIRED")
        self.assertEqual(code(b.consume, n, "n1", 12, audience="a"), "E_REPLAY")

    def test_lease_fencing(self):
        s = store.DurableStore(tempfile.mkdtemp(), fsync=False)
        lm = replay.LeaseManager(s, ttl=5)
        b = replay.ChallengeBook(s, ttl=10, leases=lm)
        la = lm.acquire("replica-a", 0)
        self.assertEqual(code(lm.acquire, "replica-b", 1), "E_FENCED")
        n = b.issue("n1", 1, audience="a", lease=la)
        lb = lm.acquire("replica-b", 6)  # a's lease expired; b takes over with a higher token
        self.assertGreater(lb.token, la.token)
        self.assertEqual(code(b.consume, n, "n1", 6, audience="a", lease=la), "E_FENCED")
        b.consume(n, "n1", 6, audience="a", lease=lb)


class EnrollmentTest(unittest.TestCase):
    def setUp(self):
        self.w = k.World()

    def test_ceremony_and_single_use_ticket(self):
        t = self.w.tpm("n1")
        b = self.w.enroll.begin("n1", t.ek_cert.public_bytes(serialization.Encoding.PEM), t.ak_public_pem, operator=k.operator())
        sig = t.sign_raw(enrollment.DOMAIN + b["challenge"] + b["ak_name"])
        self.assertEqual(self.w.enroll.complete(b["ticket"], sig)["status"], "active")
        self.assertEqual(code(self.w.enroll.complete, b["ticket"], sig), "E_UNISSUED_CHALLENGE")

    def test_pop_failure_and_expiry(self):
        t = self.w.tpm("n1")
        pem = t.ek_cert.public_bytes(serialization.Encoding.PEM)
        b = self.w.enroll.begin("n1", pem, t.ak_public_pem, operator=k.operator())
        other = self.w.tpm("x")
        self.assertEqual(code(self.w.enroll.complete, b["ticket"], other.sign_raw(b"junk")), "E_POP_FAILED")
        b = self.w.enroll.begin("n1", pem, t.ak_public_pem, operator=k.operator())
        self.w.mono.advance(enrollment.ENROLL_TTL + 1)
        self.assertEqual(code(self.w.enroll.complete, b["ticket"], t.sign_raw(enrollment.DOMAIN + b["challenge"] + b["ak_name"])), "E_CHALLENGE_EXPIRED")

    def test_authz_and_untrusted_ek(self):
        t = self.w.tpm("n1")
        pem = t.ek_cert.public_bytes(serialization.Encoding.PEM)
        self.assertEqual(code(self.w.enroll.begin, "n1", pem, t.ak_public_pem, operator=k.operator(("read",))), "E_FORBIDDEN")
        from gap06_device_identity_and_attestation.mc import simulator
        rogue = simulator.SoftTPM("rogue")  # own root, not in trust store
        self.assertEqual(code(self.w.enroll.begin, "n9", rogue.ek_cert.public_bytes(serialization.Encoding.PEM), rogue.ak_public_pem, operator=k.operator()), "E_CERT_CHAIN")

    def test_clone_refused_until_revoked_and_replace(self):
        t = self.w.enrol("n1")
        pem = t.ek_cert.public_bytes(serialization.Encoding.PEM)
        self.assertEqual(code(self.w.enroll.begin, "n2", pem, t.ak_public_pem, operator=k.operator()), "E_DUPLICATE_IDENTITY")
        b = self.w.enroll.replace("n1", "n2", pem, t.ak_public_pem, operator=k.operator())
        self.w.enroll.complete(b["ticket"], t.sign_raw(enrollment.DOMAIN + b["challenge"] + b["ak_name"]))
        self.assertEqual(self.w.store.get("nodes", "n1")["status"], "revoked")
        self.assertEqual(self.w.store.get("nodes", "n2")["status"], "active")

    def test_rotation(self):
        t = self.w.enrol("n1")
        new = self.w.tpm("n1b")
        forged = new.sign_raw(enrollment.ROTATE + enrollment.ak_name(new.ak_public_pem))
        self.assertEqual(code(self.w.enroll.rotate, "n1", new.ak_public_pem, forged), "E_POP_FAILED")
        ok = t.sign_raw(enrollment.ROTATE + enrollment.ak_name(new.ak_public_pem))
        self.assertEqual(self.w.enroll.rotate("n1", new.ak_public_pem, ok)["generation"], 2)


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.w = k.World()
        self.doc = {"environment": k.ENV, "version": 1, "not_before": k.T0 - 1, "accepted": {"0": ["00" * 32]}}

    def test_quorum_and_bad_signatures(self):
        self.assertEqual(code(self.w.publisher.activate, self.doc, self.w.sign_policy(self.doc, ("ap0",)), now=k.T0), "E_QUORUM")
        sigs = self.w.sign_policy(self.doc, ("ap0",))
        sigs["ap1"] = "00" * 64
        sigs["mallory"] = "00" * 64
        self.assertEqual(code(self.w.publisher.activate, self.doc, sigs, now=k.T0), "E_QUORUM")
        tampered = dict(self.doc, accepted={"0": ["11" * 32]})
        self.assertEqual(code(self.w.publisher.activate, tampered, self.w.sign_policy(self.doc), now=k.T0), "E_QUORUM")

    def test_rollback_env_staging(self):
        self.w.publisher.activate(self.doc, self.w.sign_policy(self.doc), now=k.T0)
        self.assertEqual(code(self.w.publisher.activate, self.doc, self.w.sign_policy(self.doc), now=k.T0), "E_POLICY_ROLLBACK")
        other = dict(self.doc, environment="dev", version=2)
        self.assertEqual(code(self.w.publisher.activate, other, self.w.sign_policy(other), now=k.T0), "E_TENANT_BOUNDARY")
        future = dict(self.doc, version=2, not_before=k.T0 + 100)
        self.assertEqual(code(self.w.publisher.activate, future, self.w.sign_policy(future), now=k.T0), "E_CONFLICT")
        self.assertEqual(self.w.publisher.active()["version"], 1)

    def test_rollout_percent(self):
        d = dict(self.doc, rollout={"percent": 30})
        self.w.publisher.activate(d, self.w.sign_policy(d), now=k.T0)
        inc = sum(self.w.publisher.rollout_includes(f"n{i}") for i in range(1000))
        self.assertTrue(230 < inc < 370, inc)

    def test_precedence(self):
        r = policy.resolve([{"domain": "cost", "decision": "allow"}, {"domain": "security", "decision": "deny", "reason": "unattested"}])
        self.assertEqual((r["decision"], r["domain"]), ("deny", "security"))
        r = policy.resolve([{"domain": "security", "decision": "allow"}, {"domain": "residency", "decision": "deny"}])
        self.assertEqual((r["decision"], r["domain"]), ("deny", "residency"))
        self.assertEqual(policy.resolve([])["decision"], "deny")
        self.assertEqual(policy.resolve([{"domain": "slo", "decision": "allow"}])["decision"], "allow")


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.w = k.World()
        self.keys = {self.w.audit_kid: self.w.ks.public_key_pem(self.w.audit_kid)}
        for i in range(5):
            self.w.ledger.append("verdict", k.T0 + i, node=f"n{i}")

    def test_verify_and_tamper(self):
        p = self.w.ledger.path
        self.assertEqual(audit.AuditLedger.verify(p, self.keys, self.w.ledger.anchor()), 5)
        lines = p.read_text().splitlines()
        rec = json.loads(lines[2]); rec["event"]["fields"]["node"] = "evil"; lines[2] = json.dumps(rec)
        p.write_text("\n".join(lines) + "\n")
        self.assertEqual(code(audit.AuditLedger.verify, p, self.keys), "E_LEDGER_TAMPER")

    def test_truncation_needs_anchor(self):
        p = self.w.ledger.path
        anchor = self.w.ledger.anchor()
        p.write_text("\n".join(p.read_text().splitlines()[:3]) + "\n")
        self.assertEqual(audit.AuditLedger.verify(p, self.keys), 3)  # hash chain alone is blind to truncation
        self.assertEqual(code(audit.AuditLedger.verify, p, self.keys, anchor), "E_LEDGER_TAMPER")

    def test_redaction_and_unknown_type(self):
        self.w.ledger.append("reject", k.T0, detail="nonce " + "ab" * 32)
        self.assertNotIn("ab" * 32, self.w.ledger.path.read_text())
        self.assertEqual(code(self.w.ledger.append, "made_up", k.T0), "E_SCHEMA")

    def test_forged_key(self):
        other = keys.SoftwareKeyStore(acl={"audit": {"gap06-audit": {"sign"}}})
        other.create("audit")
        self.assertEqual(code(audit.AuditLedger.verify, self.w.ledger.path, {self.w.audit_kid: other.public_key_pem("audit/v1")}), "E_LEDGER_TAMPER")


class KeyStoreTest(unittest.TestCase):
    def test_acl_rotation_destroy_repr(self):
        ks = keys.SoftwareKeyStore(acl={"svc": {"alice": {"sign", "rotate", "destroy"}}})
        v1 = ks.create("svc")
        self.assertEqual(code(ks.sign, v1, b"m", principal="bob"), "E_FORBIDDEN")
        ks.sign(v1, b"m", principal="alice")
        v2 = ks.rotate("svc", principal="alice")
        self.assertEqual(code(ks.sign, v1, b"m", principal="alice"), "E_FORBIDDEN")
        ks.sign(v2, b"m", principal="alice")
        ks.destroy(v2, principal="alice")
        self.assertEqual(code(ks.sign, v2, b"m", principal="alice"), "E_UNKNOWN_KEY")
        self.assertNotIn("PRIVATE", repr(ks))


if __name__ == "__main__":
    unittest.main()
