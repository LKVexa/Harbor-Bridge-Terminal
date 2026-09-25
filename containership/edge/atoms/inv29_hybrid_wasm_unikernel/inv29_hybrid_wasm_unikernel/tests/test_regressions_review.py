"""Regression tests for the 4.3.0 adversarial review findings (all were
admission bypasses or trust gaps before the fix)."""
import dataclasses
import unittest

import _fixtures as F
from inv29_hybrid_wasm_unikernel import admission as adm
from inv29_hybrid_wasm_unikernel import records as R
from inv29_hybrid_wasm_unikernel.model import HostImage, WasmModule, compose


class FS(frozenset):
    def __sub__(self, other):
        return frozenset()

    def __and__(self, other):
        return frozenset()


class LyingStr(str):
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    __hash__ = str.__hash__


class ReviewRegressionTest(unittest.TestCase):
    def setUp(self):
        self.kr = F.keyring()
        self.a = F.admitter(self.kr)

    def test_R1_frozenset_subclass_refused(self):
        with self.assertRaises(TypeError):
            compose(WasmModule("svc", FS({"raw-socket"})), HostImage("h", frozenset({"clock"})))
        with self.assertRaises(TypeError):
            self.a.admit(dataclasses.replace(F.request(self.kr),
                                             module=WasmModule("svc", FS({"ptrace"}))))

    def test_R1b_str_subclass_capabilities_names_arch_refused(self):
        for mod in (WasmModule("svc", frozenset({LyingStr("clock")})),
                    WasmModule(LyingStr("svc"), frozenset()),
                    WasmModule("svc", frozenset(), architecture=LyingStr("x"))):
            with self.subTest(mod=mod), self.assertRaises((TypeError, ValueError)):
                compose(mod, HostImage("h", frozenset({"clock"})))

    def test_R1c_model_subclass_refused(self):
        class M(WasmModule):
            __slots__ = ()
        with self.assertRaises(TypeError):
            compose(M("svc", frozenset()), HostImage("h", frozenset()))

    def test_R2_str_subclass_attestation_fields_refused(self):
        req = F.request(self.kr)
        for field in ("subject", "claim", "key_id", "mac"):
            atts = [dict(a) for a in req.attestations]
            atts[1][field] = LyingStr(atts[1][field])
            evil = dataclasses.replace(req, module_digest=adm.digest_bytes(b"EVIL"), attestations=tuple(atts),
                                       nonce=adm.new_nonce())
            with self.subTest(field=field), self.assertRaises(adm.AttestationInvalid):
                self.a.admit(evil)

    def test_R3_trailing_newline_identifiers_refused(self):
        req = F.request(self.kr)
        with self.assertRaises(adm.IdentityInvalid):
            self.a.admit(dataclasses.replace(req, module_digest=req.module_digest + "\n"))
        with self.assertRaises(adm.IdentityInvalid):
            self.a.admit(F.request(self.kr, tenant="acme\n"))
        with self.assertRaises(adm.ReplayDetected):
            self.a.admit(F.request(self.kr, nonce=adm.new_nonce() + "\n"))
        rec = self.a.admit(F.request(self.kr))
        bad = dict(rec, admission=dict(rec["admission"], module_digest=rec["admission"]["module_digest"] + "\n"))
        with self.assertRaises(R.RecordInvalid):
            R.validate(bad, "PK_HYBRID_COMPOSITION/1")

    def test_R4_verify_record_pins_signer_and_rejects_future_records(self):
        rec = self.a.admit(F.request(self.kr))
        with self.assertRaises(adm.AttestationInvalid):
            adm.verify_record(self.kr, rec, expected_key_id=F.ATTEST_KEY, now=F.NOW)
        # a record re-signed with the attestation key must not verify as a composition record
        forged = {k: v for k, v in rec.items() if k != "signature"}
        forged["signature"] = {"alg": "HMAC-SHA256", "key_id": F.ATTEST_KEY,
                               "value": self.kr.mac(F.ATTEST_KEY, forged)}
        with self.assertRaises(adm.AttestationInvalid):
            adm.verify_record(self.kr, forged, expected_key_id=F.SIGN_KEY, now=F.NOW)
        with self.assertRaises(adm.AttestationInvalid):
            adm.verify_record(self.kr, rec, expected_key_id=F.SIGN_KEY, now=F.NOW - 10**6)
        self.assertTrue(adm.verify_record(self.kr, rec, expected_key_id=F.SIGN_KEY, now=F.NOW)["verified"])

    def test_R5_unhashable_fields_are_attestation_refusals(self):
        req = F.request(self.kr)
        for field, val in (("key_id", ["k"]), ("claim", ["sealed"])):
            atts = [dict(a) for a in req.attestations]
            atts[0][field] = val
            with self.subTest(field=field), self.assertRaises(adm.AttestationInvalid):
                self.a.admit(dataclasses.replace(req, attestations=tuple(atts), nonce=adm.new_nonce()))

    def test_R6_metric_label_newline_cannot_inject_series(self):
        from inv29_hybrid_wasm_unikernel.telemetry import Metrics
        m = Metrics()
        m.inc("inv29_t_total", code="ok\ninv29_fake 1")
        self.assertNotIn("inv29_fake", m.exposition())



