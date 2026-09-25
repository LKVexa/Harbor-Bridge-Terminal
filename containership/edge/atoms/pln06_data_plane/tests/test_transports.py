"""WP #3 #21 #57 #58 #23 - adapters move real bytes; integrity, mTLS, control-path isolation."""
from __future__ import annotations

import os
import pathlib
import socket
import tempfile
import threading
import time
import unittest

from _support import tls_contexts
from pln06_data_plane import integrity as integ
from pln06_data_plane import transports as t


def dec(size, tier="bulk", locality="remote", tid="tid1", tenant="t1"):
    return {"tier": tier, "locality": locality, "size": size, "transfer_id": tid, "tenant": tenant}


class IntegrityTest(unittest.TestCase):
    def test_manifest_roundtrip_out_of_order_and_tamper(self):
        data = os.urandom(10_000)
        m = integ.build_manifest("x", data, 1000)
        parts = list(enumerate(integ.chunks(data, 1000)))[::-1]
        self.assertEqual(integ.reassemble(m, parts), data)
        bad = list(parts)
        bad[0] = (bad[0][0], b"Z" + bad[0][1][1:])
        for p in (bad, parts[:-1], parts + parts[:1], [(99, b"")]):
            with self.assertRaises(integ.IntegrityMismatch):
                integ.reassemble(m, p)
        with self.assertRaises(integ.IntegrityMismatch):
            integ.verify(integ.build_manifest("other-id", data, 1000), data[:-1])
        self.assertNotEqual(integ.build_manifest("a", data).root, integ.build_manifest("b", data).root)  # id binding

    def test_quarantine_store_bounded(self):
        q = integ.QuarantineStore(limit=2)
        for i in range(3):
            q.put(str(i), "bad", b"xx")
        self.assertEqual(sorted(q.list()), ["1", "2"])
        self.assertIsNone(q.list()["2"].get("bytes"))


class InProcessAndShmTest(unittest.TestCase):
    def test_inprocess_zero_copy_readonly_and_no_network_authority(self):
        got = []
        a = t.InProcessAdapter(lambda d, v: got.append(v))
        r = a.send(dec(5, "inline", "in_process"), b"hello")
        self.assertEqual((bytes(got[0]), r.copies), (b"hello", 0))
        self.assertTrue(got[0].readonly)
        self.assertFalse(a.grant.network)
        with self.assertRaises(t.TransportUnsupported):
            t.InProcessAdapter(lambda d, v: None, interface="pk:data-plane/transfer@2.0.0")

    def test_shared_memory_moves_bytes_and_always_unlinks(self):
        a = t.SharedMemoryAdapter(t.shm_reader, max_segment_bytes=1 << 20)
        data = os.urandom(300_000)
        r = a.send(dec(len(data), "local", "same_node"), data)
        self.assertEqual(r.bytes_moved, len(data))
        self.assertEqual(a.live_segments(), 0)
        seg = r.extra["segment"]
        from multiprocessing import shared_memory
        with self.assertRaises(FileNotFoundError):
            shared_memory.SharedMemory(name=seg)
        with self.assertRaises(t.TransportUnsupported):
            a.send(dec(2 << 20, "local", "same_node"), b"x" * (2 << 20))

        def corrupt(name, size, root):
            return b"\x00" * size
        with self.assertRaises(integ.IntegrityMismatch):
            t.SharedMemoryAdapter(corrupt).send(dec(10, "local", "same_node"), b"0123456789")
        with self.assertRaises(t.TransportError):
            a.send(dec(3, "local"), b"toolong")  # size mismatch vs admission


class VsockControlTest(unittest.TestCase):
    def test_control_path_only_carries_control_verbs(self):  # INV-36
        left, right = socket.socketpair()
        a = t.VsockControlAdapter(left)
        a.send({**dec(4, "inline", "vm_control"), "control_verb": "pause"}, b"args")
        hdr, body = t.read_control_frame(right)
        self.assertEqual((hdr["verb"], body), ("pause", b"args"))
        with self.assertRaises(t.ControlPathViolation):
            a.send({**dec(4, "inline", "vm_control"), "control_verb": "exfiltrate"}, b"args")
        with self.assertRaises(t.TransportUnsupported):
            a.send({**dec(100_000, "local", "vm_control"), "control_verb": "pause"}, b"x" * 100_000)
        self.assertEqual(a.control_bytes, 4)
        for tier_loc, prefs in t.PREFERENCE.items():
            if tier_loc[0] != "inline":
                self.assertNotIn("vsock-control", prefs, tier_loc)  # structural proof
        left.close()
        right.close()


