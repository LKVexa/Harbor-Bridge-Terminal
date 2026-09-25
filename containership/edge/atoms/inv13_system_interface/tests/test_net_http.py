"""MC-007 socket capability, MC-018 outgoing HTTP (SSRF/TLS/redirect)."""
import http.server, os, shutil, socket, ssl, subprocess, tempfile, threading, unittest
import _fx
from inv13_system_interface.host.net import NetPolicy, NetRule, SocketProvider
from inv13_system_interface.host.http_out import HttpOutgoing, HttpPolicy
from inv13_system_interface.host.errors import ErrorCode, Inv13Error


def serve(handler_cls, ctx=None):
    srv = http.server.HTTPServer(("127.0.0.1", 0), handler_cls)
    if ctx:
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/redir-private"):
            self.send_response(302); self.send_header("Location", "http://10.0.0.1/"); self.end_headers(); return
        if self.path.startswith("/redir-loop"):
            self.send_response(302); self.send_header("Location", "/redir-loop"); self.end_headers(); return
        if self.path.startswith("/big"):
            self.send_response(200); self.end_headers(); self.wfile.write(b"x" * 5000); return
        self.send_response(200); self.end_headers(); self.wfile.write(b"ok")


class Sockets(unittest.TestCase):
    def setUp(self):
        self.srv = socket.socket(); self.srv.bind(("127.0.0.1", 0)); self.srv.listen()
        self.port = self.srv.getsockname()[1]

    def tearDown(self):
        self.srv.close()

    def test_no_ambient_network(self):
        sp = SocketProvider(NetPolicy())
        for fn in (lambda: sp.connect("127.0.0.1", self.port), lambda: sp.listen("127.0.0.1", 0),
                   lambda: sp.resolve("localhost")):
            with self.assertRaises(Inv13Error) as cm:
                fn()
            self.assertEqual(cm.exception.code, ErrorCode.DESTINATION_DENIED)
        self.assertEqual(sp.open_count(), 0)

    def test_explicit_connect_and_quota(self):
        pol = NetPolicy([NetRule("connect", "tcp", "127.0.0.1/32", (self.port, self.port))], max_sockets=2)
        sp = SocketProvider(pol)
        a, b = sp.connect("127.0.0.1", self.port), sp.connect("127.0.0.1", self.port)
        with self.assertRaises(Inv13Error) as cm:
            sp.connect("127.0.0.1", self.port)
        self.assertEqual(cm.exception.code, ErrorCode.QUOTA_EXCEEDED)
        a.close(); b.close()
        sp.connect("127.0.0.1", self.port).close()
        for ip, port, proto in (("127.0.0.2", self.port, "tcp"), ("127.0.0.1", self.port + 1, "tcp"),
                                ("127.0.0.1", self.port, "udp"), ("::1", self.port, "tcp"), ("not-an-ip", 1, "tcp")):
            with self.assertRaises(Inv13Error):
                sp.connect(ip, port, proto)

    def test_listen_requires_bind_and_listen(self):
        only_bind = SocketProvider(NetPolicy([NetRule("bind", "tcp", "127.0.0.1/32", (0, 65535))]))
        with self.assertRaises(Inv13Error):
            only_bind.listen("127.0.0.1", 0)
        both = SocketProvider(NetPolicy([NetRule("bind", "tcp", "127.0.0.1/32", (0, 65535)),
                                         NetRule("listen", "tcp", "127.0.0.1/32", (0, 65535))]))
        both.listen("127.0.0.1", 0).close()

    def test_dns_allowlist_and_ip_laundering(self):
        sp = SocketProvider(NetPolicy([NetRule("connect", "tcp", "93.184.0.0/16", (443, 443))],
                                      dns_names=frozenset({"*.example.com"})), resolver=lambda h: ["127.0.0.1"])
        self.assertEqual(sp.resolve("api.example.com"), ["127.0.0.1"])
        with self.assertRaises(Inv13Error):
            sp.resolve("evil.com")
        with self.assertRaises(Inv13Error):   # resolved IP still has to pass connect policy
            sp.connect(sp.resolve("api.example.com")[0], 443)


