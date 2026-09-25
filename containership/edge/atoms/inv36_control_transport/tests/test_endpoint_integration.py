"""Full-stack integration, disaster/partition and short soak/fleet scenarios (fake byte streams)."""
from __future__ import annotations

import time
import unittest

import _util  # noqa: F401

from inv36_control_transport import quarantine as Q
from inv36_control_transport.audit_log import verify_log
from inv36_control_transport.endpoint import ConnectionLimit, EndpointConfig
from inv36_control_transport.errors import ErrorCode, Inv36Error
from inv36_control_transport.handshake import HandshakeError
from inv36_control_transport.health import AdmissionController, OverloadError
from inv36_control_transport.messages import ControlMessage
from inv36_control_transport.policy import AuthzError
from inv36_control_transport.stream import StreamError
from inv36_control_transport.testing import World, connect_pair
from inv36_control_transport.tools import soak as SOAK
from inv36_control_transport.transport import AuthFailure, Replay


def handlers(log):
    def revoke(p, m):
        log.append((p.subject, m.type_name, m.body))
        return ControlMessage.of("STATUS_QUERY", m.tenant, b"ack:" + m.body)
    return {"LEASE_REVOKE": revoke, "LEASE_RENEW": revoke, "HEARTBEAT": lambda p, m: None}


