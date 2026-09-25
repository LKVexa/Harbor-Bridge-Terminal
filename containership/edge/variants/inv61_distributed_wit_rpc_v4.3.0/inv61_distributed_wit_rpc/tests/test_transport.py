"""M03/M08/M10/M29 - real sockets: loopback, mutual TLS, two-process, faults,
drain, cancellation, reconnect and retry."""
import json
import os
import pathlib
import secrets
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from _harness import KV, ROOT, PKG_DIR, Fixture, codec, key, make_pki, negotiation, resilience, security, transport


def start(fx, **kw):
    return transport.RpcServer(fx.svc, "127.0.0.1", 0, **kw).start()


class LoopbackTest(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.srv = start(self.fx)
        self.cli = transport.RpcClient(*self.srv.address, self.fx.ckey)

    def tearDown(self):
        self.cli.close()
        self.srv.close()

    def test_calls_over_socket(self):
        r = self.cli.call(KV, "put", [{"key": "k", "value": 42, "tags": ["x"]}, "strong"], idempotency_key="p1")
        self.assertEqual(r["status"], "ok")
        self.assertEqual(self.cli.call(KV, "get", ["k"])["value"], 42)
        self.assertEqual(self.cli.chosen, (2, 1))
        big = bytes(range(256)) * 200
        self.assertEqual(bytes(self.cli.call(KV, "echo", [list(big)])["value"]), big)

    def test_multiplexed_concurrent_calls(self):
        out, errs = [], []

        def worker(i):
            try:
                out.append(self.cli.call(KV, "slow", [30])["status"])
            except Exception as e:
                errs.append(e)
        ts = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        t0 = time.monotonic()
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(errs, [])
        self.assertEqual(out, ["ok"] * 20)
        self.assertLess(time.monotonic() - t0, 20 * 0.03)  # ran concurrently, not serially

    def test_server_deadline(self):
        r = self.cli.call(KV, "slow", [800], deadline_s=0.1)
        self.assertEqual(r["status"], "deadline-exceeded")

    def test_cancellation_propagates(self):
        ev = threading.Event()
        threading.Timer(0.05, ev.set).start()
        t0 = time.monotonic()
        r = self.cli.call_once(KV, "slow", [2000], deadline_s=5, cancel=ev)
        self.assertIn(r["status"], {"cancelled", "ok"})
        self.assertLess(time.monotonic() - t0, 1.5)

    def test_hostile_bytes_close_connection_before_dispatch(self):
        cases = [b"GET / HTTP/1.1\r\n\r\n", codec.HEADER.pack(codec.MAGIC, 2, 1, codec.KIND_HELLO, 0, 2**31),
                 codec.pack_frame(codec.KIND_REQUEST, b"x", 2, 1), b"WRPC"]
        for payload in cases:
            with self.subTest(p=payload[:12]):
                s = socket.create_connection(self.srv.address, timeout=2)
                s.sendall(payload)
                try:
                    s.shutdown(socket.SHUT_WR)
                    got = s.recv(100)
                except ConnectionResetError:
                    got = b""
                self.assertEqual(got, b"")  # closed (FIN or RST), no response
                s.close()
        self.assertEqual(self.fx.svc.metrics.counter("inv61_requests_total", interface="-", function="-",
                                                     status="malformed-frame"), 0)

    def test_unknown_peer_handshake_rejected(self):
        c = transport.RpcClient(*self.srv.address, key("ghost"))
        with self.assertRaises((transport.TransportError, OSError, negotiation.NegotiationError)):
            c.connect()

    def test_version_negotiation_down_to_2_0(self):
        c = transport.RpcClient(*self.srv.address, self.fx.ckey, offered=((2, 0),))
        self.assertEqual(c.call(KV, "get", ["zz"])["status"], "ok")
        self.assertEqual(c.chosen, (2, 0))
        c.close()
        c3 = transport.RpcClient(*self.srv.address, self.fx.ckey, offered=((3, 0),), min_accepted=(3, 0))
        with self.assertRaises((transport.TransportError, OSError, negotiation.NegotiationError)):
            c3.connect()


class TlsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = pathlib.Path(tempfile.mkdtemp())
        cls.pki = make_pki(cls.d)

    def test_mutual_tls_and_identity_binding(self):
        fx = Fixture()
        stls = transport.server_tls_context(*self.pki["node-1"], self.pki["ca"])
        srv = start(fx, tls=stls, require_tls=True)
        try:
            good = transport.RpcClient(*srv.address, fx.ckey, server_hostname="localhost",
                                       tls=transport.client_tls_context(*self.pki["client-a"], self.pki["ca"]))
            self.assertEqual(good.call(KV, "get", ["a"])["status"], "ok")
            good.close()
            # valid cert for "mallory" but HMAC key of client-a: identity mismatch
            bad = transport.RpcClient(*srv.address, fx.ckey, server_hostname="localhost",
                                      tls=transport.client_tls_context(*self.pki["mallory"], self.pki["ca"]))
            self.assertEqual(bad.call(KV, "get", ["a"])["status"], "unauthenticated")
            bad.close()
            # plaintext client against TLS server
            plain = transport.RpcClient(*srv.address, fx.ckey, connect_timeout_s=1)
            with self.assertRaises((OSError, transport.TransportError, codec.CodecError)):
                plain.connect()
            # client without a certificate
            nocert = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); nocert.load_verify_locations(self.pki["ca"])
            c = transport.RpcClient(*srv.address, fx.ckey, tls=nocert, server_hostname="localhost")
            with self.assertRaises((OSError, ssl.SSLError, transport.TransportError)):
                c.connect(); c.call_once(KV, "get", ["a"])
        finally:
            srv.close()

    def test_require_tls_without_context_refused(self):
        with self.assertRaises(ValueError):
            transport.RpcServer(Fixture().svc, require_tls=True)


