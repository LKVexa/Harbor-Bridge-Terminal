"""Zero-copy shared-memory transport (C010, C011, C031, C066) incl. a real
cross-process producer."""
from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import unittest

from _support import PKG_DIR, ROOT, pkg

shm = pkg.shm_transport


class ProbeTest(unittest.TestCase):
    def test_probe_reports_scope_honestly(self):
        caps = shm.probe()
        self.assertIn(caps["mode"], ("zero_copy_intra_host", "copy_fallback"))
        self.assertFalse(caps["host_guest"])  # never claimed

    def test_selection_fails_closed(self):
        with self.assertRaises(pkg.CodedError) as cm:
            shm.select_transport("shm", False, {"shared_memory": False})
        self.assertEqual(cm.exception.code, "unsupported_capability")
        self.assertRaises(pkg.CodedError, shm.select_transport, "auto", True, {"shared_memory": False})
        self.assertRaises(pkg.CodedError, shm.select_transport, "auto", False, {"shared_memory": True}, host_guest_required=True)
        self.assertEqual(shm.select_transport("auto", False, {"shared_memory": False}), "copy")


@unittest.skipUnless(shm.probe()["shared_memory"], "REQUIRED-CAPABILITY: shared memory absent; certification env must provide it")
class ZeroCopyTest(unittest.TestCase):
    def setUp(self):
        self.key = os.urandom(32)
        self.data = os.urandom(3 * 65536 + 100)
        self.m = pkg.manifest(self.data, 65536)
        self.r = shm.SharedRegion(len(self.data), transfer_id="tx", tenant="acme", key=self.key)

    def tearDown(self):
        self.r.close()

    def test_zero_data_plane_copies(self):
        c = shm.CopyCounter()
        shm.produce_into(self.r.buf, self.data, c)
        rx = shm.ZeroCopyReceiver(self.m, self.r.buf, counter=c)
        for i in range(self.m["chunk_count"]):
            rx.commit(i)
        v = rx.object_view()
        self.assertTrue(v.readonly)
        self.assertEqual(bytes(v), self.data)
        self.assertEqual(c.data_plane_copies, 0)
        self.assertEqual(c.ingress_copies, 1)
        v.release()

    def test_corrupt_chunk_and_post_commit_mutation(self):
        buf = self.r.buf
        buf[: len(self.data)] = self.data
        rx = shm.ZeroCopyReceiver(self.m, buf)
        buf[10] ^= 1
        self.assertRaises(pkg.DigestMismatch, rx.commit, 0)
        buf[10] ^= 1
        for i in range(self.m["chunk_count"]):
            rx.commit(i)
        buf[70000] ^= 1  # tamper after commit (TOCTOU)
        with self.assertRaises(pkg.CodedError) as cm:
            rx.object_view()
        self.assertEqual(cm.exception.code, "object_digest_mismatch")

    def test_descriptor_binding(self):
        d = self.r.descriptor()
        a = shm.attach(d, key=self.key, transfer_id="tx", tenant="acme")
        a.close()
        for tamper in ({"tenant": "evil"}, {"transfer_id": "other"}, {"size": d["size"] + 1}, {"binding": "0" * 64},
                       {"abi": "X/9"}):
            bad = {**d, **tamper}
            with self.assertRaises(pkg.CodedError):
                shm.attach(bad, key=self.key, transfer_id=bad.get("transfer_id"), tenant=bad.get("tenant"))
        self.assertRaises(pkg.CodedError, shm.attach, d, key=os.urandom(32), transfer_id="tx", tenant="acme")

    def test_revoked_descriptor(self):
        d = self.r.descriptor()
        self.r.revoke()
        with self.assertRaises(pkg.CodedError) as cm:
            shm.attach(d, key=self.key, transfer_id="tx", tenant="acme")
        self.assertEqual(cm.exception.code, "authorization_denied")

    def test_cross_process_producer(self):
        d = self.r.descriptor()
        script = textwrap.dedent(f"""
            import sys; sys.path.insert(0, {str(ROOT)!r})
            from {PKG_DIR.name} import shm_transport as shm
            d = {d!r}
            a = shm.attach(d, key=bytes.fromhex({self.key.hex()!r}), transfer_id='tx', tenant='acme')
            data = sys.stdin.buffer.read()
            a.buf[:len(data)] = data
            a.close()
        """)
        r = subprocess.run([sys.executable, "-c", script], input=self.data, capture_output=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        rx = shm.ZeroCopyReceiver(self.m, self.r.buf)
        for i in range(self.m["chunk_count"]):
            rx.commit(i)
        v = rx.object_view()
        self.assertEqual(bytes(v), self.data)
        v.release()

    def test_mapped_quota(self):
        with self.assertRaises(pkg.CodedError) as cm:
            shm.SharedRegion(1 << 20, transfer_id="x", tenant="t", key=self.key, max_mapped=1024)
        self.assertEqual(cm.exception.code, "quota_exceeded")


if __name__ == "__main__":
    unittest.main()
