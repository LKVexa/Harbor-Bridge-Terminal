"""P0-01, P0-09, P0-10, P0-11, P0-12: gate integrity, provenance, audit, config, estate integration."""
import json
import pathlib
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fixtures.estate import Estate, keyring  # noqa: E402

from gap14_data_gravity_manager import compat  # noqa: E402
from gap14_data_gravity_manager.audit import FileAuditSink, verify_chain, read_records  # noqa: E402
from gap14_data_gravity_manager.engine import GravityDecisionError  # noqa: E402
from gap14_data_gravity_manager.errors import G14Error  # noqa: E402
from gap14_data_gravity_manager.schema_check import SchemaError, validate  # noqa: E402
from gap14_data_gravity_manager.trust import digest  # noqa: E402


class GateIntegrityTest(unittest.TestCase):  # G14-P0-01
    def test_missing_runtime_is_hard_fail(self):
        hs = compat.handshake()
        self.assertEqual(hs.status, "G14_PKCORE_MISSING")
        g = compat.evaluate_gate(hs, [{"check_id": f"C{i}", "status": "pass"} for i in range(100)])
        self.assertEqual((g.verdict, g.reason_code), ("FAIL", "G14_PKCORE_MISSING"))

    def _fake_pkcore(self, version="1.4.2", schema="PK_CHECKLIST/1", drop=None):
        tmp = pathlib.Path(tempfile.mkdtemp())
        pkg = tmp / "pk_core"
        pkg.mkdir()
        (pkg / "__init__.py").write_text(f"__version__ = {version!r}\nCONFORMANCE_SCHEMA = {schema!r}\n")
        (pkg / "checklist.py").write_text("class ChecklistItem: pass\nclass Finding: pass\n")
        (pkg / "component.py").write_text("class Component: pass\n")
        body = "class Contract: pass\nclass Dependency: pass\nclass Slo: pass\n"
        if drop:
            body = body.replace(f"class {drop}: pass\n", "")
        (pkg / "contract.py").write_text(body)
        return tmp

    def _with(self, root, fn):
        sys.path.insert(0, str(root))
        for m in [m for m in sys.modules if m == "pk_core" or m.startswith("pk_core.")]:
            del sys.modules[m]
        try:
            return fn()
        finally:
            sys.path.remove(str(root))
            for m in [m for m in sys.modules if m == "pk_core" or m.startswith("pk_core.")]:
                del sys.modules[m]

    def test_compatible_but_unpinned_is_non_certifying(self):
        root = self._fake_pkcore()
        hs = self._with(root, lambda: compat.handshake(allowed_roots=[str(root)]))
        self.assertEqual(hs.status, "UNPINNED")
        self.assertFalse(hs.certifying)

    def test_pinned_digest_certifies_and_mismatch_refuses(self):
        root = self._fake_pkcore()
        hs = self._with(root, lambda: compat.handshake(allowed_roots=[str(root)]))
        pin = dict(compat.PKCORE_PIN, digest=hs.tree_digest)
        ok = self._with(root, lambda: compat.handshake(pin, allowed_roots=[str(root)]))
        self.assertEqual(ok.status, "OK")
        (root / "pk_core" / "component.py").write_text("class Component: pass\n# modified\n")
        bad = self._with(root, lambda: compat.handshake(pin, allowed_roots=[str(root)]))
        self.assertEqual(bad.status, "G14_PKCORE_DIGEST_MISMATCH")

    def test_incompatible_major_schema_and_api_rejected(self):
        for kw in ({"version": "2.0.0"}, {"version": "0.9.9"}, {"schema": "PK_CHECKLIST/2"}, {"drop": "Slo"}):
            root = self._fake_pkcore(**kw)
            hs = self._with(root, lambda: compat.handshake(allowed_roots=[str(root)]))
            self.assertEqual(hs.status, "G14_PKCORE_INCOMPATIBLE", kw)

    def test_untrusted_path_rejected(self):
        root = self._fake_pkcore()
        hs = self._with(root, lambda: compat.handshake(allowed_roots=["/nonexistent/locked-env"]))
        self.assertEqual(hs.status, "G14_PKCORE_UNTRUSTED_PATH")

    def test_partial_or_unapproved_skip_never_passes(self):
        hs = compat.Handshake("OK")
        full = [{"check_id": f"C{i}", "status": "pass"} for i in range(100)]
        self.assertEqual(compat.evaluate_gate(hs, full).verdict, "PASS")
        self.assertEqual(compat.evaluate_gate(hs, full[:99]).reason_code, "G14_GATE_PARTIAL")
        skipped = full[:99] + [{"check_id": "C99", "status": "skip", "reason": "x"}]
        self.assertEqual(compat.evaluate_gate(hs, skipped).reason_code, "G14_GATE_PARTIAL")
        self.assertEqual(compat.evaluate_gate(hs, skipped, approved_skips={"C99": "RISK-1"}).verdict, "PASS")
        dup = full[:99] + [full[0]]
        self.assertEqual(compat.evaluate_gate(hs, dup).reason_code, "G14_GATE_PARTIAL")