class TwoProcessTest(unittest.TestCase):
    """Independent OS processes over TCP (cross-host semantics on loopback)."""

    def test_two_processes(self):
        d = pathlib.Path(tempfile.mkdtemp())
        k = key("client-a")
        (d / "keys.json").write_text(json.dumps([{"key_id": k.key_id, "principal": k.principal,
                                                  "secret_hex": k.secret.hex()}]))
        (d / "audit.key").write_bytes(secrets.token_bytes(32))
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        p = subprocess.Popen([sys.executable, "-m", f"{PKG_DIR.name}.demo_node", "--keyring", str(d / "keys.json"),
                              "--audit-key-file", str(d / "audit.key"), "--workdir", str(d / "run"),
                              "--port-file", str(d / "port")], env=env, stderr=subprocess.PIPE)
        try:
            for _ in range(200):
                if (d / "port").exists() and (d / "port").read_text():
                    break
                time.sleep(0.02)
            port = int((d / "port").read_text())
            c = transport.RpcClient("127.0.0.1", port, k)
            self.assertEqual(c.call(KV, "put", [{"key": "x", "value": 5, "tags": []}, "eventual"],
                                    idempotency_key="i1")["status"], "ok")
            self.assertEqual(c.call(KV, "get", ["x"])["value"], 5)
            c.close()
        finally:
            p.terminate()
            _, err = p.communicate(timeout=15)
        self.assertEqual(p.returncode, 0, err[-2000:])
        ok, n, _ = security.AuditLog.verify(d / "run" / "audit.jsonl", (d / "audit.key").read_bytes())
        self.assertTrue(ok)


class FaultInjectionTest(unittest.TestCase):
    """M29: server loss mid-call, reconnect, overload shedding, drain, conn cap."""

    def test_reconnect_after_server_restart_and_ambiguous_completion(self):
        fx = Fixture()
        srv = start(fx)
        host, port = srv.address
        c = transport.RpcClient(host, port, fx.ckey,
                                retry=resilience.RetryPolicy(max_attempts=30, base_s=0.02, cap_s=0.05))
        self.assertEqual(c.call(KV, "get", ["a"])["status"], "ok")
        threading.Timer(0.05, srv.close).start()
        r = c.call_once(KV, "slow", [500], deadline_s=3)
        self.assertEqual(r["status"], "unavailable")
        self.assertTrue(r.get("ambiguous"))
        # non-idempotent call is NOT retried
        r = c.call(KV, "get", ["a"], deadline_s=0.3)
        self.assertEqual(r["attempts"], 1)
        # restart on the same port; idempotent call retries through reconnect
        def restart():
            time.sleep(0.2)
            fx.svc.draining = fx.svc.health.draining = False
            self.srv2 = transport.RpcServer(fx.svc, host, port).start()
        threading.Thread(target=restart).start()
        r = c.call(KV, "get", ["a"], deadline_s=5, idempotency_key="g1")
        self.assertEqual(r["status"], "ok")
        self.assertGreater(r["attempts"], 1)
        c.close(); self.srv2.close()

    def test_overload_is_shed_with_retryable_status(self):
        fx = Fixture(admission=resilience.AdmissionController(max_inflight=2, per_tenant_inflight=2,
                                                              tenant_rate=1000, tenant_burst=1000))
        srv = start(fx)
        c = transport.RpcClient(*srv.address, fx.ckey)
        res = []
        ts = [threading.Thread(target=lambda: res.append(c.call_once(KV, "slow", [200])["status"])) for _ in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(res.count("ok"), 2)
        self.assertEqual(res.count("overloaded"), 6)
        c.close(); srv.close()

    def test_graceful_drain_waits_for_inflight(self):
        fx = Fixture()
        srv = start(fx)
        c = transport.RpcClient(*srv.address, fx.ckey)
        box = []
        t = threading.Thread(target=lambda: box.append(c.call_once(KV, "slow", [300])))
        t.start(); time.sleep(0.08)
        self.assertTrue(srv.drain(timeout_s=5))
        t.join()
        self.assertEqual(box[0]["status"], "ok")
        self.assertEqual(fx.svc.health.readiness()["status"], "fail")

    def test_connection_cap_and_handshake_timeout(self):
        fx = Fixture()
        srv = start(fx, max_connections=2, handshake_timeout_s=0.3)
        socks = [socket.create_connection(srv.address) for _ in range(2)]
        time.sleep(0.1)
        extra = socket.create_connection(srv.address); extra.settimeout(2)
        self.assertEqual(extra.recv(10), b"")  # refused over cap
        time.sleep(0.5)  # silent sockets hit the handshake timeout
        self.assertEqual(srv.active_connections(), 0)
        for s in socks + [extra]:
            s.close()
        srv.close()

    def test_truncated_and_slowloris_frames(self):
        fx = Fixture()
        srv = start(fx, handshake_timeout_s=0.3)
        s = socket.create_connection(srv.address)
        s.sendall(codec.HEADER.pack(codec.MAGIC, 2, 1, codec.KIND_HELLO, 0, 100) + b"x" * 10)
        s.settimeout(3)
        t0 = time.monotonic()
        self.assertEqual(s.recv(10), b"")
        self.assertLess(time.monotonic() - t0, 2)
        s.close(); srv.close()


if __name__ == "__main__":
    unittest.main()
