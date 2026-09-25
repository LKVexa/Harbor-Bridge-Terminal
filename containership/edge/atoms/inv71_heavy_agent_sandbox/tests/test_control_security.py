"""Security-boundary tests: authn, authz, egress binding, artifacts, audit, config."""
import json
import pathlib
import tempfile
import unittest

from _harness import AUDIT_KEY, EGRESS_KEY, KEY, Answer, Clock, FakeResolver, build, token  # noqa: F401

from inv71_heavy_agent_sandbox.control import audit_log, auth, egress
from inv71_heavy_agent_sandbox.control.artifacts import ARTIFACT_CLASSES, ManifestVerifier
from inv71_heavy_agent_sandbox.control.config import (ConfigStore, SECURE_DEFAULTS, merge, parse,
                                                      precedence_decide)
from inv71_heavy_agent_sandbox.control.controller import AUD
from inv71_heavy_agent_sandbox.control.errors import ControlError
from inv71_heavy_agent_sandbox.control.resilience import Shape


class AuthnTest(unittest.TestCase):
    """[C023][C044][C048][C050][C087] fail-closed authentication matrix."""

    def setUp(self):
        self.clock = Clock()
        self.ta = auth.TokenAuthority(KEY, "iss", clock=self.clock)

    def tok(self, **kw):
        base = dict(aud="svc", sub="alice", role="workload", tenant="t1", site="s", actions=["session.create"],
                    ttl_s=60, nonce="n1")
        base.update(kw)
        return self.ta.issue(**base)

    def code(self, fn):
        with self.assertRaises(ControlError) as cm:
            fn()
        return cm.exception.code.code

    def test_valid_token(self):
        self.assertEqual(self.ta.verify(self.tok(), aud="svc").sub, "alice")

    def test_anonymous(self):
        self.assertEqual(self.code(lambda: self.ta.verify(None, aud="svc")), "AUTHN.MISSING_CREDENTIAL")

    def test_wrong_audience(self):
        self.assertEqual(self.code(lambda: self.ta.verify(self.tok(), aud="other")), "AUTHN.WRONG_AUDIENCE")

    def test_expired_beyond_skew(self):
        t = self.tok()
        self.clock.advance(60 + 31)
        self.assertEqual(self.code(lambda: self.ta.verify(t, aud="svc")), "AUTHN.EXPIRED")

    def test_within_skew_accepted(self):
        t = self.tok()
        self.clock.advance(60 + 29)
        self.ta.verify(t, aud="svc")

    def test_future_issued_rejected(self):
        t = self.tok()
        self.clock.advance(-120)
        self.assertEqual(self.code(lambda: self.ta.verify(t, aud="svc")), "AUTHN.INVALID_CREDENTIAL")

    def test_replay(self):
        t = self.tok()
        self.ta.verify(t, aud="svc")
        self.assertEqual(self.code(lambda: self.ta.verify(t, aud="svc")), "AUTHN.REPLAYED")

    def test_replay_cache_flood_cannot_evict_live_nonce(self):
        ta = auth.TokenAuthority(KEY, "iss", clock=self.clock, replay_capacity=2)
        toks = [ta.issue(aud="svc", sub="a", role="workload", tenant="t1", site="s", actions=["session.create"],
                         ttl_s=60, nonce=f"f{i}") for i in range(3)]
        ta.verify(toks[0], aud="svc"); ta.verify(toks[1], aud="svc")
        self.assertEqual(self.code(lambda: ta.verify(toks[2], aud="svc")), "CAPACITY.ADMISSION_REJECTED")
        self.assertEqual(self.code(lambda: ta.verify(toks[0], aud="svc")), "AUTHN.REPLAYED")
        self.clock.advance(60 + 31)  # once the live nonces expire, capacity frees
        fresh = ta.issue(aud="svc", sub="a", role="workload", tenant="t1", site="s", actions=["session.create"], ttl_s=60, nonce="g")
        ta.verify(fresh, aud="svc")

    def test_revoked(self):
        t = self.tok()
        self.ta.revoke_subject("alice")
        self.assertEqual(self.code(lambda: self.ta.verify(t, aud="svc")), "AUTHN.REVOKED")

    def test_forged_signature_and_other_issuer(self):
        t = self.tok()
        p, s = t.split(".")
        self.assertEqual(self.code(lambda: self.ta.verify(p + "." + s[::-1], aud="svc")), "AUTHN.INVALID_CREDENTIAL")
        other = auth.TokenAuthority(b"x" * 32, "iss", clock=self.clock).issue(
            aud="svc", sub="alice", role="workload", tenant="t1", site="s", actions=["session.create"], ttl_s=60, nonce="z")
        self.assertEqual(self.code(lambda: self.ta.verify(other, aud="svc")), "AUTHN.INVALID_CREDENTIAL")

    def test_oversized_and_malformed(self):
        self.assertEqual(self.code(lambda: self.ta.verify("a" * 5000, aud="svc")), "AUTHN.INVALID_CREDENTIAL")
        self.assertEqual(self.code(lambda: self.ta.verify("a.b.c", aud="svc")), "AUTHN.INVALID_CREDENTIAL")
        self.assertEqual(self.code(lambda: self.ta.verify("!!.??", aud="svc")), "AUTHN.INVALID_CREDENTIAL")

    def test_issue_refuses_escalation(self):
        with self.assertRaises(ValueError):
            self.tok(actions=["artifact.promote"])
        with self.assertRaises(ValueError):
            self.tok(ttl_s=10_000)
        with self.assertRaises(ValueError):
            auth.TokenAuthority(b"short", "iss", clock=self.clock)


