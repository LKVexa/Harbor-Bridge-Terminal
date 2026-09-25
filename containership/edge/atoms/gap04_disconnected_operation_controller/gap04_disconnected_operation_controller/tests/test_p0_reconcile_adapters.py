"""C07 idempotency ids, C08 reconciliation engine, C09 GAP-05, C10 GAP-12, C11 GAP-13,
C12 PLN-07, C13 GAP-01, C14 boundary authn/authz."""
import unittest
from _util import T, Tmp, node, code, Gap04Error
from gap04_disconnected_operation_controller.runtime.adapters import (ReachabilityMonitor, ReferenceReplication,
    ReferenceSupervisor, negotiate, sign_heartbeat)
from gap04_disconnected_operation_controller.runtime.authz import Authorizer, Principal, principal_from_peercert


def dark_node(d, **kw):
    n, cp, m = node(d, **kw)
    T.bring_up(n, cp, m); T.go_dark(n, m)
    return n, cp, m


class Idempotency(unittest.TestCase):
    def test_T_C07_stable_ids_and_retry(self):
        with Tmp() as d:
            n, cp, m = dark_node(d)
            a = n.decide("restart", "ns/a", "req-00000001")
            b = n.decide("restart", "ns/a", "req-00000001")
            self.assertEqual(a["decision_id"], b["decision_id"]); self.assertTrue(b["replayed"])
            self.assertEqual(len(n.controller.decisions), 1)
            self.assertEqual(len(n.adapters.supervisor.executed), 1)
            code(self, "GAP04-E0004", n.decide, "restart", "ns/a", "short")
            code(self, "GAP04-E0601", n.decide, "scale", "ns/a", "req-00000001")   # same id, different content
            self.assertEqual(n.metrics.get("replays_total"), 1)
            n.close()

    def test_T_C07_reconnect_txn_is_deterministic_and_idempotent_at_peer(self):
        with Tmp() as d:
            rep = ReferenceReplication(fail_times=100)
            n, cp, m = dark_node(d, replication=rep)
            for i in range(3):
                n.decide("restart", f"ns/{i}", f"req-{i:08d}")
            T.come_back(n, cp, m)
            e = code(self, "GAP04-E0600", n.reconnect)
            txn = e.details["txn_id"]
            rep.fail_times = 0
            r = n.reconnect()
            self.assertEqual(r["txn_id"], txn)
            self.assertEqual(len(rep.applied), 3)
            n.close()


class Reconciliation(unittest.TestCase):
    def test_T_C08_conflict_compensate_and_quarantine(self):
        with Tmp() as d:
            n, cp, m = node(d)
            T.bring_up(n, cp, m)
            since = n.clock.now() + 1
            rep = ReferenceReplication(authoritative={"ns/b": {"kind": "scale", "at": since + 5, "by": "cloud"}})
            n.adapters.replication = rep
            T.go_dark(n, m)
            n.decide("restart", "ns/a", "req-00000001")
            n.decide("scale", "ns/b", "req-00000002")
            T.come_back(n, cp, m)
            r = n.reconnect()
            vals = sorted(r["outcomes"].values())
            self.assertEqual(vals, ["accepted", "compensated"])
            self.assertEqual(r["conflicts"], 1)
            self.assertEqual(n.metrics.get("reconcile_conflicts_total"), 1)
            self.assertEqual(n.adapters.supervisor.executed[[k for k, v in r["outcomes"].items() if v == "compensated"][0]]["status"], "compensated")
            n.close()

    def test_T_C08_uncompensatable_conflict_quarantines_subject(self):
        with Tmp() as d:
            sup = ReferenceSupervisor(); sup.compensate = lambda cid: {"status": "unknown"}
            n, cp, m = node(d, supervisor=sup)
            T.bring_up(n, cp, m)
            n.adapters.replication = ReferenceReplication(authoritative={"ns/b": {"kind": "scale", "at": 2**40}})
            T.go_dark(n, m)
            n.decide("scale", "ns/b", "req-00000002")
            T.come_back(n, cp, m)
            self.assertEqual(list(n.reconnect()["outcomes"].values()), ["quarantined"])
            n.close()

    def test_T_C08_partial_failure_resumes_batches(self):
        with Tmp() as d:
            from gap04_disconnected_operation_controller.runtime.config import default_config
            cfg = default_config(); cfg["reconcile"]["batch_size"] = 2
            calls = {"fail": True}
            class Flaky(ReferenceReplication):
                def submit(self, b):
                    if b["batch_no"] == 1 and calls["fail"]:
                        from gap04_disconnected_operation_controller.runtime.errors import AdapterError
                        raise AdapterError("down")
                    return super().submit(b)
            rep = Flaky()
            n, cp, m = dark_node(d, config=cfg, replication=rep)
            for i in range(5):
                n.decide("restart", f"ns/{i}", f"req-{i:08d}")
            T.come_back(n, cp, m)
            with self.assertRaises(Gap04Error):
                n.reconnect()
            self.assertEqual(n.state["reconcile"]["acked"], [0])
            self.assertGreaterEqual(n.metrics.get("retries_total", dependency="GAP-05"), 1)  # bounded retries
            code(self, "GAP04-E0600", n.reconnect)
            calls["fail"] = False; n.breakers["GAP-05"].reset_after = 0
            r = n.reconnect()
            self.assertEqual(r["decision_count"], 5); self.assertEqual(len(rep.applied), 5)
            n.close()

    def test_T_C08_record_is_complete_and_audit_anchored(self):
        with Tmp() as d:
            n, cp, m = dark_node(d)
            ids = [n.decide("restart", f"ns/{i}", f"req-{i:08d}")["decision_id"] for i in range(7)]
            T.come_back(n, cp, m)
            r = n.reconnect()
            self.assertEqual([x["decision_id"] for x in r["decisions"]], ids)
            self.assertRegex(r["audit_head"], r"^sha256:")
            code(self, "GAP04-E0001", n.reconnect)
            n.close()

    def test_T_C08_requires_verified_reachability(self):
        with Tmp() as d:
            n, cp, m = dark_node(d)
            code(self, "GAP04-E0100", n.reconnect)
            n.close()