class NetworkRpcTest(unittest.TestCase):
    def setUp(self):
        self.secret = os.urandom(32)

    def _pair(self, **kw):
        srv = t.NetworkRpcServer({"peer-a": self.secret}, ssl_context=kw.pop("srv_ctx", None)).start()
        self.addCleanup(srv.stop)
        cli = t.NetworkRpcAdapter(srv.address, peer_id=kw.pop("peer", "peer-a"), secret=kw.pop("secret", self.secret),
                                  chunk_size=4096, **kw)
        return srv, cli

    def test_bytes_cross_the_wire_verified(self):
        srv, cli = self._pair()
        data = os.urandom(50_000)
        r = cli.send(dec(len(data)), data)
        self.assertEqual(srv.received["tid1"], data)
        self.assertEqual(r.extra["protocol"], "pk06-rpc/1")

    def test_zero_byte_payload(self):
        srv, cli = self._pair()
        cli.send(dec(0), b"")
        self.assertEqual(srv.received["tid1"], b"")

    def test_bad_peer_secret_and_unknown_peer_rejected(self):
        _, cli = self._pair(secret=os.urandom(32))
        with self.assertRaises(t.TransportError):
            cli.send(dec(3), b"abc")
        _, cli2 = self._pair(peer="mallory")
        with self.assertRaises(t.TransportError):
            cli2.send(dec(3), b"abc")

    def test_server_impersonation_detected(self):
        _, cli = self._pair(server_id="expected-server")
        with self.assertRaises(t.TransportError):
            cli.send(dec(3), b"abc")

    def test_version_negotiation_refuses_unknown(self):
        _, cli = self._pair(versions=(7,))
        with self.assertRaises(t.TransportUnsupported):
            cli.send(dec(3), b"abc")

    def test_in_flight_tamper_is_quarantined(self):
        srv, cli = self._pair(tamper=lambda i, b: b[::-1] if i == 1 else b)
        with self.assertRaises(integ.IntegrityMismatch):
            cli.send(dec(20_000), os.urandom(20_000))
        self.assertIn("tid1", srv.quarantine)
        self.assertNotIn("tid1", srv.received)

    def test_deadline_and_cancel(self):
        srv, cli = self._pair()
        with self.assertRaises(t.DeadlineExceeded):
            cli.send(dec(3), b"abc", deadline=time.monotonic() - 1)
        ev = threading.Event()
        ev.set()
        with self.assertRaises(t.Cancelled):
            cli.send(dec(3), b"abc", cancel=ev)

    def test_unreachable_peer_is_retryable_transport_error(self):
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
        s.close()
        cli = t.NetworkRpcAdapter(("127.0.0.1", port), peer_id="p", secret=b"x" * 32)
        with self.assertRaises(t.TransportError) as cm:
            cli.send(dec(1), b"a")
        self.assertTrue(cm.exception.retryable)

    def test_hostile_garbage_does_not_crash_server(self):
        srv, cli = self._pair()
        for junk in (b"\xff" * 8, b"\x00\x00\x00\x05\x00\x00\x00\x00{bad}", b""):
            with socket.create_connection(srv.address) as c:
                c.sendall(junk)
        time.sleep(0.2)
        data = b"still-works"
        cli.send(dec(len(data)), data)
        self.assertEqual(srv.received["tid1"], data)

    def test_mutual_tls(self):
        ctxs = tls_contexts(pathlib.Path(tempfile.mkdtemp()))
        if ctxs is None:
            self.fail("openssl is required by the CI image for the mTLS test (no silent skip)")
        srv_ctx, cli_ctx = ctxs
        srv, cli = self._pair(srv_ctx=srv_ctx, ssl_context=cli_ctx, server_hostname="server.pk06.test")
        data = os.urandom(9000)
        r = cli.send(dec(len(data)), data)
        self.assertTrue(r.extra["tls"])
        self.assertEqual(srv.received["tid1"], data)
        import ssl
        plain = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        plain.load_verify_locations(cadata=None, cafile=None) if False else None
        with self.assertRaises((t.TransportError, t.DeadlineExceeded, ssl.SSLError)):
            t.NetworkRpcAdapter(srv.address, peer_id="peer-a", secret=self.secret, ssl_context=plain,
                                server_hostname="server.pk06.test").send(dec(3), b"abc")  # untrusted server cert


class RdmaAndSelectionTest(unittest.TestCase):
    def test_rdma_probe_and_explicit_fallback(self):
        rd = t.RdmaAdapter(sysfs="/nonexistent")
        self.assertFalse(rd.available())
        net = t.NetworkRpcAdapter(("127.0.0.1", 1), peer_id="p", secret=b"x" * 32)
        a, choice = t.select_adapter(dec(1), {"rdma": rd, "network-rpc": net})
        self.assertEqual(a.name, "network-rpc")
        self.assertEqual(choice["skipped"], [{"adapter": "rdma", "reason": "unavailable"}])
        with self.assertRaises(t.TransportUnsupported):
            t.select_adapter(dec(1), {"rdma": rd})
        with self.assertRaises(t.TransportUnsupported):
            t.select_adapter(dec(1), {"network-rpc": net}, excluded=frozenset({"network-rpc"}))
        with self.assertRaises(t.TransportUnsupported):
            t.select_adapter({"tier": "inline", "locality": "remote"}, {})


if __name__ == "__main__":
    unittest.main()