class AuthzTest(unittest.TestCase):
    """[C024][C042][C009] default-deny capabilities, tenant binding, separation of duties."""

    def claims(self, role, sub="u", tenant="t1", site="s", actions=None):
        return auth.Claims("iss", "aud", sub, role, tenant, site, tuple(actions or auth.ROLES[role]), 0, 1, "n", "1")

    def test_allowed(self):
        self.assertTrue(auth.authorize(self.claims("workload"), "session.create", tenant="t1", site="s").allowed)

    def test_tenant_substitution(self):
        d = auth.authorize(self.claims("workload"), "session.create", tenant="t2", site="s")
        self.assertEqual(d.reason, "AUTHZ.TENANT_MISMATCH")

    def test_site_and_role_confusion(self):
        self.assertEqual(auth.authorize(self.claims("workload"), "session.create", tenant="t1", site="x").reason, "AUTHZ.SITE_MISMATCH")
        self.assertEqual(auth.authorize(self.claims("workload"), "artifact.promote", tenant="t1", site="s").reason, "AUTHZ.ROLE_LACKS_ACTION")
        self.assertEqual(auth.authorize(self.claims("operator-read"), "session.quarantine", tenant="t1", site="s").reason, "AUTHZ.ROLE_LACKS_ACTION")

    def test_token_narrower_than_role(self):
        c = self.claims("workload", actions=["session.inspect"])
        self.assertEqual(auth.authorize(c, "session.create", tenant="t1", site="s").reason, "AUTHZ.TOKEN_LACKS_ACTION")

    def test_host_capability_only_node_helper(self):
        self.assertEqual(auth.authorize(self.claims("break-glass"), "host.kvm.open", tenant="", site="s").reason,
                         "AUTHZ.HOST_CAPABILITY_REQUIRES_NODE_HELPER")
        self.assertTrue(auth.authorize(self.claims("node-helper"), "host.kvm.open", tenant="", site="s").allowed)

    def test_two_person_rule(self):
        rm = self.claims("release-manager", sub="rm1")
        self.assertEqual(auth.authorize(rm, "artifact.promote", tenant="", site="s").reason, "AUTHZ.SECOND_APPROVER_REQUIRED")
        self.assertEqual(auth.authorize(rm, "artifact.promote", tenant="", site="s", approver=rm).reason, "AUTHZ.SELF_APPROVAL")
        self.assertTrue(auth.authorize(rm, "artifact.promote", tenant="", site="s",
                                       approver=self.claims("release-manager", sub="rm2")).allowed)

    def test_unknown_action_denied(self):
        self.assertEqual(auth.authorize(self.claims("break-glass"), "*", tenant="", site="s").reason, "AUTHZ.UNKNOWN_ACTION")


