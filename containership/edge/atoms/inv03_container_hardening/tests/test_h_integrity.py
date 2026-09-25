"""Items 19-29, 33-34, 38, 62: baseline integrity, exception authority, time, audit."""
import copy
import os
import tempfile
import unittest

from hkit import APPROVER, REQUESTER, SERVICE, FakeTime, build, hardened_pod, request

from inv03_container_hardening.hardening.authority import AuthError, Authenticator
from inv03_container_hardening.hardening.baseline import (
    BaselineError, BaselineStore, Keyring, default_document, migrate, resolve_settings,
    sign_baseline, validate_document, verify_signed)
from inv03_container_hardening.hardening.core import AuditLedger, ClockUntrusted, TrustedClock

KR = Keyring({"release-signer": b"s" * 32})


class Baselines(unittest.TestCase):
    def test_item19_document_validation_fails_closed(self):
        for bad in (None, [], {"schema": "PK_HARDEN_BASELINE/2"},
                    dict(default_document(), controls=[]),
                    dict(default_document(), controls=["seccomp", "seccomp"]),
                    dict(default_document(), controls=["made-up"]),
                    dict(default_document(), version="4.3"),
                    dict(default_document(), version="4.2.9"),
                    dict(default_document(), extra=1),
                    dict(default_document(), seccomp_profiles={"p": "md5:x"}),
                    dict(default_document(), overlays={"bad-scope": {}})):
            with self.assertRaises(BaselineError):
                validate_document(bad)

    def test_item20_signature_and_tamper(self):
        art = sign_baseline(default_document(), KR, "release-signer")
        self.assertEqual(verify_signed(art, KR)["version"], "4.3.0")
        t = copy.deepcopy(art)
        t["document"]["controls"].remove("sandbox-runtime")
        with self.assertRaises(BaselineError) as e:
            verify_signed(t, KR)
        self.assertEqual(e.exception.code, "BASELINE_TAMPERED")
        t = copy.deepcopy(art)
        t["signer"] = "attacker"
        with self.assertRaises(BaselineError):
            verify_signed(t, KR)
        other = Keyring({"release-signer": b"x" * 32})
        with self.assertRaises(BaselineError):
            verify_signed(art, other)

    def test_item21_22_atomic_activation_cache_and_rollback(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "b.json")
            s = BaselineStore(p, KR)
            e1 = s.activate(sign_baseline(default_document(), KR, "release-signer"), 0)
            doc2 = dict(default_document(), version="4.3.1")
            e2 = s.activate(sign_baseline(doc2, KR, "release-signer"), e1)
            with self.assertRaises(BaselineError) as e:
                s.activate(sign_baseline(doc2, KR, "release-signer"), e1)  # stale epoch
            self.assertEqual(e.exception.code, "EPOCH_CONFLICT")
            with self.assertRaises(BaselineError) as e:
                s.activate(sign_baseline(default_document(), KR, "release-signer"), e2)
            self.assertEqual(e.exception.code, "BASELINE_DOWNGRADE")
            # last-known-good survives a restart (cache re-verified on load)
            s2 = BaselineStore(p, KR)
            self.assertEqual(s2.active()[1]["version"], "4.3.1")
            s2.rollback(s2.epoch)
            self.assertEqual(BaselineStore(p, KR).active()[1]["version"], "4.3.0")
            # a tampered cache is refused on load
            raw = open(p).read().replace('"4.3.0"', '"4.9.9"', 1)
            open(p, "w").write(raw)
            with self.assertRaises(BaselineError):
                BaselineStore(p, KR)

    def test_item27_28_overlays_only_tighten(self):
        doc = default_document()
        doc["overlays"] = {"team-a/*/*": {"max_exception_ttl": 86400},
                           "team-a/prod/eu1": {"sandbox_runtime_classes": ["gvisor"]}}
        s = resolve_settings(validate_document(doc), "team-a", "prod", "eu1")
        self.assertEqual(s["max_exception_ttl"], 86400)
        for loosen in ({"max_exception_ttl": 10**9}, {"require_user_namespace": False},
                       {"sandbox_runtime_classes": ["gvisor", "runc"]}, {"namespace_default_deny": False},
                       {"unknown": 1}):
            d2 = default_document()
            d2["settings"]["namespace_default_deny"] = True
            d2["overlays"] = {"team-a/prod/*": loosen}
            with self.assertRaises(BaselineError, msg=str(loosen)):
                resolve_settings(validate_document(d2), "team-a", "prod", "eu1")

    def test_item29_migration(self):
        m = migrate({"schema": "PK_HARDEN_BASELINE/1", "version": "4.2.0", "controls": ["non-root"]})
        self.assertIn("sandbox-runtime", m["controls"])
        self.assertTrue(m["settings"]["require_user_namespace"])
        with self.assertRaises(BaselineError):
            migrate({"schema": "PK_HARDEN_BASELINE/0"})