class ProvenanceTest(unittest.TestCase):  # G14-P0-09
    def test_envelope_signed_and_complete(self):
        e = Estate()
        d = e.decide()
        validate(d, "PK_GRAVITY_DECISION/2")
        prov = d["provenance"]
        self.assertEqual(prov["input_digest"], digest(prov["inputs"]))
        for k in ("topology", "placement", "convergence", "policy", "config"):
            self.assertIn(k, prov["inputs"])
        body = {k: v for k, v in d.items() if k not in ("sig", "audit")}
        e.keys.verify(body, d["sig"], expected_issuer="gap14-data-gravity", now=e.clock.now())
        body["recommendation"]["to"] = "evil"
        with self.assertRaises(G14Error):
            e.keys.verify(body, d["sig"], expected_issuer="gap14-data-gravity", now=e.clock.now())

    def test_trace_context_propagated(self):
        e = Estate()
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        d = e.service.decide(e.request(), e.token(), traceparent=tp)
        self.assertEqual(d["provenance"]["trace"]["trace_id"], "4bf92f3577b34da6a3ce929d0e0e4736")


class AuditTest(unittest.TestCase):  # G14-P0-10
    def test_chain_verifies_and_detects_tamper_delete_reorder(self):
        e = Estate()
        for s in (500, 2, 3):
            e.decide(size=s)
        recs = e.audit.records
        self.assertEqual(verify_chain(recs, e.keys)["records"], len(recs))
        for mutate in (lambda r: r[1]["payload"].__setitem__("cost", 0.0), lambda r: r.pop(1),
                       lambda r: r.insert(0, r.pop(1))):
            rr = json.loads(json.dumps(recs))
            mutate(rr)
            with self.assertRaises(G14Error) as ctx:
                verify_chain(rr, e.keys)
            self.assertEqual(ctx.exception.code, "G14_AUDIT_CHAIN_BROKEN")
        for r in recs:
            validate(r, "PK_AUDIT_RECORD/1")

    def test_audit_failure_withholds_decision(self):
        e = Estate(audit_fail=True)
        with self.assertRaises(G14Error) as ctx:
            e.decide()
        self.assertEqual(ctx.exception.code, "G14_AUDIT_UNAVAILABLE")
        self.assertFalse(e.service.health()["ready"])
        self.assertIn('gap14_audit_records_total{result="failed"}', e.service.registry.exposition())

    def test_file_sink_resumes_and_verifies(self):
        path = pathlib.Path(tempfile.mkdtemp()) / "audit.jsonl"
        ks = keyring()
        s = FileAuditSink(ks, "k-audit", path)
        s.append("a", {"x": 1}, 1.0)
        s.append("b", {"x": 2}, 2.0)
        s2 = FileAuditSink(ks, "k-audit", path)
        s2.append("c", {"x": 3}, 3.0)
        self.assertEqual(verify_chain(read_records(path), ks)["records"], 3)
        lines = path.read_text().splitlines()
        path.write_text("\n".join(lines[:1] + lines[2:]) + "\n")
        with self.assertRaises(G14Error):
            FileAuditSink(ks, "k-audit", path)


