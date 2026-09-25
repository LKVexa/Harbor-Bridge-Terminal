"""Standalone safety tests for the dependency-independent transport model."""
from __future__ import annotations

import importlib.util
import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = PKG_DIR / "transport.py"
SPEC = importlib.util.spec_from_file_location("inv38_transport_standalone", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
transport = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = transport
SPEC.loader.exec_module(transport)

BypassQueue = transport.BypassQueue
CompletionRingFull = transport.CompletionRingFull
NotRegistered = transport.NotRegistered
OutOfBounds = transport.OutOfBounds
RegionBusy = transport.RegionBusy
RegionLimitReached = transport.RegionLimitReached
RingFull = transport.RingFull


class BypassQueueTest(unittest.TestCase):
    def test_configuration_is_bounded_and_strict(self):
        for kwargs in ({"ring_size": 0}, {"max_regions": 0}, {"completion_limit": 0}, {"address_bits": 0}):
            with self.assertRaises(ValueError):
                BypassQueue(**kwargs)
        with self.assertRaises(TypeError):
            BypassQueue(ring_size=True)
        with self.assertRaises(TypeError):
            BypassQueue(available="yes")
        with self.assertRaises(ValueError):
            BypassQueue(address_bits=129)

    def test_registration_rejects_invalid_and_overflowing_ranges(self):
        q = BypassQueue(address_bits=16)
        with self.assertRaises((OutOfBounds, ValueError)):
            q.register(-1, 1)
        with self.assertRaises((OutOfBounds, ValueError)):
            q.register(0, 0)
        with self.assertRaises(OutOfBounds):
            q.register(0xFFF0, 0x20)

    def test_region_limit_is_enforced(self):
        q = BypassQueue(max_regions=1)
        q.register(0, 16)
        with self.assertRaises(RegionLimitReached):
            q.register(32, 16)

    def test_bounds_stale_key_and_inflight_deregister(self):
        q = BypassQueue()
        key = q.register(0x1000, 0x1000)
        self.assertEqual(q.post(key, 0x1000, 16, b"a"), "bypass")
        with self.assertRaises(RegionBusy):
            q.deregister(key)
        with self.assertRaises(OutOfBounds):
            q.post(key, 0x1FFF, 2, b"x")
        self.assertEqual(q.poll(), 1)
        q.deregister(key)
        with self.assertRaises(NotRegistered):
            q.post(key, 0x1000, 1, b"x")

    def test_payload_is_snapshotted_before_async_completion(self):
        q = BypassQueue()
        key = q.register(0, 64)
        payload = bytearray(b"sealed")
        q.post(key, 0, len(payload), payload)
        payload[:] = b"xxxxxx"
        q.poll()
        self.assertEqual(q.pop_completion(), ("bypass", b"sealed"))

    def test_ring_and_completion_capacity_are_lossless(self):
        q = BypassQueue(ring_size=1, completion_limit=1)
        key = q.register(0, 8)
        q.post(key, 0, 1, b"a")
        with self.assertRaises(RingFull):
            q.post(key, 1, 1, b"b")
        self.assertEqual(q.poll(), 1)
        q.post(key, 1, 1, b"b")
        with self.assertRaises(CompletionRingFull):
            q.poll()
        self.assertEqual(q.ring_depth, 1)
        self.assertEqual(q.pop_completion(), ("bypass", b"a"))
        self.assertEqual(q.poll(), 1)
        self.assertEqual(q.pop_completion(), ("bypass", b"b"))

    def test_fallback_preserves_order_and_does_not_require_device_key(self):
        q = BypassQueue(ring_size=2, completion_limit=3)
        key = q.register(0, 32)
        q.post(key, 0, 5, b"first")
        q.set_available(False)
        self.assertEqual(q.post(0, 8, 8, b"fallback"), "kernel")
        self.assertEqual(q.completions, [("bypass", b"first"), ("kernel", b"fallback")])
        self.assertEqual(q.fallbacks, 1)
        with self.assertRaises(TypeError):
            q.set_available(0)

    def test_invalid_descriptor_and_payload_types_are_rejected(self):
        q = BypassQueue()
        key = q.register(0, 16)
        with self.assertRaises(TypeError):
            q.post(key, 0, 1, "not-bytes")
        with self.assertRaises(TypeError):
            q.post(key, True, 1, b"x")
        with self.assertRaises(OutOfBounds):
            q.post(key, 0, 1, b"too long")

    def test_thread_safe_bounded_posting(self):
        q = BypassQueue(ring_size=64, completion_limit=64)
        key = q.register(0, 64)
        errors: list[BaseException] = []

        def worker(i: int) -> None:
            try:
                q.post(key, i, 1, bytes([i]))
            except BaseException as exc:  # capture worker failure for the assertion thread
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(32)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(q.ring_depth, 32)
        self.assertEqual(q.poll(), 32)
        self.assertEqual(q.completion_depth, 32)


if __name__ == "__main__":
    unittest.main()