class Http(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = serve(H)
        cls.port = cls.srv.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def client(self, **kw):
        pol = HttpPolicy(allowed_hosts=frozenset({"svc.test", "10.0.0.1"}), allow_http_hosts=frozenset({"svc.test", "10.0.0.1"}),
                         allow_private=frozenset({"127.0.0.1/32"}), ports=frozenset({self.port, 80, 443}), **kw)
        return HttpOutgoing(pol, resolver=lambda h: ["127.0.0.1"] if h == "svc.test" else [h])

    def test_allowed_request(self):
        r = self.client().request("GET", f"http://svc.test:{self.port}/")
        self.assertEqual((r.status, r.body), (200, b"ok"))

    def test_ssrf_defences(self):
        c = self.client()
        for url in (f"http://svc.test:{self.port}/redir-private", f"http://svc.test:{self.port}/redir-loop",
                    "http://169.254.169.254/latest/meta-data", f"http://user:pw@svc.test:{self.port}/",
                    f"ftp://svc.test:{self.port}/", "http://other.test/", f"http://svc.test:{self.port + 1}/"):
            with self.assertRaises(Inv13Error, msg=url):
                c.request("GET", url)
        rebinding = HttpOutgoing(HttpPolicy(allowed_hosts=frozenset({"x.test"})), resolver=lambda h: ["93.184.216.34", "10.1.1.1"])
        with self.assertRaises(Inv13Error):
            rebinding.vet("https://x.test/")
        v6 = HttpOutgoing(HttpPolicy(allowed_hosts=frozenset({"x.test"})), resolver=lambda h: ["::ffff:127.0.0.1"])
        with self.assertRaises(Inv13Error):
            v6.vet("https://x.test/")

    def test_limits(self):
        with self.assertRaises(Inv13Error) as cm:
            self.client(max_response_bytes=100).request("GET", f"http://svc.test:{self.port}/big")
        self.assertEqual(cm.exception.code, ErrorCode.QUOTA_EXCEEDED)
        with self.assertRaises(Inv13Error):
            self.client(max_request_bytes=1).request("POST", f"http://svc.test:{self.port}/", body=b"12")
        with self.assertRaises(Inv13Error):
            self.client(methods=frozenset({"GET"})).request("DELETE", f"http://svc.test:{self.port}/")

    def test_tls_verification_cannot_be_disabled(self):
        ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
        with self.assertRaises(Inv13Error):
            HttpOutgoing(HttpPolicy(allowed_hosts=frozenset()), ssl_context=ctx)

    @unittest.skipUnless(shutil.which("openssl"), "openssl CLI needed for self-signed fixture")
    def test_untrusted_certificate_refused(self):
        d = tempfile.mkdtemp()
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=svc.test",
                        "-keyout", f"{d}/k.pem", "-out", f"{d}/c.pem"], check=True, capture_output=True)
        sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); sctx.load_cert_chain(f"{d}/c.pem", f"{d}/k.pem")
        srv = serve(H, sctx)
        try:
            port = srv.server_address[1]
            c = HttpOutgoing(HttpPolicy(allowed_hosts=frozenset({"svc.test"}), allow_private=frozenset({"127.0.0.1/32"}),
                                        ports=frozenset({port})), resolver=lambda h: ["127.0.0.1"])
            with self.assertRaises(Inv13Error) as cm:
                c.request("GET", f"https://svc.test:{port}/")
            self.assertEqual(cm.exception.code, ErrorCode.DESTINATION_DENIED)
            trusted = ssl.create_default_context(cafile=f"{d}/c.pem")
            c2 = HttpOutgoing(c.policy, resolver=lambda h: ["127.0.0.1"], ssl_context=trusted)
            self.assertEqual(c2.request("GET", f"https://svc.test:{port}/").body, b"ok")
        finally:
            srv.shutdown()


if __name__ == "__main__":
    unittest.main()
