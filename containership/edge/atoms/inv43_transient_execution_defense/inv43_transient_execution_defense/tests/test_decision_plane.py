"""Checklists 15, 19, 20, 22, 31, 32, 40, 42: registry, placement, service,
negotiation, audit chain, controls, explain, end-to-end integration."""
from __future__ import annotations

import http.client
import json
import os
import pathlib
import tempfile
import unittest

from _harness import (COSTS, FULL, Fleet, W, attestation, auditlog, collector, negotiation, pkg, placement,
                      registry, service)


class RegistryTest(unittest.TestCase):
    def setUp(self):
        self.f = Fleet()
        self.f.attest("node-a")

    def tearDown(self):
        self.f.close()

    def decide(self, a=None, b=None, node="node-a", tier="microvm", who="sched"):
        return self.f.reg.decide(who, node, a or W("t1"), b or W("t2"), tier=tier)

    def test_attested_fresh_fully_mitigated_node_permits(self):
        out = self.decide()
        self.assertTrue(out["permitted"], out)
        self.assertIn("decision_id", out)

    def test_absent_posture_fails_closed(self):
        out = self.decide(node="node-b")
        self.assertEqual(out["code"], "posture_absent")

    def test_stale_posture_fails_closed(self):
        self.f.clock.advance(301)
        self.assertEqual(self.decide()["code"], "posture_stale")
        self.f.attest("node-a")
        self.assertTrue(self.decide()["permitted"])

    def test_config_ttl_tightening_applies(self):
        self.f.reg.config.activate(site={"posture_ttl_s": 30.0}, source="t", author="t")
        self.f.clock.advance(31)
        self.assertEqual(self.decide()["code"], "posture_stale")

    def test_same_tenant_needs_no_posture_but_honours_controls(self):
        self.assertTrue(self.decide(W("t1"), W("t1"), node="node-b")["permitted"])
        self.f.reg.quarantine("ops", "node-b", "incident-42")
        self.assertEqual(self.decide(W("t1"), W("t1"), node="node-b")["code"], "node_quarantined")

    def test_policy_trust_class_raises_requirement(self):
        # public-untrusted adds reg_file_data_sampling (not_affected: ok) etc; all satisfied on FULL
        self.assertTrue(self.decide(W("t1", "public-untrusted"), W("t2"))["permitted"])
        self.assertEqual(self.decide(W("t1", "regulated-secret"), W("t2"))["code"], "cross_tenant_forbidden_by_policy")
        self.assertEqual(self.decide(tier="dedicated-host")["code"], "cross_tenant_forbidden_by_policy")

    def test_partial_mitigation_refuses(self):
        v = dict(FULL, spectre_v2="Mitigation: Enhanced / Automatic IBRS; BHI: Vulnerable")
        f = Fleet(nodes=("n",), vulns=v)
        try:
            f.attest("n")
            out = f.reg.decide("sched", "n", W("t1"), W("t2"), tier="microvm")
            self.assertEqual(out["code"], "required_mitigation_missing")
            self.assertIn("spectre_v2", out["details"]["missing"])
        finally:
            f.close()

    def test_smt_on_without_core_scheduling_refuses_and_with_it_permits(self):
        f = Fleet(nodes=("n",), smt="on")
        g = Fleet(nodes=("n",), smt="on", core_sched=True)
        try:
            f.attest("n")
            g.attest("n")
            self.assertEqual(f.reg.decide("sched", "n", W("a"), W("b"), tier="microvm")["code"], "unsafe_smt")
            self.assertTrue(g.reg.decide("sched", "n", W("a"), W("b"), tier="microvm")["permitted"])
        finally:
            f.close()
            g.close()

    def test_claimed_status_is_rederived_from_raw(self):
        rb = collector.collect("node-a", root=self.f.roots["node-a"], clock=self.f.clock.time, mono=self.f.clock.mono)
        d = rb.to_dict(include_monotonic=False)
        for o in d["observations"]:
            if o["mitigation"] == "spectre_v2":
                o["raw"], o["status"] = "Vulnerable", "active"  # lie about the status
        forged = registry.readback_from_dict(d)
        self.assertEqual({o.mitigation: o.status for o in forged.observations}["spectre_v2"], pkg.INACTIVE)

    def test_older_epoch_is_refused(self):
        self.f.epoch["node-a"] = 5
        self.f.attest("node-a")
        with self.assertRaises(pkg.MitigationMissing) as cm:
            self.f.attest("node-a", epoch=4)
        self.assertEqual(cm.exception.code, "posture_stale_epoch")

    def test_gap02_contradiction_downgrades(self):
        env = self.f.envelope("node-a")
        self.f.reg.submit("collector-node-a", env, gap02={"affected": ["mds"]})
        out = self.decide()
        self.assertEqual(out["code"], "required_mitigation_missing")
        self.assertIn("mds", out["details"]["missing"])

    def test_scheduler_cannot_inject_posture(self):
        with self.assertRaises(pkg.MitigationMissing) as cm:
            self.f.reg.submit("sched", self.f.envelope("node-a"))
        self.assertEqual(cm.exception.code, "authz_denied")
        with self.assertRaises(pkg.MitigationMissing) as cm:
            self.f.reg.submit("collector-node-b", self.f.envelope("node-a"))
        self.assertEqual(cm.exception.code, "authz_denied")

    def test_explain_links_inputs_policy_config_release(self):
        out = self.decide()
        ex = self.f.reg.explain("obs", out["decision_id"])
        self.assertEqual(ex["verdict"], "permit")
        self.assertEqual(ex["policy"]["policy_digest"], self.f.pol.digest)
        self.assertEqual(ex["release"]["digest"], "test-release")
        self.assertIn("digest", ex["config"])
        self.assertIn("report", ex["posture"])
        with self.assertRaises(pkg.MitigationMissing):
            self.f.reg.explain("sched", out["decision_id"])  # scheduler lacks explain

    def test_freeze_and_kill_switch(self):
        with self.assertRaises(pkg.MitigationMissing):
            self.f.reg.freeze("sched")
        self.f.reg.freeze("ops")
        self.assertEqual(self.decide()["code"], "placement_frozen")
        self.assertEqual(self.f.reg.health.state().value, "frozen")
        self.f.reg.freeze("ops", False)
        self.f.reg.config.activate(site={"cross_tenant_placement_enabled": False}, source="kill", author="ops")
        self.assertEqual(self.decide()["code"], "cross_tenant_disabled")

    def test_controls_survive_restart_via_audit_chain(self):
        self.f.reg.quarantine("ops", "node-a", "cve-2026-0001")
        self.f.reg.freeze("ops")
        entries = auditlog.verify_entries(self.f.audit.entries(), key=b"k" * 32)
        fresh = registry.PostureRegistry(keys=self.f.keys, authz=self.f.az, policy=self.f.pol,
                                         clock=self.f.clock.time, mono=self.f.clock.mono)
        # restart closed: no posture at all until re-attestation
        self.assertEqual(fresh.decide("sched", "node-a", W("a"), W("b"), tier="microvm")["code"], "posture_absent")
        restored = fresh.restore_controls(entries)
        self.assertEqual(restored, {"quarantined": ["node-a"], "frozen": True})

    def test_every_decision_is_audited_and_chain_verifies(self):
        self.decide()
        self.decide(node="node-b")
        kinds = [e["body"]["kind"] for e in self.f.audit.entries()]
        self.assertEqual(kinds.count("cotenancy_decision"), 2)
        auditlog.verify_entries(self.f.audit.entries(), key=b"k" * 32, expected_head=self.f.audit.head())

    def test_internal_defect_never_permits(self):
        self.f.reg.policy = None  # simulate a defect deep in the decision path
        out = self.decide()
        self.assertFalse(out.get("permitted", False))
        self.assertEqual(out["code"], "internal_error")

    def test_status_versions(self):
        v2 = self.f.reg.status("obs", "node-a", version=2)
        self.assertEqual(v2["schema"], "PK_MITIGATIONS/2")
        self.assertIn("l1tf", v2["not_affected"])
        with self.assertRaises(pkg.MitigationMissing) as cm:
            self.f.reg.status("obs", "node-a", version=1)
        self.assertEqual(cm.exception.code, "schema_version_unrepresentable")