class Authority(unittest.TestCase):
    def setUp(self):
        self.eng, self.ft, _ = build()
        self.store = self.eng.exceptions

    def _pod(self):
        p = hardened_pod()
        p["containers"][0]["securityContext"]["readOnlyRootFilesystem"] = False
        return p

    def test_item23_24_approved_exception_admits_and_is_audited(self):
        wl = "team-a/Deployment/api"
        rid = self.store.request(REQUESTER, wl, "read-only-root", "writes spool", "OPS-12", "team-a", 3600)
        self.assertFalse(self.eng.decide(request(self._pod()))["admit"])  # requested != approved
        with self.assertRaises(AuthError) as e:
            self.store.approve(REQUESTER, rid)
        self.assertEqual(e.exception.code, "UNAUTHORIZED")
        with self.assertRaises(AuthError):
            self.store.approve(SERVICE, rid)  # service principals never approve
        self.store.approve(APPROVER, rid)
        d = self.eng.decide(request(self._pod()))
        self.assertTrue(d["admit"], d)
        self.assertEqual(d["excepted"][0]["exception_id"], rid)
        kinds = [e["kind"] for e in self.eng.ledger.events()]
        self.assertIn("exception.approved", kinds)

    def test_item24_separation_of_duties(self):
        both = type(APPROVER)("dave", "human", frozenset({"approver", "developer"}))
        rid = self.store.request(both, "w", "seccomp", "r", "T-1", "o", 60)
        with self.assertRaises(AuthError) as e:
            self.store.approve(both, rid)
        self.assertEqual(e.exception.code, "SEPARATION_OF_DUTIES")

    def test_item25_ttl_renewal_sweep(self):
        with self.assertRaises(AuthError):
            self.store.request(REQUESTER, "w", "seccomp", "r", "T", "o", 31 * 86400)
        rid = self.store.request(REQUESTER, "w", "seccomp", "r", "T", "o", 100)
        self.store.approve(APPROVER, rid)
        self.store.renew(APPROVER, rid, 100)
        self.store.renew(APPROVER, rid, 100)
        with self.assertRaises(AuthError) as e:
            self.store.renew(APPROVER, rid, 100)
        self.assertEqual(e.exception.code, "RENEWAL_LIMIT")
        self.ft.t += 1000
        self.assertIn(rid, self.store.sweep(int(self.ft.t)))
        reg = self.store.registry(int(self.ft.t))
        self.assertEqual(reg[0]["status"], "expired")

    def test_sandbox_control_is_never_waivable(self):
        rid = self.store.request(REQUESTER, "team-a/Deployment/api", "sandbox-runtime", "r", "T", "o", 100)
        self.store.approve(APPROVER, rid)
        p = hardened_pod()
        p["runtimeClassName"] = "runc"
        self.assertEqual(self.eng.decide(request(p))["failed"], ["sandbox-runtime"])

    def test_revocation_takes_effect_immediately(self):
        wl = "team-a/Deployment/api"
        rid = self.store.request(REQUESTER, wl, "read-only-root", "r", "T", "o", 3600)
        self.store.approve(APPROVER, rid)
        self.store.revoke(APPROVER, rid)
        self.assertFalse(self.eng.decide(request(self._pod()))["admit"])

    def test_item23_store_rebuilds_from_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            eng, ft, _ = build(d)
            rid = eng.exceptions.request(REQUESTER, "w", "seccomp", "r", "T", "o", 100)
            eng.exceptions.approve(APPROVER, rid)
            eng2, *_ = build(d)
            self.assertIsNotNone(eng2.exceptions.active_for("w", "seccomp", int(ft.t)))

    def test_item33_authentication(self):
        ft = FakeTime()
        auth = Authenticator(b"k" * 32, {"carol": REQUESTER}, TrustedClock(ft))
        tok = auth.issue("carol", "n1")
        self.assertEqual(auth.authenticate(tok), REQUESTER)
        for bad in (tok, tok[:-1] + ("0" if tok[-1] != "0" else "1"), "x.y.z", None,
                    auth.issue("mallory", "n2")):
            with self.assertRaises(AuthError):
                auth.authenticate(bad)
        tok2 = auth.issue("carol", "n3")
        ft.t += 301
        with self.assertRaises(AuthError):
            auth.authenticate(tok2)

    def test_item34_authorization(self):
        d = self.eng.decide(request(), principal=APPROVER)  # approver lacks "evaluate"
        self.assertEqual(d["reason"], "UNAUTHORIZED")
        self.assertTrue(self.eng.decide(request(), principal=REQUESTER)["admit"])
        with self.assertRaises(AuthError):
            self.eng.set_emergency(SERVICE, True, "x")


