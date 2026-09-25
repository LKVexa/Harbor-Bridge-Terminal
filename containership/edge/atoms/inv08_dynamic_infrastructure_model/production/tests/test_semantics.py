"""Tests for components 13-25 (group: semantics)."""
from __future__ import annotations

import json
import os
import random
import tempfile
import unittest
from pathlib import Path

from ...model import Pool
from .. import (authn, authz, compat, constraints, errors_catalog as ec, idempotency as idem,
                lifecycle, limits, partition, quota, schemas)
from ..audit import AuditLog, verify_file
from ..core import Inv08Error, Outcome, TrustRoot, canonical, digest, parse_outcome, wrap_provider_error

GOLDEN = Path(__file__).resolve().parent.parent / "fixtures" / "golden"


class Clock:
    def __init__(self, t: float = 1000.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def sleep(self, d: float) -> None:
        self.t += d


def code_of(cm) -> str:
    return cm.exception.code


# ------------------------------------------------------------------ 13
class TestResultTaxonomy(unittest.TestCase):
    def test_result_codes_stable(self):
        self.assertEqual([o.value for o in Outcome],
                         ["SUCCESS", "PARTIAL", "DEGRADED", "RETRYABLE_FAILURE", "TERMINAL_FAILURE",
                          "OPERATOR_REQUIRED", "BLOCKED"])
        self.assertIs(parse_outcome("SUCCESS"), Outcome.SUCCESS)

    def test_unknown_code_fails_safe(self):
        self.assertIs(parse_outcome("NEW_FROM_FUTURE"), Outcome.OPERATOR_REQUIRED)
        self.assertIs(parse_outcome(""), Outcome.OPERATOR_REQUIRED)

    def test_retryable_vs_terminal(self):
        self.assertTrue(ec.error("INV08.LIMIT.RATE", "x").retryable)
        self.assertFalse(ec.error("INV08.AUTHZ.DENIED", "x").retryable)
        for code, (o, *_rest) in ec.CATALOG.items():
            self.assertEqual(ec.error(code, "m").retryable,
                             o in (Outcome.RETRYABLE_FAILURE, Outcome.DEGRADED), code)

    def test_partial_degraded_operator_envelopes(self):
        for o in (Outcome.PARTIAL, Outcome.DEGRADED, Outcome.OPERATOR_REQUIRED):
            env = ec.result(o, "2 of 3 nodes", correlation_id="c-1", ts=5.0, details={"done": 2})
            self.assertEqual(env["outcome"], o.value)
            self.assertEqual(env["schema"], "PK_DYN_RESULT/1")
        with self.assertRaises(ValueError):
            ec.result(Outcome.PARTIAL, "", correlation_id="c", ts=1)
        with self.assertRaises(ValueError):
            ec.result(Outcome.TERMINAL_FAILURE, "x", correlation_id="c", ts=1)
        with self.assertRaises(ValueError):
            ec.result("SUCCESS", "x", correlation_id="c", ts=1)

    def test_causal_detail_and_remediation(self):
        inner = wrap_provider_error("dummy", TimeoutError("slow"), retryable=True)
        outer = ec.error("INV08.IDEMP.DEADLINE", "gave up", cause=inner)
        env = ec.result(Outcome.RETRYABLE_FAILURE, "timeout", correlation_id="c-9", ts=1, error_obj=outer)
        self.assertEqual(env["error"]["cause"]["code"], "INV08.PROVIDER.RETRYABLE")
        self.assertTrue(env["error"]["remediation"])
        self.assertEqual(outer.chain(), ["INV08.IDEMP.DEADLINE", "INV08.PROVIDER.RETRYABLE"])

    def test_evolution_rules(self):
        old = ec.catalog_document()
        added = json.loads(json.dumps(old))
        added["codes"]["INV08.NEW.THING"] = {"outcome": "SUCCESS", "retryable": False, "severity": "info",
                                            "remediation": "", "deprecated_since": None}
        self.assertEqual(ec.evolution_ok(old, added), (True, []))
        removed = json.loads(json.dumps(old))
        del removed["codes"]["INV08.LIMIT.RATE"]
        self.assertFalse(ec.evolution_ok(old, removed)[0])
        removed["version"] = "2.0.0"
        self.assertFalse(ec.evolution_ok(old, removed)[0])   # not deprecated first
        old2 = json.loads(json.dumps(old))
        old2["codes"]["INV08.LIMIT.RATE"]["deprecated_since"] = "1.1.0"
        self.assertTrue(ec.evolution_ok(old2, removed)[0])
        changed = json.loads(json.dumps(old))
        changed["codes"]["INV08.LIMIT.RATE"]["outcome"] = "TERMINAL_FAILURE"
        self.assertFalse(ec.evolution_ok(old, changed)[0])
        dropped = json.loads(json.dumps(old))
        dropped["outcomes"].remove("BLOCKED")
        self.assertFalse(ec.evolution_ok(old, dropped)[0])


# ------------------------------------------------------------------ 14
class TestLifecycle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.j = Path(self.tmp.name) / "lc.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def _to_leased(self, lc, n="node-1"):
        lc.register(n, 0)
        lc.transition(n, "JOINING", 1, op_id="a")
        lc.transition(n, "READY", 2, op_id="b")
        lc.transition(n, "LEASED", 3, op_id="c", lease_id="lease-1")

    def test_canonical_states(self):
        self.assertEqual(set(lifecycle.STATES), set(lifecycle.TRANSITIONS))
        for s in ("JOINING", "LEASED", "DRAINING", "QUARANTINED", "RECLAIMING", "TERMINATED",
                  "ORPHANED", "RECOVERING"):
            self.assertIn(s, lifecycle.STATES)
        self.assertEqual(lifecycle.TRANSITIONS["TERMINATED"], frozenset())

    def test_allowed_and_forbidden(self):
        lc = lifecycle.Lifecycle()
        self._to_leased(lc)
        self.assertEqual(lc.state("node-1"), "LEASED")
        with self.assertRaises(Inv08Error) as cm:
            lc.transition("node-1", "TERMINATED", 4, op_id="d")
        self.assertEqual(code_of(cm), "INV08.LIFECYCLE.FORBIDDEN_TRANSITION")
        self.assertEqual(lc.state("node-1"), "LEASED")
        with self.assertRaises(Inv08Error):
            lc.transition("node-1", "BOGUS", 4, op_id="e")
        with self.assertRaises(Inv08Error) as cm:
            lc.state("node-9")
        self.assertEqual(code_of(cm), "INV08.LIFECYCLE.UNKNOWN_NODE")

    def test_exhaustive_transition_table(self):
        for src in lifecycle.STATES:
            for dst in lifecycle.STATES:
                lc = lifecycle.Lifecycle()
                lc.register("n", 0)
                lc.nodes["n"]["state"] = src
                attrs = {"lease_id": "l", "busy": False, "health_ok": True}
                if dst in lifecycle.TRANSITIONS[src]:
                    lc.transition("n", dst, 1, op_id="x", **attrs)
                    self.assertEqual(lc.state("n"), dst)
                else:
                    with self.assertRaises(Inv08Error):
                        lc.transition("n", dst, 1, op_id="x", **attrs)

    def test_guards_and_idempotency(self):
        lc = lifecycle.Lifecycle()
        lc.register("node-1", 0)
        lc.transition("node-1", "JOINING", 1, op_id="a")
        lc.transition("node-1", "READY", 2, op_id="b")
        with self.assertRaises(Inv08Error) as cm:
            lc.transition("node-1", "LEASED", 3, op_id="c")
        self.assertEqual(code_of(cm), "INV08.LIFECYCLE.GUARD_FAILED")
        e1 = lc.transition("node-1", "LEASED", 3, op_id="c", lease_id="lease-1")
        e2 = lc.transition("node-1", "LEASED", 9, op_id="c", lease_id="lease-1")
        self.assertEqual(e1, e2)
        lc.transition("node-1", "DRAINING", 4, op_id="d")
        with self.assertRaises(Inv08Error):
            lc.transition("node-1", "RECLAIMING", 5, op_id="e")      # busy defaults True
        lc.transition("node-1", "RECLAIMING", 5, op_id="e", busy=False)
        self.assertEqual(lc.register("node-1", 0), lc._ops["register:node-1"])

    def test_timeouts_and_orphan_recovery(self):
        lc = lifecycle.Lifecycle(timeouts={"heartbeat_timeout": 10, "orphan_timeout": 20, "join_timeout": 5,
                                           "drain_timeout": 7})
        self._to_leased(lc)
        lc.heartbeat("node-1", 12)
        self.assertEqual(lc.sweep(22), [])                  # boundary: 10 is not > 10
        self.assertEqual([e["to"] for e in lc.sweep(23)], ["ORPHANED"])
        lc.transition("node-1", "RECOVERING", 24, op_id="r")
        with self.assertRaises(Inv08Error):
            lc.transition("node-1", "READY", 25, op_id="r2")
        lc.transition("node-1", "READY", 25, op_id="r2", health_ok=True)
        lc.register("node-2", 0)
        lc.transition("node-2", "JOINING", 0, op_id="j")
        out = lc.sweep(30)
        self.assertEqual(out[0]["node"], "node-2")
        self.assertEqual(lc.state("node-2"), "ORPHANED")
        lc.sweep(51)
        self.assertEqual(lc.state("node-2"), "RECLAIMING")
        self.assertEqual(lc.sweep(51), [])                  # idempotent

    def test_persistence_replay(self):
        lc = lifecycle.Lifecycle(self.j)
        self._to_leased(lc)
        lc.transition("node-1", "DRAINING", 4, op_id="d")
        snap = lc.snapshot()
        lc2 = lifecycle.Lifecycle(self.j)
        self.assertEqual(lc2.snapshot(), snap)
        self.assertEqual(lc2.transition("node-1", "DRAINING", 4, op_id="d")["seq"], 5)  # retry after restart

    def test_torn_write_and_corruption(self):
        lc = lifecycle.Lifecycle(self.j)
        self._to_leased(lc)
        with open(self.j, "ab") as fh:
            fh.write(b'{"seq": 5, "par')
        lc2 = lifecycle.Lifecycle(self.j)
        self.assertEqual(lc2.state("node-1"), "LEASED")
        lc2.transition("node-1", "DRAINING", 9, op_id="z")
        self.assertEqual(lifecycle.Lifecycle(self.j).state("node-1"), "DRAINING")
        lines = self.j.read_bytes().splitlines()
        ev = json.loads(lines[1]); ev["to"] = "READY"
        lines[1] = canonical(ev)
        self.j.write_bytes(b"\n".join(lines) + b"\n")
        with self.assertRaises(Inv08Error) as cm:
            lifecycle.Lifecycle(self.j)
        self.assertEqual(code_of(cm), "INV08.LIFECYCLE.JOURNAL_CORRUPT")

    def test_property_random_walk_replay_equivalence(self):
        rng = random.Random(7)
        lc = lifecycle.Lifecycle(self.j)
        for i in range(4):
            lc.register(f"node-{i}", 0)
        for step in range(300):
            nid = f"node-{rng.randrange(4)}"
            to = rng.choice(lifecycle.STATES)
            before = lc.state(nid)
            try:
                lc.transition(nid, to, step, op_id=f"s{step}", lease_id="l", busy=False, health_ok=True)
                self.assertIn(to, lifecycle.TRANSITIONS[before])
            except Inv08Error:
                self.assertEqual(lc.state(nid), before)
        self.assertEqual(lifecycle.Lifecycle(self.j).snapshot(), lc.snapshot())


# ------------------------------------------------------------------ 15 / 24
class TestCompat(unittest.TestCase):
    def test_version_matrix(self):
        m = compat.matrix()
        self.assertTrue(m["4.2.0"]["4.1.0"])
        self.assertFalse(m["4.2.0"]["4.0.0"])
        self.assertTrue(all(m[v][v] for v in m))
        self.assertEqual(m, {a: {b: m[b][a] for b in m} for a in m})   # symmetric

    def test_n_minus_1_and_downgrade(self):
        self.assertTrue(compat.compatible("4.2.7", "4.1.0"))
        self.assertFalse(compat.compatible("5.0.0", "4.9.0"))
        with self.assertRaises(Inv08Error) as cm:
            compat.negotiate(compat.Offer.for_release("4.2.0"), compat.Offer.for_release("4.0.0"))
        self.assertEqual(code_of(cm), "INV08.COMPAT.UNSUPPORTED_PEER")
        with self.assertRaises(Inv08Error):
            compat.parse("4.2")
        with self.assertRaises(Inv08Error):
            compat.Offer.for_release("4.9.0")

    def test_deprecation_windows(self):
        self.assertEqual(compat.deprecation_windows_ok(), [])
        item = "scale.one_tick_equals_one_hour"
        self.assertEqual(compat.deprecation_status(item, "4.1.0"), "active")
        self.assertEqual(compat.deprecation_status(item, "4.3.9"), "deprecated")
        self.assertEqual(compat.deprecation_status(item, "4.4.0"), "removable")
        compat.DEPRECATIONS["tmp.bad"] = ("4.2.0", "4.3.0")
        try:
            self.assertEqual(len(compat.deprecation_windows_ok()), 1)
        finally:
            del compat.DEPRECATIONS["tmp.bad"]

    def test_schema_evolution_rules(self):
        old = schemas.load("PK_DYN_LEASE/1")
        self.assertEqual(compat.schema_change_ok(old, old), [])
        new = json.loads(json.dumps(old))
        new["properties"]["zone"] = {"type": "string"}
        self.assertEqual(compat.schema_change_ok(old, new), [])
        for mutate in (lambda s: s["required"].append("zone"),
                       lambda s: s["properties"].pop("busy"),
                       lambda s: s["properties"]["epoch"].__setitem__("type", "string"),
                       lambda s: s["properties"]["op"].__setitem__("enum", ["GRANT"]),
                       lambda s: s["properties"]["pool_id"].__setitem__("maxLength", 8)):
            bad = json.loads(json.dumps(new))
            mutate(bad)
            self.assertTrue(compat.schema_change_ok(new, bad))

    def test_upgrade_and_rollback_sequencing(self):
        nodes = {"n1": "4.1.0", "n2": "4.1.0"}
        log = compat.check_rollout("4.1.0", nodes, [("controller", "4.2.0"), ("n1", "4.2.0"), ("n2", "4.2.0")])
        self.assertEqual(log[-1]["nodes"], {"n1": "4.2.0", "n2": "4.2.0"})
        with self.assertRaises(Inv08Error) as cm:
            compat.check_rollout("4.1.0", nodes, [("n1", "4.2.0")])
        self.assertEqual(code_of(cm), "INV08.COMPAT.BAD_SEQUENCE")
        with self.assertRaises(Inv08Error):
            compat.check_rollout("4.2.0", {"n1": "4.2.0"}, [("controller", "4.0.0")])
        compat.check_rollout("4.2.0", {"n1": "4.1.0"}, [("controller", "4.1.0")])   # rollback to N-1 ok
        with self.assertRaises(Inv08Error):
            compat.check_rollout("4.2.0", {"n1": "4.2.0"}, [("nX", "4.2.0")])


class TestMixedVersion(unittest.TestCase):
    def test_interop_matrix_negotiates(self):
        for a, row in compat.matrix().items():
            for b, ok in row.items():
                if ok:
                    r = compat.negotiate(compat.Offer.for_release(a), compat.Offer.for_release(b))
                    self.assertEqual(set(r["wire"]), set(schemas.INTERFACES))
                else:
                    with self.assertRaises(Inv08Error):
                        compat.negotiate(compat.Offer.for_release(a), compat.Offer.for_release(b))

    def test_feature_negotiation(self):
        n = compat.Offer.for_release("4.2.0")
        n1 = compat.Offer.for_release("4.1.0")
        self.assertEqual(compat.negotiate(n, n1)["features"], ["lease.epoch"])
        strict = compat.Offer("4.2.0", n.wire, n.features, frozenset({"cost.tenant"}))
        with self.assertRaises(Inv08Error) as cm:
            compat.negotiate(strict, n1)
        self.assertEqual(code_of(cm), "INV08.COMPAT.MISSING_FEATURE")
        nowire = compat.Offer("4.1.0", {"PK_DYN_LEASE": (2,)}, frozenset())
        with self.assertRaises(Inv08Error) as cm:
            compat.negotiate(n, nowire)
        self.assertEqual(code_of(cm), "INV08.COMPAT.NO_COMMON_VERSION")

    def test_mixed_version_golden_fixtures(self):
        g = json.loads((GOLDEN / "pk_dyn_v1.json").read_text())
        newer = g["valid"]["lease_minor1_with_ext"]["message"]
        self.assertEqual(schemas.validate_message(newer), [])          # N-1 schema accepts minor 1
        down = compat.read_tolerant(newer, supported_minor=0)
        self.assertTrue(down["_downlevel"])
        self.assertNotIn("ext", down)
        old = g["valid"]["lease"]["message"]
        self.assertFalse(compat.read_tolerant(old, 0)["_downlevel"])

    def test_rolling_upgrade_property(self):
        rng = random.Random(3)
        for _ in range(20):
            nodes = {f"n{i}": "4.1.0" for i in range(5)}
            order = list(nodes)
            rng.shuffle(order)
            steps = [("controller", "4.2.0")] + [(n, "4.2.0") for n in order]
            self.assertEqual(len(compat.check_rollout("4.1.0", nodes, steps)), 6)

    def test_downgrade_unsupported_peer(self):
        with self.assertRaises(Inv08Error) as cm:
            compat.negotiate(compat.Offer.for_release("4.2.0"), compat.Offer("3.9.0", {}, frozenset()))
        self.assertEqual(code_of(cm), "INV08.COMPAT.UNSUPPORTED_PEER")
        self.assertFalse(cm.exception.retryable)
        with self.assertRaises(Inv08Error):
            compat.negotiate(compat.Offer.for_release("4.2.0"), compat.Offer("garbage", {}, frozenset()))


# ------------------------------------------------------------------ 16
class TestQuota(unittest.TestCase):
    def test_quota_model_validation(self):
        quota.Quota("a", 5, reserved=2, burst=1, weight=2, priority=1)
        for kw in ({"limit": -1}, {"limit": 1, "reserved": 2}, {"limit": 1, "weight": 0},
                   {"limit": True}, {"limit": 1, "burst": 1.5}):
            with self.assertRaises(Inv08Error):
                quota.Quota("a", **kw)
        with self.assertRaises(Inv08Error):
            quota.QuotaEngine(3, [quota.Quota("a", 5, reserved=2), quota.Quota("b", 5, reserved=2)])
        with self.assertRaises(Inv08Error):
            quota.QuotaEngine(3, [quota.Quota("a", 1), quota.Quota("a", 1)])

    def test_priority_and_reservation(self):
        e = quota.QuotaEngine(10, [quota.Quota("lo", 10, reserved=3), quota.Quota("hi", 10, priority=5)])
        a = e.allocate({"lo": 10, "hi": 10})
        self.assertEqual(a, {"lo": 3, "hi": 7})        # reservation honoured despite priority
        self.assertEqual(sum(a.values()), 10)

    def test_weighted_fair_share(self):
        e = quota.QuotaEngine(9, [quota.Quota("a", 9, weight=2), quota.Quota("b", 9, weight=1)])
        self.assertEqual(e.allocate({"a": 9, "b": 9}), {"a": 6, "b": 3})
        e2 = quota.QuotaEngine(9, [quota.Quota("a", 9, weight=2), quota.Quota("b", 9, weight=1)])
        self.assertEqual(e2.allocate({"a": 2, "b": 9}), {"a": 2, "b": 7})   # max-min redistribution
        e3 = quota.QuotaEngine(1, [quota.Quota("a", 1), quota.Quota("b", 1)])
        self.assertEqual(e3.allocate({"a": 1, "b": 1}), {"a": 1, "b": 0})    # deterministic tie
        rng = random.Random(11)
        for _ in range(200):
            cap = rng.randrange(0, 30)
            qs = [quota.Quota(t, rng.randrange(0, 15), weight=rng.randrange(1, 4), priority=rng.randrange(3))
                  for t in "abcd"]
            dem = {t: rng.randrange(0, 20) for t in "abcd"}
            a = quota.QuotaEngine(cap, qs).allocate(dem)
            self.assertLessEqual(sum(a.values()), cap)
            for q in qs:
                self.assertLessEqual(a[q.tenant], min(dem[q.tenant], q.limit))
            # work-conserving: either all capacity used or every tenant capped
            if sum(a.values()) < cap:
                self.assertTrue(all(a[q.tenant] == min(dem[q.tenant], q.limit) for q in qs))

    def test_starvation_detection_and_aging(self):
        e = quota.QuotaEngine(2, [quota.Quota("big", 2, priority=9), quota.Quota("small", 2)],
                              starvation_rounds=2)
        self.assertEqual(e.allocate({"big": 2, "small": 1})["small"], 0)
        self.assertEqual(e.starving(), [])
        e.allocate({"big": 2, "small": 1})
        self.assertEqual(e.starving(), ["small"])
        served = False
        for _ in range(12):
            if e.allocate({"big": 2, "small": 1})["small"] > 0:
                served = True
                break
        self.assertTrue(served)
        self.assertEqual(e.starving(), [])
        self.assertGreaterEqual(e.telemetry["starved_flags"], 1)

    def test_admission_burst_and_telemetry(self):
        e = quota.QuotaEngine(10, [quota.Quota("a", 3, burst=2), quota.Quota("b", 5, reserved=4)])
        e.admit("a", 3)
        r = e.admit("a", 2)                          # burst: idle capacity exists
        self.assertTrue(r["burst"])
        with self.assertRaises(Inv08Error) as cm:
            e.admit("a", 1)
        self.assertEqual(code_of(cm), "INV08.QUOTA.EXCEEDED")
        self.assertTrue(cm.exception.retryable)
        self.assertEqual(e.admit("b", 4)["usage"], 4)   # reservation still available
        with self.assertRaises(Inv08Error):
            e.admit("zz", 1)
        with self.assertRaises(Inv08Error):
            e.admit("a", 0)
        e.release("a", 5)
        self.assertEqual(e.telemetry["admitted"], 3)
        self.assertEqual(e.telemetry["rejected"], 1)
        self.assertEqual(e.telemetry["burst_used"], 2)


# ------------------------------------------------------------------ 17
class TestPartition(unittest.TestCase):
    def agent(self):
        a = partition.NodeAgent("node-1", suspect_after=10, partitioned_after=30, grace=20)
        a.command({"epoch": 1, "seq": 1, "action": "renew", "expires_at": 100}, now=50)
        return a

    def test_reachability_states(self):
        a = self.agent()
        self.assertEqual(a.reachability(59.9), "CONNECTED")
        self.assertEqual(a.reachability(60), "SUSPECT")
        self.assertEqual(a.reachability(80), "PARTITIONED")
        self.assertEqual(partition.NodeAgent("n").reachability(0), "PARTITIONED")
        with self.assertRaises(ValueError):
            partition.NodeAgent("n", suspect_after=5, partitioned_after=5)

    def test_lease_grace_and_fencing(self):
        a = self.agent()
        self.assertEqual(a.lease_state(99), "VALID")
        self.assertEqual(a.lease_state(100), "GRACE")
        self.assertEqual(a.lease_state(120), "FENCED")
        self.assertEqual(a.lease_state(0), "FENCED")          # sticky
        with self.assertRaises(Inv08Error) as cm:
            a.command({"epoch": 2, "seq": 1, "action": "renew", "expires_at": 500}, now=121)
        self.assertEqual(code_of(cm), "INV08.PARTITION.FENCED")
        self.assertFalse(partition.controller_may_regrant(100, 20, 124, 5))
        self.assertTrue(partition.controller_may_regrant(100, 20, 125, 5))

    def test_stale_command_rejection(self):
        a = self.agent()
        for cmd in ({"epoch": 1, "seq": 1}, {"epoch": 0, "seq": 99}):
            with self.assertRaises(Inv08Error) as cm:
                a.command({**cmd, "action": "noop"}, now=51)
            self.assertEqual(code_of(cm), "INV08.PARTITION.STALE_COMMAND")
        a.command({"epoch": 1, "seq": 2, "action": "noop"}, now=52)
        a.command({"epoch": 2, "seq": 0, "action": "noop"}, now=53)   # new leader resets seq
        with self.assertRaises(Inv08Error):
            a.command({"epoch": 1, "seq": 3, "action": "noop"}, now=54)

    def test_autonomy_limits(self):
        a = self.agent()
        a.act_locally("scale_up", 55)                 # allowed while connected
        with self.assertRaises(Inv08Error) as cm:
            a.act_locally("scale_up", 85)
        self.assertEqual(code_of(cm), "INV08.PARTITION.AUTONOMY_LIMIT")
        a.act_locally("local_reclaim", 85)
        with self.assertRaises(Inv08Error):
            a.act_locally("local_reclaim", 86)
        a.act_locally("drain", 86)
        with self.assertRaises(Inv08Error):
            a.act_locally("drain", 130)                 # fenced now
        a.act_locally("report", 130)

    def test_reconcile(self):
        ctrl = {"n1": {"state": "LEASED", "epoch": 2, "version": 5},
                "n2": {"state": "LEASED", "epoch": 2, "version": 5},
                "n3": {"state": "READY", "epoch": 1, "version": 3},
                "n4": {"state": "TERMINATED", "epoch": 2, "version": 9}}
        node = {"n1": {"state": "FENCED", "epoch": 2, "version": 4},
                "n2": {"state": "DRAINING", "epoch": 2, "version": 5},
                "n3": {"state": "LEASED", "epoch": 2, "version": 1},
                "n4": {"state": "LEASED", "epoch": 3, "version": 1},
                "n5": {"state": "READY", "epoch": 2, "version": 1}}
        r = partition.reconcile(ctrl, node)
        self.assertEqual({k: v["state"] for k, v in r["merged"].items()},
                         {"n1": "FENCED", "n2": "LEASED", "n3": "LEASED", "n4": "TERMINATED", "n5": "READY"})
        self.assertEqual(sorted(c["kind"] for c in r["conflicts"]),
                         ["divergent_same_version", "local_terminal_fact", "unknown_to_controller"])
        self.assertEqual(partition.reconcile(ctrl, node), r)       # deterministic


# ------------------------------------------------------------------ 18
C = constraints.Constraint
CANDS = [{"id": "z1", "encrypted": True, "region": "eu", "latency": 5, "zone": "a", "free": 4, "price": 3},
         {"id": "z2", "encrypted": True, "region": "eu", "latency": 20, "zone": "b", "free": 8, "price": 1},
         {"id": "z3", "encrypted": False, "region": "eu", "latency": 1, "zone": "a", "free": 9, "price": 0},
         {"id": "z4", "encrypted": True, "region": "us", "latency": 1, "zone": "c", "free": 9, "price": 0}]


class TestConstraints(unittest.TestCase):
    def test_normalized_model(self):
        c = C("slo", "latency", "le", 10, hard=False)
        self.assertTrue(c.ok({"latency": 10}))
        self.assertFalse(c.ok({"latency": "x"}))        # incomparable -> fail closed
        self.assertFalse(c.ok({}))
        for bad in ({"kind": "vibes", "attr": "a", "op": "eq", "value": 1},
                    {"kind": "cost", "attr": "a", "op": "like", "value": 1},
                    {"kind": "cost", "attr": "a", "op": "in", "value": 1}):
            with self.assertRaises(Inv08Error):
                C(**bad)

    def test_precedence(self):
        cons = [C("security", "encrypted", "eq", True), C("residency", "region", "eq", "eu"),
                C("slo", "latency", "le", 10, hard=False), C("cost", "price", "le", 1, hard=False)]
        r = constraints.resolve(CANDS, cons)
        self.assertEqual(r["choice"], "z1")               # SLO beats cost
        self.assertEqual(r["ranking"], ["z1", "z2"])
        soft_sec = C("security", "encrypted", "eq", True, hard=False)   # cannot be downgraded
        self.assertNotIn("z3", constraints.resolve(CANDS, [soft_sec])["ranking"])

    def test_deterministic(self):
        cons = [C("cost", "price", "le", 1, hard=False), C("topology", "zone", "in", ["a", "c"], hard=False)]
        base = constraints.resolve(CANDS, cons)
        rng = random.Random(5)
        for _ in range(30):
            cs, cc = list(CANDS), list(cons)
            rng.shuffle(cs); rng.shuffle(cc)
            self.assertEqual(constraints.resolve(cs, cc), base)
        self.assertEqual(base["choice"], "z3")            # topology+cost tie -> id order
        with self.assertRaises(Inv08Error):
            constraints.resolve([{"id": "a"}, {"id": "a"}], [])

    def test_unsatisfiable_diagnostics(self):
        cons = [C("security", "encrypted", "eq", True), C("residency", "region", "eq", "eu"),
                C("capacity", "free", "ge", 10, name="need10")]
        d = constraints.resolve(CANDS, cons)
        self.assertFalse(d["satisfiable"])
        self.assertEqual(d["blocking"], "need10")
        self.assertEqual(d["last_candidates"], ["z1", "z2"])
        with self.assertRaises(Inv08Error) as cm:
            constraints.resolve(CANDS, cons, raise_on_fail=True)
        self.assertEqual(code_of(cm), "INV08.CONSTRAINT.UNSATISFIABLE")
        self.assertIs(cm.exception.outcome, Outcome.OPERATOR_REQUIRED)

    def test_precedence_stable_across_versions(self):
        self.assertEqual(constraints.PRECEDENCE,
                         ("security", "residency", "slo", "topology", "capacity", "cost"))
        self.assertEqual(constraints.PRECEDENCE_DIGEST, digest(constraints.CONSTRAINT_SPEC))
        pinned = "sha256:" + __import__("hashlib").sha256(canonical({
            "version": "PK_DYN_CONSTRAINT/1",
            "precedence": ["security", "residency", "slo", "topology", "capacity", "cost"],
            "always_hard": ["residency", "security"],
            "ops": ["eq", "ge", "in", "le", "ne", "not_in"]})).hexdigest()
        self.assertEqual(constraints.PRECEDENCE_DIGEST, pinned)


# ------------------------------------------------------------------ 19
class TestSchemas(unittest.TestCase):
    def setUp(self):
        self.g = json.loads((GOLDEN / "pk_dyn_v1.json").read_text())

    def _roundtrip(self, key):
        fx = self.g["valid"][key]
        b = schemas.encode(fx["message"])
        self.assertEqual(b.decode(), fx["canonical"])
        self.assertEqual(digest(fx["message"]), fx["digest"])
        self.assertEqual(schemas.decode(b), fx["message"])

    def test_lease_schema(self):
        self._roundtrip("lease")
        for k in ("lease_expiry_before_issue", "lease_unknown_field"):
            with self.assertRaises(Inv08Error):
                schemas.encode(self.g["invalid"][k]["message"])

    def test_scale_schema(self):
        self._roundtrip("scale")
        sc = self.g["pool_scenario"]
        r = Pool(sc["min_nodes"], sc["max_nodes"]).tick(sc["now"], sc["demand"])
        m = self.g["valid"]["scale"]["message"]
        self.assertEqual({k: r[k] for k in ("size", "target", "added", "reclaimed", "renewed")},
                         {k: m[k] for k in ("size", "target", "added", "reclaimed", "renewed")})

    def test_cost_schema(self):
        self._roundtrip("cost")

    def test_invalid_golden_fixtures(self):
        for name, fx in self.g["invalid"].items():
            with self.subTest(name):
                with self.assertRaises(Inv08Error) as cm:
                    schemas.encode(fx["message"])
                text = cm.exception.message + cm.exception.code
                self.assertIn(fx["expect"], text)

    def test_negotiation(self):
        self.assertEqual(schemas.negotiate(["PK_DYN_LEASE/1", "PK_DYN_LEASE/2", "PK_DYN_SCALE/1", "PK_DYN_COST/1"]),
                         {"PK_DYN_LEASE": "PK_DYN_LEASE/1", "PK_DYN_SCALE": "PK_DYN_SCALE/1",
                          "PK_DYN_COST": "PK_DYN_COST/1"})
        with self.assertRaises(Inv08Error):
            schemas.negotiate(["PK_DYN_LEASE/1", "PK_DYN_SCALE/1"])
        with self.assertRaises(Inv08Error):
            schemas.load("../etc/passwd/1")

    def test_decoder_rejections(self):
        for bad in (b"\xff", b"[1]", b'{"schema": "PK_DYN_COST/1", "node_hours": NaN}', b"x" * 50):
            with self.assertRaises(Inv08Error):
                schemas.decode(bad, max_bytes=40)
        for f in ("PK_DYN_LEASE_1", "PK_DYN_SCALE_1", "PK_DYN_COST_1"):
            schemas.check_schema(json.loads((schemas.SCHEMA_DIR / f"{f}.json").read_text()))
        with self.assertRaises(ValueError):
            schemas.check_schema({"oneOf": []})
        deep = {"type": "array", "items": {}}
        self.assertTrue(schemas.validate([[[[]]]], deep, depth=schemas.MAX_DEPTH))


# ------------------------------------------------------------------ 20
class AuthBase(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.trust = TrustRoot()
        self.trust.add("k1", b"k" * 32)
        self.rng = random.Random(1)
        self.auth = authn.Authority(self.trust, "k1", clock=self.clock, admin_secret=b"bootstrap-secret-test")
        self.ctrl = self.auth.issue_controller("ctrl-1", b"bootstrap-secret-test")


class TestAuthn(AuthBase):
    def test_controller_issuance(self):
        c = self.auth.verify(self.ctrl["token"], role="controller")
        self.assertEqual(c["sub"], "ctrl-1")
        with self.assertRaises(Inv08Error) as cm:
            self.auth.issue_controller("evil", b"wrong")
        self.assertEqual(code_of(cm), "INV08.AUTHN.BAD_BOOTSTRAP")

    def test_node_and_provider_issuance(self):
        jt = self.auth.new_join_token(self.ctrl["token"], self.rng, tenant="t1")
        node = self.auth.issue_node("node-1", jt)
        self.assertEqual(self.auth.verify(node["token"], role="node")["tenant"], "t1")
        with self.assertRaises(Inv08Error):
            self.auth.issue_node("node-2", jt)             # single-use
        prov = self.auth.issue_provider("prov-1", self.ctrl["token"])
        self.assertEqual(self.auth.verify(prov["token"])["role"], "provider")
        with self.assertRaises(Inv08Error):
            self.auth.issue_provider("prov-2", node["token"])   # node cannot mint providers

    def test_token_format_and_trust_root(self):
        tok = json.loads(json.dumps(self.ctrl["token"]))
        self.assertEqual(tok["claims"]["typ"], "PK_DYN_IDENT/1")
        self.assertFalse(tok["sig"]["production"])
        self.assertFalse(self.trust.verify(tok["claims"], tok["sig"], require_production=True))
        tok["claims"]["role"] = "provider"
        with self.assertRaises(Inv08Error) as cm:
            self.auth.verify(tok)
        self.assertEqual(code_of(cm), "INV08.AUTHN.INVALID_TOKEN")
        with self.assertRaises(Inv08Error):
            self.auth.verify({"claims": 1})
        with self.assertRaises(Inv08Error):
            self.auth.verify(self.ctrl["token"], role="node")

    def test_mutual_handshake_and_rotation(self):
        jt = self.auth.new_join_token(self.ctrl["token"], self.rng)
        node = self.auth.issue_node("node-1", jt)
        s = authn.mutual_handshake(self.auth, self.ctrl, node, self.rng)
        self.assertEqual((s["a"], s["b"]), ("ctrl-1", "node-1"))
        with self.assertRaises(Inv08Error):
            authn.mutual_handshake(self.auth, self.ctrl, node, self.rng, tamper="B")
        with self.assertRaises(Inv08Error) as cm:
            self.auth._fresh_nonce(s["nonces"][0], 300)
        self.assertEqual(code_of(cm), "INV08.AUTHN.REPLAY")
        stolen = dict(node, pop_key=b"\0" * 32)
        with self.assertRaises(Inv08Error):
            authn.mutual_handshake(self.auth, self.ctrl, stolen, self.rng)
        self.auth.rotate("k2", b"q" * 32, overlap=60)
        new_ctrl = self.auth.issue_controller("ctrl-1", b"bootstrap-secret-test")
        self.assertEqual(new_ctrl["token"]["claims"]["kid"], "k2")
        self.clock.t += 59
        self.auth.verify(self.ctrl["token"])               # old kid inside overlap
        self.clock.t += 1
        with self.assertRaises(Inv08Error) as cm:
            self.auth.verify(self.ctrl["token"])
        self.assertEqual(code_of(cm), "INV08.AUTHN.REVOKED")
        self.auth.verify(new_ctrl["token"])

    def test_revocation_expiry_compromise(self):
        jt = self.auth.new_join_token(self.ctrl["token"], self.rng)
        node = self.auth.issue_node("node-1", jt, ttl=100)
        self.clock.t += 104.9
        self.auth.verify(node["token"])                    # within leeway
        self.clock.t += 0.1
        with self.assertRaises(Inv08Error) as cm:
            self.auth.verify(node["token"])
        self.assertEqual(code_of(cm), "INV08.AUTHN.EXPIRED")
        self.auth.revoke_token(self.ctrl["token"]["claims"]["jti"])
        with self.assertRaises(Inv08Error) as cm:
            self.auth.verify(self.ctrl["token"])
        self.assertEqual(code_of(cm), "INV08.AUTHN.REVOKED")
        c2 = self.auth.issue_controller("ctrl-2", b"bootstrap-secret-test")
        self.auth.compromise("ctrl-2")
        with self.assertRaises(Inv08Error):
            self.auth.verify(c2["token"])
        with self.assertRaises(Inv08Error):
            self.auth._issue("x", "root", 10, None)


# ------------------------------------------------------------------ 21
P = authz.Principal
POOL_T1 = {"type": "pool", "id": "p1", "tenant": "t1", "residency": "eu"}
LEASE_T1 = {"type": "lease", "id": "l1", "tenant": "t1"}


class TestAuthz(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.log = Path(self.tmp.name) / "audit.jsonl"
        self.az = authz.Authorizer(audit=AuditLog(self.log))

    def tearDown(self):
        self.tmp.cleanup()

    def test_policy_model(self):
        self.assertEqual(authz.validate_policy(), [])
        bad = json.loads(json.dumps(authz.POLICY))
        bad["roles"]["x"] = {"principal_types": ["controller"], "scope": "tenant", "caps": ["*:pool"]}
        self.assertTrue(authz.validate_policy(bad))
        with self.assertRaises(ValueError):
            authz.Authorizer(bad)

    def test_permission_matrix(self):
        m = self.az.matrix()
        self.assertEqual(m["tenant_viewer"]["read:pool"], "tenant")
        self.assertIsNone(m["tenant_viewer"]["scale:pool"])
        self.assertEqual(m["platform_admin"]["set_quota:quota"], "global")
        self.assertIsNone(m["node_agent"]["grant_lease:lease"])
        self.assertEqual(len(m["provider"]), len(authz.ACTIONS) * len(authz.RESOURCES))

    def test_tenant_and_admin_scopes(self):
        op = P("u1", ("tenant_operator",), "controller", tenant="t1", residencies=("eu",))
        self.assertTrue(self.az.evaluate(op, "scale", POOL_T1).allow)
        self.assertFalse(self.az.evaluate(op, "scale", dict(POOL_T1, tenant="t2")).allow)
        self.assertFalse(self.az.evaluate(op, "scale", dict(POOL_T1, residency="us")).allow)
        admin = P("adm", ("platform_admin",), "controller")
        self.assertTrue(self.az.evaluate(admin, "scale", dict(POOL_T1, tenant="t2")).allow)
        node = P("node-1", ("node_agent",), "node", tenant="t1")
        self.assertTrue(self.az.evaluate(node, "renew_lease", LEASE_T1).allow)
        spoof = P("node-1", ("platform_admin",), "node")          # wrong principal type
        self.assertFalse(self.az.evaluate(spoof, "set_quota", {"type": "quota", "id": "q"}).allow)

    def test_deny_by_default(self):
        nobody = P("x", (), "controller", tenant="t1")
        for a in authz.ACTIONS:
            for t in authz.RESOURCES:
                self.assertFalse(self.az.evaluate(nobody, a, {"type": t, "tenant": "t1"}).allow)
        op = P("u1", ("tenant_operator", "ghost_role"), "controller", tenant="t1")
        self.assertFalse(self.az.evaluate(op, "nuke", POOL_T1).allow)
        d = self.az.evaluate(op, "grant_lease", dict(LEASE_T1, frozen=True))
        self.assertEqual((d.allow, d.rule), (False, "deny[0]"))
        with self.assertRaises(Inv08Error) as cm:
            self.az.require(nobody, "read", POOL_T1)
        self.assertEqual(code_of(cm), "INV08.AUTHZ.DENIED")

    def test_audit_and_privilege_review(self):
        op = P("u1", ("tenant_operator",), "controller", tenant="t1")
        self.az.evaluate(op, "scale", POOL_T1)
        self.az.evaluate(op, "scale", dict(POOL_T1, tenant="t9"))
        ok, problems, entries = verify_file(self.log)
        self.assertTrue(ok, problems)
        self.assertEqual([e["outcome"] for e in entries], ["ALLOW", "DENY"])
        rev = authz.privilege_review(authz.POLICY, self.log)
        self.assertNotIn("scale:pool", rev["unused_grants"]["tenant_operator"])
        self.assertIn("grant_lease:lease", rev["unused_grants"]["tenant_operator"])
        self.assertIn("platform_admin", rev["global_roles"])


# ------------------------------------------------------------------ 22
class TestIdempotency(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()

    def test_operation_ids(self):
        a, b = idem.new_op_id(random.Random(1)), idem.new_op_id(random.Random(1))
        self.assertEqual(a, b)
        self.assertRegex(a, r"^op-[0-9a-f]{16}$")
        rng = random.Random(2)
        self.assertEqual(len({idem.new_op_id(rng) for _ in range(1000)}), 1000)

    def test_dedup_window(self):
        s = idem.IdempotencyStore(clock=self.clock, window=10, max_entries=2)
        calls = []
        f = lambda: calls.append(1) or len(calls)
        self.assertEqual(s.execute("p", "op1", {"n": 1}, f), 1)
        self.assertEqual(s.execute("p", "op1", {"n": 1}, f), 1)
        self.assertEqual(s.execute("q", "op1", {"n": 1}, f), 2)       # key includes principal
        with self.assertRaises(Inv08Error) as cm:
            s.execute("p", "op1", {"n": 2}, f)
        self.assertEqual(code_of(cm), "INV08.IDEMP.KEY_REUSE")
        with self.assertRaises(Inv08Error) as cm:
            s.execute("p", "op2", {}, f)
        self.assertEqual(code_of(cm), "INV08.IDEMP.STORE_FULL")
        self.clock.t += 10
        self.assertEqual(s.execute("p", "op1", {"n": 1}, f), 3)       # window elapsed -> re-exec

    def test_in_progress_and_failure_caching(self):
        s = idem.IdempotencyStore(clock=self.clock)
        def reenter():
            with self.assertRaises(Inv08Error) as cm:
                s.execute("p", "op", {}, lambda: 0)
            self.assertEqual(code_of(cm), "INV08.IDEMP.IN_PROGRESS")
            return "ok"
        self.assertEqual(s.execute("p", "op", {}, reenter), "ok")
        def boom():
            raise ec.error("INV08.PROVIDER.TERMINAL", "no")
        for _ in range(2):
            with self.assertRaises(Inv08Error):
                s.execute("p", "t", {}, boom)
        self.assertEqual(s.executions, 2)                              # terminal failure cached
        def flaky():
            raise ec.error("INV08.PROVIDER.RETRYABLE", "later")
        with self.assertRaises(Inv08Error):
            s.execute("p", "r", {}, flaky)
        self.assertEqual(s.execute("p", "r", {}, lambda: 7), 7)       # retryable not cached

    def test_timeout_and_cancellation_budgets(self):
        b = idem.Budget(10, self.clock)
        c = b.child(0.5)
        self.assertEqual(c.remaining(), 5)
        self.clock.t += 5
        with self.assertRaises(Inv08Error) as cm:
            c.check()
        self.assertEqual(code_of(cm), "INV08.IDEMP.DEADLINE")
        b.check()
        b.cancel()
        with self.assertRaises(Inv08Error) as cm:
            b.child(1).check()
        self.assertEqual(code_of(cm), "INV08.IDEMP.CANCELLED")
        for bad in (0, 1.5):
            with self.assertRaises(ValueError):
                b.child(bad)

    def test_retry_classes_with_jitter(self):
        rng = random.Random(4)
        ds = [idem.backoff(a, rng, base=1, cap=8) for a in range(10) for _ in range(20)]
        self.assertTrue(all(0 <= d <= 8 for d in ds))
        self.assertGreater(len(set(ds)), 150)
        n = []
        def flaky():
            n.append(1)
            if len(n) < 3:
                raise ec.error("INV08.LIMIT.RATE", "x")
            return "done"
        self.assertEqual(idem.retry(flaky, klass="IDEMPOTENT", budget=idem.Budget(100, self.clock),
                                    rng=rng, sleep=self.clock.sleep), "done")
        n.clear()
        with self.assertRaises(Inv08Error):
            idem.retry(flaky, klass="NEVER", budget=idem.Budget(100, self.clock), rng=rng, sleep=self.clock.sleep)
        self.assertEqual(len(n), 1)
        term = lambda: (_ for _ in ()).throw(ec.error("INV08.AUTHZ.DENIED", "no"))
        with self.assertRaises(Inv08Error) as cm:
            idem.retry(term, klass="SAFE_READ", budget=idem.Budget(100, self.clock), rng=rng, sleep=self.clock.sleep)
        self.assertEqual(code_of(cm), "INV08.AUTHZ.DENIED")
        always = lambda: (_ for _ in ()).throw(ec.error("INV08.LIMIT.RATE", "x"))
        with self.assertRaises(Inv08Error) as cm:
            idem.retry(always, klass="SAFE_READ", budget=idem.Budget(0.01, self.clock), rng=random.Random(9),
                       sleep=self.clock.sleep, base=1)
        self.assertEqual(code_of(cm), "INV08.IDEMP.DEADLINE")

    def test_admission_backpressure(self):
        q = idem.AdmissionQueue(4, 2)
        q.offer(1); q.offer(2)
        with self.assertRaises(Inv08Error) as cm:
            q.offer(3)
        self.assertEqual(code_of(cm), "INV08.BACKPRESSURE.SHED")
        self.assertTrue(cm.exception.retryable)
        q.offer(3, priority=1); q.offer(4, priority=1)
        with self.assertRaises(Inv08Error) as cm:
            q.offer(5, priority=9)
        self.assertEqual(cm.exception.details["retry_after"], 3.0)
        self.assertEqual(q.take(), 1)
        self.assertEqual(q.stats, {"accepted": 4, "shed": 2})
        with self.assertRaises(ValueError):
            idem.AdmissionQueue(1, 2)


# ------------------------------------------------------------------ 23
class TestErrorModel(unittest.TestCase):
    def test_namespace(self):
        for code in ec.CATALOG:
            self.assertRegex(code, r"^INV08\.[A-Z0-9_]+\.[A-Z0-9_]+$")
        with self.assertRaises(ValueError):
            Inv08Error("OTHER.X.Y", "m")
        with self.assertRaises(Inv08Error) as cm:
            ec.error("INV08.NOT.CATALOGUED", "m")
        self.assertEqual(code_of(cm), "INV08.CATALOG.UNKNOWN_CODE")

    def test_retryability_severity(self):
        doc = ec.catalog_document()
        for code, e in doc["codes"].items():
            self.assertIn(e["severity"], ("info", "warning", "error", "critical"))
            self.assertEqual(ec.error(code, "m").to_dict()["retryable"], e["retryable"])
        with self.assertRaises(ValueError):
            Inv08Error("INV08.X.Y", "m", severity="fatal")

    def test_causal_chain(self):
        p = wrap_provider_error("sim", ConnectionError("reset"), retryable=True)
        e = ec.error("INV08.IDEMP.DEADLINE", "outer", cause=ec.error("INV08.LIMIT.RATE", "mid", cause=p))
        self.assertEqual(e.chain(), ["INV08.IDEMP.DEADLINE", "INV08.LIMIT.RATE", "INV08.PROVIDER.RETRYABLE"])
        self.assertEqual(e.to_dict()["cause"]["cause"]["details"]["exception_type"], "ConnectionError")

    def test_remediation_hints(self):
        for code in ec.CATALOG:
            self.assertTrue(ec.error(code, "m").remediation, code)

    def test_redaction(self):
        e = ec.error("INV08.AUTHN.INVALID_TOKEN", "bad token=abc123 for ops@example.com",
                     details={"password": "hunter2", "note": "api_key: SECRET1"})
        s = json.dumps(e.to_dict())
        for leak in ("abc123", "ops@example.com", "hunter2", "SECRET1"):
            self.assertNotIn(leak, s)
        self.assertIn("[REDACTED]", s)


# ------------------------------------------------------------------ 25
class TestLimits(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.l = limits.Limits(max_payload_bytes=100, max_connections=2, max_streams_per_connection=2,
                               rate_per_s=10, burst=5, max_concurrency=3, max_queue_depth=2,
                               memory_budget_bytes=1000)
        self.e = limits.Enforcer(self.l, clock=self.clock)

    def test_payload(self):
        self.e.check_payload(100)
        with self.assertRaises(Inv08Error) as cm:
            self.e.check_payload(101)
        self.assertEqual(code_of(cm), "INV08.LIMIT.PAYLOAD_TOO_LARGE")
        self.assertFalse(cm.exception.retryable)
        self.assertEqual(limits.LIMITS["max_payload_bytes"], 1 << 20)
        with self.assertRaises(ValueError):
            limits.Limits(max_connections=0)

    def test_connections_streams(self):
        self.e.open_connection("c1"); self.e.open_connection("c2")
        with self.assertRaises(Inv08Error) as cm:
            self.e.open_connection("c3")
        self.assertEqual(code_of(cm), "INV08.LIMIT.CONNECTIONS")
        self.e.open_stream("c1"); self.e.open_stream("c1")
        with self.assertRaises(Inv08Error):
            self.e.open_stream("c1")
        self.e.close_stream("c1"); self.e.open_stream("c1")
        self.e.close_connection("c2"); self.e.open_connection("c3")
        with self.assertRaises(ValueError):
            self.e.open_connection("c3")

    def test_rate_and_concurrency(self):
        for _ in range(3):
            self.e.begin_request(10)
        with self.assertRaises(Inv08Error) as cm:
            self.e.begin_request(10)
        self.assertEqual(code_of(cm), "INV08.LIMIT.CONCURRENCY")
        for _ in range(3):
            self.e.end_request()
        self.e.begin_request(1); self.e.end_request()
        self.e.begin_request(1); self.e.end_request()
        with self.assertRaises(Inv08Error) as cm:
            self.e.begin_request(1)
        self.assertEqual(code_of(cm), "INV08.LIMIT.RATE")
        self.assertAlmostEqual(cm.exception.details["retry_after"], 0.1)
        self.clock.t += 0.1
        self.e.begin_request(1)
        self.assertEqual(limits.TokenBucket(1, 2, self.clock).take(3), float("inf"))

    def test_queue_and_memory(self):
        self.e.enqueue(); self.e.enqueue()
        with self.assertRaises(Inv08Error) as cm:
            self.e.enqueue()
        self.assertEqual(code_of(cm), "INV08.LIMIT.QUEUE_DEPTH")
        self.e.dequeue(); self.e.enqueue()
        self.e.begin_request(1, mem_bytes=900)
        with self.assertRaises(Inv08Error) as cm:
            self.e.begin_request(1, mem_bytes=101)
        self.assertEqual(code_of(cm), "INV08.LIMIT.MEMORY")
        self.e.end_request(900)
        self.e.begin_request(1, mem_bytes=1000)

    def test_overload(self):
        e = limits.Enforcer(limits.Limits(rate_per_s=50, burst=50, max_concurrency=10**6), clock=self.clock)
        ok = 0
        for i in range(10000):
            self.clock.t += 0.001                      # 1000 req/s offered vs 50/s allowed
            try:
                e.begin_request(10)
                e.end_request()
                ok += 1
            except Inv08Error as exc:
                self.assertEqual(exc.code, "INV08.LIMIT.RATE")
        self.assertLessEqual(ok, 50 + 50 * 10 + 1)
        self.assertGreaterEqual(ok, 50 * 10)
        self.assertEqual(e.inflight, 0)
        self.assertEqual(e.rejections["INV08.LIMIT.RATE"], 10000 - ok)


if __name__ == "__main__":
    unittest.main()
