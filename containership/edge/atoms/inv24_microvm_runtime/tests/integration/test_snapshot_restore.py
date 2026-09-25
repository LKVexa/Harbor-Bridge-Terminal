"""MC-004-A01/A02: Firecracker snapshot create/load on a real host."""
import unittest

from ._realhost import need_real_host


@need_real_host
class RealSnapshotTest(unittest.TestCase):
    def test_pause_snapshot_restore(self):
        self.skipTest("NOT_TESTED: adapter snapshot API calls (/snapshot/create, /snapshot/load) await approved Firecracker version")
