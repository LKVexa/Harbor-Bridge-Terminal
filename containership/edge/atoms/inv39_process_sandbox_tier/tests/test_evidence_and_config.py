"""MC-023..028/046/049/050/053/054/075..083 — evidence, audit chain, configuration, telemetry."""
from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from importlib import import_module

from _support import PKG_DIR

att = import_module(PKG_DIR.name + ".attestation")
cfg = import_module(PKG_DIR.name + ".config")
obs = import_module(PKG_DIR.name + ".observability")
errors = import_module(PKG_DIR.name + ".errors")
K = b"n" * 32


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.now = [1_000_000.0]
        self.signer = att.EvidenceSigner(att.NodeIdentity("node-a", K), clock=lambda: self.now[0])
        self.ver = att.EvidenceVerifier({"node-a": K}, clock=lambda: self.now[0])
        self.body = {"sandbox_id": "s1", "profile_digest": "sha256:" + "a" * 64, "nonce": att.new_nonce()}

    def expect(self):
        return {"sandbox_id": "s1", "profile_digest": self.body["profile_digest"], "node_id": "node-a"}

    def test_valid(self):
        self.ver.verify(self.signer.sign(self.body), expect=self.expect())

    def test_tamper_replay_rebind_stale(self):
        rec = self.signer.sign(self.body)
        bad = dict(rec, profile_digest="sha256:" + "b" * 64)
        for name, r, exp in (("tamper", bad, {}), ("other node", dict(rec, node_id="node-b"), {}),
                             ("rebind workload", rec, dict(self.expect(), sandbox_id="s2"))):
            with self.subTest(name), self.assertRaises(errors.SandboxError) as c:
                att.EvidenceVerifier({"node-a": K, "node-b": K}, clock=lambda: self.now[0]).verify(r, expect=exp)
            self.assertEqual(c.exception.code, "E_ATTESTATION_FAILED")
        self.ver.verify(rec, expect=self.expect())
        with self.assertRaises(errors.SandboxError):
            self.ver.verify(rec, expect=self.expect())  # replay
        rec2 = self.signer.sign(dict(self.body, nonce=att.new_nonce()))
        self.now[0] += att.MAX_EVIDENCE_AGE_S + 1
        with self.assertRaises(errors.SandboxError):
            self.ver.verify(rec2, expect=self.expect())

    def test_time_source_down_fails_safe(self):
        rec = self.signer.sign(self.body)

        def broken():
            raise OSError("ntp down")
        with self.assertRaises(errors.SandboxError) as c:
            att.EvidenceVerifier({"node-a": K}, clock=broken).verify(rec, expect={})
        self.assertEqual(c.exception.code, "E_DEPENDENCY_UNAVAILABLE")

    def test_short_key_refused(self):
        with self.assertRaises(errors.SandboxError):
            att.NodeIdentity("n", b"short")


class AuditChainTest(unittest.TestCase):
    def test_file_chain_detects_edit_reorder_and_deletion(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "audit.jsonl")
        ch = att.AuditChain(p)
        for i in range(5):
            ch.append("e", {"i": i})
        self.assertEqual(att.verify_chain_file(p)[:2], (True, ch.head))
        lines = open(p).read().splitlines()
        variants = {
            "edit": lines[:2] + [lines[2].replace('"i":2', '"i":9')] + lines[3:],
            "reorder": [lines[1], lines[0]] + lines[2:],
            "delete-middle": lines[:2] + lines[3:],
        }
        for name, ls in variants.items():
            with self.subTest(name):
                q = os.path.join(d, name)
                open(q, "w").write("\n".join(ls) + "\n")
                self.assertFalse(att.verify_chain_file(q)[0])
        # tail truncation: detectable only against the separately held head
        q = os.path.join(d, "trunc")
        open(q, "w").write("\n".join(lines[:3]) + "\n")
        ok, head, n = att.verify_chain_file(q)
        self.assertTrue(ok)
        self.assertNotEqual(head, ch.head)

    def test_reopen_refuses_tampered_chain(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "a.jsonl")
        ch = att.AuditChain(p)
        ch.append("e", {"x": 1}); ch.append("e", {"x": 2})
        s = open(p).read().replace('"x":1', '"x":7')
        open(p, "w").write(s)
        with self.assertRaises(errors.SandboxError):
            att.AuditChain(p)

    def test_oversize_event_is_digested(self):
        e = att.AuditChain().append("big", {"blob": "x" * 100_000})
        self.assertTrue(e["data"]["truncated"])