class TimeAndAudit(unittest.TestCase):
    def test_item26_trusted_clock(self):
        ft = FakeTime()
        c = TrustedClock(ft)
        c.now()
        ft.t -= 10
        with self.assertRaises(ClockUntrusted):
            c.now()
        with self.assertRaises(ClockUntrusted):
            TrustedClock(lambda: 1_800_000_000.0, reference=lambda: 1_800_000_100.0).now()
        with self.assertRaises(ClockUntrusted):
            TrustedClock(lambda: (_ for _ in ()).throw(OSError("ntp down"))).now()

    def test_item26_untrusted_clock_denies(self):
        eng, ft, _ = build()
        eng.clock.now()
        ft.t -= 100
        self.assertEqual(eng.decide(request())["reason"], "CLOCK_UNTRUSTED")

    def test_item38_audit_chain_detects_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "a.jsonl")
            led = AuditLedger(p, b"a" * 32)
            for i in range(5):
                led.append("decision", f"w{i}", "x", i, {"i": i})
            head = led.head
            self.assertTrue(AuditLedger(p, b"a" * 32).verify(head)[0])
            lines = open(p).read().splitlines()
            for mutate in (lambda L: L[:2] + L[3:],                       # deletion
                           lambda L: [L[1], L[0]] + L[2:],                # reorder
                           lambda L: L[:-1],                              # tail truncation
                           lambda L: L[:1] + [L[1].replace('"i":1', '"i":9')] + L[2:]):  # edit
                open(p, "w").write("\n".join(mutate(lines)) + "\n")
                self.assertFalse(AuditLedger(p, b"a" * 32).verify(head)[0])
            open(p, "w").write("\n".join(lines) + "\n")
            self.assertFalse(AuditLedger(p, b"b" * 32).verify(head)[0])  # wrong seal key

    def test_item38_fork_splice_detected(self):
        # Two ledgers under the same key diverge; splicing a correctly sealed,
        # correctly numbered record from the fork must still break the chain.
        a, b = AuditLedger(None, b"a" * 32), AuditLedger(None, b"a" * 32)
        a.append("k", "s", "x", 0, {"v": 0})
        b.append("k", "s", "x", 0, {"v": "fork"})
        a.append("k", "s", "x", 1, {"v": 1})
        b.append("k", "s", "x", 1, {"v": 1})
        a._mem[1] = b._mem[1]
        ok, why = a.verify()
        self.assertFalse(ok)
        self.assertIn("chain break", why)


if __name__ == "__main__":
    unittest.main()