class EgressBindingTest(unittest.TestCase):
    """[INV71-X007][C043][C050][C087] DNS-to-destination enforcement."""

    def setUp(self):
        self.clock = Clock()
        self.res = FakeResolver({"api.example.com": Answer((), ("93.184.216.34",), 30),
                                 "cdn.example.com": Answer(("edge.cdn.example.net",), ("93.184.216.35",), 30),
                                 "evil.example.com": Answer((), ("169.254.169.254",), 30)})
        self.pol = egress.EgressPolicy.build("p1", [("api.example.com", [443]), ("cdn.example.com", [443]),
                                                    ("evil.example.com", [443]), ("93.184.216.99", [443])],
                                             key=EGRESS_KEY, resolver=self.res, clock=self.clock)

    def deny(self, *a):
        with self.assertRaises(ControlError) as cm:
            self.pol.decide("s1", *a)
        return cm.exception.code.code

    def test_allow_binds_address(self):
        cap = self.pol.decide("s1", "API.example.com.", 443)
        self.assertEqual((cap.canonical, cap.address, cap.port), ("api.example.com", "93.184.216.34", 443))
        egress.enforce(cap, key=EGRESS_KEY, sid="s1", address="93.184.216.34", port=443, protocol="tcp", now=self.clock())

    def test_enforcement_rejects_other_tuple_or_forged(self):
        cap = self.pol.decide("s1", "api.example.com", 443)
        for kw in ({"address": "93.184.216.35"}, {"port": 80}, {"sid": "s2"}):
            args = dict(key=EGRESS_KEY, sid="s1", address="93.184.216.34", port=443, protocol="tcp", now=self.clock())
            args.update(kw)
            with self.assertRaises(ControlError):
                egress.enforce(cap, **args)
        with self.assertRaises(ControlError):
            egress.enforce(cap, key=b"z" * 32, sid="s1", address="93.184.216.34", port=443, protocol="tcp", now=self.clock())
        with self.assertRaises(ControlError):
            egress.enforce(cap, key=EGRESS_KEY, sid="s1", address="93.184.216.34", port=443, protocol="tcp", now=self.clock() + 3600)

    def test_not_allowlisted_port_protocol(self):
        self.assertEqual(self.deny("other.com", 443), "POLICY.EGRESS_DENIED")
        self.assertEqual(self.deny("api.example.com", 80), "POLICY.EGRESS_DENIED")

    def test_metadata_and_private_targets(self):
        self.assertEqual(self.deny("evil.example.com", 443), "POLICY.EGRESS_DENIED")
        for a in ("127.0.0.1", "10.0.0.1", "192.168.1.1", "::1", "fe80::1", "::ffff:169.254.169.254",
                  "64:ff9b::a9fe:a9fe", "100.64.0.1", "fd00:ec2::254", "0.0.0.0", "224.0.0.1"):
            self.assertIsNotNone(egress.blocked_address(a), a)
        self.assertIsNone(egress.blocked_address("93.184.216.34"))

    def test_rebinding_after_ttl(self):
        self.pol.decide("s1", "api.example.com", 443)
        self.res.answers["api.example.com"] = Answer((), ("10.1.2.3",), 30)
        self.pol.decide("s1", "api.example.com", 443)  # still cached, bounded TTL
        self.clock.advance(31)
        self.assertEqual(self.deny("api.example.com", 443), "POLICY.EGRESS_DENIED")

    def test_capability_never_outlives_dns_answer(self):
        self.res.answers["api.example.com"] = Answer((), ("93.184.216.34",), 1)
        cap = self.pol.decide("s1", "api.example.com", 443)
        self.assertLessEqual(cap.expires_at, self.clock() + 1)

    def test_ttl_bounded(self):
        self.res.answers["api.example.com"] = Answer((), ("93.184.216.34",), 10**9)
        self.pol.decide("s1", "api.example.com", 443)
        self.res.answers["api.example.com"] = Answer((), ("127.0.0.1",), 1)
        self.clock.advance(egress.MAX_TTL_S + 1)
        self.assertEqual(self.deny("api.example.com", 443), "POLICY.EGRESS_DENIED")

    def test_cname_hop_must_be_allowlisted(self):
        self.assertEqual(self.deny("cdn.example.com", 443), "POLICY.EGRESS_DENIED")
        self.assertEqual(self.pol.decisions[-1]["reason"], "cname_not_allowlisted")

    def test_resolver_down_fails_closed(self):
        self.res.down = True
        self.assertEqual(self.deny("api.example.com", 443), "POLICY.DESTINATION_UNVERIFIED")

    def test_literal_and_malformed(self):
        self.assertEqual(self.pol.decide("s1", "93.184.216.99", 443).address, "93.184.216.99")
        for bad in ("http://api.example.com", "api.example.com:443", "a b", "fe80::1%eth0"):
            self.assertEqual(self.deny(bad, 443), "POLICY.EGRESS_DENIED", bad)

    def test_decision_log_bounded_and_complete(self):
        self.pol.decision_limit = 5
        for _ in range(10):
            try:
                self.pol.decide("s1", "nope.com", 443)
            except ControlError:
                pass
        self.assertEqual(len(self.pol.decisions), 5)
        self.assertTrue({"requested", "canonical", "resolved", "selected", "policy_version", "reason"} <= set(self.pol.decisions[0]))