class ConfigTest(unittest.TestCase):
    def test_defaults_and_validation(self):
        c = cfg.load("{}")
        self.assertEqual(c["deny_action"], "errno")
        for bad in ('{"unknown": 1}', '{"syscall_budget": 0}', '{"syscall_budget": true}', "[]", "nope",
                    '{"backend": "docker"}', '{"node_key_ref": "plaintext-secret"}', "x" * (cfg.MAX_CONFIG_BYTES + 1)):
            with self.subTest(bad[:30]), self.assertRaises(errors.SandboxError) as e:
                cfg.load(bad)
            self.assertEqual(e.exception.code, "E_CONFIG_INVALID")

    def test_overlay_tighten_only(self):
        c = cfg.overlay({}, {"syscall_budget": 40}, {"deny_action": "kill"})
        self.assertEqual((c["syscall_budget"], c["deny_action"]), (40, "kill"))
        for loosen in ({"syscall_budget": 80}, {"require_userns": False}):
            with self.subTest(loosen), self.assertRaises(errors.SandboxError):
                cfg.overlay({}, loosen)
        with self.assertRaises(errors.SandboxError):
            cfg.overlay({"deny_action": "kill"}, {"deny_action": "errno"})

    def test_atomic_activation_provenance_and_rollback(self):
        d = tempfile.mkdtemp()
        st = cfg.ConfigStore(d)
        r1 = st.activate({"syscall_budget": 50}, actor="alice", source="git:abc")
        self.assertEqual((r1["version"], r1["actor"], r1["source"]), (1, "alice", "git:abc"))
        self.assertTrue(r1["digest"].startswith("sha256:"))
        with self.assertRaises(errors.SandboxError):
            st.activate({"syscall_budget": 40}, actor="bob", source="x", health_check=lambda c: False)
        self.assertEqual(st.active["config"]["syscall_budget"], 50)   # auto-rolled back
        self.assertEqual(st.active["source"].split(":")[0], "rollback")
        with self.assertRaises(errors.SandboxError):
            st.activate({"syscall_budget": -1}, actor="bob", source="x")
        self.assertEqual(json.load(open(os.path.join(d, "active.json")))["config"]["syscall_budget"], 50)
        st2 = cfg.ConfigStore(d)  # restart: history recovered
        self.assertEqual(st2.active["digest"], st.active["digest"])
        st2.rollback(actor="op", reason="manual", to_version=1)
        self.assertFalse([f for f in os.listdir(d) if f.startswith(".tmp-")])

    def test_redaction(self):
        r = cfg.redact({"api_token": "abc", "node_key_ref": "vault:x", "nested": [{"password": "p"}],
                        "note": "sig hmac-sha256:" + "a" * 64})
        self.assertEqual(r["api_token"], "[REDACTED]")
        self.assertEqual(r["node_key_ref"], "vault:x")
        self.assertEqual(r["nested"][0]["password"], "[REDACTED]")
        self.assertEqual(r["note"], "[REDACTED]")


class TelemetryTest(unittest.TestCase):
    def test_metrics_bounded_and_exposed(self):
        m = obs.Metrics()
        for i in range(obs.MAX_SERIES + 50):
            m.inc("x", {"k": str(i)})
        self.assertGreater(m.dropped_series, 0)
        m.observe("dropped_hist", 1.0)                      # cap also applies to new histograms
        self.assertNotIn("dropped_hist", m.exposition())
        m = obs.Metrics()
        m.observe("launch_seconds", 0.02, {"profile": "p"})
        text = m.exposition()
        self.assertIn('inv39_launch_seconds_bucket{profile="p",le="0.025"} 1', text)
        m.inc("y", {"k": 'bad"label\n'})
        self.assertNotIn('bad"label', m.exposition())

    def test_logger_ids_and_redaction(self):
        buf = io.StringIO()
        lg = obs.Logger(buf, node="n1")
        tp = obs.new_traceparent()
        lg.log("info", "m", tenant="t", workload="w", operation="launch", trace=tp, secret="s3cr3t")
        rec = json.loads(buf.getvalue())
        for k in obs.Logger.REQUIRED:
            self.assertIn(k, rec)
        self.assertEqual(rec["trace_id"], obs.trace_id(tp))
        self.assertEqual(rec["secret"], "[REDACTED]")

    def test_trace_propagation(self):
        parent = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
        child = obs.new_traceparent(parent)
        self.assertEqual(obs.trace_id(child), "ab" * 16)
        self.assertNotEqual(child, parent)
        self.assertNotEqual(obs.trace_id(obs.new_traceparent("garbage")), "ab" * 16)

    def test_diagnostics_sampled_and_redacted(self):
        d = obs.Diagnostics(sample_rate=0.0)
        self.assertFalse(d.record("k", {"a": 1}))
        d = obs.Diagnostics(sample_rate=1.0, capacity=3)
        for i in range(10):
            d.record("k", {"token": "t", "i": i})
        self.assertEqual(len(d.ring), 3)
        self.assertEqual(d.ring[-1]["data"]["token"], "[REDACTED]")

    def test_reasons_and_explain(self):
        r = obs.Reasons(att.AuditChain())
        r.record("rejection", "refused", subject="t/w", code="E_PROFILE_INVALID", because=["cap"])
        r.record("admission", "admitted", subject="t/other", code=None, because=[])
        ex = r.explain("t/w")
        self.assertEqual(len(ex), 1)
        self.assertEqual(ex[0]["data"]["code"], "E_PROFILE_INVALID")

    def test_alert_classes_distinct(self):
        self.assertEqual(set(obs.ALERT_RULES), {"load", "degradation", "policy_rejection",
                                                 "dependency_failure", "attack", "software_defect"})
        self.assertEqual(len(set(obs.ALERT_RULES.values())), 6)


if __name__ == "__main__":
    unittest.main()
