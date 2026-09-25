"""MC04 / MC09 / MC13 / MC62 — unpack pipeline, snapshotter, adversarial layers."""
import gzip
import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path

from inv02_container_substrate import rootfs as rf
from inv02_container_substrate.registry import IntegrityError, LimitExceeded, ValidationError
from inv02_container_substrate.tests.fixtures import make_tar


class UnpackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "root"

    def tearDown(self):
        self.tmp.cleanup()

    def test_basic_unpack_and_diff_id(self):
        blob, did = make_tar([("etc/", "dir"), ("etc/.hidden", "file", b"h"), ("bin/sh", "file", b"#!", 0o4755),
                              ("lnk", "sym", "etc/.hidden"), ("hard", "hard", "etc/.hidden")])
        stats = rf.apply_layer(self.root, blob, diff_id=did)
        self.assertEqual(stats["diff_id"], did)
        self.assertEqual((self.root / "etc/.hidden").read_bytes(), b"h")
        self.assertEqual(os.stat(self.root / "bin/sh").st_mode & 0o7777, 0o755)  # setuid stripped
        self.assertEqual(os.readlink(self.root / "lnk"), "etc/.hidden")
        with self.assertRaises(IntegrityError):
            rf.apply_layer(Path(self.tmp.name) / "r2", blob, diff_id="sha256:" + "0" * 64)

    def test_whiteouts_and_opaque(self):
        l1, _ = make_tar([("d/", "dir"), ("d/a", "file", b"a"), ("d/b", "file", b"b"), ("x", "file", b"x"),
                          ("o/", "dir"), ("o/old", "file", b"o")])
        l2, _ = make_tar([("d/.wh.a", "file", b""), (".wh.x", "file", b""), ("o/.wh..wh..opq", "file", b""),
                          ("o/new", "file", b"n")])
        rf.apply_layer(self.root, l1)
        rf.apply_layer(self.root, l2)
        self.assertFalse((self.root / "d/a").exists())
        self.assertTrue((self.root / "d/b").exists())
        self.assertFalse((self.root / "x").exists())
        self.assertEqual(sorted(p.name for p in (self.root / "o").iterdir()), ["new"])

    def test_adversarial_layers_refused(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        cases = {
            "absolute": [("/etc/passwd", "file", b"x")],
            "traversal": [("../../escape", "file", b"x")],
            "symlink-parent": [("evil", "sym", str(outside)), ("evil/pwned", "file", b"x")],
            "hardlink-outside": [("h", "hard", "../../../etc/passwd")],
            "device": [("dev/mem", "chr", None)],
        }
        for name, ents in cases.items():
            with self.subTest(name):
                blob, _ = make_tar(ents)
                with self.assertRaises((rf.UnsafeLayer, IntegrityError)):
                    rf.apply_layer(Path(self.tmp.name) / f"r-{name}", blob)
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlink_then_overwrite_replaces_link_not_target(self):
        target = Path(self.tmp.name) / "victim"
        target.write_bytes(b"safe")
        l1, _ = make_tar([("f", "sym", str(target))])
        l2, _ = make_tar([("f", "file", b"payload")])
        rf.apply_layer(self.root, l1)
        rf.apply_layer(self.root, l2)
        self.assertEqual(target.read_bytes(), b"safe")
        self.assertEqual((self.root / "f").read_bytes(), b"payload")

    def test_decompression_bomb_and_entry_limits(self):
        blob, _ = make_tar([("big", "file", b"\0" * 2_000_000)])
        self.assertLess(len(blob), 20_000)
        with self.assertRaises(LimitExceeded):
            rf.apply_layer(self.root, blob, policy=rf.UnpackPolicy(max_uncompressed_bytes=1_000_000))
        many, _ = make_tar([(f"f{i}", "file", b"") for i in range(50)])
        with self.assertRaises(LimitExceeded):
            rf.apply_layer(Path(self.tmp.name) / "r3", many, policy=rf.UnpackPolicy(max_entries=10))

    def test_zstd_and_garbage(self):
        with self.assertRaises(rf.UnsupportedCompression):
            rf.apply_layer(self.root, b"\x28\xb5\x2f\xfd" + b"\0" * 20)
        with self.assertRaises(rf.UnsafeLayer):
            rf.apply_layer(self.root, gzip.compress(b"not a tar at all" * 100))

    def test_uncompressed_layer(self):
        blob, did = make_tar([("a", "file", b"1")], gz=False)
        self.assertEqual(rf.apply_layer(self.root, blob)["diff_id"], did)


class SnapshotterTests(unittest.TestCase):
    def test_chain_and_prepare(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = rf.Snapshotter(tmp)
            l1, d1 = make_tar([("a", "file", b"1")])
            l2, d2 = make_tar([("b", "file", b"2"), (".wh.a", "file", b"")])
            cid = s.unpack_image([l1, l2], [d1, d2])
            self.assertEqual(cid, rf.chain_ids([d1, d2])[-1])
            self.assertEqual(rf.chain_ids([d1])[0], d1)
            self.assertTrue(s.has(rf.chain_ids([d1])[0]))
            again = s.unpack_image([l1, l2], [d1, d2])  # idempotent, cached
            self.assertEqual(again, cid)
            active = s.prepare("c1", cid)
            self.assertEqual(sorted(p.name for p in active.iterdir()), ["b"])
            (active / "b").write_bytes(b"changed")  # writes do not leak into committed layers
            self.assertEqual((s._committed(cid) / "b").read_bytes(), b"2")
            with self.assertRaises(ValidationError):
                s.prepare("c1", cid)
            s.remove("c1")
            self.assertEqual(s.usage()["active"], 0)
            bad = make_tar([("../x", "file", b"")])[0]
            with self.assertRaises(rf.UnsafeLayer):
                s.unpack_image([bad], ["sha256:" + "1" * 64])
            self.assertFalse(any(p.name.startswith(".unpack") for p in (Path(tmp) / "active").iterdir()))


class BindMountPolicyTests(unittest.TestCase):
    def test_bind_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "data"
            src.mkdir()
            opts = rf.validate_bind_mount(str(src), "/data", [], (tmp,))
            self.assertIn("ro", opts)
            self.assertIn("nosuid", opts)
            for bad_src, dest in (("/etc", "/x"), ("/var/run/docker.sock", "/s"), ("/", "/host"), (str(src), "rel"),
                                  (str(src), "/a/../b"), ("/usr", "/usr")):
                with self.subTest(bad_src), self.assertRaises(ValidationError):
                    rf.validate_bind_mount(bad_src, dest, [], (tmp,))


if __name__ == "__main__":
    unittest.main()
