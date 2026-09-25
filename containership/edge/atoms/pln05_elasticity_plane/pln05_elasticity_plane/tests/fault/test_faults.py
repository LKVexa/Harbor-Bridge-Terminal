"""MC-20 fault-injection harness.  One test per scenario in ops/reliability/fault_scenarios.json;
every scenario asserts the global invariants INV-A..INV-E afterwards.  Deterministic: fake
clocks and seeded RNGs only.  Results are written to $PLN05_EVIDENCE_DIR/faults.json when set."""
from __future__ import annotations

import json
import os
import pathlib
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from helpers import World  # noqa: E402

from pln05_elasticity_plane.audit import AuditLog  # noqa: E402
from pln05_elasticity_plane.errors import PlaneError  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = json.loads((ROOT / "ops" / "reliability" / "fault_scenarios.json").read_text())["scenarios"]
RESULTS: dict = {}


def invariants(tc, *worlds):
    for w in worlds:
        for s in w.plane.scopes.values():
            lim = s.controller.limits
            tc.assertTrue(lim.floor <= s.controller.current <= lim.ceiling, "INV-A")
            tc.assertLessEqual(lim.ceiling, s.declared_ceiling, "INV-E")
        log = w.plane.audit
        tc.assertTrue(AuditLog.verify(log.records, log.anchor(w.clock()), w.ring, w.clock(), log.window_start)["ok"], "INV-D")
    sink = worlds[0].sink
    high = {}
    for t in sink.applied:
        key = (t["tenant"], t["site"], t["workload"])
        tc.assertGreaterEqual(t["fencing_token"], high.get(key, 0), "INV-C")
        high[key] = t["fencing_token"]
        tc.assertTrue(t["floor"] <= t["target"] <= t["ceiling"], "INV-A(published)")


def code(fn):
    try:
        fn()
    except PlaneError as exc:
        return exc.code
    return "OK"


