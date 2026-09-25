"""Group A — concrete NAT traversal and transport adapters (loopback + codec level).
The kernel-NAT behaviour is exercised separately by lab/scenarios.py."""
import os
import random
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gap12_wan_resilience_and_nat_traversal.tests._covers import covers  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import (holepunch, ice, natclass, portmap, stun,  # noqa: E402
                                                        transport, turn, netenv)


class StunTest(unittest.TestCase):
    @covers("G12-A001:spec1,unit,impl-doc,txn,interfaces", "G12-H085:coverage")
    def test_binding_roundtrip_and_xor_mapped(self):
        with stun.StunServer([("127.0.0.1", 0), ("127.0.0.2", 0)]) as srv:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(("127.0.0.1", 0))
            r = stun.binding(s, srv.addresses[0], rto=0.05, rc=3, rm=2)
            self.assertTrue(r.ok)
            self.assertEqual(r.mapped, s.getsockname())
            self.assertEqual(r.other, srv.addresses[1])
            self.assertEqual(r.sends, 1)
            s.close()

    @covers("G12-A001:spec1,unit,txn")
    def test_message_type_bits_and_fingerprint_integrity(self):
        for method in (1, 3, 4, 8, 9, 0xFFF):
            for cls in range(4):
                self.assertEqual(stun.split_type(stun.msg_type(method, cls)), (method, cls))
        key = stun.long_term_key("u", "r", "p")
        m = stun.Message(stun.BINDING, stun.CLS_SUCCESS).add(stun.A_SOFTWARE, b"x")
        wire = m.encode(key, fingerprint=True)
        d = stun.decode(wire)
        self.assertTrue(stun.check_fingerprint(d))
        self.assertTrue(stun.check_integrity(d, key))
        self.assertFalse(stun.check_integrity(d, b"wrong"))
        tampered = bytearray(wire)
        tampered[25] ^= 1
        self.assertFalse(stun.check_fingerprint(stun.decode(bytes(tampered))))
        wire256 = m.encode(key, sha256=True)
        self.assertTrue(stun.check_integrity(stun.decode(wire256), key))

    @covers("G12-A001:unit,txn", "G12-A011:spec1,unit")
    def test_xor_address_ipv6_uses_transaction_id(self):
        tx = bytes(range(12))
        v = stun.encode_address("2001:db8::1", 3478, xor=True, txid=tx)
        self.assertEqual(stun.decode_address(v, xor=True, txid=tx), ("2001:db8::1", 3478))
        self.assertNotEqual(stun.decode_address(v, xor=True, txid=b"\x00" * 12)[0], "2001:db8::1")

    @covers("G12-A001:unit,txn,fault", "G12-H085:coverage")
    def test_duplicate_foreign_and_late_responses_are_discarded(self):
        with stun.StunServer([("127.0.0.1", 0)], duplicate=True) as srv:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(("127.0.0.1", 0))
            r1 = stun.binding(s, srv.addresses[0], rto=0.05, rc=3, rm=2)
            # the duplicate of r1 is now queued: the next transaction must discard it (foreign txid)
            r2 = stun.binding(s, srv.addresses[0], rto=0.05, rc=3, rm=2)
            self.assertTrue(r1.ok and r2.ok)
            self.assertGreaterEqual(r2.discarded, 1)
            s.close()

    @covers("G12-A001:spec2,unit,fault,deps", "G12-H091:impl-doc")
    def test_discovery_distinguishes_failure_classes(self):
        with stun.StunServer([("127.0.0.1", 0)]) as good, stun.StunServer([("127.0.0.1", 0)], malformed=True) as bad, \
                stun.StunServer([("127.0.0.1", 0)], wrong_mapping=True) as liar:
            d = stun.discover([good.addresses[0], liar.addresses[0]], deadline_s=2)
            self.assertEqual(d.reason, "DEP_INCONSISTENT")
            self.assertFalse(d.consistent)
            d = stun.discover([bad.addresses[0]], deadline_s=0.8)
            self.assertEqual(d.reason, "DEP_MALFORMED")
            with stun.StunServer([("127.0.0.1", 0)], fail_with=500) as broken:
                d = stun.discover([broken.addresses[0], good.addresses[0]], deadline_s=2)
                self.assertEqual(d.reason, "OK")                           # one healthy server suffices
                self.assertEqual(d.per_server[0]["reason"], "DEP_UNAVAILABLE")   # server failure named
            dead = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            dead.bind(("127.0.0.1", 0))
            d = stun.discover([dead.getsockname()], deadline_s=0.6, rto=0.05, rc=3, rm=2)
            self.assertEqual(d.reason, "NET_UDP_BLOCKED")
            dead.close()

            def resolver(host):
                raise LookupError(host)
            d = stun.discover([("stun.invalid", 3478)], resolver=resolver)
            self.assertEqual(d.reason, "DNS_TIMEOUT")
            self.assertEqual(d.per_server[0]["reason"], "DNS_NXDOMAIN")

    @covers("G12-A001:unit,txn,fault", "G12-C028:spec1")
    def test_retransmission_schedule_and_deadline(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("127.0.0.1", 0))
        sink = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sink.bind(("127.0.0.1", 0))
        t0 = time.monotonic()
        r = stun.binding(s, sink.getsockname(), rto=0.02, rc=4, rm=2)
        el = time.monotonic() - t0
        self.assertFalse(r.ok)
        self.assertEqual(r.sends, 4)
        n = 0
        sink.settimeout(0.05)
        while True:
            try:
                sink.recvfrom(2048)
                n += 1
            except socket.timeout:
                break
        self.assertEqual(n, 4)
        # sends at 0, .02, .06, .14 then wait Rm*RTO=.04  -> ~0.18 s
        self.assertLess(el, 0.6)
        r = stun.binding(s, sink.getsockname(), rto=0.5, rc=7, rm=16, deadline=time.monotonic() + 0.2)
        self.assertEqual(r.reason, "CANCELLED_DEADLINE")
        s.close()
        sink.close()

    @covers("G12-A001:unit,txn")
    def test_cancellation_event(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.bind(("127.0.0.1", 0))
        ev = threading.Event()
        threading.Timer(0.1, ev.set).start()
        t0 = time.monotonic()
        msg, res = stun.transact(s, ("127.0.0.1", 9), stun.Message(stun.BINDING, stun.CLS_REQUEST), rto=0.5, cancel=ev)
        self.assertIsNone(msg)
        self.assertEqual(res.reason, "CANCELLED_SHUTDOWN")
        self.assertLess(time.monotonic() - t0, 0.5)
        s.close()

    @covers("G12-A001:unit", "G12-D043:auth-control")
    def test_integrity_protected_server_rejects_unkeyed(self):
        key = b"k" * 16
        with stun.StunServer([("127.0.0.1", 0)], require_key=key) as srv:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.bind(("127.0.0.1", 0))
            r = stun.binding(s, srv.addresses[0], rto=0.05, rc=2, rm=2)
            self.assertEqual((r.ok, r.reason, r.error), (False, "AUTH_FAILED", 401))
            msg, res = stun.transact(s, srv.addresses[0], stun.Message(stun.BINDING, stun.CLS_REQUEST), key=key, rto=0.05, rc=2, rm=2)
            self.assertIsNotNone(msg)
            self.assertTrue(stun.check_integrity(msg, key))
            s.close()


class TurnTest(unittest.TestCase):
    @covers("G12-A002:spec1,unit,impl-doc,txn,interfaces", "G12-C040:unit")
    def test_allocate_permission_send_data_channel_teardown(self):
        with turn.TurnServer(("127.0.0.1", 0), {"alice": "pw"}) as srv:
            c = turn.TurnClient(srv.address, "alice", "pw")
            relayed = c.allocate()
            peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            peer.bind(("127.0.0.1", 0))
            pa = peer.getsockname()
            with self.assertRaises(turn.TurnError):
                c.send(pa, b"no-permission")                      # refused locally before a permission exists
            c.create_permission("127.0.0.1")
            c.send(pa, b"via-send-indication")
            self.assertEqual(peer.recvfrom(100), (b"via-send-indication", relayed))
            peer.sendto(b"back", relayed)
            self.assertEqual(c.recv(), (pa, b"back"))
            ch = c.channel_bind(pa)
            self.assertTrue(turn.CHANNEL_MIN <= ch <= turn.CHANNEL_MAX)
            c.send(pa, b"via-channel")
            self.assertEqual(peer.recvfrom(100)[0], b"via-channel")
            counters = c.counters.as_dict()
            self.assertEqual(counters["payload_out"], len(b"via-send-indication") + len(b"via-channel"))
            self.assertGreater(counters["overhead_out"], 0)
            c.close()
            c.close()                                            # idempotent
            time.sleep(0.1)
            self.assertEqual(len(srv.allocs), 0)
            peer.close()

    @covers("G12-A002:spec1,unit,fault", "G12-D047:unit,key-lifecycle,fault", "G12-H096:neg-security")
    def test_stale_nonce_and_bad_credentials(self):
        with turn.TurnServer(("127.0.0.1", 0), {"alice": "pw"}) as srv:
            c = turn.TurnClient(srv.address, "alice", "pw")
            c.allocate()
            srv.rotate_nonces()                                  # server forgets nonces -> 438 -> client retries
            self.assertGreater(c.refresh(300), 0)
            c.close()
            bad = turn.TurnClient(srv.address, "alice", "wrong")
            with self.assertRaises(turn.TurnError) as cm:
                bad.allocate()
            self.assertEqual(cm.exception.reason, "AUTH_FAILED")
            bad.close()

    @covers("G12-A002:unit", "G12-D048:resource-bounds")
    def test_quota_enforced_at_server_and_reconciled(self):
        with turn.TurnServer(("127.0.0.1", 0), {"t": "pw"}, quota_bytes={"t": 64}) as srv:
            c = turn.TurnClient(srv.address, "t", "pw")
            relayed = c.allocate()
            peer = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            peer.bind(("127.0.0.1", 0))
            peer.settimeout(0.3)
            c.create_permission("127.0.0.1")
            c.send(peer.getsockname(), b"x" * 60)
            self.assertEqual(len(peer.recvfrom(100)[0]), 60)
            c.send(peer.getsockname(), b"y" * 10)
            with self.assertRaises(socket.timeout):
                peer.recvfrom(100)
            self.assertEqual(srv.usage["t"], 60)
            c.close()
            peer.close()

    @covers("G12-A002:unit")
    def test_refresh_schedule_due(self):
        clk = [1000.0]
        with turn.TurnServer(("127.0.0.1", 0), {"a": "p"}) as srv:
            c = turn.TurnClient(srv.address, "a", "p", clock=lambda: clk[0])
            c.allocate(600)
            c.create_permission("127.0.0.1")
            self.assertEqual(c.due_refreshes()["permissions"], [])
            clk[0] += 250
            self.assertEqual(c.due_refreshes()["permissions"], ["127.0.0.1"])
            clk[0] += 300
            self.assertTrue(c.due_refreshes()["allocation"])
            c.close()

    @covers("G12-A002:unit", "G12-H094:spec1")
    def test_channeldata_framing_bounds(self):
        self.assertEqual(turn.parse_channel_data(turn.channel_data(0x4001, b"abc")), (0x4001, b"abc"))
        for bad in (b"", b"\x40\x00\x00\x09abc", b"\x30\x00\x00\x00"):
            with self.assertRaises(ValueError):
                turn.parse_channel_data(bad)
        with self.assertRaises(ValueError):
            turn.channel_data(0x5000, b"")


class IceTest(unittest.TestCase):
    def _cands(self, n, base="10.0.0.", typ="host"):
        return [ice.Candidate(typ, f"{base}{i % 250 + 1}", 5000 + i) for i in range(n)]

    @covers("G12-A003:spec1,unit,impl-doc", "G12-H085:coverage")
    def test_priorities_foundations_and_pair_formula(self):
        h = ice.Candidate("host", "10.0.0.1", 5000)
        s = ice.Candidate("srflx", "198.51.100.1", 6000, base=("10.0.0.1", 5000), server="stun1")
        r = ice.Candidate("relay", "203.0.113.5", 7000, server="turn1")
        self.assertEqual(h.priority, (126 << 24) + (65535 << 8) + 255)
        self.assertGreater(h.priority, s.priority)
        self.assertGreater(s.priority, r.priority)
        self.assertNotEqual(h.foundation, s.foundation)
        p = ice.Pair(h, r, controlling=True)
        g, d = h.priority, r.priority
        self.assertEqual(p.priority, (1 << 32) * min(g, d) + 2 * max(g, d) + 1)

    @covers("G12-A003:spec1,unit")
    def test_illegal_transitions_rejected(self):
        p = ice.Pair(ice.Candidate("host", "10.0.0.1", 1), ice.Candidate("host", "10.0.0.2", 2), True)
        with self.assertRaises(ice.IllegalTransition):
            p.move("succeeded")
        p.move("waiting")
        p.move("in-progress")
        p.move("succeeded")
        with self.assertRaises(ice.IllegalTransition):
            p.move("waiting")

    @covers("G12-A003:spec2,unit", "G12-H096:neg-security")
    def test_hostile_candidate_sets_are_bounded(self):
        a = ice.Agent(True, 1)
        a.set_candidates(self._cands(500), self._cands(500, "10.1.0."))
        self.assertLessEqual(len(a.pairs), ice.MAX_PAIRS)
        self.assertLessEqual(len(a.remote), ice.MAX_CANDIDATES)
        self.assertGreater(a.pruned, 0)
        t0 = time.monotonic()
        a.run_checks(lambda p: False)
        self.assertLess(time.monotonic() - t0, 1.0)

    @covers("G12-A003:spec1,unit")
    def test_checks_nominate_and_role_conflict_and_prflx(self):
        a = ice.Agent(True, tie_breaker=10)
        loc = [ice.Candidate("host", "10.0.0.1", 5000)]
        rem = [ice.Candidate("host", "10.9.0.1", 5000), ice.Candidate("relay", "203.0.113.9", 7000)]
        a.set_candidates(loc, rem)
        sel = a.run_checks(lambda p: p.remote.type == "relay", now=5.0)
        self.assertEqual(sel.remote.type, "relay")
        self.assertTrue(sel.nominated)
        self.assertTrue(a.consent(20.0))
        self.assertFalse(a.consent(40.0))                       # RFC 7675 consent lost after 30 s
        b = ice.Agent(True, tie_breaker=1)
        b.set_candidates(loc, rem)
        self.assertEqual(b.on_incoming_check(("10.9.9.9", 1234), loc[0], remote_controlling=True, remote_tie_breaker=99),
                         "triggered")
        self.assertFalse(b.controlling)                          # lower tie-breaker switches role
        self.assertTrue(any(c.type == "prflx" for c in b.remote))


class HolePunchTest(unittest.TestCase):
    def _pair(self, window=1.0):
        a = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        b = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        a.bind(("127.0.0.1", 0))
        b.bind(("127.0.0.1", 0))
        rv = holepunch.Rendezvous({"a": b"ka", "b": b"kb"})
        ta, tb = rv.issue("a", a.getsockname(), "b", b.getsockname(), delay=0.05, window=window)
        return a, b, ta, tb

    @covers("G12-A004:spec1,unit,impl-doc")
    def test_authenticated_simultaneous_open_loopback(self):
        a, b, ta, tb = self._pair()
        out = {}
        th = threading.Thread(target=lambda: out.setdefault("b", holepunch.punch(b, tb, ticket_key=b"kb", session_key=b"s")))
        th.start()
        ra = holepunch.punch(a, ta, ticket_key=b"ka", session_key=b"s")
        th.join()
        self.assertTrue(ra.ok and out["b"].ok)
        self.assertLessEqual(ra.sent, holepunch.MAX_PROBES)
        a.close()
        b.close()

    @covers("G12-A004:spec1,spec2,unit,fault", "G12-H096:neg-security", "G12-D046:unit")
    def test_forged_ticket_and_spoofed_packets(self):
        a, b, ta, tb = self._pair(window=0.4)
        forged = holepunch.Ticket(ta.session, ta.me, ("127.0.0.1", 9), ta.start, ta.expires, ta.tag)
        self.assertEqual(holepunch.punch(a, forged, ticket_key=b"ka", session_key=b"s").cause, "coordination")
        # b sprays packets with the wrong session key: a must not accept them
        stop = threading.Event()

        def spray():
            while not stop.is_set():
                b.sendto(b"G12P" + bytes.fromhex(ta.session) + b"\x00" * 20, a.getsockname())
                time.sleep(0.01)
        threading.Thread(target=spray, daemon=True).start()
        r = holepunch.punch(a, ta, ticket_key=b"ka", session_key=b"s")
        stop.set()
        self.assertFalse(r.ok)
        self.assertGreater(r.received_invalid, 0)
        self.assertEqual(r.cause, "nat_filtering")
        a.close()
        b.close()

    @covers("G12-A004:spec2,unit")
    def test_mapping_change_attribution(self):
        a, b, ta, tb = self._pair(window=0.6)
        other = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        other.bind(("127.0.0.1", 0))                             # peer's packets arrive from a different mapping
        stop = threading.Event()

        def from_other():
            seq = 0
            while not stop.is_set():
                other.sendto(holepunch._punch_packet(ta, b"s", seq), a.getsockname())
                seq += 1
                time.sleep(0.02)
        threading.Thread(target=from_other, daemon=True).start()
        r = holepunch.punch(a, ta, ticket_key=b"ka", session_key=b"s")
        stop.set()
        self.assertEqual(r.cause, "mapping_change")
        for s in (a, b, other):
            s.close()


class PunchAttributionNetnsTest(unittest.TestCase):
    """Runs in a private network namespace (unshare -n): no routes at all, then a local OUTPUT drop."""

    CODE = r"""
import json, socket, subprocess, sys, time
sys.path.insert(0, %r)
from gap12_wan_resilience_and_nat_traversal.wan import holepunch
sys.path.insert(0, %r); import netlab; netlab.up('lo')
rv = holepunch.Rendezvous({'a': b'ka'})
out = {}
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.bind(('127.0.0.1', 0))
ta, _ = rv.issue('a', s.getsockname(), 'a', ('192.0.2.1', 40000), delay=0.01, window=0.3)
out['no_route'] = holepunch.punch(s, ta, ticket_key=b'ka', session_key=b'x').cause
subprocess.run(['iptables', '-A', 'OUTPUT', '-p', 'udp', '-j', 'DROP'], check=True)
ta, _ = rv.issue('a', s.getsockname(), 'a', ('127.0.0.1', 9), delay=0.01, window=0.3)
out['local_drop'] = holepunch.punch(s, ta, ticket_key=b'ka', session_key=b'x').cause
print(json.dumps(out))
"""

    @covers("G12-A004:spec2,unit,fault")
    def test_local_firewall_and_unreachable_are_attributed(self):
        import json as _json
        pkg_parent = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        lab = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lab")
        r = subprocess.run(["unshare", "-n", sys.executable, "-B", "-c", self.CODE % (pkg_parent, lab)],
                           capture_output=True, text=True, timeout=30)
        if r.returncode and r.stderr.startswith("unshare:"):
            self.skipTest("private network namespace unavailable: " + r.stderr[-200:])
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        out = _json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(out, {"no_route": "unreachable", "local_drop": "local_firewall"})


class TransportTest(unittest.TestCase):
    @covers("G12-A005:spec2,unit", "G12-C028:unit")
    def test_blackholed_syn_is_bounded_and_no_sockets_leak(self):
        t0 = time.monotonic()
        r = transport.tcp_connect(("10.255.255.1", 9), deadline_s=0.3)
        self.assertEqual(r.reason, "CANCELLED_DEADLINE")
        self.assertLess(time.monotonic() - t0, 0.6)
        self.assertEqual(transport.open_sockets(), 0)

    @covers("G12-A014:unit", "G12-A005:unit")
    def test_racing_cancels_losers_and_reports_attempts(self):
        l = socket.socket()
        l.bind(("127.0.0.1", 0))
        l.listen()
        r = transport.race([("127.0.0.1", 1), ("10.255.255.1", 9), l.getsockname()], attempt_delay=0.02, deadline_s=2)
        self.assertTrue(r.ok)
        self.assertEqual(r.address, l.getsockname())
        outcomes = {a["address"]: a["outcome"] for a in r.attempts}
        self.assertEqual(outcomes["127.0.0.1:1"], "NET_REFUSED")
        self.assertEqual(outcomes["10.255.255.1:9"], "cancelled-loser")
        self.assertEqual(transport.open_sockets(), 0)
        r.sock.close()
        l.close()

    @covers("G12-A014:spec2,unit")
    def test_interleave_and_bounded_history(self):
        addrs = [("2001:db8::1", 1), ("2001:db8::2", 1), ("192.0.2.1", 1), ("192.0.2.2", 1)]
        self.assertEqual([a[0] for a in transport.interleave(addrs)], ["2001:db8::1", "192.0.2.1", "2001:db8::2", "192.0.2.2"])
        demoted = transport.interleave(addrs, history={6: 50, 4: 0})
        self.assertEqual(demoted[0][0], "192.0.2.1")
        self.assertIn("2001:db8::1", [a[0] for a in demoted])      # demoted, never starved
        with self.assertRaises(ValueError):
            transport.race(addrs, attempt_delay=10)

    @covers("G12-A016:spec4,unit")
    def test_tls_fallback_verifies_identity_with_distinct_reasons(self):
        d = tempfile.mkdtemp()
        key, crt = os.path.join(d, "k.pem"), os.path.join(d, "c.pem")
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", crt,
                        "-days", "1", "-subj", "/CN=relay.gap12.test", "-addext", "subjectAltName=DNS:relay.gap12.test"],
                       check=True, capture_output=True)
        sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        sctx.load_cert_chain(crt, key)
        ls = socket.socket()
        ls.bind(("127.0.0.1", 0))
        ls.listen()

        def serve():
            for _ in range(2):
                c, _ = ls.accept()
                try:
                    t = sctx.wrap_socket(c, server_side=True)
                    t.sendall(b"hi")
                    t.close()
                except (ssl.SSLError, OSError):
                    c.close()
        threading.Thread(target=serve, daemon=True).start()
        ok = transport.tls_connect(ls.getsockname(), "relay.gap12.test", transport.tls_context(cafile=crt))
        self.assertTrue(ok.ok, ok.reason)
        self.assertEqual(ok.sock.recv(2), b"hi")
        self.assertGreaterEqual(ok.sock.version(), "TLSv1.2")
        ok.sock.close()
        bad = transport.tls_connect(ls.getsockname(), "other.name", transport.tls_context(cafile=crt))
        self.assertEqual(bad.reason, "AUTH_TLS_CERT")
        ls.close()

    @covers("G12-A015:impl-doc")
    def test_quic_is_explicitly_unsupported_not_silently_emulated(self):
        r = transport.QuicAdapter().connect(("192.0.2.1", 443))
        self.assertEqual((r.ok, r.reason), (False, "UNSUPPORTED"))
        self.assertFalse(transport.QuicAdapter.supported)