class ArtifactTest(unittest.TestCase):
    """[C031][C032][C045][INV71-X004] approved-version manifest verification."""

    def setUp(self):
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.v = ManifestVerifier(b"m" * 32, min_serial=3)
        arts = {}
        for c in ARTIFACT_CLASSES:
            p = self.tmp / c
            p.write_bytes(c.encode() * 10)
            import hashlib
            arts[c] = {"version": "1.2.3", "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        self.m = {"schema": "PK_HEAVYBOX_ARTIFACT_MANIFEST/1", "serial": 3, "artifacts": arts}
        self.m["signature"] = self.v.sign(self.m)

    def code(self, m, cls="firecracker"):
        with self.assertRaises(ControlError) as cm:
            self.v.verify_artifact(m, cls, self.tmp / cls)
        return cm.exception.code.code

    def test_good(self):
        self.assertEqual(self.v.check_manifest(self.m), [])
        self.assertEqual(self.v.verify_artifact(self.m, "firecracker", self.tmp / "firecracker").version, "1.2.3")

    def test_tampered_file(self):
        (self.tmp / "firecracker").write_bytes(b"evil")
        self.assertEqual(self.code(self.m), "ARTIFACT.DIGEST_MISMATCH")

    def test_wrong_signer(self):
        m = dict(self.m, signature=ManifestVerifier(b"q" * 32).sign(self.m))
        self.assertEqual(self.code(m), "ARTIFACT.SIGNATURE_INVALID")

    def test_replayed_old_manifest(self):
        m = dict(self.m, serial=2)
        m["signature"] = self.v.sign(m)
        self.assertEqual(self.code(m), "ARTIFACT.UNAPPROVED_VERSION")

    def test_floating_tag(self):
        m = json.loads(json.dumps(self.m))
        m["artifacts"]["firecracker"]["version"] = "latest"
        m["signature"] = self.v.sign(m)
        self.assertEqual(self.code(m), "ARTIFACT.UNAPPROVED_VERSION")

    def test_revoked(self):
        self.v.revoked.add(self.m["artifacts"]["firecracker"]["sha256"])
        self.assertEqual(self.code(self.m), "ARTIFACT.REVOKED")

    def test_shipped_manifest_is_unpinned_and_refused(self):
        shipped = json.loads((pathlib.Path(__file__).resolve().parents[1] / "artifacts" / "approved-manifest.json").read_text())
        problems = ManifestVerifier(b"m" * 32).check_manifest(shipped)
        self.assertIn("firecracker:unpinned", problems)


class AuditStreamTest(unittest.TestCase):
    """[C049][C073][C050] durable signed audit: deletion/insertion/mutation/reorder/truncation."""

    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.anchors = []
        self.clock = Clock()
        self.s = audit_log.AuditStream(self.d / "a.jsonl", key=AUDIT_KEY, node="n", clock=self.clock,
                                       anchor=self.anchors.append, checkpoint_every=3, fsync=False)
        for i in range(7):
            self.s.append(actor="u", operation="op", outcome="allowed", reason=f"R.{i}", token="SECRET-TOKEN")

    def lines(self):
        return (self.d / "a.jsonl").read_text().splitlines()

    def write(self, lines):
        (self.d / "a.jsonl").write_text("\n".join(lines) + "\n")

    def ok(self):
        return audit_log.verify_file(self.d / "a.jsonl", key=AUDIT_KEY, anchors=self.anchors)[0]

    def test_intact_and_redacted(self):
        self.assertTrue(self.ok())
        self.assertNotIn("SECRET-TOKEN", (self.d / "a.jsonl").read_text())
        self.assertEqual(len(self.anchors), 2)

    def test_mutation(self):
        ls = self.lines(); ls[0] = ls[0].replace("R.0", "R.X"); self.write(ls)
        self.assertFalse(self.ok())

    def test_deletion(self):
        ls = self.lines(); del ls[1]; self.write(ls)
        self.assertFalse(self.ok())

    def test_reorder_and_duplicate(self):
        ls = self.lines(); ls[0], ls[1] = ls[1], ls[0]; self.write(ls)
        self.assertFalse(self.ok())
        ls = self.lines(); ls.insert(1, ls[0]); self.write(ls)
        self.assertFalse(self.ok())

    def test_tail_truncation_detected_by_anchor(self):
        ls = self.lines()
        self.write(ls[:2])
        self.assertTrue(audit_log.verify_file(self.d / "a.jsonl", key=AUDIT_KEY)[0])  # locally consistent
        self.assertFalse(self.ok())  # but the external anchor proves truncation

    def test_resume_after_restart(self):
        s2 = audit_log.AuditStream(self.d / "a.jsonl", key=AUDIT_KEY, node="n", clock=self.clock,
                                   anchor=self.anchors.append, checkpoint_every=3, fsync=False)
        self.assertEqual(s2.seq, 7)
        s2.append(actor="u", operation="op", outcome="allowed", reason="R.8")
        self.assertTrue(self.ok())

    def test_refuses_to_open_tampered_stream(self):
        ls = self.lines(); ls[0] = ls[0].replace("R.0", "R.X"); self.write(ls)
        with self.assertRaises(ControlError):
            audit_log.AuditStream(self.d / "a.jsonl", key=AUDIT_KEY, node="n", clock=self.clock, anchor=list().append)

    def test_spool_full_refuses_not_drops(self):
        self.s.max_bytes = 10
        with self.assertRaises(ControlError) as cm:
            self.s.append(actor="u", operation="op", outcome="allowed", reason="R.9")
        self.assertEqual(cm.exception.code.code, "AUDIT.SINK_UNAVAILABLE")


class ConfigTest(unittest.TestCase):
    """[C033][C034][C035][C036][C037][C038][C019][C058] configuration lifecycle."""

    def test_secure_defaults_validate(self):
        eff = merge({})
        self.assertEqual(eff["egress.default"], "deny")
        self.assertFalse(eff["host.debug_console"])

    def test_forbidden_override_every_layer(self):
        for layer in ("environment", "site", "tenant", "session"):
            with self.assertRaises(ControlError) as cm:
                merge({layer: {"egress.default": "allow"}})
            self.assertEqual(cm.exception.code.code, "CONFIG.FORBIDDEN_OVERRIDE")

    def test_layer_field_allowlist_and_lower_only(self):
        with self.assertRaises(ControlError):
            merge({"site": {"session.pids_max": 99}})
        with self.assertRaises(ControlError) as cm:
            merge({"session": {"session.vcpu": 8}})
        self.assertEqual(cm.exception.code.code, "POLICY.CONSTRAINT_CONFLICT")
        self.assertEqual(merge({"environment": {"session.vcpu": 4}, "session": {"session.vcpu": 1}})["session.vcpu"], 1)

    def test_deterministic_merge(self):
        a = merge({"environment": {"session.vcpu": 4}, "site": {"session.vcpu": 3}})
        b = merge({"site": {"session.vcpu": 3}, "environment": {"session.vcpu": 4}})
        self.assertEqual(a, b)
        self.assertEqual(a["session.vcpu"], 3)

    def test_parse_rejects(self):
        good = {"schema": "PK_HEAVYBOX_CONFIG/1", "values": {}}
        parse(json.dumps(good).encode())
        for raw in (b"\xff", b"[]", b'{"schema":"x","values":{}}', b'{"a":1,"a":2}',
                    b'{"schema":"PK_HEAVYBOX_CONFIG/1","values":{"x":NaN}}', b" " * (300 * 1024)):
            with self.assertRaises(ControlError):
                parse(raw)

    def test_range_type_unknown_crossfield(self):
        for ov in ({"session.vcpu": 0}, {"session.vcpu": "2"}, {"session.vcpu": True}, {"bogus": 1}):
            with self.assertRaises(ControlError):
                merge({"environment": ov})
        with self.assertRaises(ControlError):
            merge({"environment": {"profile": "far-edge", "session.mem_mib": 16384}})

    def test_signed_staging_generation_switch_and_rollback(self):
        from inv71_heavy_agent_sandbox.control.config import Participant
        clock = Clock()
        st = ConfigStore(signing_key=b"c" * 32, clock=clock)
        v1 = merge({})
        v2 = merge({"environment": {"session.vcpu": 4}})
        with self.assertRaises(ControlError):
            st.stage(v1, config_id="c", version=1, source="git:abc", author="a", approvals=["r1"], signature="00")
        for bad in ([], ["a"]):  # no approver / self-approval
            with self.assertRaises(ControlError):
                st.stage(v1, config_id="c", version=1, source="git:abc", author="a", approvals=bad, signature=st.sign(v1))
        p1 = st.stage(v1, config_id="c", version=1, source="git:abc", author="a", approvals=["r1"], signature=st.sign(v1))
        p2 = st.stage(v2, config_id="c", version=2, source="git:def", author="a", approvals=["r1"], signature=st.sign(v2))
        node, fw = Participant("node"), Participant("firewall")
        st.activate(p1.digest, actor="op", reason="init", participants=[node, fw], expected_generation=0)
        self.assertEqual((node.committed, fw.committed), (1, 1))
        with self.assertRaises(ControlError):  # participant rejects -> everyone aborts, previous generation stays
            st.activate(p2.digest, actor="op", reason="r", participants=[node, Participant("cg", accept=False)], expected_generation=1)
        self.assertEqual((st.generation, st.active_digest, node.committed, node.aborted), (1, p1.digest, 1, [2]))
        with self.assertRaises(ControlError) as cm:  # stale writer
            st.activate(p2.digest, actor="op", reason="r", participants=[node], expected_generation=0)
        self.assertEqual(cm.exception.code.code, "CONFIG.STALE_GENERATION")
        st.activate(p2.digest, actor="op", reason="r", participants=[node, fw], expected_generation=1)
        act = st.rollback(actor="op", reason="regression", participants=[node, fw], to_generation=1)
        self.assertEqual((act.generation, act.digest, act.rollback_of, act.previous_digest), (3, p1.digest, 1, p2.digest))
        self.assertEqual((node.committed, fw.committed), (3, 3))
        self.assertEqual(st.effective()[1].source, "git:abc")

    def test_precedence_matrix(self):
        base = {k: True for k in ("authenticated", "artifact_verified", "isolation_available", "residency_ok",
                                  "egress_policy_ok", "teardown_verifiable", "tenant_policy_ok", "capacity_ok")}
        self.assertEqual(precedence_decide(base), ("ADMIT", "PREC.ALL_SATISFIED"))
        self.assertEqual(precedence_decide({**base, "authenticated": False, "capacity_ok": False})[1], "PREC.AUTHENTICATION")
        self.assertEqual(precedence_decide({**base, "residency_ok": False, "slo_ok": False})[1], "PREC.RESIDENCY")
        self.assertEqual(precedence_decide({**base, "slo_ok": False}), ("ADMIT_DEGRADED", "PREC.SLO_AT_RISK"))
        self.assertEqual(precedence_decide({}), ("DENY", "PREC.AUTHENTICATION"))  # missing input fails closed


if __name__ == "__main__":
    unittest.main()
