"""Unit coverage for config (C033-C039), lifecycle (C015), policy (C017/C025/C053/C054), telemetry (C072-C077)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from _support import (FakeClock, Inv35Error, State, config, health, lifecycle, policy, stack, telemetry, one)


class ConfigTest(unittest.TestCase):
    def test_secure_defaults_validate(self):
        d = config.validate(config.defaults())
        self.assertTrue(d["require_capability"])

    def test_every_profile_builds(self):
        for p in config.PROFILES:
            values, prov = config.build(profile=p)
            self.assertEqual(prov["digest"], config.digest_of(values))

    def test_far_edge_tightens_depth_and_is_enforced(self):
        r, cp, dp, ctl, bulk = stack()
        cp.apply_config(ctl, tenant="t1", queue="q0", profile="far_edge")
        tok = r.authority.mint("c", "t1", {"e"}, {"register_memory"})
        from _support import REGION
        cp.register_queue(tok, tenant="t1", queue="e", regions=REGION)
        self.assertEqual(r.queues["e"].vq.depth_limit, 32)

    def test_failed_apply_leaves_active_untouched(self):
        store = config.ConfigStore()
        before = store.active
        bad = dict(before.values, queue_depth=0)
        with self.assertRaises(Inv35Error):
            store.apply(bad, {"digest": config.digest_of(bad)})
        self.assertIs(store.active, before)

    def test_provenance_mismatch_refused(self):
        store = config.ConfigStore()
        v, p = config.build(environment={"stall_threshold_s": 1.0})
        with self.assertRaises(Inv35Error) as cm:
            store.apply(v, {**p, "digest": "0" * 64})
        self.assertEqual(cm.exception.code, "INV35-E501")

    def test_optimistic_concurrency(self):
        store = config.ConfigStore()
        v, p = config.build(environment={"stall_threshold_s": 1.0})
        with self.assertRaises(Inv35Error):
            store.apply(v, p, expected_generation=99)

    def test_rollback_restores_previous_digest(self):
        store = config.ConfigStore()
        g1 = store.active.digest
        store.apply(*config.build(environment={"stall_threshold_s": 2.0}))
        snap = store.rollback()
        self.assertEqual(snap.digest, g1)
        self.assertEqual(snap.generation, 3)
        self.assertEqual(snap.provenance["rollback_of"], 2)

    def test_file_override_without_rebuild(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "site.json"
            p.write_text(json.dumps({"profile": "near_edge", "site": {"stall_threshold_s": 0.25}, "author": "ops"}))
            values, prov = config.load_file(p)
            self.assertEqual(values["stall_threshold_s"], 0.25)
            self.assertIn("sha256:", prov["source"])
            p.write_text("{not json")
            with self.assertRaises(Inv35Error):
                config.load_file(p)

    def test_shipped_examples_load(self):
        from _support import PKG_DIR
        for p in sorted((PKG_DIR / "config" / "examples").glob("*.json")):
            with self.subTest(p=p.name):
                config.load_file(p)


class LifecycleTest(unittest.TestCase):
    def test_every_illegal_transition_refused(self):
        for src in lifecycle.State:
            for dst in lifecycle.State:
                life = lifecycle.Lifecycle("q", state=src)
                legal = dst in lifecycle.TRANSITIONS[src]
                try:
                    life.transition(dst, reason="r", actor="a", mode=lifecycle.DegradedMode.REDUCED_DEPTH)
                    ok = True
                except Inv35Error:
                    ok = False
                self.assertEqual(ok, legal, (src, dst))

    def test_terminal_states_have_no_exits(self):
        self.assertEqual(lifecycle.TRANSITIONS[State.DISABLED], frozenset())
        self.assertNotIn(State.SERVING, lifecycle.TRANSITIONS[State.QUARANTINED])


class PolicyTest(unittest.TestCase):
    def test_retry_only_retryable_and_bounded(self):
        calls = []

        def flaky():
            calls.append(1)
            raise Inv35Error("INV35-E200")
        with self.assertRaises(Inv35Error):
            policy.RetryPolicy(max_attempts=4).run(flaky, sleep=lambda s: None)
        self.assertEqual(len(calls), 4)
        calls.clear()

        def terminal():
            calls.append(1)
            raise Inv35Error("INV35-E105")
        with self.assertRaises(Inv35Error):
            policy.RetryPolicy().run(terminal, sleep=lambda s: None)
        self.assertEqual(len(calls), 1)

    def test_backoff_jitter_bounded(self):
        p = policy.RetryPolicy(max_attempts=6, base_delay=0.01, max_delay=0.05)
        ds = p.delays()
        self.assertEqual(len(ds), 5)
        self.assertTrue(all(0 <= d <= 0.05 for d in ds))

    def test_cancel_and_deadline(self):
        tok = policy.CancelToken()
        tok.cancel()
        with self.assertRaises(Inv35Error) as cm:
            policy.RetryPolicy().run(lambda: 1, cancel=tok)
        self.assertEqual(cm.exception.code, "INV35-E204")
        clock = FakeClock()
        d = policy.Deadline.after(1.0, clock)
        clock.advance(2)
        with self.assertRaises(Inv35Error):
            d.check(clock)
        r, cp, dp, ctl, bulk = stack()
        with self.assertRaises(Inv35Error) as cm:
            dp.submit(bulk, tenant="t1", queue="q0", chain=one(), head=0, deadline=policy.Deadline(0.0))
        self.assertEqual(cm.exception.code, "INV35-E203")
        self.assertEqual(r.queues["q0"].vq.in_flight, 0)

    def test_token_bucket_refills(self):
        clock = FakeClock()
        b = policy.TokenBucket(rate=10, burst=2, clock=clock)
        self.assertTrue(b.take() and b.take())
        self.assertFalse(b.take())
        clock.advance(0.1)
        self.assertTrue(b.take())


class TelemetryTest(unittest.TestCase):
    def test_traceparent_parse_rejects_malformed(self):
        good = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        self.assertEqual(telemetry.TraceContext.parse(good).trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")
        for bad in ("", "00-" + "0" * 32 + "-00f067aa0ba902b7-01", "ff-x", None, 7, good.upper()):
            self.assertNotEqual(telemetry.TraceContext.parse(bad).trace_id, "4bf92f3577b34da6a3ce929d0e0e4736")

    def test_exposition_format(self):
        r, cp, dp, ctl, bulk = stack()
        dp.submit(bulk, tenant="t1", queue="q0", chain=one(), head=0)
        text = r.metrics.exposition()
        self.assertIn('inv35_queue_depth{queue="q0"} 1', text)
        self.assertIn('inv35_submit_latency_us_bucket{queue="q0",le="+Inf"} 1', text)
        for line in text.strip().splitlines():
            self.assertRegex(line, r'^inv35_[a-z_]+(\{.*\})? [0-9.e+-]+$')

    def test_logs_are_json_with_correlation(self):
        r, cp, dp, ctl, bulk = stack()
        try:
            dp.submit(bulk, tenant="t1", queue="q0", chain=one(addr=0), head=0,
                      traceparent="00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
        except Inv35Error:
            pass
        recs = [json.loads(l) for l in r.log.jsonl().splitlines()]
        refused = [x for x in recs if x["event"] == "submit.refused"]
        self.assertEqual(refused[0]["trace_id"], "4bf92f3577b34da6a3ce929d0e0e4736")
        self.assertEqual(refused[0]["code"], "INV35-E105")

    def test_explain_view(self):
        r, cp, dp, ctl, bulk = stack()
        try:
            dp.submit(bulk, tenant="t1", queue="q0", chain=one(addr=0), head=0)
        except Inv35Error:
            pass
        view = r.explain("q0")
        self.assertIn("INV35-E105", view)
        self.assertIn("io_model.validate", view)


class HealthTest(unittest.TestCase):
    def test_status_surface(self):
        r, cp, dp, ctl, bulk = stack()
        st = cp.status(ctl, tenant="t1", queue="q0")
        self.assertTrue(st["live"] and st["ready"])
        self.assertEqual(st["dependencies"]["key_service"], "ok")
        self.assertIn(st["dependencies"]["pk_core"], ("available", "unavailable"))


if __name__ == "__main__":
    unittest.main()
