"""P2-20: adjacent-layer integration tests (INV-13, INV-15, GAP-15).

These need the real adjacent packages on PK_ADJACENT_PATH.  Outside a release job
they SKIP (visible as skips, never as passes); with INV14_RELEASE=1 an absent
layer is a FAILURE (checklist xx.29).  The expected surfaces are the minimum the
INV-14 contract depends on: INV-13 supplies pollables, INV-15 is the migration
target, GAP-15 certifies runtimes.
"""
import importlib, os, sys, unittest
from _support import PKG_DIR
import polling, migration

ADJ = os.environ.get("PK_ADJACENT_PATH")
RELEASE = os.environ.get("INV14_RELEASE") == "1"
if ADJ:
    sys.path.insert(0, ADJ)
LAYERS = {"INV-13": "inv13_system_interface", "INV-15": "inv15_new_asynchronous_abi",
          "GAP-15": "gap15_runtime_compatibility_certification"}


def _load(name):
    try:
        return importlib.import_module(LAYERS[name])
    except ModuleNotFoundError:
        if RELEASE:
            raise AssertionError(f"{name} ({LAYERS[name]}) absent in a release job: FAIL, not skip")
        raise unittest.SkipTest(f"{name} not supplied (set PK_ADJACENT_PATH)")


class C20Adjacent(unittest.TestCase):
    def test_c20_inv13_pollables_are_accepted_by_inv14(self):
        inv13 = _load("INV-13")
        make = getattr(inv13, "make_pollable")
        p = make("net", "t/c/i")
        self.assertIsInstance(p, polling.Pollable)
        p.signal()
        self.assertEqual(polling.PollSet("t/c/i").poll([p], timeout_ticks=5)["ready"], ["net"])

    def test_c20_inv15_future_satisfies_bridge_protocol(self):
        inv15 = _load("INV-15")
        fut = inv15.Future()
        fp = migration.FuturePollable("f", "t/c/i", fut)
        fut.set_result(None)
        self.assertTrue(polling.PollSet("t/c/i").poll([fp], timeout_ticks=100)["ready"])

    def test_c20_gap15_certifies_runtime_supporting_legacy_poll(self):
        gap15 = _load("GAP-15")
        self.assertIn("wasi:io/poll@0.2.0", gap15.certified_interfaces())


if __name__ == "__main__":
    unittest.main()