class ConfigTest(unittest.TestCase):  # G14-P0-11
    def setUp(self):
        self.e = Estate()
        self.base = {"schema": "PK_GAP14_CONFIG/1", "revision": 2, "mode": "production"}

    def code(self, body, signed=True):
        doc = self.e.signed_config(body) if signed else {"body": body, "sig": {"alg": "HS256", "kid": "k-cfg", "iss": "x", "mac": "0" * 64}}
        with self.assertRaises(G14Error) as ctx:
            self.e.config.activate(doc, self.e.clock.now())
        return ctx.exception.code

    def test_signed_activation_and_schema(self):
        cfg = self.e.config.activate(self.e.signed_config(self.base), self.e.clock.now())
        self.assertEqual(cfg.revision, 2)
        validate(self.base, "PK_GAP14_CONFIG/1")

    def test_rejections_leave_previous_active(self):
        self.assertEqual(self.code(self.base, signed=False), "G14_UNKNOWN_ISSUER")
        self.assertEqual(self.code({**self.base, "knobs": {"decision_deadline_s": 999}}), "G14_CONFIG_INVALID")
        self.assertEqual(self.code({**self.base, "knobs": {"bogus": 1}}), "G14_CONFIG_INVALID")
        self.assertEqual(self.code({**self.base, "extra": 1}), "G14_CONFIG_INVALID")
        self.assertEqual(self.code({**self.base, "dev_flags": {"allow_fake_clock": True}}), "G14_CONFIG_FORBIDDEN_IN_PRODUCTION")
        self.assertEqual(self.code({**self.base, "revision": 1}), "G14_VERSION_ROLLBACK")
        self.assertEqual(self.code({**self.base, "canary_percent": 5}), "G14_CONFIG_INVALID")
        self.assertEqual(self.e.config.active.revision, 1)

    def test_activation_and_rejection_are_audited(self):
        self.e.config.activate(self.e.signed_config(self.base), self.e.clock.now())
        self.code({**self.base, "revision": 1})
        events = [r["event"] for r in self.e.audit.records]
        self.assertIn("config.activated", events)
        self.assertIn("config.rejected", events)

    def test_dev_flags_allowed_outside_production(self):
        self.e.config.activate(self.e.signed_config({**self.base, "mode": "test", "dev_flags": {"allow_fake_clock": True}}), 0)

    def test_rollback_then_forward_needs_newer_than_highest(self):
        self.e.config.activate(self.e.signed_config({**self.base, "revision": 3}), self.e.clock.now())
        self.e.config.rollback(1, self.e.clock.now(), "oncall")
        self.assertEqual(self.e.config.active.revision, 1)
        self.assertEqual(self.code({**self.base, "revision": 2}), "G14_VERSION_ROLLBACK")
        self.e.config.activate(self.e.signed_config({**self.base, "revision": 4}), self.e.clock.now())

    def test_load_file(self):
        p = pathlib.Path(tempfile.mkdtemp()) / "c.json"
        p.write_text(json.dumps(self.e.signed_config({**self.base, "revision": 9})))
        self.assertEqual(self.e.config.load_file(p, self.e.clock.now()).revision, 9)
        p.write_text("{not json")
        with self.assertRaises(G14Error):
            self.e.config.load_file(p, 0)