class NatClassTest(unittest.TestCase):
    @covers("G12-A006:spec1,unit")
    def test_loopback_no_nat_is_detected_without_forcing_a_label(self):
        with stun.StunServer([("127.0.0.1", 0)]) as srv:              # no OTHER-ADDRESS server
            c = natclass.classify(srv.addresses[0], bind=("127.0.0.1", 0))
            self.assertEqual(c.mapping, "none")
            self.assertEqual(c.filtering, "undetermined")            # uncertainty is represented
            self.assertTrue(c.missing)
            self.assertEqual(c.label(), "undetermined")

    @covers("G12-A006:spec2,unit")
    def test_classification_expires_on_network_change(self):
        c = natclass.Classification("endpoint-independent", "address-and-port-dependent", {}, "fp1", 100.0)
        self.assertTrue(c.valid("fp1", 150.0))
        self.assertFalse(c.valid("fp2", 150.0))
        self.assertFalse(c.valid("fp1", 100.0 + natclass.TTL + 1))
        self.assertNotEqual(natclass.network_fingerprint({"interface": "eth0", "gateway": "a"}),
                            natclass.network_fingerprint({"interface": "eth0", "gateway": "b"}))

    @covers("G12-A007:spec1,spec2,unit,impl-doc")
    def test_cgnat_needs_multiple_indicators(self):
        one = natclass.assess_cgnat(local_address="100.64.1.2", mapped_address="198.51.100.9")
        self.assertEqual(one.verdict, "possible")                  # a single heuristic never yields "likely"
        two = natclass.assess_cgnat(local_address="192.168.1.2", mapped_address="198.51.100.9",
                                    gateway_wan_address="100.64.0.2")
        self.assertEqual(two.verdict, "likely")
        single = natclass.assess_cgnat(local_address="192.168.1.2", mapped_address="198.51.100.9",
                                       mapping_behaviour="address-and-port-dependent")
        self.assertEqual(single.verdict, "possible")
        none = natclass.assess_cgnat(local_address="192.168.1.2", mapped_address="198.51.100.9")
        self.assertEqual(none.verdict, "unlikely")
        self.assertIn("never proof of peer identity", one.note)

    @covers("G12-A012:spec1,unit")
    def test_nat64_prefix_discovery_rfc6052_vectors(self):
        vectors = {"2001:db8::/32": "2001:db8:c000:221::", "2001:db8:100::/40": "2001:db8:1c0:2:21::",
                   "2001:db8:122::/48": "2001:db8:122:c000:2:2100::", "2001:db8:122:300::/56": "2001:db8:122:3c0:0:221::",
                   "2001:db8:122:344::/64": "2001:db8:122:344:c0:2:2100:0", "2001:db8:122:344::/96": "2001:db8:122:344::c000:221"}
        for prefix, want in vectors.items():
            self.assertEqual(natclass.synthesize(prefix, "192.0.2.33"), want, prefix)
        for prefix in vectors:
            syn = natclass.synthesize(prefix, "192.0.0.170")
            self.assertEqual(natclass.discover_nat64_prefixes([syn]), [prefix])
            self.assertTrue(natclass.is_synthesized(syn, [prefix]))
        self.assertFalse(natclass.is_synthesized("2001:db8:ffff::1", ["64:ff9b::/96"]))


