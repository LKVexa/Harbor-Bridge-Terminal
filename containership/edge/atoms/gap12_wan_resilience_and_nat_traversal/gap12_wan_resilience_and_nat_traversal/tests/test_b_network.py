"""Group B — link, interface and routing management; DNS; captive portal; PMTU."""
import http.server
import os
import socket
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gap12_wan_resilience_and_nat_traversal.tests._covers import covers  # noqa: E402
from gap12_wan_resilience_and_nat_traversal.wan import dns, netenv  # noqa: E402


def _snap(fp_seed: str, ifs=None):
    iface = netenv.Interface("eth0", 2, "ethernet", True, 1500, (fp_seed,), ())
    return netenv.Snapshot(0.0, tuple(ifs or [iface]), (), (), False)


class SnapshotTest(unittest.TestCase):
    @covers("G12-B017:impl-doc,unit,snapshot", "G12-B018:snapshot")
    def test_real_snapshot_is_immutable_and_fingerprinted(self):
        s = netenv.snapshot()
        names = [i.name for i in s.interfaces]
        self.assertIn("lo", names)
        self.assertEqual(s.fingerprint(), netenv.snapshot().fingerprint())
        with self.assertRaises(Exception):
            s.interfaces[0].mtu = 1                                  # frozen dataclass
        kinds = {i.name: i.kind for i in s.interfaces}
        self.assertEqual(kinds["lo"], "loopback")
        self.assertTrue(all(isinstance(r.metric, int) for r in s.routes))


class WatcherTest(unittest.TestCase):
    @covers("G12-B018:impl-doc,unit,notifications,coalescing", "G12-B017:notifications,coalescing",
            "G12-B020:coalescing")
    def test_missed_events_are_reconciled_and_flaps_coalesced(self):
        state = {"v": "10.0.0.2/24"}
        w = netenv.RouteWatcher(sample=lambda: _snap(state["v"]), full_interval=30,
                                debounce=netenv.Debounce(min_stable=2, hold_down=5))
        self.assertIsNotNone(w.tick(0))                                # initial publish
        state["v"] = "10.0.0.3/24"                                     # change with NO event delivered
        self.assertIsNone(w.tick(10))
        self.assertIsNotNone(w.tick(31))                               # periodic reconcile notices it...
        self.assertEqual(w.published.interfaces[0].ipv4, ("10.0.0.3/24",))
        # flapping: A/B/A/B every 0.5 s never publishes
        published = 0
        for i in range(20):
            state["v"] = "A" if i % 2 else "B"
            published += w.on_event(100 + i * 0.5) is not None
        self.assertEqual(published, 0)
        self.assertGreater(w.debounce.suppressed, 5)


class DebounceTest(unittest.TestCase):
    @covers("G12-B020:impl-doc,unit,coalescing", "G12-C033:anti-oscillation")
    def test_min_stability_and_hold_down(self):
        d = netenv.Debounce(min_stable=2, hold_down=10, value="wifi")
        self.assertFalse(d.feed("cell", 0))
        self.assertFalse(d.feed("cell", 1))
        self.assertTrue(d.feed("cell", 2.5))
        self.assertFalse(d.feed("wifi", 3))
        self.assertFalse(d.feed("wifi", 6))                            # stable but inside hold-down
        self.assertTrue(d.feed("wifi", 13))


