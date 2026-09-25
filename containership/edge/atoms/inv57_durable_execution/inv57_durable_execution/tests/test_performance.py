"""MC-46 regression gate: replay must stay linear and inside the contract SLO.

Thresholds are deliberately loose (CI machines vary); the benchmark bundle in
``evidence/benchmark`` holds the precise measurement.  The scaling assertion is
what caught the v4.2.0 O(n^2) replay (1000 events: ~3.7 s)."""
from __future__ import annotations

import time
import unittest

from . import _path  # noqa: F401

from inv57_durable_execution.durable import InMemoryHistoryStore, Worker


def _replay_ms(n: int) -> float:
    wf = lambda w: [w.activity(f"a{i}", lambda i=i: {"i": i}) for i in range(n)]
    w = Worker()
    w.run(wf)
    text = w.history_store.to_json()
    best = float("inf")
    for _ in range(5):
        s = InMemoryHistoryStore.from_json(text)
        t0 = time.perf_counter()
        Worker(s).run(wf)
        best = min(best, (time.perf_counter() - t0) * 1000)
    return best


class PerformanceGate(unittest.TestCase):
    def test_1000_event_replay_under_slo(self):
        self.assertLess(_replay_ms(500), 100.0)

    def test_replay_scales_linearly(self):
        small, large = _replay_ms(500), _replay_ms(2000)
        # 4x the work; quadratic would be ~16x.  Allow 8x for noise.
        self.assertLess(large / max(small, 1e-6), 8.0)


if __name__ == "__main__":
    unittest.main()