class AuditChainTest(unittest.TestCase):
    def test_file_chain_detects_tamper_truncation_and_reopens(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "audit.jsonl"
            log = auditlog.AuditLog(p, key=b"x" * 32)
            for i in range(5):
                log.append("e", i=i)
            head = log.head()
            auditlog.verify_file(p, key=b"x" * 32, expected_head=head)
            reopened = auditlog.AuditLog(p, key=b"x" * 32)
            reopened.append("e", i=5)
            self.assertEqual(reopened.head()[0], 5)
            lines = p.read_text().splitlines()
            # tamper with a body
            bad = json.loads(lines[2])
            bad["body"]["i"] = 99
            p.write_text("\n".join(lines[:2] + [json.dumps(bad)] + lines[3:]) + "\n")
            with self.assertRaises(auditlog.AuditChainError) as cm:
                auditlog.verify_file(p, key=b"x" * 32)
            self.assertEqual(cm.exception.code, "audit_hash_mismatch")
            # truncation is only visible against an anchored head
            p.write_text("\n".join(lines[:3]) + "\n")
            auditlog.verify_file(p, key=b"x" * 32)
            with self.assertRaises(auditlog.AuditChainError) as cm:
                auditlog.verify_file(p, key=b"x" * 32, expected_head=head)
            self.assertEqual(cm.exception.code, "audit_head_mismatch")

    def test_recomputed_chain_without_key_is_caught_by_mac(self):
        log = auditlog.AuditLog(key=b"x" * 32)
        log.append("e", i=0)
        forged = auditlog.AuditLog(key=b"attacker-key-attacker-key-000000")
        forged.append("e", i=0)
        with self.assertRaises(auditlog.AuditChainError) as cm:
            auditlog.verify_entries(forged.entries(), key=b"x" * 32)
        self.assertEqual(cm.exception.code, "audit_mac_mismatch")


class PlacementTest(unittest.TestCase):
    def test_filter_propagates_refusals(self):
        f = Fleet(nodes=("node-a", "node-b", "node-c"))
        try:
            f.attest("node-a")
            f.attest("node-c")
            f.reg.quarantine("ops", "node-c", "maintenance")
            out = placement.filter_nodes(f.reg, "sched", W("new"),
                                         {"node-a": [W("t1")], "node-b": [W("t2")], "node-c": []}, tier="microvm")
            self.assertEqual(out["eligible"], ["node-a"])
            self.assertEqual(out["refused"]["node-b"][0]["code"], "posture_absent")
            self.assertEqual(out["refused"]["node-c"][0]["code"], "node_quarantined")
            self.assertTrue(all("decision_id" in e for errs in out["refused"].values() for e in errs))
            bad = placement.filter_nodes(f.reg, "sched", W("new"), {"node-a": "x"}, tier="microvm")
            self.assertEqual(bad["eligible"], [])
        finally:
            f.close()


class NegotiationTest(unittest.TestCase):
    def test_negotiate(self):
        self.assertEqual(negotiation.negotiate("PK_MITIGATIONS", None), 1)
        self.assertEqual(negotiation.negotiate("PK_MITIGATIONS", "PK_MITIGATIONS/2, PK_MITIGATIONS/1"), 2)
        self.assertEqual(negotiation.negotiate("PK_MITIGATIONS", "PK_MITIGATIONS/9, PK_MITIGATIONS/1"), 1)
        with self.assertRaises(pkg.MitigationMissing):
            negotiation.negotiate("PK_MITIGATIONS", "PK_MITIGATIONS/9")
        with self.assertRaises(pkg.MitigationMissing):
            negotiation.negotiate("PK_NOPE", None)

    def test_forward_compatible_reader_fails_closed_on_new_status(self):
        future = {"schema": "PK_MITIGATIONS/3", "mitigations": {"x": {"status": "microcode_pending"},
                                                                 "y": {"status": "active"}}}
        self.assertEqual(negotiation.read_status_forward_compatible(future), {"x": "unknown", "y": "active"})
        v1 = {"schema": "PK_MITIGATIONS/1", "mitigations": {"x": {"status": "not_affected"}}}
        self.assertEqual(negotiation.read_status_forward_compatible(v1), {"x": "unknown"})

    def test_backward_compat_v1_report_unchanged_for_v1_expressible_nodes(self):
        node = pkg.MitigationState("n", smt_enabled=False)
        for m in pkg.REQUIRED_FOR_COTENANCY:
            node.record(m, pkg.ACTIVE, 1.0)
        fixture = json.loads((pathlib.Path(__file__).parent / "fixtures" / "status.example.json").read_text())
        self.assertEqual(set(node.report()), set(fixture))


class ServiceTest(unittest.TestCase):
    TOK = {"sched": "s" * 40, "collector-node-a": "c" * 40, "ops": "o" * 40, "obs": "b" * 40}

    def setUp(self):
        self.f = Fleet()
        self.tokens = service.TokenStore()
        for p, t in self.TOK.items():
            self.tokens.add(t, p)
        self.srv, _ = service.serve(self.f.reg, self.tokens)
        self.port = self.srv.server_address[1]

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.f.close()

    def req(self, method, path, body=None, who=None, headers=None, raw=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        h = dict(headers or {})
        if who:
            h["Authorization"] = f"Bearer {self.TOK[who]}"
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        if data is not None:
            h.setdefault("Content-Length", str(len(data)))
            h["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        payload = r.read()
        c.close()
        try:
            return r.status, json.loads(payload), r
        except json.JSONDecodeError:
            return r.status, payload.decode(), r

    def test_full_http_flow(self):
        st, out, _ = self.req("POST", "/v1/posture", {"envelope": self.f.envelope("node-a")}, who="collector-node-a")
        self.assertEqual(st, 202, out)
        body = {"node": "node-a", "a": W("t1"), "b": W("t2"), "tier": "microvm"}
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        st, out, _ = self.req("POST", "/v1/cotenancy", body, who="sched", headers={"traceparent": tp})
        self.assertEqual(st, 200, out)
        st, ex, _ = self.req("GET", f"/v1/explain/{out['decision_id']}", who="obs")
        self.assertEqual((st, ex["trace_id"]), (200, "a" * 32))
        st, rep, _ = self.req("GET", "/v1/status/node-a", who="obs", headers={"Accept-Schema": "PK_MITIGATIONS/2"})
        self.assertEqual((st, rep["schema"]), (200, "PK_MITIGATIONS/2"))
        st, rep, _ = self.req("GET", "/v1/status/node-a", who="obs")
        self.assertEqual((st, rep["code"]), (406, "schema_version_unrepresentable"))
        st, text, _ = self.req("GET", "/metrics", who="obs")
        self.assertIn("inv43_decisions_total", text)
        st, h, _ = self.req("GET", "/healthz")
        self.assertEqual((st, h["health"]), (200, "ready"))

    def test_authn_authz_errors(self):
        self.assertEqual(self.req("GET", "/v1/status/node-a")[0], 401)
        st, out, _ = self.req("GET", "/v1/status/node-a", headers={"Authorization": "Bearer " + "z" * 40})
        self.assertEqual((st, out["code"]), (401, "authn_failed"))
        st, out, _ = self.req("POST", "/v1/posture", {"envelope": self.f.envelope("node-a")}, who="sched")
        self.assertEqual((st, out["code"]), (403, "authz_denied"))
        self.assertEqual(self.req("POST", "/v1/control/freeze", {}, who="sched")[0], 403)

    def test_refusal_is_409_with_pk_error(self):
        st, out, _ = self.req("POST", "/v1/cotenancy", {"node": "node-a", "a": W("t1"), "b": W("t2"),
                                                        "tier": "microvm"}, who="sched")
        self.assertEqual((st, out["schema"], out["code"]), (409, "PK_ERROR/1", "posture_absent"))

    def test_limits_and_malformed(self):
        big = b"{" + b" " * 70000 + b"}"
        self.assertEqual(self.req("POST", "/v1/cotenancy", raw=big, who="sched")[0], 413)
        self.assertEqual(self.req("POST", "/v1/cotenancy", raw=b"not json", who="sched")[0], 400)
        self.assertEqual(self.req("POST", "/v1/cotenancy", raw=b"[1]", who="sched")[0], 400)
        self.assertEqual(self.req("GET", "/v1/nope", who="sched")[0], 404)

    def test_idempotency(self):
        body = {"node": "node-a", "reason": "r1"}
        h = {"Idempotency-Key": "abc"}
        st1, o1, _ = self.req("POST", "/v1/control/quarantine", body, who="ops", headers=h)
        st2, o2, r2 = self.req("POST", "/v1/control/quarantine", body, who="ops", headers=h)
        self.assertEqual((st1, o1), (st2, o2))
        self.assertEqual(r2.getheader("Idempotent-Replay"), "true")
        quarantines = [e for e in self.f.audit.entries() if e["body"]["kind"] == "control_quarantine"]
        self.assertEqual(len(quarantines), 1)
        st3, o3, _ = self.req("POST", "/v1/control/quarantine", {"node": "node-a", "reason": "r2"}, who="ops", headers=h)
        self.assertEqual((st3, o3["code"]), (409, "idempotency_conflict"))

    def test_non_loopback_without_tls_refused(self):
        with self.assertRaises(ValueError):
            service.Inv43Server(("0.0.0.0", 0), self.f.reg, self.tokens)

    def test_short_tokens_refused(self):
        with self.assertRaises(ValueError):
            service.TokenStore().add("short", "x")


class IntegrationTest(unittest.TestCase):
    """Checklist 42: collector -> attestation -> registry -> GAP-02/PLN-04/INV-34
    policy -> SCH-01 filter -> audit -> metrics -> explain, in one flow."""

    def test_end_to_end(self):
        f = Fleet(nodes=("legacy", "modern", "eol"))
        try:
            for n in f.roots:
                f.attest(n)
            wl = W("new", "tenant-standard")
            residents = {"modern": [W("other")], "legacy": [dict(W("other"), cpu_lineage="x86-legacy-inv34")],
                         "eol": [dict(W("other"), cpu_lineage="x86-eol-no-microcode")]}
            out = placement.filter_nodes(f.reg, "sched", wl, residents, tier="microvm")
            self.assertIn("modern", out["eligible"])
            self.assertIn("legacy", out["eligible"])  # tsx_async_abort + itlb_multihit are not_affected on FULL
            self.assertEqual(out["refused"]["eol"][0]["code"], "cross_tenant_forbidden_by_policy")
            m = f.reg.metrics.render()
            self.assertIn('inv43_refusals_total{code="cross_tenant_forbidden_by_policy"', m)
            ex = f.reg.explain("auditor", out["refused"]["eol"][0]["decision_id"])
            self.assertIn("inv34:x86-eol-no-microcode", " ".join(ex["result"]["details"]["derivation"]))
            auditlog.verify_entries(f.audit.entries(), key=b"k" * 32, expected_head=f.audit.head())
        finally:
            f.close()


if __name__ == "__main__":
    unittest.main()