class UplinkTest(unittest.TestCase):
    @covers("G12-B019:impl-doc,unit")
    def test_priority_metering_policy_and_stickiness(self):
        ups = [netenv.Uplink("eth", 1, True), netenv.Uplink("lte", 2, True, metered=True, cost_per_gb=5),
               netenv.Uplink("wifi", 1, True)]
        self.assertEqual(netenv.select_uplink(ups)[0].name, "eth")
        self.assertEqual(netenv.select_uplink(ups, current="wifi")[0].name, "wifi")   # tie -> keep current
        down = [netenv.Uplink("eth", 1, False), ups[1]]
        self.assertEqual(netenv.select_uplink(down), (None, "POLICY_MECHANISM_DISABLED"))
        self.assertEqual(netenv.select_uplink(down, allow_metered=True)[0].name, "lte")
        self.assertIsNone(netenv.select_uplink(down, allow_metered=True, max_cost_per_gb=1)[0])
        self.assertIsNone(netenv.select_uplink([netenv.Uplink("x", 1, True, policy_allowed=False)])[0])

    @covers("G12-B021:impl-doc,unit")
    def test_migration_rule(self):
        self.assertFalse(netenv.should_migrate(1.0, 1.1, current_healthy=True))
        self.assertTrue(netenv.should_migrate(1.0, 1.2, current_healthy=True))
        self.assertTrue(netenv.should_migrate(1.0, 0.1, current_healthy=False))
        self.assertTrue(netenv.should_migrate(1.0, 1.01, current_healthy=True, session_active=False))


class PinningTest(unittest.TestCase):
    @covers("G12-B022:impl-doc,unit,pinning", "G12-B017:pinning", "G12-B019:pinning")
    def test_source_pinning(self):
        s = netenv.pinned_socket("127.0.0.2")
        self.assertTrue(netenv.verify_pinning(s, "127.0.0.2"))
        s.close()
        s = netenv.pinned_socket("127.0.0.1", interface="lo")
        self.assertTrue(netenv.verify_pinning(s, "127.0.0.1"))
        s.close()
        with self.assertRaises(OSError):
            netenv.pinned_socket("203.0.113.77")                        # not a local address: refuse, don't fall back


class CaptiveTest(unittest.TestCase):
    @covers("G12-B024:impl-doc,unit", "G12-H093:impl-doc")
    def test_captive_portal_verdicts_against_live_http(self):
        mode = {"m": "open"}

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):
                if mode["m"] == "open":
                    self.send_response(204)
                    self.end_headers()
                elif mode["m"] == "portal":
                    self.send_response(302)
                    self.send_header("Location", "http://portal.example/login")
                    self.end_headers()
                else:
                    body = b"<html>Welcome to Hotel WiFi</html>"
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
        srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        import http.client as hc

        def probe():
            c = hc.HTTPConnection(*srv.server_address, timeout=2)
            c.request("GET", "/generate_204")
            r = c.getresponse()
            body = r.read()
            return netenv.captive_verdict(r.status, body, redirected_to=r.getheader("Location"))
        self.assertEqual(probe(), "open")
        mode["m"] = "portal"
        self.assertEqual(probe(), "captive")
        mode["m"] = "walled"
        self.assertEqual(probe(), "captive")
        srv.shutdown()
        self.assertEqual(netenv.captive_verdict(None, None), "blocked")


class FirewallDiagTest(unittest.TestCase):
    @covers("G12-B027:impl-doc,unit,observe-only", "G12-B017:observe-only", "G12-B024:observe-only")
    def test_diagnostics_never_mutate(self):
        out = netenv.diagnose_firewall({"udp_ok": False, "tcp_ok": True, "stun_ok": True, "inbound_ok": False})
        codes = [c for c, _ in out["findings"]]
        self.assertEqual(codes, ["NET_UDP_BLOCKED", "NET_FILTERED"])
        self.assertEqual(out["mutations"], [])
        with open(netenv.__file__) as fh:
            src = fh.read()
        for forbidden in ("iptables", "nft ", "netsh", "route add", "RTM_NEWROUTE", "resolv.conf\", \"w"):
            self.assertNotIn(forbidden, src)                           # observation module has no mutation path


