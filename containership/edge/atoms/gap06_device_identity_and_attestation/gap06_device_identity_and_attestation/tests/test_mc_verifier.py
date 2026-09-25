"""MC-01/02/31/32/33 verifier, parser and certificate-chain tests."""
import datetime as dt
import json
import struct
import unittest

import _kit as k
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, ed25519

from gap06_device_identity_and_attestation.mc import algorithms as alg, certchain, simulator, tpm, verifier
from gap06_device_identity_and_attestation.mc.errors import Gap06Error


def code(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except Gap06Error as e:
        return e.code
    return "NO_ERROR"


class QuoteParserTest(unittest.TestCase):
    def setUp(self):
        self.t = simulator.SoftTPM("n1")
        k.boot_pcrs(self.t)
        self.attest, self.sig, self.pcrs = self.t.quote(b"\x01" * 32)

    def test_roundtrip(self):
        q = tpm.parse_attest(self.attest)
        self.assertEqual(q.extra_data, b"\x01" * 32)
        self.assertEqual(q.pcr_selection, (("sha256", (0, 1, 2, 7)),))

    def test_trailing_bytes(self):
        self.assertEqual(code(tpm.parse_attest, self.attest + b"\0"), "E_TRAILING_BYTES")

    def test_bad_magic(self):
        self.assertEqual(code(tpm.parse_attest, b"\0\0\0\0" + self.attest[4:]), "E_BAD_MAGIC")

    def test_truncation_every_offset(self):
        for n in range(len(self.attest)):
            self.assertIn(code(tpm.parse_attest, self.attest[:n]), {"E_MALFORMED_EVIDENCE", "E_BAD_MAGIC"}, n)

    def test_wrong_type(self):
        bad = self.attest[:4] + struct.pack(">H", 0x8017) + self.attest[6:]
        self.assertEqual(code(tpm.parse_attest, bad), "E_MALFORMED_EVIDENCE")

    def test_duplicate_bank_and_illegal_select(self):
        sel = (("sha256", (0,)), ("sha256", (1,)))
        raw = tpm.build_attest(nonce=b"n", signer=b"s", clock=self.t.clock, firmware=1, selection=sel, pcr_digest=b"d")
        self.assertEqual(code(tpm.parse_attest, raw), "E_MALFORMED_EVIDENCE")
        i = raw.index(struct.pack(">H", 0x000B)) + 2
        self.assertEqual(code(tpm.parse_attest, raw[:i] + b"\x09" + raw[i + 1:]), "E_MALFORMED_EVIDENCE")

    def test_sha1_bank_rejected_by_policy_in_verifier(self):
        sel = (("sha1", (0,)),)
        raw = tpm.build_attest(nonce=b"n", signer=b"s", clock=self.t.clock, firmware=1, selection=sel, pcr_digest=b"d")
        self.assertEqual(tpm.parse_attest(raw).pcr_selection[0][0], "sha1")  # parses, but ...
        self.assertEqual(code(alg.DEFAULT_POLICY.check_digest, "sha1"), "E_UNSUPPORTED_ALG")

    def test_signature_parse(self):
        prof, _ = tpm.parse_signature(self.sig)
        self.assertEqual(prof, "ecdsa-p256-sha256")
        self.assertEqual(code(tpm.parse_signature, self.sig + b"x"), "E_TRAILING_BYTES")
        self.assertEqual(code(tpm.parse_signature, b"\x00\x99" + self.sig[2:]), "E_UNSUPPORTED_ALG")
        self.assertEqual(code(tpm.parse_signature, self.sig[:2] + b"\x00\x04" + self.sig[4:]), "E_UNSUPPORTED_ALG")


class EventLogTest(unittest.TestCase):
    def test_replay_matches_and_divergence(self):
        t = simulator.SoftTPM("n1")
        k.boot_pcrs(t)
        ev = tpm.parse_event_log(t.event_log())
        quoted = {p: t.pcrs[("sha256", p)] for p in (0, 1, 2, 7)}
        self.assertIsNone(tpm.first_divergence(ev, "sha256", quoted))
        quoted[7] = b"\x11" * 32
        self.assertEqual(tpm.first_divergence(ev, "sha256", quoted), 3)

    def test_malformed_logs(self):
        self.assertEqual(code(tpm.parse_event_log, b"\0" * 10), "E_MALFORMED_EVIDENCE")
        good = tpm.build_event_log([(0, 1, {"sha256": b"\0" * 32}, b"x")])
        self.assertEqual(code(tpm.parse_event_log, good[:-1]), "E_MALFORMED_EVIDENCE")
        body_flip = bytearray(tpm.build_event_log([(0, 0x0D, {"sha256": __import__("hashlib").sha256(b"x").digest()}, b"x")]))
        body_flip[-1] ^= 1
        self.assertEqual(code(tpm.parse_event_log, bytes(body_flip)), "E_EVENTLOG_MISMATCH")
        hdr = bytearray(good); hdr[10] ^= 1
        self.assertEqual(code(tpm.parse_event_log, bytes(hdr)), "E_MALFORMED_EVIDENCE")
        undeclared = tpm.build_event_log([(0, 1, {"sha384": b"\0" * 48}, b"x")])
        self.assertEqual(code(tpm.parse_event_log, undeclared), "E_MALFORMED_EVIDENCE")
        bad_pcr = tpm.build_event_log([(30, 1, {"sha256": b"\0" * 32}, b"x")])
        self.assertEqual(code(tpm.parse_event_log, bad_pcr), "E_MALFORMED_EVIDENCE")


class ClockTest(unittest.TestCase):
    def test_monotonic_counters(self):
        c = tpm.ClockTracker()
        c.check("a", tpm.ClockInfo(10, 1, 0, True))
        self.assertEqual(code(c.check, "a", tpm.ClockInfo(10, 1, 0, True)), "E_CLOCK_ROLLBACK")
        self.assertEqual(code(c.check, "a", tpm.ClockInfo(99, 0, 5, True)), "E_CLOCK_ROLLBACK")
        self.assertEqual(code(c.check, "a", tpm.ClockInfo(99, 1, 0, False)), "E_TPM_CLOCK_UNSAFE")
        c.check("a", tpm.ClockInfo(1, 2, 0, True))  # reboot: resetCount up, clock may restart


class VerifierTest(unittest.TestCase):
    def setUp(self):
        self.t = simulator.SoftTPM("n1")
        k.boot_pcrs(self.t)
        self.v = verifier.Verifier()
        self.ak = verifier.EnrolledAK("n1", self.t.ak_public_pem, self.t.ak_name, "dev-1")
        self.allowed = {p: {self.t.pcrs[("sha256", p)].hex()} for p in (0, 1, 2, 7)}

    def run_(self, nonce=b"\x07" * 32, expect=None, mutate=None, **kw):
        attest, sig, pcrs = self.t.quote(nonce)
        args = dict(ak=self.ak, expected_nonce=expect or nonce, attest=attest, signature=sig, pcr_values=pcrs,
                    event_log=self.t.event_log(), allowed_pcrs=self.allowed, policy_version="1")
        args.update(kw)
        if mutate:
            mutate(args)
        return self.v.verify_tpm_quote(**args)

    def test_positive(self):
        d = self.run_()
        self.assertTrue(d.ok, d.code)
        for f in ("verifier_version", "trust_anchor_set", "policy_version", "raw_evidence_sha256",
                  "claims_sha256", "decision", "reason_code", "decided_at"):
            self.assertIn(f, d.record)

    def test_negative_vectors(self):
        def flip_sig(a):
            s = bytearray(a["signature"]); s[-1] ^= 1; a["signature"] = bytes(s)

        def flip_attest(a):
            s = bytearray(a["attest"]); s[-1] ^= 1; a["attest"] = bytes(s)

        def bad_pcr(a):
            a["pcr_values"] = {**a["pcr_values"], 7: b"\x22" * 32}

        def bad_log(a):
            t2 = simulator.SoftTPM("x"); t2.extend(0, b"other"); a["event_log"] = t2.event_log()

        cases = {"E_NONCE_MISMATCH": dict(expect=b"\x08" * 32), "E_SIGNATURE": dict(mutate=flip_sig),
                 "E_PCR_MISMATCH": dict(mutate=bad_pcr), "E_EVENTLOG_MISMATCH": dict(mutate=bad_log)}
        for want, kw in cases.items():
            self.assertEqual(self.run_(**kw).code, want)
        self.assertIn(self.run_(mutate=flip_attest).code, {"E_SIGNATURE"})

    def test_other_key_and_revoked(self):
        other = simulator.SoftTPM("evil")
        self.ak = verifier.EnrolledAK("n1", other.ak_public_pem, self.t.ak_name, "dev-1")
        self.assertEqual(self.run_().code, "E_SIGNATURE")
        self.ak = verifier.EnrolledAK("n1", self.t.ak_public_pem, self.t.ak_name, "dev-1", active=False)
        self.assertEqual(self.run_().code, "E_REVOKED")

    def test_measurement_not_accepted(self):
        self.allowed[0] = {"00" * 32}
        self.assertEqual(self.run_().code, "E_MEASUREMENT_REJECTED")

    def test_required_pcr_missing(self):
        attest, sig, pcrs = self.t.quote(b"\x07" * 32, pcrs=(0, 1))
        d = self.v.verify_tpm_quote(ak=self.ak, expected_nonce=b"\x07" * 32, attest=attest, signature=sig,
                                    pcr_values=pcrs, event_log=None, allowed_pcrs={}, policy_version="1")
        self.assertEqual(d.code, "E_PCR_MISMATCH")

    def test_counter_rollback_rejected(self):
        self.assertTrue(self.run_().ok)
        self.t.clock = tpm.ClockInfo(5, 1, 0, True)
        self.t.tick = lambda n=10: None
        self.assertEqual(self.run_().code, "E_CLOCK_ROLLBACK")

    def test_relay_channel_binding_and_duplicate_device(self):
        self.assertEqual(self.run_(channel_binding=b"a", expected_channel_binding=b"b").code, "E_NONCE_MISMATCH")
        self.assertTrue(self.run_().ok)
        self.ak = verifier.EnrolledAK("n2", self.t.ak_public_pem, self.t.ak_name, "dev-1")
        self.v.clocks = tpm.ClockTracker()
        self.assertEqual(self.run_().code, "E_DUPLICATE_IDENTITY")

    def test_ima(self):
        good = "10 " + "a" * 64 + " ima-ng sha256:" + "b" * 64 + " /usr/bin/x"
        self.assertTrue(self.run_(ima=good, ima_allowed={"sha256:" + "b" * 64}).ok)
        self.assertEqual(self.run_(ima=good, ima_allowed=set()).code, "E_MEASUREMENT_REJECTED")
        self.assertEqual(self.run_(ima=good.replace("ima-ng", "ima-sig")).code, "E_MEASUREMENT_REJECTED")
        self.assertEqual(self.run_(ima=good.replace("sha256:" + "b" * 64, "sha1:" + "b" * 40)).code, "E_UNSUPPORTED_ALG")

    def test_internal_error_never_trusts(self):
        d = self.run_(mutate=lambda a: a.update(pcr_values=None))
        self.assertFalse(d.ok)
        self.assertEqual(d.level, "untrusted")


class TeeAdapterTest(unittest.TestCase):
    def setUp(self):
        self.vk = ec.generate_private_key(ec.SECP256R1())
        self.a = verifier.GenericSignedReportAdapter(k.pem(self.vk.public_key()), min_svn=3)

    def rep(self, **over):
        doc = {"svn": 4, "debug": False, "tcb_status": "UpToDate", "report_data": "ab" * 32, "measurement": "m"}
        doc.update(over)
        b = json.dumps(doc).encode()
        return b, self.vk.sign(b, ec.ECDSA(hashes.SHA256()))

    def test_cases(self):
        self.assertEqual(self.a.verify(*self.rep(), expected_report_data=b"\xab" * 32)["svn"], 4)
        for over, want in [({"debug": True}, "E_DEBUG_ENABLED"), ({"svn": 2}, "E_TCB_OUT_OF_DATE"),
                           ({"tcb_status": "OutOfDate"}, "E_TCB_OUT_OF_DATE"), ({"report_data": "00"}, "E_NONCE_MISMATCH")]:
            self.assertEqual(code(self.a.verify, *self.rep(**over), expected_report_data=b"\xab" * 32), want)
        b, s = self.rep()
        self.assertEqual(code(self.a.verify, b + b" ", s, expected_report_data=b"\xab" * 32), "E_SIGNATURE")


class AlgorithmAgilityTest(unittest.TestCase):
    def test_policy(self):
        p = alg.AlgorithmPolicy(sha1_migration_expires_at=100.0)
        self.assertEqual(p.check_digest("sha1", now=50.0), "sha1")
        self.assertEqual(code(p.check_digest, "sha1", now=150.0), "E_UNSUPPORTED_ALG")
        self.assertEqual(code(alg.AlgorithmPolicy(fips_mode=True).check_signature, "ed25519"), "E_UNSUPPORTED_ALG")
        self.assertEqual(code(alg.DEFAULT_POLICY.check_digest, "md5"), "E_UNSUPPORTED_ALG")

    def test_curve_mismatch_and_ed25519_length(self):
        key = ec.generate_private_key(ec.SECP384R1())
        self.assertEqual(code(alg.verify, key.public_key(), "ecdsa-p256-sha256", b"x", b"m"), "E_UNSUPPORTED_ALG")
        ek = ed25519.Ed25519PrivateKey.generate()
        self.assertEqual(code(alg.verify, ek.public_key(), "ed25519", b"x" * 63, b"m"), "E_SIGNATURE")


class CertChainTest(unittest.TestCase):
    def setUp(self):
        self.rk = ec.generate_private_key(ec.SECP256R1())
        self.root = simulator.make_cert("root", self.rk, "root", self.rk, ca=True, days=3650)
        self.ik = ec.generate_private_key(ec.SECP256R1())
        self.inter = simulator.make_cert("inter", self.ik, "root", self.rk, ca=True, path_len=0)
        self.lk = ec.generate_private_key(ec.SECP256R1())
        self.leaf = simulator.make_cert("ek", self.lk, "inter", self.ik, ca=False, key_usage="ek")
        self.at = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)

    def store(self, **kw):
        return certchain.TrustStore(anchors=[self.root], intermediates=[self.inter], allow_test_roots=True, **kw)

    def test_valid(self):
        self.assertEqual(len(certchain.validate(self.leaf, self.store(), self.at, leaf_usage="ek")), 3)

    def test_failures(self):
        s = self.store()
        self.assertEqual(code(certchain.validate, self.leaf, s, dt.datetime(2030, 1, 1, tzinfo=dt.timezone.utc), leaf_usage="ek"), "E_CERT_CHAIN")
        self.assertEqual(code(certchain.validate, self.leaf, s, self.at, leaf_usage="ak"), "E_CERT_CHAIN")
        self.assertEqual(code(certchain.validate, self.leaf, certchain.TrustStore(anchors=[self.root], allow_test_roots=True), self.at, leaf_usage="ek"), "E_CERT_CHAIN")
        self.assertEqual(code(certchain.validate, self.leaf, self.store(require_revocation_info=True), self.at, leaf_usage="ek"), "E_CERT_CHAIN")
        rogue = simulator.make_cert("inter", ec.generate_private_key(ec.SECP256R1()), "root", self.rk, ca=False, key_usage="sig")
        lk2 = ec.generate_private_key(ec.SECP256R1())
        # leaf issued by a non-CA "inter" (same name, different key) must fail
        self.assertEqual(code(certchain.validate, simulator.make_cert("ek2", lk2, "inter", ec.generate_private_key(ec.SECP256R1()), ca=False, key_usage="ek"),
                              certchain.TrustStore(anchors=[self.root], intermediates=[rogue], allow_test_roots=True), self.at, leaf_usage="ek"), "E_CERT_CHAIN")

    def _crl(self, key, issuer_cn, serials):
        b = (x509.CertificateRevocationListBuilder().issuer_name(simulator._name(issuer_cn))
             .last_update(self.at - dt.timedelta(days=1)).next_update(self.at + dt.timedelta(days=7)))
        for s in serials:
            b = b.add_revoked_certificate(x509.RevokedCertificateBuilder().serial_number(s).revocation_date(self.at).build())
        return b.sign(key, hashes.SHA256())

    def test_revocation_and_poisoned_crl(self):
        s = self.store()
        s.add_crl(self._crl(self.ik, "inter", [self.leaf.serial_number]))
        self.assertEqual(code(certchain.validate, self.leaf, s, self.at, leaf_usage="ek"), "E_CERT_REVOKED")
        s2 = self.store()
        self.assertEqual(code(s2.add_crl, self._crl(ec.generate_private_key(ec.SECP256R1()), "inter", [1])), "E_CERT_CHAIN")

    def test_test_only_root_refused_by_default(self):
        s = certchain.TrustStore(anchors=[self.root], intermediates=[self.inter])
        self.assertEqual(code(certchain.validate, self.leaf, s, self.at, leaf_usage="ek"), "E_CERT_CHAIN")

    def test_pathlen(self):
        ik2 = ec.generate_private_key(ec.SECP256R1())
        inter2 = simulator.make_cert("inter2", ik2, "inter", self.ik, ca=True)
        leaf = simulator.make_cert("ek", self.lk, "inter2", ik2, ca=False, key_usage="ek")
        s = certchain.TrustStore(anchors=[self.root], intermediates=[self.inter, inter2], allow_test_roots=True)
        self.assertEqual(code(certchain.validate, leaf, s, self.at, leaf_usage="ek"), "E_CERT_CHAIN")


if __name__ == "__main__":
    unittest.main()