class Reachability(unittest.TestCase):
    def setUp(self):
        self.cp = T.ControlPlane(); self.mon = ReachabilityMonitor("site-a", self.cp.trust(), up_after=2, down_after=2,
                                                                    flap_threshold=4, flap_window_s=100)

    def ok(self, now, **kw):
        return self.mon.observe(self.cp.heartbeat(self.mon, now), now, **kw)

    def test_T_C10_hysteresis(self):
        self.assertEqual(self.mon.state, "unknown")
        self.ok(1); self.assertFalse(self.mon.reachable)
        self.ok(2); self.assertEqual(self.mon.state, "up")
        self.mon.observe(None, 3); self.assertEqual(self.mon.state, "up")
        self.mon.observe(None, 4); self.assertEqual(self.mon.state, "down")

    def test_T_C10_spoof_and_replay(self):
        other_seed, _ = __import__("gap04_disconnected_operation_controller.runtime.crypto", fromlist=["x"]).generate_signing_key()
        for _ in range(5):
            n = self.mon.challenge()
            self.mon.observe(sign_heartbeat("site-a", n, 1, "cp-1", "cp-1-k1", other_seed), 1)
        self.assertNotEqual(self.mon.state, "up")
        n = self.mon.challenge(); hb = sign_heartbeat("site-a", n, 1, "cp-1", "cp-1-k1", self.cp.seed)
        self.mon.observe(hb, 1); self.mon.observe(hb, 2)   # replayed nonce
        self.assertNotEqual(self.mon.state, "up")
        self.mon.challenge(); self.mon.observe(sign_heartbeat("site-b", self.mon._nonce, 1, "cp-1", "cp-1-k1", self.cp.seed), 3)
        self.assertNotEqual(self.mon.state, "up")

    def test_T_C10_flapping_and_degraded(self):
        t = 0
        for _ in range(3):
            self.ok(t); self.ok(t + 1); self.mon.observe(None, t + 2); self.mon.observe(None, t + 3); t += 4
        self.ok(t); self.ok(t + 1)
        self.assertEqual(self.mon.state, "flapping"); self.assertFalse(self.mon.reachable)
        mon = ReachabilityMonitor("site-a", self.cp.trust(), up_after=1)
        mon.observe(self.cp.heartbeat(mon, 1), 1, latency_ms=5000)
        self.assertEqual(mon.state, "degraded"); self.assertTrue(mon.reachable)


class Policy(unittest.TestCase):
    def test_T_C11_policy_evaluation_and_freeze(self):
        with Tmp() as d:
            n, cp, m = dark_node(d)
            code(self, "GAP04-E0101", n.decide, "restart", "kube-system/dns", "req-00000001")
            m.t += 7300
            code(self, "GAP04-E0101", n.decide, "rebalance", "ns/a", "req-00000002")
            n.decide("restart", "ns/a", "req-00000003")
            n.close()

    def test_T_C11_stale_policy_refused(self):
        with Tmp() as d:
            from gap04_disconnected_operation_controller.runtime.config import default_config
            cfg = default_config(); cfg["max_policy_staleness_s"] = 600; cfg["tier_schedule"] = [[0, "full"]]
            n, cp, m = dark_node(d, config=cfg)
            m.t += 700
            code(self, "GAP04-E0102", n.decide, "restart", "ns/a", "req-00000001")
            n.close()