class EstateIntegrationTest(unittest.TestCase):  # G14-P0-12 (fixture-backed)
    def test_end_to_end_decision_explain_handoff(self):
        e = Estate()
        d = e.decide(size=2)
        self.assertEqual(d["recommendation"]["direction"], "move-data")
        tok = e.token()
        ex = e.service.explain(d["provenance"]["decision_id"], tok)
        validate(ex, "PK_GRAVITY_EXPLAIN/1")
        ack = e.service.handoff(d, tok)
        self.assertTrue(ack["accepted"])
        validate(e.dataplane.received[0], "PK_DATA_MOVE_HANDOFF/1")
        self.assertEqual(e.dataplane.received[0]["obligations"], {"encryption_domain": "eu-kms"})
        self.assertTrue(e.service.handoff(d, tok)["duplicate"])
        self.assertEqual(len(e.dataplane.received), 1)
        self.assertEqual(verify_chain(e.audit.records, e.keys)["records"], len(e.audit.records))
        validate(e.service.health(), "PK_HEALTH/1")

    def test_move_compute_cannot_be_handed_off(self):
        e = Estate()
        d = e.decide(size=500)
        with self.assertRaises(G14Error) as ctx:
            e.service.handoff(d, e.token())
        self.assertEqual(ctx.exception.code, "G14_INVALID_REQUEST")

    def test_modified_envelope_cannot_be_executed(self):
        e = Estate()
        d = e.decide(size=2)
        d["recommendation"]["to"] = "fra"
        with self.assertRaises(G14Error) as ctx:
            e.service.handoff(d, e.token())
        self.assertEqual(ctx.exception.code, "G14_SIGNATURE_INVALID")

    def test_handoff_expires(self):
        e = Estate()
        d = e.decide(size=2)
        e.clock.advance(301)
        with self.assertRaises(G14Error) as ctx:
            e.service.handoff(d, e.token(ttl=900))
        self.assertEqual(ctx.exception.code, "G14_STALE_INPUT")

    def test_pln06_rejection_is_surfaced(self):
        e = Estate()
        e.dataplane.reject = True
        d = e.decide(size=2)
        with self.assertRaises(G14Error) as ctx:
            e.service.handoff(d, e.token())
        self.assertEqual(ctx.exception.code, "G14_HANDOFF_REJECTED")

    def test_explain_is_tenant_scoped(self):
        e = Estate()
        d = e.decide()
        with self.assertRaises(G14Error) as ctx:
            e.service.explain(d["provenance"]["decision_id"], e.token(tenants=("t-other",)))
        self.assertEqual(ctx.exception.code, "G14_FORBIDDEN")

    def test_request_schema_matches_parser(self):
        e = Estate()
        r = e.request(profile={"runs": 3, "shards": [{"name": "s1", "size_gb": 1, "needed": True}]})
        validate(r, "PK_GRAVITY_DECISION_REQUEST/1")
        r["dataset"]["bogus"] = 1
        with self.assertRaises(SchemaError):
            validate(r, "PK_GRAVITY_DECISION_REQUEST/1")
        with self.assertRaises(GravityDecisionError):
            e.service.decide(r, e.token())

    def test_adapter_outputs_match_wire_schemas(self):
        e = Estate()
        req = {"schema": "PK_POLICY_REQUEST/1", "tenant_id": "t", "workload_id": "w", "dataset": "d", "classification": "public",
               "source_site": "dub", "destination_site": "ams", "operation": "hold", "jurisdiction_tags": [], "evaluated_at": 1.0}
        validate(req, "PK_POLICY_REQUEST/1")
        validate(e.policy(req, 1)["body"], "PK_POLICY_VERDICT/1")
        validate(e.topology({"sites": ["dub"]}, 1)["body"], "PK_TOPOLOGY_SNAPSHOT/1")
        validate(e.replication({"tenant_id": "t", "dataset": "d"}, 1)["body"], "PK_CONVERGENCE_PROOF/1")
        validate(e.placement({"tenant_id": "t", "sites": ["dub", "ams"]}, 1)["body"], "PK_PLACEMENT_SNAPSHOT/1")
        validate(e.token(), "PK_CAPABILITY_TOKEN/1")


if __name__ == "__main__":
    unittest.main()