class ReviewRound2Test(unittest.TestCase):
    def test_N1_decisions_reach_structured_log(self):
        import io, json, pathlib, tempfile
        from inv29_hybrid_wasm_unikernel.service import Service
        with tempfile.TemporaryDirectory() as d:
            kr, log = F.keyring(), io.StringIO()
            svc = Service.build(kr, F.policy(), signing_key_id=F.SIGN_KEY, state_dir=pathlib.Path(d),
                                log_stream=log, clock=F.Clock())
            svc.submit(F.request(kr)); svc.submit(F.request(kr, tenant="mallory"))
            events = [json.loads(l) for l in log.getvalue().splitlines()]
            outcomes = [e.get("outcome") for e in events if e["event"] == "decision"]
            self.assertEqual(outcomes, ["admitted", "refused"])

    def test_N2_restore_cannot_resurrect_revoked(self):
        import pathlib, tempfile
        from inv29_hybrid_wasm_unikernel import lifecycle as L
        with tempfile.TemporaryDirectory() as d:
            kr = F.keyring(); a = F.admitter(kr)
            lc = L.Lifecycle(a, L.Store(pathlib.Path(d) / "s"), clock=F.Clock())
            cid = lc.submit(F.request(kr))["id"]; lc.mark_running(cid)
            lc.store.backup(pathlib.Path(d) / "b.json")
            lc.revoke(cid, "operator: compromised")
            out = lc.store.restore(pathlib.Path(d) / "b.json")
            self.assertEqual(out["terminal_states_kept"], 1)
            self.assertEqual(lc.store.get(cid)["state"], L.REVOKED)

    def test_N3_gate_requires_executed_tests(self):
        from inv29_hybrid_wasm_unikernel import evidence as E
        st = {"components": [{"id": "MC1", "priority": "P0", "status": "CLOSED"}]}
        g = E.derive_gate(st, tests={"failed": 0, "errors": 0}, manifest={"source_digest": "x"},
                          source_digest="x", version="4.3.0")
        self.assertEqual(g["verdict"], "NO_GO")

    def test_N4_ledger_truncation_detected_against_anchor(self):
        import pathlib, tempfile
        from inv29_hybrid_wasm_unikernel import evidence as E
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "l.jsonl"; led = E.Ledger(p)
            for i in range(3):
                led.append("t", {"i": i})
            head = led.head()
            p.write_text(p.read_text().splitlines()[0] + "\n")
            with self.assertRaises(E.EvidenceInvalid):
                led.verify(expected_head=head)
            with self.assertRaises(E.EvidenceInvalid):
                led.verify(min_entries=3)

    def test_N5_empty_or_odd_control_file_fails_closed(self):
        import pathlib, tempfile
        from inv29_hybrid_wasm_unikernel import lifecycle as L
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "c.json"; ctl = L.ControlFile(p); a = F.admitter()
            for body in ("{}", '{"disabled":"","at":1,"actor":"x"}', '{"disabled":1,"at":1,"actor":"x"}'):
                p.write_text(body)
                with self.subTest(body=body):
                    self.assertTrue(ctl.apply(a))
                    self.assertIsNotNone(a.disabled)


if __name__ == "__main__":
    unittest.main()