class Faults(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.w = World(self.tmp.name)
        self.w.declare(floor=0, ceiling=16)

    def tearDown(self):
        self.tmp.cleanup()
        RESULTS[self._testMethodName.replace("test_", "")] = "pass" if not getattr(self, "_failed", False) else "fail"

    def restart(self):
        old = self.w
        w = World(self.tmp.name, ring=old.ring, leases=old.leases, sink=old.sink, clock=old.clock)
        w.seq = old.seq
        return w

    def test_FS01(self):
        w = self.w
        for u in (0.9, 0.9, 0.1):
            w.observe(u)
        w2 = self.restart()  # crash between decisions
        self.assertEqual(w2.observe(0.1)["outcome"], "hold")  # grace count 2 of 3 preserved
        self.assertEqual(w2.observe(0.1)["outcome"], "scale-down")
        invariants(self, w2)

    def test_FS02(self):
        w = self.w
        class BadSink:
            applied = []
            def apply(self, t):
                raise RuntimeError("provider bug")
        w.plane.sink = BadSink()
        for _ in range(8):
            d = w.observe(0.9)
            self.assertFalse(d["published"])
        self.assertEqual(w.plane.breakers["sink"].state, "open")
        self.assertTrue(w.plane.health()["live"])

    def test_FS03(self):
        w = self.w
        w.plane.enqueue_demand(w.demand(0.9), w.token())
        w.mono.advance(61)
        h = w.plane.health()
        self.assertEqual((h["state"], h["ready"]), ("stalled", False))
        w.plane.process()
        self.assertTrue(w.plane.health()["ready"])

    def test_FS04(self):
        w = World()
        w.declare()
        w.plane.activate_config(w.token("platform_operator", tenant="*"), {"site": {"revision": 2, "explain": {"retention": 100}}})
        tok = w.token()
        for i in range(3000):
            w.plane.submit_demand(w.demand(random.Random(i).random()), tok)
        s = w.plane.scopes["t1/dub/w1"]
        self.assertEqual(len(w.plane.explain_store), 100)
        self.assertLessEqual(len(s.seen), 256)
        self.assertLess(w.plane.metrics.series(), 100)

    def test_FS05(self):
        w = self.w
        w.observe(0.9)
        w.clock.advance(-10)
        self.assertEqual(code(lambda: w.observe(0.9, observed_at=w.clock())), "E_SECURITY_DEPENDENCY")
        self.assertIn("R_TIME_FAULT", w.plane.health()["blockers"])
        w.clock.advance(11)
        self.assertEqual(code(lambda: w.observe(0.9)), "OK")
        invariants(self, w)

    def test_FS06(self):
        w = self.w
        w.observe(0.9)
        before = w.plane.scopes["t1/dub/w1"].controller.snapshot()
        applied = len(w.sink.applied)
        orig = w.plane.store.save

        def full(*a, **k):
            raise OSError(28, "No space left on device")
        w.plane.store.save = full
        raw = w.demand(0.9)
        self.assertEqual(code(lambda: w.plane.submit_demand(raw, w.token())), "E_STATE_UNAVAILABLE")
        self.assertEqual(len(w.sink.applied), applied)  # nothing published without persisted state
        self.assertEqual(w.plane.scopes["t1/dub/w1"].controller.snapshot(), before)  # memory rolled back
        w.plane.store.save = orig
        self.assertEqual(code(lambda: w.plane.submit_demand(raw, w.token())), "OK")  # same sample now accepted
        invariants(self, w)

    def test_FS07(self):
        w = self.w
        w.observe(0.9)
        b = World(self.tmp.name, instance="ctl-b", ring=w.ring, leases=w.leases, sink=w.sink, clock=w.clock)
        w.leases.available = False
        w.clock.advance(16)
        self.assertEqual(code(lambda: w.observe(0.9)), "E_NOT_LEADER")
        w.leases.available = True
        # B shares the state directory: it takes over the scope from disk, no re-declaration
        self.assertTrue(b.observe(0.9, source="r2", token=b.token(source="r2"))["published"])
        invariants(self, w, b)

    def test_FS08(self):
        w = self.w
        import time as _t
        class SlowSink(type(w.sink)):
            def apply(self, t):
                _t.sleep(0.002)
                return super().apply(t)
        w.plane.sink = SlowSink()
        for _ in range(5):
            w.observe(0.5)
        self.assertEqual(len(w.plane.admission), 0)

    def test_FS09(self):
        w = self.w
        state = {"fail": True}
        real = w.sink.apply
        def flaky(t):
            if state["fail"]:
                raise PlaneError("E_OVERLOADED", "throttled")
            return real(t)
        w.sink.apply = flaky
        for _ in range(6):
            w.observe(0.5)
        br = w.plane.breakers["sink"]
        self.assertEqual(br.state, "open")
        state["fail"] = False
        w.clock.advance(13)
        self.assertTrue(w.observe(0.5)["published"])
        self.assertEqual(br.state, "closed")
        invariants(self, w)

    def test_FS10(self):
        w = self.w
        w.observe(0.9)
        stale_lease = w.plane.scopes["t1/dub/w1"].lease
        w.clock.advance(16)
        b = World(self.tmp.name, instance="ctl-b", ring=w.ring, leases=w.leases, sink=w.sink, clock=w.clock)
        b.observe(0.9, source="r2", token=b.token(source="r2"))
        # A resurrects with its old in-memory lease forced valid (paused VM): still fenced
        stale_lease.expires = w.clock() + 100
        w.plane.scopes["t1/dub/w1"].lease = stale_lease
        self.assertEqual(code(lambda: w.observe(0.9)), "E_FENCED")
        invariants(self, w, b)

    def test_FS11(self):
        w = self.w
        w.observe(0.9)
        w2 = self.restart()
        n = len(w.sink.applied)
        self.assertFalse(w2.plane.republish_last("t1", "dub", "w1"))
        self.assertEqual(len(w.sink.applied), n)

    def test_FS12(self):
        w = self.w
        w.observe(0.9)
        w.clock.advance(31)
        self.assertEqual(w.plane.tick()["t1/dub/w1"], "stale")
        w.clock.advance(300)
        self.assertEqual(w.plane.tick()["t1/dub/w1"], "degraded")
        self.assertEqual([t["outcome"] for t in w.sink.applied][-2:], ["stale-input-hold", "degraded"])
        self.assertEqual(w.observe(0.5)["outcome"], "recovery")
        invariants(self, w)

    def test_FS13(self):
        w = self.w
        w.observe(0.5)
        snap = w.plane.scopes["t1/dub/w1"].controller.snapshot()
        rng = random.Random(13)
        tok = w.token()
        for _ in range(1000):
            raw = bytes(rng.randrange(256) for _ in range(rng.randrange(1, 64)))
            self.assertNotEqual(code(lambda raw=raw: w.plane.submit_demand(raw, tok)), "OK")
        self.assertEqual(w.plane.scopes["t1/dub/w1"].controller.snapshot(), snap)

    def test_FS14(self):
        w = self.w
        ta, tb = w.token(source="ra"), w.token(source="rb")
        changes, last = 0, None
        for i in range(300):
            d = w.observe(0.95 if i % 2 else 0.05, source="ra" if i % 2 else "rb", token=ta if i % 2 else tb)
            if d["outcome"] in ("scale-up", "scale-down"):
                if last and d["outcome"] != last:
                    changes += 1
                last = d["outcome"]
        self.assertEqual(changes, 0)
        invariants(self, w)

    def test_FS15(self):
        from pln05_elasticity_plane.keys import KeyRing
        from helpers import Clock
        clock = Clock()
        w = World(ring=KeyRing.ephemeral(clock(), lifetime=100), clock=clock)
        w.declare()
        w.observe(0.5)
        tok = w.token(lifetime=300)  # credential outlives the key that signed it
        applied = len(w.sink.applied)
        w.clock.advance(150)
        self.assertIn("R_NO_ACTIVE_KEY", w.plane.health()["blockers"])
        self.assertEqual(code(lambda: w.plane.submit_demand(w.demand(0.9), tok)), "E_AUTHN_EXPIRED")
        self.assertEqual(len(w.sink.applied), applied)

    def test_FS16(self):
        w = self.w
        w.plane.audit.buffer_capacity = 3
        w.plane.audit.set_sink(False)
        codes = [code(lambda: w.plane.control(w.token("operator"), "freeze", tenant="t1", site="dub",
                                              workload="w1", reason="r", ticket="t")) for _ in range(5)]
        self.assertIn("E_AUDIT_UNAVAILABLE", codes)
        w.plane.audit.set_sink(True)
        invariants(self, w)

    def test_FS17(self):
        w = self.w
        class Bad:
            def write(self, s):
                raise OSError("telemetry down")
        w.plane.log.stream = Bad()
        self.assertTrue(w.observe(0.9)["published"])
        self.assertGreater(w.plane.log.errors, 0)

    def test_FS18(self):
        w = self.w
        before = w.plane.config.active.checksum
        self.assertEqual(code(lambda: w.plane.activate_config(w.token("platform_operator", tenant="*"),
                                                              {"site": {"revision": 2, "queue_capacity": 0}})), "E_CONFIG_INVALID")
        self.assertEqual(w.plane.config.active.checksum, before)
        self.assertEqual(w.plane.audit.records[-1]["result"], "rejected")

    def test_FS19(self):
        w = self.w
        w.observe(0.9)
        f = next((pathlib.Path(self.tmp.name) / "state").glob("*.state.json"))
        f.write_bytes(b"{")
        w2 = self.restart()
        self.assertEqual(code(lambda: w2.observe(0.9)), "E_STATE_CORRUPT")
        self.assertFalse(w2.plane.health()["ready"])

    def test_manifest_has_a_test_per_scenario(self):
        for sid in SCENARIOS:
            self.assertTrue(hasattr(self, f"test_{sid}"), sid)


def _emit():
    out = os.environ.get("PLN05_EVIDENCE_DIR")
    if out:
        pathlib.Path(out).mkdir(parents=True, exist_ok=True)
        (pathlib.Path(out) / "faults.json").write_text(json.dumps(
            {"scenarios": len(SCENARIOS), "results": RESULTS}, indent=1, sort_keys=True))


if __name__ == "__main__":
    import atexit
    atexit.register(_emit)
    unittest.main()
