"""MC-003 descriptor-relative filesystem resolver: adversarial suite."""
import os, threading, unittest
import _fx
from inv13_system_interface.host import fs
from inv13_system_interface.host.errors import ErrorCode, Inv13Error


class _Base:
    use_openat2 = True

    def setUp(self):
        self._saved = fs._openat2_ok
        fs.openat2_available()
        if not self.use_openat2:
            fs._openat2_ok = False
        elif not fs._openat2_ok:
            self.skipTest("openat2 unavailable")
        self.root = _fx.tmpdir()
        self.outside = _fx.tmpdir()
        (self.outside / "secret").write_text("TOP-SECRET")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "ok.txt").write_text("fine")
        self.p = fs.Preopen("/data", str(self.root))

    def tearDown(self):
        self.p.close()
        fs._openat2_ok = self._saved

    def code(self, fn, *a):
        with self.assertRaises(Inv13Error) as cm:
            fn(*a)
        return cm.exception.code

    def test_plain_access(self):
        self.assertEqual(self.p.read_bytes("sub/ok.txt"), b"fine")
        self.assertEqual(self.p.read_bytes("./sub//ok.txt"), b"fine")
        self.p.write_bytes("new.txt", b"x")
        self.assertIn("new.txt", self.p.listdir(""))
        self.assertEqual(self.p.listdir("sub"), ["ok.txt"])
        self.p.mkdir("made")
        self.p.write_bytes("made/f", b"1", exclusive=True)
        with self.assertRaises(Inv13Error) as cm:
            self.p.write_bytes("made/f", b"1", exclusive=True)
        self.assertEqual(cm.exception.code, ErrorCode.ALREADY_EXISTS)
        self.p.unlink("made/f")

    def test_lexical_escapes(self):
        for bad in ("../secret", "sub/../../x", "/etc/passwd", "a\0b", "..", "\\x"):
            self.assertEqual(self.code(self.p.open, bad), ErrorCode.PATH_ESCAPE, bad)
        self.assertEqual(self.code(self.p.open, "a" * 256), ErrorCode.TOO_LONG)
        self.assertEqual(self.code(self.p.open, "/".join(["a"] * 200)), ErrorCode.TOO_LONG)

    def test_symlink_final_component_refused(self):
        os.symlink(self.outside / "secret", self.root / "link")
        self.assertEqual(self.code(self.p.read_bytes, "link"), ErrorCode.SYMLINK_REFUSED)

    def test_symlink_intermediate_dir_refused(self):
        os.symlink(self.outside, self.root / "dirlink")
        self.assertIn(self.code(self.p.read_bytes, "dirlink/secret"),
                      (ErrorCode.SYMLINK_REFUSED, ErrorCode.NOT_A_DIRECTORY))

    def test_relative_symlink_inside_still_refused(self):
        os.symlink("sub/ok.txt", self.root / "inner")
        self.assertEqual(self.code(self.p.read_bytes, "inner"), ErrorCode.SYMLINK_REFUSED)

    def test_host_root_rename_does_not_retarget(self):
        # after grant, renaming the host directory away and planting a new one must not change authority
        moved = self.root.with_name(self.root.name + "-moved")
        os.rename(self.root, moved)
        self.root.mkdir()
        (self.root / "planted").write_text("attacker")
        self.assertEqual(self.p.read_bytes("sub/ok.txt"), b"fine")   # still the original directory
        self.assertEqual(self.code(self.p.read_bytes, "planted"), ErrorCode.NOT_FOUND)

    def test_symlink_swap_race(self):
        # attacker flips sub2 between a real dir and a symlink to outside while we read in a loop
        (self.root / "sub2").mkdir()
        (self.root / "sub2" / "secret").write_text("inside")
        stop = threading.Event()
        def flip():
            real, tmp = self.root / "sub2", self.root / "sub2.real"
            while not stop.is_set():
                try:
                    os.rename(real, tmp); os.symlink(self.outside, real)
                    os.unlink(real); os.rename(tmp, real)
                except OSError:
                    pass
        t = threading.Thread(target=flip); t.start()
        leaks = 0
        try:
            for _ in range(3000):
                try:
                    if self.p.read_bytes("sub2/secret") == b"TOP-SECRET":
                        leaks += 1
                except Inv13Error:
                    pass
        finally:
            stop.set(); t.join()
        self.assertEqual(leaks, 0)

    def test_read_only_preopen(self):
        ro = fs.Preopen("/ro", str(self.root), read_only=True)
        try:
            self.assertEqual(self.code(ro.write_bytes, "x", b"1"), ErrorCode.POLICY_DENIED)
            self.assertEqual(self.code(ro.mkdir, "d"), ErrorCode.POLICY_DENIED)
            self.assertEqual(self.code(ro.unlink, "sub/ok.txt"), ErrorCode.POLICY_DENIED)
            self.assertEqual(ro.read_bytes("sub/ok.txt"), b"fine")
        finally:
            ro.close()

    def test_mount_crossing_refused(self):
        if os.stat("/").st_dev == os.stat("/proc").st_dev:
            self.skipTest("no distinct /proc mount")
        root = fs.Preopen("/", "/")
        try:
            self.assertIn(self.code(root.read_bytes, "proc/self/status"),
                          (ErrorCode.PATH_ESCAPE, ErrorCode.SYMLINK_REFUSED))
        finally:
            root.close()

    def test_stat_leaks_nothing(self):
        st = self.p.stat("sub/ok.txt")
        self.assertEqual(set(st), {"type", "size"})
        os.symlink("x", self.root / "l")
        self.assertEqual(self.p.stat("l")["type"], "symlink")

    def test_closed_preopen(self):
        self.p.close()
        self.assertEqual(self.code(self.p.open, "sub/ok.txt"), ErrorCode.STALE_HANDLE)


class Openat2Resolver(_Base, unittest.TestCase):
    use_openat2 = True


class WalkResolver(_Base, unittest.TestCase):
    """Portable O_NOFOLLOW component walk (used where openat2 is unavailable)."""
    use_openat2 = False


if __name__ == "__main__":
    unittest.main()
