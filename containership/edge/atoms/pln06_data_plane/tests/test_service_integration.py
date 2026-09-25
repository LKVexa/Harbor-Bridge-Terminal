"""WP #14 #27 #34-#39 #46 #53-#58 - governed service end to end with adjacent-layer fixtures."""
from __future__ import annotations

import io
import json
import os
import time
import unittest

from _support import ALL_WORKLOAD_CAPS, Env
from pln06_data_plane import integrations as ig
from pln06_data_plane import transports as t
from pln06_data_plane.data_plane import Backpressure, InvalidRequest, ResidencyViolation
from pln06_data_plane.integrity import IntegrityMismatch
from pln06_data_plane.observability import StructuredLogger, parse_traceparent
from pln06_data_plane.resilience import FailoverController, RetryExhausted, RetryPolicy
from pln06_data_plane.security import AuthenticationFailed, AuthorizationDenied, KeyUnavailable, LabelInvalid
from pln06_data_plane.service import AdmissionFrozen, DestinationQuarantined, GovernedDataPlane


class ServiceHappyPathTest(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.addCleanup(self.e.close)

    def test_inline_and_shared_memory_paths_complete_and_are_audited(self):
        small = self.e.send(b"hi")
        big = self.e.send(os.urandom(100_000), locality="same_node")
        self.assertEqual(small["receipt"]["adapter"], "component-model-inprocess")
        self.assertEqual(big["receipt"]["adapter"], "shared-memory")
        self.assertEqual(self.e.plane.inflight, 0)
        self.assertEqual(self.e.journal.state[big["transfer_id"]]["state"], "completed")
        events = [r["event"] for r in self.e.audit.records()]
        self.assertEqual(events.count("admit"), 2)
        self.assertEqual(events.count("complete"), 2)
        self.assertEqual(self.e.audit.verify(), len(events))
        self.assertEqual(len(self.e.runtime.accepted), 1)          # PLN-03 hand-off for non-inline only
        self.assertIsNotNone(parse_traceparent(big["traceparent"]))

    def test_explain_is_redacted_and_authorized(self):
        r = self.e.send(b"secret-bytes", tenant="acme")
        view = self.e.svc.explain(self.e.op(), r["transfer_id"])
        blob = json.dumps(view)
        self.assertNotIn("acme", blob)
        self.assertNotIn("secret-bytes", blob)
        self.assertEqual(view["schema"], "PK_DATA_PLANE_EXPLAIN/1")
        with self.assertRaises(AuthorizationDenied):
            self.e.svc.explain(self.e.cred(), r["transfer_id"])

    def test_metrics_export_and_health_dependencies(self):
        self.e.send(b"x" * 100)
        text = self.e.svc.metrics_text()
        for series in ("pk06_admitted_total", "pk06_transfer_seconds_bucket", "pk06_inflight",
                       "pk06_process_max_rss_bytes", "pk06_backlog_oldest_seconds"):
            self.assertIn(series, text)
        h = self.e.svc.health()
        self.assertTrue(h["ready"])
        self.assertIn("key_service", h["dependencies"])
        self.e.keys.set_provider_outage(True)
        h = self.e.svc.health()
        self.assertFalse(h["ready"])
        self.assertIn("key_service", h["degraded"])


class ServiceRefusalTest(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.addCleanup(self.e.close)

    def test_authn_authz_label_residency_refusals_are_audited(self):
        e = self.e
        with self.assertRaises(AuthenticationFailed):
            e.svc.submit({"body": {}, "kid": "k1", "mac": "0"}, workload="w", data=b"x", classification="public",
                         destination="eu")
        with self.assertRaises(AuthorizationDenied):
            e.svc.submit(e.cred(caps=("transfer.submit",)), workload="w", data=b"x" * 100_000,
                         classification="public", destination="eu", label=e.label(b"x" * 100_000),
                         locality="same_node")                       # lacks transport.use.local
        self.assertEqual(e.plane.inflight, 0)                        # reservation released
        with self.assertRaises(LabelInvalid):
            e.svc.submit(e.cred(), workload="w", data=b"x", classification="pii", destination="eu",
                         label=e.label(b"x", "public"))
        with self.assertRaises(InvalidRequest):
            e.svc.submit(e.cred(), workload="w", data=b"x", classification="public", destination="eu")
        with self.assertRaises(ResidencyViolation):
            e.send(b"x", classification="pii", destination="us")
        with self.assertRaises(LabelInvalid):   # label for tenant t1 replayed by tenant t2
            e.svc.submit(e.cred("t2"), workload="w", data=b"x", classification="public", destination="eu",
                         label=e.label(b"x", tenant="t1"))
        events = [r["event"] for r in e.audit.records()]
        self.assertEqual(events.count("authn_failure"), 1)
        self.assertEqual(events.count("authz_denied"), 1)
        self.assertGreaterEqual(events.count("refuse"), 4)

    def test_key_outage_fails_closed(self):
        self.e.keys.set_provider_outage(True)
        with self.assertRaises(KeyUnavailable):
            self.e.send(b"x")

    def test_operator_controls(self):
        e, op = self.e, self.e.op()
        with self.assertRaises(AuthorizationDenied):
            e.svc.freeze(e.cred(), "nope")
        e.svc.freeze(op, "maintenance")
        with self.assertRaises(AdmissionFrozen) as cm:
            e.send()
        self.assertTrue(cm.exception.retryable)
        e.svc.unfreeze(op)
        e.svc.quarantine(op, destination="eu", reason="suspect")
        with self.assertRaises(DestinationQuarantined):
            e.send()
        e.svc.unquarantine(op, destination="eu")
        e.svc.quarantine(op, transport="shared-memory", reason="leak")
        with self.assertRaises(t.TransportUnsupported):
            e.send(b"y" * 100_000, locality="same_host_vm")
        e.svc.unquarantine(op, transport="shared-memory")
        e.send(b"y" * 100_000, locality="same_host_vm")
        self.assertTrue(e.svc.drain(op, timeout=1))
        e.svc.unfreeze(op)
        e.svc.emergency_disable(op, "incident-123")
        with self.assertRaises(AdmissionFrozen) as cm:
            e.send()
        self.assertFalse(cm.exception.retryable)
        self.assertFalse(e.svc.health()["ready"])
        ev = [r["event"] for r in e.audit.records()]
        for needed in ("freeze", "unfreeze", "quarantine", "unquarantine", "drain", "emergency_disable"):
            self.assertIn(needed, ev)

    def test_policy_update_requires_capability_and_protects_live_transfers(self):
        e = self.e
        with self.assertRaises(AuthorizationDenied):
            e.svc.update_policy(e.cred(), {"eu": ["public"]}, revision="r2")
        e.svc.update_policy(e.op(), {"eu": ["public"], "us": ["public"]}, revision="r2")
        self.assertEqual(e.plane.config_snapshot()["revision"], "r2")
        with self.assertRaises(ResidencyViolation):
            e.send(b"x", classification="pii")

    def test_tenant_quota_isolation_under_governed_path(self):
        slow = []

        class Hold(t.TransportAdapter):
            name = "shared-memory"
            tiers = frozenset({"local", "bulk"})

            def _send(self, decision, data, *, deadline, cancel):
                slow.append(decision)
                raise Backpressure("peer busy")
        e = Env(adapters={"shared-memory": Hold()}, retry=RetryPolicy(max_attempts=1))
        self.addCleanup(e.close)
        with self.assertRaises(RetryExhausted):
            e.send(b"z" * 100_000, locality="same_node")
        self.assertEqual(e.plane.inflight, 0)                         # failure released capacity
        self.assertEqual(e.journal.state[next(iter(e.journal.state))]["state"], "failed")


class AdjacentLayerTest(unittest.TestCase):
    """GAP-13 / GAP-14 / PLN-03 / INV-36 / INV-37 reference-fixture integration."""

    def test_gap13_policy_sync_degraded_and_fail_closed(self):
        clk = [1000.0]
        e = Env()
        self.addCleanup(e.close)
        svc_ = ig.ReferencePolicyService(e.keys, {"eu": ["public", "pii"]}, revision="gap13-r5", serial=5,
                                         clock=lambda: clk[0])
        pc = ig.PolicyClient(svc_, e.keys, max_age=60, clock=lambda: clk[0])
        e.svc.policy = pc
        self.assertEqual(e.svc.sync_policy(), "gap13-r5")
        e.send(b"x", classification="pii")
        svc_.down = True
        clk[0] += 30
        e.svc.sync_policy()                                           # degraded: last verified copy
        self.assertTrue(pc.degraded)
        clk[0] += 60
        with self.assertRaises(ig.PolicyUnavailable):
            e.send(b"x")                                              # too old -> fail closed
        svc_.down = False
        svc_.serial = 4
        with self.assertRaises(ig.PolicyInvalid):
            pc.refresh()                                              # downgrade refused
        forged = svc_.fetch()
        forged["body"]["residency"] = {"us": ["pii"]}
        with self.assertRaises(ig.PolicyInvalid):
            ig.PolicyClient(type("S", (), {"fetch": lambda self: forged})(), e.keys).refresh()

    def test_gap14_gravity_is_authentic_advisory_and_never_overrides_residency(self):
        e = Env()
        self.addCleanup(e.close)
        grav = ig.ReferenceGravityService(e.keys, {("t1", "eu"): "same_node", ("t1", "us"): "same_node"})
        e.svc.gravity_keys = e.keys
        r = e.send(b"q" * 10, gravity=grav.hint("t1", "w", "eu"))
        self.assertEqual(r["decision"]["tier"], "local")               # promoted by hint
        self.assertEqual(ig.verified_locality(grav.hint("t2", "w", "eu"), e.keys, tenant="t1", destination="eu"), "auto")
        tampered = grav.hint("t1", "w", "eu")
        tampered["body"]["locality"] = "remote"
        self.assertEqual(ig.verified_locality(tampered, e.keys, tenant="t1", destination="eu"), "auto")
        with self.assertRaises(ResidencyViolation):
            e.send(b"q", classification="pii", destination="us", gravity=grav.hint("t1", "w", "us"))

    def test_pln03_handoff_failure_propagates_and_releases(self):
        e = Env(retry=RetryPolicy(max_attempts=2, base_delay=0, max_delay=0))
        self.addCleanup(e.close)
        e.runtime.fail_next = 5
        with self.assertRaises(RetryExhausted):
            e.send(b"p" * 100_000, locality="same_node")
        self.assertEqual(e.plane.inflight, 0)
        e.runtime.fail_next = 1
        e.send(b"p" * 100_000, locality="same_node")                  # one retry absorbs one failure
        self.assertEqual(len(e.runtime.accepted), 1)

    def test_inv37_bulk_over_network_with_quarantine_and_inv36_isolation(self):
        secret = os.urandom(32)
        srv = t.NetworkRpcServer({"n1": secret}).start()
        self.addCleanup(srv.stop)
        net = t.NetworkRpcAdapter(srv.address, peer_id="n1", secret=secret, chunk_size=8192)
        e = Env(adapters={"network-rpc": net}, retry=RetryPolicy(max_attempts=1))
        self.addCleanup(e.close)
        data = os.urandom(70_000)
        r = e.send(data, locality="remote")
        self.assertEqual(srv.received[r["transfer_id"]], data)
        bad = t.NetworkRpcAdapter(srv.address, peer_id="n1", secret=secret, tamper=lambda i, b: b"!" + b[1:])
        e2 = Env(adapters={"network-rpc": bad}, retry=RetryPolicy(max_attempts=3))
        self.addCleanup(e2.close)
        with self.assertRaises(IntegrityMismatch):
            e2.send(data, locality="remote")
        tid = next(iter(e2.journal.state))
        self.assertEqual(e2.journal.state[tid]["state"], "quarantined")  # never auto-retried
        self.assertEqual(e2.plane.inflight, 0)

    def test_inv36_control_verbs_over_vsock_profile(self):
        import socket
        a, b = socket.socketpair()
        self.addCleanup(a.close)
        self.addCleanup(b.close)
        e = Env(adapters={"vsock-control": t.VsockControlAdapter(a)})
        self.addCleanup(e.close)
        e.send(b"cfg", locality="vm_control", control_verb="configure")
        hdr, body = t.read_control_frame(b)
        self.assertEqual(hdr["verb"], "configure")
        with self.assertRaises(t.TransportUnsupported):   # non-inline never routes to vsock
            e.send(b"x" * 100_000, locality="vm_control", control_verb="configure")


class DisasterRecoveryTest(unittest.TestCase):
    def test_crash_restart_reconciles_open_transfers(self):
        e = Env()
        self.addCleanup(e.close)
        e.journal.transition("ghost", "admitted")
        e.journal.transition("ghost", "in_flight")
        from pln06_data_plane.lifecycle import TransferJournal
        j2 = TransferJournal(e.dir / "journal.jsonl")
        svc2 = GovernedDataPlane(e.plane, keyring=e.keys, authenticator=e.authn, labels=e.labels, audit=e.audit,
                                 journal=j2, adapters=e.svc.adapters)
        self.assertEqual(svc2.recovered, ["ghost"])
        self.assertEqual(j2.state["ghost"]["state"], "expired")
        self.assertEqual(e.audit.records()[-1]["event"], "restore")

    def test_partition_failover_to_residency_safe_site(self):
        import socket
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        dead = s.getsockname()
        s.close()
        secret = os.urandom(32)
        srv = t.NetworkRpcServer({"n": secret}).start()
        self.addCleanup(srv.stop)

        class Routed(t.TransportAdapter):
            """Routes by destination: eu-a is partitioned, eu-b reachable."""
            name = "network-rpc"
            tiers = frozenset({"local", "bulk"})

            def __init__(self):
                super().__init__()
                self.a = t.NetworkRpcAdapter(dead, peer_id="n", secret=secret)
                self.b = t.NetworkRpcAdapter(srv.address, peer_id="n", secret=secret)

            def _send(self, d, data, *, deadline, cancel):
                return (self.a if d["destination"] == "eu-a" else self.b).send(d, data, deadline=deadline)
        residency = {"eu-a": {"pii"}, "eu-b": {"pii"}, "us": {"public", "pii"}}
        e = Env(residency=residency, adapters={"network-rpc": Routed()},
                retry=RetryPolicy(max_attempts=2, base_delay=0, max_delay=0))
        self.addCleanup(e.close)
        e.svc.failover_ctl = FailoverController(e.plane.residency_snapshot,
                                                {"eu-a": "sovereign", "eu-b": "sovereign", "us": "shared"},
                                                health=lambda s: True)
        r = e.send(b"d" * 1000, classification="pii", destination="eu-a", locality="remote",
                   failover_candidates=["us", "eu-b"])
        self.assertEqual(r["decision"]["destination"], "eu-b")        # us rejected: weaker isolation
        self.assertIn("failover", [x["event"] for x in e.audit.records()])

    def test_stalled_transfer_reaped(self):
        e = Env(stall_timeout=0.0)
        self.addCleanup(e.close)
        d = e.plane.admit(tenant="t1", workload="w", size=100_000, classification="public", destination="eu",
                          locality="same_node")
        e.svc._decisions[d["transfer_id"]] = d
        e.journal.transition(d["transfer_id"], "admitted")
        e.journal.transition(d["transfer_id"], "in_flight")
        e.svc.stalls.progress(d["transfer_id"])
        time.sleep(0.01)
        self.assertEqual(e.svc.reap_stalled(), [d["transfer_id"]])
        self.assertEqual(e.plane.inflight, 0)


class LoggingTracingTest(unittest.TestCase):
    def test_structured_log_schema_redaction_and_sink_failure(self):
        buf = io.StringIO()
        log = StructuredLogger(node="n1", release="4.3.0", sink=buf, ring=2)
        rec = log.log("INFO", "e", operation="op", tenant="t", secret_token="abc", payload=b"123",
                      trace={"trace_id": "a" * 32, "span_id": "b" * 16})
        self.assertEqual(rec["fields"], {"secret_token": "[REDACTED]", "payload": "[REDACTED]"})
        parsed = json.loads(buf.getvalue())
        for k in ("schema", "node", "component", "release", "operation", "tenant", "trace_id", "ts", "level"):
            self.assertIn(k, parsed)
        buf.close()
        log.log("INFO", "e2", operation="op")          # closed sink must not raise
        log.log("INFO", "e3", operation="op")
        self.assertGreaterEqual(log.dropped, 1)
        self.assertIsNone(log.log("DEBUG", "quiet", operation="op"))

    def test_trace_context_propagates_ingress_to_egress(self):
        e = Env()
        self.addCleanup(e.close)
        incoming = "00-" + "1" * 32 + "-" + "2" * 16 + "-01"
        r = e.send(b"x", traceparent=incoming)
        self.assertEqual(parse_traceparent(r["traceparent"])["trace_id"], "1" * 32)
        span = e.svc.tracer.spans[-1]
        self.assertEqual(span["parent_id"], "2" * 16)
        for bad in ("", "00-" + "0" * 32 + "-" + "2" * 16 + "-01", "zz", "00-abc-def-01"):
            self.assertIsNone(parse_traceparent(bad))


class WorkloadCapsTest(unittest.TestCase):
    def test_cap_constants_valid(self):
        from pln06_data_plane.security import CAPABILITIES
        self.assertTrue(set(ALL_WORKLOAD_CAPS) <= CAPABILITIES)


if __name__ == "__main__":
    unittest.main()


class OpsDefinitionsTest(unittest.TestCase):
    """WP #41: every metric referenced by alerts/dashboards is actually emitted."""

    def test_alert_and_dashboard_series_exist(self):
        import re

        from _support import PKG_DIR
        e = Env()
        self.addCleanup(e.close)
        e.send(b"x")
        with self.assertRaises(ResidencyViolation):
            e.send(b"x", classification="pii", destination="us")
        text = e.svc.metrics_text()
        emitted = {re.sub(r"(_bucket|_sum|_count)$", "", ln.split("{")[0].split(" ")[0]) for ln in text.splitlines()}
        emitted |= {n.replace("_total", "") for n in emitted}
        refs = set(re.findall(r"\bpk06_[a-z_]+", (PKG_DIR / "ops/alerts/pln06-rules.yml").read_text()
                              + (PKG_DIR / "ops/dashboards/pln06.json").read_text()))
        missing = {r for r in refs if re.sub(r"(_bucket|_total)$", "", r) not in emitted}
        self.assertEqual(missing, set())
        classes = set(re.findall(r"class: (\w+)", (PKG_DIR / "ops/alerts/pln06-rules.yml").read_text()))
        self.assertTrue({"load", "degradation", "policy_rejection", "dependency_failure", "attack", "defect"} <= classes)
