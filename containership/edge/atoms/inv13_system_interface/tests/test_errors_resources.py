"""MC-011 resource table, MC-012 error taxonomy."""
import errno, json, unittest
import _fx  # noqa: F401
from inv13_system_interface.host.errors import ErrorCode, Inv13Error, all_codes, from_os_error, Category
from inv13_system_interface.host.resources import ResourceTable


class ErrorTaxonomy(unittest.TestCase):
    def test_codes_unique_and_complete(self):
        codes = all_codes()
        self.assertEqual(len({c["code"] for c in codes}), len(codes))
        self.assertTrue(all(c["category"] in {x.value for x in Category} for c in codes))

    def test_no_host_detail_crosses(self):
        e = from_os_error(OSError(errno.ENOENT, "No such file", "/srv/secret/tenant-a/key.pem"))
        blob = json.dumps(e.to_guest()) + str(e) + repr(e)
        self.assertNotIn("/srv", blob)
        self.assertNotIn("No such file", blob)
        self.assertEqual(e.code, ErrorCode.NOT_FOUND)

    def test_errno_mapping(self):
        for en, code in [(errno.ELOOP, ErrorCode.SYMLINK_REFUSED), (errno.EMFILE, ErrorCode.QUOTA_EXCEEDED),
                         (errno.EXDEV, ErrorCode.PATH_ESCAPE), (12345, ErrorCode.INTERNAL)]:
            self.assertEqual(from_os_error(OSError(en, "x")).code, code)

    def test_code_stability_snapshot(self):
        # additive-only: these codes are published in the WIT contract and may never change value
        self.assertEqual(ErrorCode.CAP_NOT_GRANTED.value, "E1001")
        self.assertEqual(ErrorCode.PATH_ESCAPE.value, "E1003")
        self.assertEqual(ErrorCode.STALE_HANDLE.value, "E2005")
        self.assertEqual(ErrorCode.QUOTA_EXCEEDED.value, "E4001")


class ResourceTableTest(unittest.TestCase):
    def test_stale_handle_after_drop_and_reuse(self):
        t = ResourceTable(4)
        h = t.push("fd", 1)
        t.drop(h)
        h2 = t.push("fd", 2)
        self.assertEqual(h & 0xFFFFF, h2 & 0xFFFFF)  # same slot reused
        with self.assertRaises(Inv13Error) as cm:
            t.get(h, "fd")
        self.assertEqual(cm.exception.code, ErrorCode.STALE_HANDLE)
        self.assertEqual(t.get(h2, "fd"), 2)

    def test_type_confusion_and_invalid(self):
        t = ResourceTable(4)
        h = t.push("socket", object())
        for bad in (0, -1, True, "1", 1 << 40, h + 7):
            with self.assertRaises(Inv13Error):
                t.get(bad, "socket")
        with self.assertRaises(Inv13Error) as cm:
            t.get(h, "fd")
        self.assertEqual(cm.exception.code, ErrorCode.WRONG_HANDLE_TYPE)

    def test_borrow_rules(self):
        t = ResourceTable(8)
        h = t.push("fd", 5)
        b = t.borrow(h)
        with self.assertRaises(Inv13Error):
            t.drop(b)            # borrower cannot drop
        with self.assertRaises(Inv13Error):
            t.drop(h)            # owner cannot drop while borrowed
        t.release_borrow(b)
        t.drop(h)
        self.assertEqual(len(t), 0)

    def test_exhaustion_and_leaks_and_teardown(self):
        closed = []
        t = ResourceTable(4)
        hs = [t.push("fd", i, on_drop=closed.append) for i in range(3)]
        t.borrow(hs[0])
        with self.assertRaises(Inv13Error) as cm:
            t.push("fd", 9)
        self.assertEqual(cm.exception.code, ErrorCode.QUOTA_EXCEEDED)
        self.assertEqual(len(t.leak_report()), 4)
        self.assertEqual(t.close_all(), 4)
        self.assertEqual(sorted(closed), [0, 1, 2])
        self.assertEqual(t.leak_report(), [])

    def test_transfer_kills_source(self):
        a, b = ResourceTable(2), ResourceTable(2)
        h = a.push("fd", 7)
        h2 = b.push("x", 0) and a.transfer(h, b)
        with self.assertRaises(Inv13Error):
            a.get(h, "fd")
        self.assertEqual(b.get(h2, "fd"), 7)


if __name__ == "__main__":
    unittest.main()
