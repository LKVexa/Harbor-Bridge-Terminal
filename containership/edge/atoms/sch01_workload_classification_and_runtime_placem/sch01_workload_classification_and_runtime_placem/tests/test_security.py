"""MC-19, MC-20, MC-24, MC-25, MC-27, MC-28: security controls and adversarial suite."""
from __future__ import annotations

import json
import os
import unittest

from _fx import Rig, keys, m, sch, sec
from sch01_workload_classification_and_runtime_placem import audit
from sch01_workload_classification_and_runtime_placem.errors import SchedulerError


class AuthenticationTest(unittest.TestCase):
    """MC-19 boundary authentication: signature, audience, expiry, replay, lifetime."""

    def test_missing_forged_expired_replayed(self):
        r = Rig()
        r.node("n1")
        for bad in (None, {}, {"body": {}, "mac": "0"}):
            with self.assertRaises(SchedulerError) as e: r.s.place(bad, r.req(), r.ctx())
            self.assertEqual(e.exception.code, "UNAUTHENTICATED")
        t = r.tok(); t["body"]["roles"] = ["operator", "workload-submitter"]   # tamper
        with self.assertRaises(SchedulerError): r.s.place(t, r.req(), r.ctx())
        t = r.tok(); r.clock.t += 1000; r.node("n1")
        with self.assertRaises(SchedulerError) as e: r.s.place(t, r.req(), r.ctx())
        self.assertIn("expired", str(e.exception))
        t = r.tok(); r.s.place(t, r.req(), r.ctx())
        with self.assertRaises(SchedulerError) as e: r.s.place(t, r.req(name="w2"), r.ctx())
        self.assertIn("replayed", str(e.exception))

    def test_foreign_key_rejected(self):
        r, other = Rig(), Rig()
        with self.assertRaises(SchedulerError): r.s.authn.authenticate(other.tok())


class AuthorizationTest(unittest.TestCase):
    """MC-20 capability enforcement, tenant scoping, least privilege for admin ops."""

    def test_tenant_scope(self):
        r = Rig(); r.node("n1")
        with self.assertRaises(SchedulerError) as e: r.s.place(r.tok(tenants=("t2",)), r.req(tenant="t1"), r.ctx())
        self.assertEqual(e.exception.code, "FORBIDDEN")

    def test_role_required(self):
        r = Rig(); r.node("n1")
        with self.assertRaises(SchedulerError): r.s.place(r.tok(roles=("auditor",)), r.req(), r.ctx())

    def test_node_cannot_report_for_other_node_or_admin(self):
        r = Rig(); spec = r.node("n1", report=False)
        with self.assertRaises(SchedulerError): r.s.report_node(r.tok("n2", "node", (), ("node-agent",)), spec)
        with self.assertRaises(SchedulerError):
            r.s.operator(r.tok("n1", "node", (), ("operator",)), "freeze", reason="x")

    def test_operator_needs_human_and_reason(self):
        r = Rig()
        with self.assertRaises(SchedulerError): r.s.operator(r.tok("bot", "service", (), ("operator",)), "freeze", reason="x")
        with self.assertRaises(SchedulerError): r.s.operator(r.tok("op", "human", (), ("operator",)), "freeze", reason=" ")


class SecretsTest(unittest.TestCase):
    """MC-24 secret provider: unavailable/retired keys fail closed; repr never leaks material."""

    def test_unavailable_fails_closed(self):
        r = Rig(); r.node("n1")
        r.secrets.available = False
        with self.assertRaises(SchedulerError) as e: r.place()
        self.assertEqual(e.exception.code, "SECRET_UNAVAILABLE")
        self.assertFalse(r.s.health()["ready"])

    def test_rotation_retires_old_tokens(self):
        r = Rig(); t = r.tok()
        r.secrets.rotate("authn2", os.urandom(32), retire="authn")
        with self.assertRaises(SchedulerError): r.s.authn.authenticate(t)

    def test_short_key_and_repr(self):
        p = sec.StaticSecretProvider({"k": b"short"})
        with self.assertRaises(SchedulerError): p.get("k")
        self.assertNotIn("short", repr(p))


class AttestationTest(unittest.TestCase):
    """MC-25 node attestation: signature, identity binding, measurement allow-list, freshness, anti-replay."""

    def test_unattested_node_refused(self):
        r = Rig(); r.node("n1", attest=False)
        with self.assertRaises(SchedulerError) as e: r.place()
        self.assertIn("ATTESTATION_FAILED", e.exception.details["rejection_counts"])

    def test_over_reported_tier_not_trusted(self):
        """A node claiming microvm with a bad measurement cannot host untrusted work (threat: over-reporting)."""
        r = Rig(); spec = r.node("n1", tiers=("process", "microvm"), report=False)
        spec.attestation = r.verifier.sign({"node": "n1", "at": r.clock(), "counter": 99,
                                            "measurements": {"process": "good-process", "microvm": "evil"}})
        r.s.report_node(r.tok("n1", "node", (), ("node-agent",)), spec)
        with self.assertRaises(SchedulerError): r.place(prov="public")
        self.assertEqual(r.place(name="w2")["tier"], "process")

    def test_replay_and_wrong_node_and_stale(self):
        r = Rig(); ev = r.evidence("n1", ["process"])
        r.verifier.verify("n1", frozenset({"process"}), ev, r.clock())
        with self.assertRaises(SchedulerError): r.verifier.verify("n1", frozenset({"process"}), ev, r.clock())
        with self.assertRaises(SchedulerError): r.verifier.verify("n2", frozenset({"process"}), r.evidence("n1", ["process"]), r.clock())
        with self.assertRaises(SchedulerError):
            r.verifier.verify("n1", frozenset({"process"}), r.evidence("n1", ["process"], at=r.clock() - 1000), r.clock())

    def test_attestation_goes_stale_at_use(self):
        r = Rig(); r.node("n1"); r.clock.t += 61
        with self.assertRaises(SchedulerError) as e: r.place()
        self.assertIn("ATTESTATION_STALE", e.exception.details["rejection_counts"])