class Capabilities(unittest.TestCase):
    def test_T_C12_least_privilege_and_revocation(self):
        with Tmp() as d:
            n, cp, m = node(d, capabilities=True)
            T.bring_up(n, cp, m)
            now = n.clock.now()
            g = cp.grant(T.WORKLOAD.spiffe_id, ["gap04.decide.restart"], now)
            n.adapters.capabilities.install_grant(g, now)
            code(self, "GAP04-E0105", n.adapters.capabilities.install_grant, dict(g, capabilities=["gap04.decide.scale"]), now)
            T.go_dark(n, m)
            n.decide("restart", "ns/a", "req-00000001", principal=T.WORKLOAD)
            code(self, "GAP04-E0105", n.decide, "scale", "ns/a", "req-00000002", principal=T.WORKLOAD)
            code(self, "GAP04-E0105", n.decide, "restart", "ns/a", "req-00000003")
            T.come_back(n, cp, m); n.reconnect()
            n.apply_revocations(2, revoked_grants=[g["grant_id"]])
            self.assertEqual(n.adapters.capabilities.grants, {})
            code(self, "GAP04-E0105", n.adapters.capabilities.install_grant, g, now)   # predates epoch
            n.close()


class Supervisor(unittest.TestCase):
    def test_T_C13_commands_fenced_and_contracted(self):
        sup = ReferenceSupervisor()
        cmd = {"contract": "PK_SUPERVISOR_COMMAND/1", "command_id": "d-" + "0" * 32, "kind": "restart",
               "subject": "ns/a", "authority_epoch": 2, "generation": 5}
        sup.execute(cmd)
        self.assertTrue(sup.execute(cmd)["replayed"])
        code(self, "GAP04-E0500", sup.execute, dict(cmd, command_id="d-" + "1" * 32, generation=4))
        code(self, "GAP04-E0901", sup.execute, dict(cmd, contract="PK_SUPERVISOR_COMMAND/0"))
        code(self, "GAP04-E0901", negotiate, "GAP-05", "PK_REPLICATION_BATCH/9")

    def test_T_C13_supervisor_failure_recorded_and_resumed(self):
        with Tmp() as d:
            fail = {"on": True}
            sup = ReferenceSupervisor(fail=lambda c: fail["on"])
            n, cp, m = dark_node(d, supervisor=sup)
            r = n.decide("restart", "ns/a", "req-00000001")
            self.assertTrue(n.state["effects"][r["decision_id"]].startswith("failed:"))
            fail["on"] = False
            n.state["effects"].clear()
            self.assertEqual(n.resume_effects(), 0)  # effect frame exists (failed) -> not blindly re-driven
            n.close()


class Authz(unittest.TestCase):
    def test_T_C14_deny_by_default(self):
        with Tmp() as d:
            az = Authorizer(T.TD)
            n, cp, m = node(d, authorizer=az)
            n.clock.anchor_trusted(cp.t0); T.come_back(n, cp, m)
            code(self, "GAP04-E0104", n.install_policy, cp.policy())
            code(self, "GAP04-E0104", n.install_policy, cp.policy(), principal=T.OPERATOR)
            az.allow("policy.install", T.OPERATOR.spiffe_id)
            n.install_policy(cp.policy(), principal=T.OPERATOR)
            code(self, "GAP04-E0104", n.install_policy, cp.policy(), principal=Principal("spiffe://evil.org/ops/alice", "evil.org"))
            code(self, "GAP04-E0104", n.decide, "restart", "ns/a", "req-00000001", principal=T.WORKLOAD)
            n.close()

    def test_T_C14_peer_certificate_identity(self):
        p = principal_from_peercert({"subjectAltName": (("URI", "spiffe://example.org/ops/alice"),)})
        self.assertEqual(p.trust_domain, "example.org")
        code(self, "GAP04-E0104", principal_from_peercert, None)
        code(self, "GAP04-E0104", principal_from_peercert, {"subjectAltName": (("DNS", "x"),)})
        code(self, "GAP04-E0104", principal_from_peercert, {"subjectAltName": (("URI", "spiffe://a/x"), ("URI", "spiffe://b/y"))})


if __name__ == "__main__":
    unittest.main()