class FullStackTest(unittest.TestCase):
    """REQ: INV36-REQ-001, INV36-REQ-002, INV36-REQ-012, INV36-REQ-033, INV36-REQ-041 | KIND: integration"""

    def setUp(self):
        self.w = World()
        self.audit = self.w.audit_log()
        self.log = []
        self.host = self.w.endpoint("host:h1", "host_agent", "t1", audit=self.audit, handlers=handlers(self.log))
        self.guest = self.w.endpoint("guest:g1", "guest_agent", "t1", audit=self.audit)

    def test_round_trip_authorization_and_audit(self):
        s, c = connect_pair(self.host, self.guest)
        c.send(ControlMessage.of("LEASE_RENEW", "t1", b"lease-1"))
        s.serve_one()
        self.assertEqual(c.receive().body, b"ack:lease-1")
        c.send(ControlMessage.of("DRAIN", "t1"))       # guests may not drain (explicit deny)
        with self.assertRaises(AuthzError):
            s.serve_one()
        c.send(ControlMessage.of("LEASE_RENEW", "t2"))  # cross-tenant
        with self.assertRaises(AuthzError) as cm:
            s.serve_one()
        self.assertEqual(cm.exception.code, ErrorCode.AUTHZ_CROSS_TENANT)
        self.assertEqual(self.log, [("guest:g1", "LEASE_RENEW", b"lease-1")])
        r = verify_log(self.audit.path, {"audit#1": self.w.audit_key.public_bytes()}, expected_head=self.audit.head)
        self.assertTrue(r.ok, r.to_dict())
        ex = self.host.explain()
        self.assertEqual(ex["active_sessions"], 1)
        self.assertTrue(any(d["kind"] == "authz" for d in ex["recent_decisions"]))
        self.assertIn("inv36_authz_denials_total", self.host.metrics.exposition())

    def test_unauthenticated_bytes_never_reach_dispatch(self):
        s, c = connect_pair(self.host, self.guest)
        frame = c.session.seal(ControlMessage.of("LEASE_REVOKE", "t1", b"x").encode())
        tampered = bytearray(frame)
        tampered[-1] ^= 1
        c.conn.send_record(2, bytes(tampered))
        with self.assertRaises(AuthFailure):
            s.serve_one()
        self.assertEqual(self.log, [])
        self.assertTrue(s.closed)  # integrity failure is terminal for the channel

    def test_duplicate_op_id_not_dispatched_twice(self):
        s, c = connect_pair(self.host, self.guest)
        m = ControlMessage.of("LEASE_RENEW", "t1", b"lease-9")
        c.send(m)
        s.serve_one()
        c.receive()
        c.send(m)  # same op_id, new frame sequence (application-level replay)
        self.assertIsNone(s.serve_one())
        self.assertEqual(len(self.log), 1)

    def test_frame_replay_closes_channel(self):
        s, c = connect_pair(self.host, self.guest)
        frame = c.session.seal(ControlMessage.of("HEARTBEAT", "t1").encode())
        c.conn.send_record(2, frame)
        s.serve_one()
        c.conn.send_record(2, frame)
        with self.assertRaises(Replay):
            s.serve_one()
        self.assertTrue(s.closed)

    def test_rekey_trigger_by_frames_and_age(self):
        self.host.cfg = EndpointConfig(session_max_frames=3)
        s, c = connect_pair(self.host, self.guest)
        for _ in range(3):
            c.send(ControlMessage.of("HEARTBEAT", "t1"))
            s.serve_one()
        self.assertTrue(s.needs_rekey())
        self.host.cfg = EndpointConfig(session_max_age_s=0.0)
        self.assertTrue(s.needs_rekey())

    def test_session_limits_per_process_and_tenant(self):
        self.host.cfg = EndpointConfig(max_sessions=10, max_sessions_per_tenant=1)
        connect_pair(self.host, self.guest)
        other = self.w.endpoint("guest:g2", "guest_agent", "t1")
        with self.assertRaises((ConnectionLimit, HandshakeError, StreamError, Inv36Error)):
            connect_pair(self.host, other)
        third = self.w.endpoint("guest:g3", "guest_agent", "t3")
        connect_pair(self.host, third)

    def test_overload_does_not_bypass_authorization(self):
        self.host.admission = AdmissionController(high_water=2, low_water=1, per_tenant=100)
        self.host.admission.depth = 50
        s, c = connect_pair(self.host, self.guest)
        c.send(ControlMessage.of("DRAIN", "t1"))
        with self.assertRaises(AuthzError):   # denied before admission is even consulted
            s.serve_one()
        c.send(ControlMessage.of("HEARTBEAT", "t1"))
        with self.assertRaises(OverloadError):
            s.serve_one()

    def test_drain_stops_new_sessions_and_closes_existing(self):
        s, c = connect_pair(self.host, self.guest)
        self.assertEqual(self.host.drain(), 1)
        self.assertTrue(s.closed)
        with self.assertRaises(StreamError):
            c.receive()               # peer observes CLOSE / EOF
        with self.assertRaises((HandshakeError, StreamError, Inv36Error)):
            connect_pair(self.host, self.guest)
        self.assertTrue(self.host.explain()["draining"])

    def test_repeated_auth_failures_isolate_peer(self):
        self.host.penalty.limit = 2
        for _ in range(2):
            s, c = connect_pair(self.host, self.guest)
            bad = bytearray(c.session.seal(b"x"))
            bad[-1] ^= 1
            c.conn.send_record(2, bytes(bad))
            with self.assertRaises(AuthFailure):
                s.serve_one()
        with self.assertRaises((HandshakeError, StreamError, Inv36Error)):
            connect_pair(self.host, self.guest)   # isolated for the cooldown window

    def test_explain_reports_version_protocols_config(self):
        from inv36_control_transport import config as C
        st = C.ConfigStore()
        st.activate(C.dev_profile(), source="t", author="t")
        self.host.config_store = st
        ex = self.host.explain()
        self.assertEqual(ex["protocols"]["frame"], "PK_CTRL_FRAME/2")
        self.assertEqual(ex["config"]["digest"], st.current.digest)
        self.assertIn("LEASE_REVOKE", ex["capabilities"]["operations"])

    def test_trace_context_propagation(self):
        s, c = connect_pair(self.host, self.guest)
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        c.send(ControlMessage.of("LEASE_RENEW", "t1", b"x", traceparent=tp))
        s.serve_one()
        self.assertTrue(any(sp["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736" for sp in self.host.tracer.spans))


class QuarantineIntegrationTest(unittest.TestCase):
    """REQ: INV36-REQ-027, INV36-REQ-028 | KIND: integration"""

    def test_terminate_active_sessions_and_block_new(self):
        w = World()
        audit = w.audit_log()
        qr = w.quarantine_registry(audit=audit.listener())
        host = w.endpoint("host:h1", "host_agent", "t1", quarantine=qr, audit=audit)
        g1 = w.endpoint("guest:bad", "guest_agent", "t1")
        g2 = w.endpoint("guest:good", "guest_agent", "t1")
        s1, c1 = connect_pair(host, g1)
        s2, c2 = connect_pair(host, g2)
        d = Q.Directive("q1", 1, "apply", Q.Scope.PEER, "guest:bad", Q.Action.TERMINATE, time.time(), 600, "alice",
                        ("alice", "bob"), "incident")
        t0 = time.monotonic()
        qr.submit(Q.sign_directive(w.quarantine_authority, d), actor="alice")
        self.assertLess(time.monotonic() - t0, 1.0)
        self.assertTrue(s1.closed)
        self.assertEqual(s1.session.send_seq, 0)
        with self.assertRaises(Exception):
            s1.session.seal(b"x")  # keys discarded
        self.assertFalse(s2.closed)
        with self.assertRaises((HandshakeError, Q.QuarantineError, StreamError, Inv36Error)):
            connect_pair(host, g1)
        self.assertLess(qr.last_activation_latency_s, 1.0)

    def test_operation_block_during_traffic(self):
        w = World()
        qr = w.quarantine_registry()
        host = w.endpoint("host:h1", "host_agent", "t1", quarantine=qr, handlers=handlers([]))
        s, c = connect_pair(host, w.endpoint("guest:g", "guest_agent", "t1"))
        d = Q.Directive("q2", 1, "apply", Q.Scope.OPERATION, "LEASE_RENEW", Q.Action.BLOCK_OPERATIONS, time.time(),
                        600, "alice", ("alice", "bob"), "bug")
        qr.submit(Q.sign_directive(w.quarantine_authority, d), actor="alice")
        c.send(ControlMessage.of("LEASE_RENEW", "t1"))
        with self.assertRaises(Q.QuarantineError):
            s.serve_one()
        c.send(ControlMessage.of("HEARTBEAT", "t1"))
        s.serve_one()


class DisasterPartitionTest(unittest.TestCase):
    """REQ: INV36-REQ-026, INV36-REQ-038, INV36-REQ-018, INV36-REQ-017 | KIND: integration"""

    def test_peer_restart_asymmetric_failure_forces_fresh_session(self):
        w = World()
        host = w.endpoint("host:h1", "host_agent", "t1", handlers=handlers([]))
        guest = w.endpoint("guest:g1", "guest_agent", "t1")
        s, c = connect_pair(host, guest)
        old_sid = s.session.session_id
        c.conn.stream.reset()      # guest crashes; host still believes the session is live
        with self.assertRaises(StreamError):
            s.serve_one()
        self.assertTrue(s.closed)
        s2, c2 = connect_pair(host, guest)
        self.assertNotEqual(s2.session.session_id, old_sid)
        stale = c.session  # old client state cannot be replayed into the new session
        frame = stale.seal(ControlMessage.of("HEARTBEAT", "t1").encode()) if not stale.closed else None
        if frame:
            c2.conn.send_record(2, frame)
            with self.assertRaises(AuthFailure):
                s2.serve_one()

    def test_mid_frame_reset_and_stalled_peer(self):
        w = World()
        host = w.endpoint("host:h1", "host_agent", "t1")
        guest = w.endpoint("guest:g1", "guest_agent", "t1")
        s, c = connect_pair(host, guest, timeout=0.5)
        payload = c.session.seal(ControlMessage.of("HEARTBEAT", "t1", b"x" * 500).encode())
        c.conn.stream.send(b"\x02\x00" + len(payload).to_bytes(4, "big") + payload[:100], 1)
        c.conn.stream.reset()
        with self.assertRaises(StreamError):
            s.serve_one()
        s2, c2 = connect_pair(host, guest, timeout=0.2)
        with self.assertRaises(StreamError):   # stalled peer: bounded by read deadline
            s2.serve_one()

    def test_identity_outage_blocks_new_sessions_keeps_existing(self):
        w = World()
        host = w.endpoint("host:h1", "host_agent", "t1", handlers=handlers([]))
        guest = w.endpoint("guest:g1", "guest_agent", "t1")
        s, c = connect_pair(host, guest)
        w.revocations.available = False
        with self.assertRaises((HandshakeError, StreamError, Inv36Error)):
            connect_pair(host, w.endpoint("guest:g2", "guest_agent", "t1"))
        c.send(ControlMessage.of("LEASE_RENEW", "t1", b"still-works"))
        s.serve_one()
        self.assertEqual(c.receive().body, b"ack:still-works")

    def test_prolonged_partition_then_reconnect(self):
        w = World()
        host = w.endpoint("host:h1", "host_agent", "t1")
        guest = w.endpoint("guest:g1", "guest_agent", "t1")
        sids = set()
        for _ in range(5):
            s, c = connect_pair(host, guest)
            sids.add(s.session.session_id)
            c.conn.stream.reset()
            s.close(graceful=False)
        self.assertEqual(len(sids), 5)

    def test_key_rotation_and_revocation_under_active_traffic(self):
        w = World()
        host = w.endpoint("host:h1", "host_agent", "t1", handlers=handlers([]))
        guest = w.endpoint("guest:g1", "guest_agent", "t1")
        s, c = connect_pair(host, guest)
        w.epochs.rotate(2, grace_s=60)
        c.send(ControlMessage.of("LEASE_RENEW", "t1"))
        s.serve_one()                        # live session unaffected by scheduled rotation
        c.receive()
        s2, _ = connect_pair(host, guest)    # epoch-1 creds still valid inside grace
        w.epochs.revoke(1, reason="emergency")
        with self.assertRaises((HandshakeError, StreamError, Inv36Error)):
            connect_pair(host, guest)        # emergency revocation blocks new sessions immediately
        host.identity, host.credential = w.identity("host:h1", "host_agent", "t1", epoch=2)
        guest.identity, guest.credential = w.identity("guest:g1", "guest_agent", "t1", epoch=2)
        connect_pair(host, guest)

    def test_historical_ciphertext_not_openable_by_other_sessions_or_tenants(self):
        w = World()
        host = w.endpoint("host:h1", "host_agent", "t1")
        g1 = w.endpoint("guest:a", "guest_agent", "t1")
        g2 = w.endpoint("guest:b", "guest_agent", "t2")
        s1, c1 = connect_pair(host, g1)
        s2, c2 = connect_pair(host, g2)
        frame = c1.session.seal(b"tenant-1 secret")
        with self.assertRaises(AuthFailure):
            s2.session.open(frame)


class SoakFleetShortTest(unittest.TestCase):
    """REQ: INV36-REQ-037, INV36-REQ-030 | KIND: performance"""

    def test_short_soak_no_leaks(self):
        r = SOAK.soak(2.0, window_s=0.5)
        self.assertGreater(r["frames"], 100)
        self.assertFalse(r["leak_suspected"], r["growth"])

    def test_small_fleet_fair_and_bounded(self):
        r = SOAK.fleet(24, tenants=6)
        self.assertTrue(r["fair"])
        self.assertTrue(r["bounded_cardinality"])
        self.assertGreater(r["reconnect_delay_spread"]["stdev_s"], 0)


if __name__ == "__main__":
    unittest.main()