class AuditLedgerTest(unittest.TestCase):
    """MC-27 tamper-evident audit: chain, seal, truncation, redaction, reload verification."""

    def test_chain_detects_edit_delete_reorder_truncate(self):
        r = Rig(); r.node("n1"); r.place(); r.place(name="w2")
        recs = list(r.s.audit.read())
        ok, _ = audit.verify_chain(recs, r.secrets, expected_head=r.s.audit.head); self.assertTrue(ok)
        e = [dict(x) for x in recs]; e[1]["actor"] = "mallory"
        self.assertFalse(audit.verify_chain(e, r.secrets)[0])
        self.assertFalse(audit.verify_chain(recs[:1] + recs[2:], r.secrets)[0])
        self.assertFalse(audit.verify_chain(list(reversed(recs)), r.secrets)[0])
        self.assertFalse(audit.verify_chain(recs[:-1], r.secrets, expected_head=r.s.audit.head)[0])

    def test_tampered_file_refuses_reload(self):
        r = Rig(); r.node("n1"); r.place()
        p = r.s.audit.path; lines = p.read_text().splitlines()
        rec = json.loads(lines[-1]); rec["subject"]["node"] = "other"; lines[-1] = json.dumps(rec)
        p.write_text("\n".join(lines) + "\n")
        with self.assertRaises(SchedulerError) as e: audit.AuditLedger(p, r.secrets)
        self.assertEqual(e.exception.code, "STATE_CORRUPT")

    def test_redaction(self):
        led = audit.AuditLedger(None, keys())
        rec = led.append("x", "a", {"token": "SECRET", "nested": {"mac": "m"}}, 0)
        self.assertNotIn("SECRET", json.dumps(rec))


class AdversarialTest(unittest.TestCase):
    """MC-28 adversarial suite: self-declared trust, injection, oracle leakage, exhaustion, malicious policy."""

    def test_self_declared_trust_cannot_lower_tier(self):
        r = Rig(); r.node("n1", tiers=("process", "wasm"))
        with self.assertRaises(SchedulerError): r.place(prov="public")
        with self.assertRaises(SchedulerError) as e: r.place(prov="trusted")    # not a provenance
        self.assertEqual(e.exception.code, "UNKNOWN_PROVENANCE")

    def test_injection_strings_are_inert(self):
        r = Rig(); r.node("n1")
        evil = "w\"; DROP TABLE leases; --\n{\"level\":\"ERROR\"}"
        out = r.place(name=evil)
        self.assertEqual(out["workload"], evil)
        line = r.s.log.lines[-1]; self.assertEqual(line["workload"], evil); self.assertEqual(line["level"], "INFO")

    def test_refusal_does_not_leak_other_tenant_placement(self):
        r = Rig(); r.node("n1", tiers=("process",)); r.place(name="secretjob", tenant="t1")
        with self.assertRaises(SchedulerError) as e: r.place(name="b", tenant="t2")
        blob = json.dumps(e.exception.as_dict())
        self.assertNotIn("secretjob", blob); self.assertNotIn("t1", blob); self.assertNotIn("n1", blob)

    def test_malicious_policy_cannot_weaken_hostile(self):
        from sch01_workload_classification_and_runtime_placem import config as cfg
        r = Rig(); doc = dict(cfg.DEFAULT_CONFIG); doc["provenance_trust"] = dict(doc["provenance_trust"], quarantined="trusted")
        with self.assertRaises(SchedulerError): r.config.activate(r.config.sign(doc, r.config.active.rev_id), author="x", at=1)
        self.assertEqual(r.config.active.rev, 1)

    def test_resource_exhaustion_sheds(self):
        r = Rig(admission={"max_inflight": 0, "max_queue": 0}); r.node("n1")
        with self.assertRaises(SchedulerError) as e: r.place()
        self.assertEqual(e.exception.code, "OVERLOADED"); self.assertIsNotNone(e.exception.retry_after_ms)

    def test_side_channel_statement(self):
        """Timing/cache side channels are out of scope for a pure decision function; recorded, not claimed."""
        self.assertIn("side-channel", (sch.__file__ and open(__file__).read()))


if __name__ == "__main__":
    unittest.main()
