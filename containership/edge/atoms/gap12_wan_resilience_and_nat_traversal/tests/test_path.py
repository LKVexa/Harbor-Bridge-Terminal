"""Standalone unit tests for the GAP-12 path state machine (stdlib only)."""
import importlib.util
import pathlib
import sys
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gap12_path_under_test", PKG_DIR / "path.py")
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)

ATTEMPT_HISTORY = MOD.ATTEMPT_HISTORY
BACKOFF_CEILING = MOD.BACKOFF_CEILING
PROBE_FRESHNESS = MOD.PROBE_FRESHNESS
Partitioned = MOD.Partitioned
Path = MOD.Path


class PathBehaviorTest(unittest.TestCase):
    def test_new_path_is_unknown_not_confirmed_partition(self):
        state = Path("peer-a", _jitter_seed=1).state(0)
        self.assertEqual(state["status"], "unknown")
        self.assertFalse(state["healthy"])
        self.assertFalse(state["partitioned"])

    def test_direct_success_stops_escalation(self):
        p = Path("peer-a", _jitter_seed=1)
        result = p.connect(lambda strategy: strategy == "direct", 10)
        self.assertEqual(result["tried"], ["direct"])
        self.assertEqual(p.attempts[-1]["outcome"], "success")
        self.assertEqual(p.state(10)["status"], "healthy")

    def test_relay_is_last_resort(self):
        p = Path("peer-a", _jitter_seed=1)
        result = p.connect(lambda strategy: strategy == "relay", 0)
        self.assertEqual(result["tried"], ["direct", "hole-punch", "relay"])
        self.assertEqual(p.strategy, "relay")

    def test_probe_exception_does_not_block_fallback(self):
        p = Path("peer-a", _jitter_seed=1)
        def prober(strategy):
            if strategy == "direct":
                raise TimeoutError("sensitive endpoint details should not be stored")
            return strategy == "hole-punch"
        result = p.connect(prober, 0)
        self.assertEqual(result["strategy"], "hole-punch")
        self.assertEqual(p.attempts[0]["outcome"], "error")
        self.assertEqual(p.attempts[0]["error_type"], "TimeoutError")
        self.assertNotIn("sensitive", repr(p.attempts))

    def test_exhaustion_sets_partition_and_enforces_retry_window(self):
        p = Path("peer-a", _jitter_seed=1)
        with self.assertRaises(Partitioned):
            p.connect(lambda strategy: False, 0)
        self.assertTrue(p.partitioned)
        self.assertEqual(p.backoff(), 1)
        self.assertTrue(0.5 <= p.retry_at <= 1)  # v4.3.0: ms-resolution jitter (was exactly 1 for every peer)
        calls = []
        with self.assertRaises(Partitioned):
            p.connect(lambda strategy: calls.append(strategy) or True, 0.5)
        self.assertEqual(calls, [])

    def test_backoff_is_bounded_and_jittered(self):
        p = Path("peer-a", _jitter_seed=7)
        expected_bounds = [1, 2, 4, 8, 16, 32, 60, 60]
        now = 0.0
        for expected in expected_bounds:
            with self.assertRaises(Partitioned):
                p.connect(lambda strategy: False, now)
            self.assertEqual(p.backoff(), expected)
            delay = p.retry_at - now
            self.assertGreaterEqual(delay, max(0.5, expected * 0.5))  # v4.3.0: 0.5 s floor, never zero
            self.assertLessEqual(delay, expected)
            now = p.retry_at
        self.assertEqual(p.backoff(), BACKOFF_CEILING)

    def test_freshness_rejects_future_and_stale_success(self):
        p = Path("peer-a", _jitter_seed=1)
        p.connect(lambda strategy: True, 10)
        self.assertFalse(p.healthy_at(9))
        self.assertTrue(p.healthy_at(10 + PROBE_FRESHNESS))
        self.assertFalse(p.healthy_at(10 + PROBE_FRESHNESS + 0.001))
        self.assertEqual(p.state(10 + PROBE_FRESHNESS + 1)["status"], "stale")

    def test_attempt_history_is_bounded_and_has_outcomes(self):
        p = Path("peer-a", _jitter_seed=1)
        for now in range(ATTEMPT_HISTORY + 10):
            p.connect(lambda strategy: True, now)
        self.assertEqual(len(p.attempts), ATTEMPT_HISTORY)
        self.assertTrue(all(a["outcome"] == "success" for a in p.attempts))

    def test_relay_byte_accounting(self):
        p = Path("peer-a", _jitter_seed=1)
        with self.assertRaises(RuntimeError):
            p.record_relay_bytes(1)
        p.connect(lambda strategy: strategy == "relay", 0)
        self.assertEqual(p.record_relay_bytes(512), 512)
        self.assertEqual(p.record_relay_bytes(256), 768)
        with self.assertRaises(ValueError):
            p.record_relay_bytes(-1)

    def test_input_validation(self):
        for peer in ["   ", "bad\npeer"]:
            with self.assertRaises(ValueError):
                Path(peer)
        p = Path("peer-a")
        with self.assertRaises(TypeError):
            p.connect(None, 0)
        for now in [-1, float("inf"), float("nan")]:
            with self.assertRaises(ValueError):
                p.state(now)


if __name__ == "__main__":
    unittest.main()