class PmtuTest(unittest.TestCase):
    @covers("G12-B025:spec1,unit,impl-doc,fault")
    def test_blackhole_search_and_expiry(self):
        true_mtu = 1420
        p = netenv.Plpmtud(base=1200, max_size=9000)
        found = p.search(lambda size: size <= true_mtu, now=0.0)
        self.assertLessEqual(found, true_mtu)
        self.assertGreater(found, true_mtu - 16)
        self.assertTrue(p.blackhole)                                  # oversize probes vanished silently
        self.assertEqual(p.pmtu(10.0), found)
        self.assertEqual(p.pmtu(10_000.0), 1200)                      # cached value expires to the safe base

    @covers("G12-B025:spec2,unit", "G12-B026:impl-doc,unit")
    def test_encapsulation_never_assumes_physical_mtu(self):
        self.assertEqual(netenv.usable_mtu(1500, ["wireguard"]), 1420)
        self.assertEqual(netenv.usable_mtu(1500, ["ipsec", "turn_send"], path_mtu=1400), 1400 - 73 - 36)
        self.assertEqual(netenv.mss_for(1420), 1380)
        with self.assertRaises(ValueError):
            netenv.usable_mtu(600, ["wireguard"])


class DnsTest(unittest.TestCase):
    @covers("G12-B023:spec1,unit,impl-doc,fault", "G12-H091:impl-doc,unit")
    def test_ordering_negative_cache_and_serve_stale(self):
        clk = [0.0]
        with dns.DnsServer(records={"relay.example": ["192.0.2.7"]}, ttl=10) as good, dns.DnsServer(mode="silent") as dead:
            r = dns.Resolver([dead.address, good.address], query_timeout=0.2, race_delay=0.05, overall_timeout=1,
                             clock=lambda: clk[0] if clk[0] else __import__("time").monotonic())
            a = r.resolve("relay.example")
            self.assertEqual((a.addresses, a.source), (["192.0.2.7"], "fresh"))
            self.assertEqual(r.preferred, good.address)                   # sticky-best next time
            nx = r.resolve("missing.example")
            self.assertEqual((nx.rcode, nx.reason), ("NXDOMAIN", "DNS_NXDOMAIN"))
            hits = good.hits
            self.assertEqual(r.resolve("missing.example").source, "negative-cache")
            self.assertEqual(good.hits, hits)
        # both resolvers now gone: stale answer is served (bounded), then refused
        r.servers = [dead.address]
        clk[0] = __import__("time").monotonic() + 30
        st = r.resolve("relay.example")
        self.assertEqual(st.source, "stale")
        clk[0] += r.max_stale + 100
        self.assertEqual(r.resolve("relay.example").reason, "DNS_TIMEOUT")

    @covers("G12-B023:spec2,unit", "G12-H091:impl-doc", "G12-H096:neg-security")
    def test_spoofed_answers_rejected_and_queries_capped(self):
        with dns.DnsServer(mode="spoof") as spoof, dns.DnsServer(mode="servfail") as sf:
            r = dns.Resolver([spoof.address], overall_timeout=0.5, query_timeout=0.4)
            self.assertEqual(r.resolve("x.example").reason, "DNS_MISMATCH")
            r = dns.Resolver([sf.address], overall_timeout=0.5)
            self.assertEqual(r.resolve("x.example").reason, "DNS_SERVFAIL")
            r = dns.Resolver([sf.address] * 10, overall_timeout=0.5, max_concurrent=2, query_timeout=0.2, race_delay=0.01)
            r.resolve("y.example")
            self.assertLessEqual(r.queries_sent, 10)                        # one attempt per resolver, never multiplied

    @covers("G12-B023:spec1,unit")
    def test_split_horizon(self):
        with dns.DnsServer(records={"db.corp.internal": ["10.0.0.5"]}) as internal, dns.DnsServer() as public:
            r = dns.Resolver([public.address], zones={"corp.internal": [internal.address]})
            self.assertEqual(r.resolve("db.corp.internal").addresses, ["10.0.0.5"])
            self.assertEqual(public.hits, 0)                                 # internal names never leak

    @covers("G12-B023:unit", "G12-H094:spec1")
    def test_decoder_rejects_malformed(self):
        for bad in (b"", b"\x00" * 11, b"\x12\x34\x81\x80\x00\x01\x00\x01\x00\x00\x00\x00\xc0\x0c"):
            with self.assertRaises(ValueError):
                dns.decode_response(bad)
        with self.assertRaises(ValueError):
            dns.encode_query("a" * 64 + ".example", "A", 1)


if __name__ == "__main__":
    unittest.main()
