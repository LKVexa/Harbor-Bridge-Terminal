"""Tests for query/pagination, dry-run impact, background verification, SIEM export, RBAC CAS."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.support import EcpError, Estate
from inv66_enterprise_wasm_control_plane.production.keys import Signer
from inv66_enterprise_wasm_control_plane.production.siem import SiemExporter


class AdditionsTest(unittest.TestCase):
    def setUp(self):
        self.e = Estate()
        self.s = self.e.service
        for n in ("a", "b", "c", "d", "e"):
            self.s.admit(self.e.request(n), self.e.token("ops"))

    def test_audit_cursor_pagination_and_filters(self):
        aud = self.e.principal("auditor")
        seen, frm = [], 1
        while True:
            r = self.s.audit_query({"protocol": "PK_ECP_AUDIT/1", "request_id": "q", "kind": "admit.decision",
                                    "from_seq": frm, "limit": 2}, aud)
            seen += [x["seq"] for x in r["records"]]
            if "next_from_seq" not in r:
                break
            frm = r["next_from_seq"]
        self.assertEqual(len(seen), 5)
        self.assertEqual(seen, sorted(set(seen)))
        by_subject = self.s.audit_query({"protocol": "PK_ECP_AUDIT/1", "request_id": "q", "subject": "ops",
                                         "kind": "admit.decision"}, aud)
        self.assertEqual(len(by_subject["records"]), 5)
        with self.assertRaises(EcpError):
            self.s.audit_query({"protocol": "PK_ECP_AUDIT/1", "request_id": "q", "lattice": "prod"}, aud)

    def test_inventory_pagination(self):
        aud = self.e.principal("auditor")
        p1 = self.s.inventory_view(aud, limit=3)
        p2 = self.s.inventory_view(aud, cursor=p1["next_cursor"], limit=3)
        self.assertEqual(len(p1["items"]) + len(p2["items"]), 5)
        self.assertNotIn("next_cursor", p2)

    def test_policy_impact_dry_run(self):
        doc = self.e.config(registries=[{"host": "registry.estate.local", "scope": "acme"}])
        imp = self.s.policy_impact(doc, self.e.principal("sec1"))
        self.assertEqual(len(imp["violations"]), 5)
        self.assertEqual(imp["violations"][0]["codes"], ["ECP_REGISTRY_NOT_APPROVED"])
        doc2 = self.e.config()
        doc2["signers"][0]["revoked"] = True
        imp2 = self.s.policy_impact(doc2, self.e.principal("sec1"))
        self.assertTrue(all("ECP_SIGNER_NOT_APPROVED" in v["codes"] for v in imp2["violations"]))
        with self.assertRaises(EcpError):
            self.s.policy_impact(doc, self.e.principal("ops"))

    def test_background_verification_alerts(self):
        k = Signer("anchor-1")
        self.s.journal.anchor(k)
        self.assertEqual(self.s.verify_audit_background({"anchor-1": k.public_b64()})["result"], "INTACT")
        seg = self.s.journal._segments()[0]
        seg.write_bytes(seg.read_bytes().replace(b'"app":"c"', b'"app":"x"', 1))
        with self.assertRaises(EcpError):
            self.s.verify_audit_background({"anchor-1": k.public_b64()})
        self.assertEqual(self.s.metrics.value("ecp_audit_verify_failures_total"), 1.0)
        self.assertIn("ecp_audit_last_verify_ok 0", self.s.metrics.render())

    def test_siem_export_checkpoint_retry_dedupe(self):
        got, state = [], {"fail": 2}

        def sink(batch):
            if state["fail"]:
                state["fail"] -= 1
                raise ConnectionError("siem down")
            got.append(batch)
        ex = SiemExporter(self.s.journal, Path(tempfile.mkdtemp()), sink, batch_size=4, max_failures=2)
        for _ in range(2):
            with self.assertRaises(EcpError):
                ex.run_once()
        self.assertEqual(ex.checkpoint, 0)
        self.assertTrue((ex.dir / "dead_letter.jsonl").exists())
        while ex.run_once()["sent"]:
            pass
        seqs = [r["seq"] for b in got for r in b["records"]]
        self.assertEqual(seqs, list(range(1, self.s.journal.head[0] + 1)))
        self.assertEqual(ex.backlog(), 0)
        ex2 = SiemExporter(self.s.journal, ex.dir, sink)  # restart resumes from the durable checkpoint
        self.assertEqual(ex2.run_once()["sent"], 0)

    def test_rbac_optimistic_concurrency(self):
        ta = self.e.principal("tadmin")
        rev = self.s.rbac({"protocol": "PK_ECP_RBAC/1", "op": "list", "request_id": "l", "scope": "acme/payments"}, ta)["revision"]
        b = {"subject": "x", "role": "viewer", "scope": "acme/payments", "effect": "allow"}
        self.s.rbac({"protocol": "PK_ECP_RBAC/1", "op": "bind", "request_id": "1", "binding": b, "if_revision": rev,
                     "reason": "onboarding"}, ta)
        with self.assertRaises(EcpError) as cm:  # a second admin working from the stale revision
            self.s.rbac({"protocol": "PK_ECP_RBAC/1", "op": "bind", "request_id": "2",
                         "binding": dict(b, subject="y"), "if_revision": rev}, ta)
        self.assertEqual(cm.exception.code, "ECP_CONFIG_CONFLICT")
        self.assertEqual(self.e.open().rbac_revision, self.s.rbac_revision)

    def test_health_runtime_gauges(self):
        h = self.s.health()
        self.assertEqual(h["site"], "eu-west-1")
        self.assertIn("process_open_fds", self.s.metrics.render())


if __name__ == "__main__":
    unittest.main()
