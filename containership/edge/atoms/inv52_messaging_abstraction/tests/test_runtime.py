"""Standalone runtime tests that do not require pk_core or network access."""
import importlib
import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)


class RuntimeTest(unittest.TestCase):
    def test_version_and_import_without_pk_core(self):
        self.assertEqual(pkg.__version__, "4.3.0")
        self.assertEqual((PKG_DIR / "VERSION").read_text().strip(), "4.3.0")
        self.assertTrue(callable(pkg.envelope))
        self.assertTrue(pkg.PubSub)

    def test_envelope_ids_are_unique_and_complete(self):
        a = pkg.envelope("shop", "order.created", {"id": 1})
        b = pkg.envelope("shop", "order.created", {"id": 2})
        self.assertNotEqual(a["id"], b["id"])
        self.assertTrue(a["time"])
        pkg.validate_envelope(a)

    def test_authorization_and_source_spoofing(self):
        ps = pkg.PubSub()
        ps.allow("orders", "shop")
        with self.assertRaises(pkg.TopicDenied):
            ps.publish("mallory", "orders", pkg.envelope("mallory", "x", {}))
        with self.assertRaises(pkg.TopicDenied):
            ps.publish("shop", "orders", pkg.envelope("other", "x", {}))

    def test_routing_dead_letter_and_predicate_isolation(self):
        ps = pkg.PubSub()
        ps.allow("orders", "shop")
        good = []
        ps.subscribe("orders", lambda m: (_ for _ in ()).throw(RuntimeError("boom")), [])
        ps.subscribe("orders", lambda m: m["data"]["total"] > 10, good)
        self.assertEqual(ps.publish("shop", "orders", pkg.envelope("shop", "order", {"total": 20})), 1)
        self.assertEqual(len(good), 1)
        self.assertEqual(len(ps.dead_letter), 0)
        self.assertEqual(ps.metrics()["route_errors"], 1)

    def test_subscribers_receive_isolated_copies(self):
        ps = pkg.PubSub()
        ps.allow("t", "a")
        first, second = [], []
        ps.subscribe("t", lambda m: True, first)
        ps.subscribe("t", lambda m: True, second)
        original = pkg.envelope("a", "e", {"n": 1})
        ps.publish("a", "t", original)
        first[0]["data"]["n"] = 99
        original["data"]["n"] = 77
        self.assertEqual(second[0]["data"]["n"], 1)

    def test_dead_letter_is_bounded(self):
        ps = pkg.PubSub(max_dead_letters=2)
        ps.allow("t", "a")
        for n in range(3):
            ps.publish("a", "t", pkg.envelope("a", "e", {"n": n}))
        self.assertEqual(len(ps.dead_letter), 2)
        self.assertEqual(ps.dropped_dead_letters, 1)
        self.assertEqual(ps.metrics()["dead_letter_evictions"], 1)

    def test_route_limit_is_enforced(self):
        ps = pkg.PubSub(max_routes_per_topic=1)
        ps.subscribe("t", lambda m: True, [])
        with self.assertRaises(pkg.ResourceLimitExceeded):
            ps.subscribe("t", lambda m: True, [])

    def test_concurrent_publish_updates_metrics_safely(self):
        ps = pkg.PubSub()
        ps.allow("t", "a")
        sink = []
        ps.subscribe("t", lambda m: True, sink)
        threads = [threading.Thread(target=ps.publish, args=("a", "t", pkg.envelope("a", "e", {"n": n}))) for n in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(sink), 50)
        self.assertEqual(ps.metrics()["published"], 50)
        self.assertEqual(ps.metrics()["delivered"], 50)

    def test_structured_failures_for_invalid_inputs(self):
        with self.assertRaises(pkg.IncompleteEnvelope) as ctx:
            pkg.envelope("", "event", {})
        self.assertEqual(ctx.exception.code, "PK_MSG_ENVELOPE_INVALID")
        with self.assertRaises(pkg.InvalidArgument) as ctx:
            pkg.PubSub(max_dead_letters=0)
        self.assertEqual(ctx.exception.code, "PK_MSG_ARGUMENT_INVALID")
        with self.assertRaises(pkg.InvalidSubscription):
            pkg.PubSub().subscribe("t", object(), [])

    def test_dead_letter_reasons_for_no_route_and_handler_failure(self):
        ps = pkg.PubSub()
        ps.allow("t", "a")
        self.assertEqual(ps.publish("a", "t", pkg.envelope("a", "e", {})), 0)
        self.assertEqual(ps.dead_letter[-1]["reason"], "no route matched")

        class BrokenSink:
            def append(self, message):
                raise RuntimeError("sink down")

        ps.subscribe("t", lambda m: True, BrokenSink())
        self.assertEqual(ps.publish("a", "t", pkg.envelope("a", "e", {})), 0)
        self.assertEqual(ps.dead_letter[-1]["reason"], "handler failure")
        self.assertEqual(ps.dead_letter[-1]["errors"][0]["error_type"], "RuntimeError")


if __name__ == "__main__":
    unittest.main()