class PortMapTest(unittest.TestCase):
    @covers("G12-A008:unit")
    def test_pcp_codec_validation_and_epoch(self):
        req, nonce = portmap.pcp_map_request("192.168.1.10", 17, 40000, 7200)
        self.assertEqual(len(req), 60)
        resp = bytearray(60)
        struct.pack_into("!BBBBII", resp, 0, 2, 0x81, 0, 0, 7200, 1000)
        resp[24:36] = nonce
        struct.pack_into("!B3xHH", resp, 36, 17, 40000, 61000)
        resp[44:60] = b"\x00" * 10 + b"\xff\xff" + bytes([198, 51, 100, 1])
        r = portmap.pcp_parse_response(bytes(resp))
        portmap.pcp_validate(r, nonce=nonce, proto=17, internal_port=40000)
        self.assertEqual((r.external_ip, r.external_port, r.reason), ("198.51.100.1", 61000, "OK"))
        with self.assertRaises(ValueError):
            portmap.pcp_validate(r, nonce=b"x" * 12, proto=17, internal_port=40000)
        with self.assertRaises(ValueError):
            portmap.pcp_validate(r, nonce=nonce, proto=6, internal_port=40000)
        ep = portmap.EpochTracker()
        self.assertFalse(ep.observe(1000, 50.0))
        self.assertFalse(ep.observe(1010, 60.0))
        self.assertTrue(ep.observe(3, 70.0))                     # gateway rebooted

    @covers("G12-A009:spec2,unit,impl-doc")
    def test_natpmp_bounded_retry_and_gateway_scope(self):
        self.assertEqual(portmap.natpmp_map_request("udp", 40000, 40000, 3600)[:2], b"\x00\x01")
        resp = struct.pack("!BBHIHHI", 0, 129, 0, 55, 40000, 40001, 3600)
        self.assertEqual(portmap.natpmp_parse(resp)["external"], 40001)
        t0 = time.monotonic()
        r = portmap.natpmp_transact("127.0.0.1", portmap.natpmp_public_request(), attempts=3, initial=0.02)
        self.assertIsNone(r)                                       # nothing listens: bounded, then gives up
        self.assertLess(time.monotonic() - t0, 0.5)

    @covers("G12-A010:unit", "G12-H096:neg-security")
    def test_upnp_ssrf_guard_and_soap_escaping(self):
        ok = portmap.validate_igd_url("http://192.168.1.1:5000/ctl", "192.168.1.1", "192.168.1.0/24")
        self.assertTrue(ok.startswith("http://192.168.1.1"))
        for bad in ("http://169.254.169.254/latest", "https://192.168.1.1/x", "http://router.local/x",
                    "http://user:pw@192.168.1.1/", "http://192.168.1.2/ctl", "file:///etc/passwd"):
            with self.assertRaises(ValueError, msg=bad):
                portmap.validate_igd_url(bad, "192.168.1.1", "192.168.1.0/24")
        body = portmap.soap_add_port_mapping(40000, "udp", 40000, "192.168.1.10", "<script>&", 3600)
        self.assertIn("&lt;script&gt;&amp;", body)
        led = portmap.MappingLedger(enabled={"upnp"})
        led.add(portmap.Mapping("upnp", "udp", 40000, 40000, None, "192.168.1.1", 100.0))
        with self.assertRaises(ValueError):
            led.add(portmap.Mapping("upnp", "udp", 40001, 40000, None, "192.168.1.1", 100.0))
        with self.assertRaises(PermissionError):
            led.add(portmap.Mapping("pcp", "udp", 1, 1, None, "192.168.1.1", 1.0))
        self.assertEqual(len(led.gateway_changed("192.168.1.254")), 1)
        self.assertEqual(led.teardown(), [])


class Ipv6Test(unittest.TestCase):
    @covers("G12-A011:unit")
    def test_policy_eligible_ipv6_candidates(self):
        iface = netenv.Interface("eth0", 2, "ethernet", True, 1500, (),
                                 (("fe80::1", "link"), ("2001:db8::10", "global"), ("::1", "host"), ("ff02::1", "global")))
        self.assertEqual(netenv.eligible_ipv6(iface), ["2001:db8::10"])


if __name__ == "__main__":
    unittest.main()
