"""Controller pipeline, safety modes, drain scheduler, reconciliation, and
property/concurrency/chaos/fuzz tests (components 5,7,8,10-15,20-30,34-36,40)."""
import json
import os
import random
import threading
import unittest
from unittest import mock

from helpers import KEYS, Harness

from gap01_edge_node_supervisor import make_request
from gap01_edge_node_supervisor.config import SupervisorConfig
from gap01_edge_node_supervisor.controller import Watchdog
from gap01_edge_node_supervisor.schemas import validate
from gap01_edge_node_supervisor.store import AuditLog
from gap01_edge_node_supervisor.supervisor import TRANSITIONS


def code(r):
    return r.get("error", {}).get("code")


class PipelineTest(unittest.TestCase):
    def test_authn_replay_skew(self):
        h = Harness()
        req = h.req("cp", "status")
        bad = dict(req, sig="0" * 64)
        self.assertEqual(code(h.ctl.handle(bad)), "E_UNAUTHENTICATED")
        self.assertTrue(h.ctl.handle(req)["ok"])
        # same nonce, new request id -> replay
        req2 = make_request("cp", KEYS["cp"], "status", request_id="other", nonce=req["nonce"],
                            ts=h.clock.wall())
        self.assertEqual(code(h.ctl.handle(req2)), "E_REPLAY")
        old = make_request("cp", KEYS["cp"], "status", ts=h.clock.wall() - 120)
        self.assertEqual(code(h.ctl.handle(old)), "E_STALE_REQUEST")

    def test_authz_denied_is_audited(self):
        h = Harness()
        r = h.call("obs", "cordon")
        self.assertEqual(code(r), "E_FORBIDDEN")
        tail = (h.ctl.dir / "audit.jsonl").read_text().strip().splitlines()[-1]
        self.assertIn('"denied"', tail)

    def test_idempotent_request_id(self):
        h = Harness()
        h.make_ready()
        r1 = h.call("cp", "admit", {"workload": "w", "trust_class": "trusted"}, request_id="req-1")
        r2 = h.call("cp", "admit", {"workload": "w", "trust_class": "trusted"}, request_id="req-1")
        self.assertTrue(r1["ok"] and r2["ok"] and r2["replayed"])
        self.assertEqual(r1["result"], r2["result"])
        self.assertEqual(h.rt.calls.count(("launch", "w")), 1)
        # idempotency survives restart
        h2 = h.restart()
        r3 = h2.call("cp", "admit", {"workload": "w", "trust_class": "trusted"}, request_id="req-1")
        self.assertTrue(r3.get("replayed"))

    def test_schema_rejects_bad_args(self):
        h = Harness()
        r = h.call("cp", "admit", {"workload": "../../etc", "trust_class": "trusted"})
        self.assertEqual(code(r), "E_BAD_REQUEST")
        r = h.call("cp", "transition", {"to": "ready", "extra": 1})
        self.assertEqual(code(r), "E_BAD_REQUEST")

    def test_ready_requires_health_and_placement_gating(self):
        h = Harness()
        self.assertEqual(code(h.call("cp", "transition", {"to": "ready"})), "E_NOT_ACCEPTING")
        h.make_ready()
        self.assertTrue(h.admit("a")["ok"])
        self.assertEqual(code(h.admit("a")), "E_DUPLICATE_WORKLOAD")
        h.clock.advance(31)  # health stale
        self.assertEqual(code(h.admit("b")), "E_NOT_ACCEPTING")

    def test_capacity(self):
        h = Harness(config=SupervisorConfig(max_workloads=2))
        h.make_ready()
        h.admit("a"); h.admit("b")
        self.assertEqual(code(h.admit("c")), "E_CAPACITY")

    def test_rate_limit(self):
        h = Harness(config=SupervisorConfig(rate_burst=3, rate_per_second=0.1))
        codes = [code(h.call("cp", "status")) for _ in range(5)]
        self.assertEqual(codes.count("E_RATE_LIMITED"), 2)

    def test_status_matches_schema(self):
        h = Harness()
        self.assertEqual(validate("status", h.call("obs", "status")["result"]), [])


class DrainTest(unittest.TestCase):
    def test_trust_order_and_completion(self):
        h = Harness()
        h.make_ready()
        for n, t in (("a", "trusted"), ("b", "hostile"), ("c", "third-party")):
            h.admit(n, t)
        r = h.call("cp", "drain", {"timeout_s": 10})["result"]
        self.assertEqual(r["released"], ["b", "c", "a"])
        self.assertTrue(r["complete"])
        self.assertEqual(validate("drain", r), [])
        self.assertEqual(h.ctl.sup.state, "stopped")

    def test_deadline_breach_then_force_kill(self):
        h = Harness()
        h.make_ready()
        h.admit("s", "untrusted")
        h.rt.stubborn.add("s")
        r = h.call("cp", "drain", {"timeout_s": 5})["result"]
        self.assertEqual(r["remaining"], ["s"])
        h.clock.advance(6)
        r = h.ctl.tick()["drain"]
        self.assertIn("deadline exceeded", r["escalation"])
        self.assertEqual(h.ctl.sup.state, "draining")
        h.clock.advance(60)
        r = h.ctl.tick()["drain"]
        self.assertTrue(r["complete"] and r["forced"])
        self.assertIn(("kill", "s"), h.rt.calls)

    def test_unproven_reclaim_never_stops_node(self):
        h = Harness()
        h.make_ready()
        h.admit("leaky")
        h.rt.leak.add("leaky")
        r = h.call("cp", "drain", {"timeout_s": 1})["result"]
        self.assertEqual(r["unproven_reclaim"], ["leaky"])
        h.clock.advance(100)
        h.ctl.tick()
        self.assertEqual(h.ctl.sup.state, "draining")
        self.assertIn("leaky", h.ctl.sup.workloads)

    def test_operator_override(self):
        h = Harness()
        h.make_ready()
        h.admit("s")
        h.rt.stubborn.add("s")
        h.call("cp", "drain", {"timeout_s": 100})
        self.assertEqual(code(h.call("cp", "drain_override", {"force_now": True})), "E_FORBIDDEN")
        r = h.call("op", "drain_override", {"force_now": True})
        self.assertTrue(r["result"]["complete"])

    def test_drain_resumes_after_restart(self):
        h = Harness()
        h.make_ready()
        h.admit("s")
        h.rt.stubborn.add("s")
        h.call("cp", "drain", {"timeout_s": 5})
        h2 = h.restart()
        self.assertEqual(h2.ctl.sup.state, "draining")
        self.assertIsNotNone(h2.ctl.drain_intent)
        h2.clock.advance(70)
        self.assertTrue(h2.ctl.tick()["drain"]["complete"])


class SafetyModesTest(unittest.TestCase):
    def test_cordon_ack_generation(self):
        h = Harness()
        h.make_ready()
        c = h.call("cp", "cordon", {"reason": "maint"})["result"]["cordon"]
        self.assertEqual(code(h.call("cp", "cordon_ack", {"generation": c["generation"] + 5})),
                         "E_BAD_REQUEST")
        self.assertIsNotNone(h.call("cp", "cordon_ack", {"generation": c["generation"]})
                             ["result"]["cordon"]["acked_at"])
        self.assertEqual(code(h.admit("x")), "E_NOT_ACCEPTING")

    def test_cordon_ack_overdue_metric(self):
        h = Harness()
        h.make_ready()
        h.call("cp", "cordon")
        h.clock.advance(11)
        h.ctl.tick()
        self.assertEqual(h.ctl.metrics.get("cordon_ack_overdue"), 1)

    def test_partition_state_machine(self):
        h = Harness(config=SupervisorConfig(partition_lease_s=10, partition_max_autonomy_s=20))
        h.make_ready()
        seen = []
        for _ in range(4):
            h.clock.advance(8)
            h.call("hr", "report_health", {"signal": "runtime", "ok": True})
            seen.append(h.ctl.tick()["partition"])
        self.assertEqual(seen, ["suspect", "partitioned", "partitioned", "autonomy-expired"])
        self.assertIsNotNone(h.ctl.emergency)
        self.assertEqual(h.ctl.sup.state, "cordoned")
        self.assertEqual(h.call("cp", "control_plane_heartbeat")["result"]["partition"], "connected")

    def test_partitioned_refuses_admit(self):
        h = Harness(config=SupervisorConfig(partition_lease_s=4))
        h.make_ready()
        h.clock.advance(5)
        h.call("hr", "report_health", {"signal": "runtime", "ok": True})
        h.ctl.tick()
        self.assertEqual(code(h.admit("x")), "E_PARTITIONED")

    def test_emergency_mode(self):
        h = Harness()
        h.make_ready()
        self.assertEqual(code(h.call("cp", "emergency_enter")), "E_FORBIDDEN")
        h.call("bg", "emergency_enter", {"reason": "suspected compromise"})
        self.assertEqual(h.ctl.sup.state, "cordoned")
        self.assertEqual(code(h.call("cp", "uncordon")), "E_EMERGENCY")
        self.assertTrue(h.call("op", "emergency_exit")["ok"])
        self.assertTrue(h.call("cp", "uncordon")["ok"])

    def test_emergency_disable_persists(self):
        h = Harness()
        h.make_ready()
        self.assertTrue(h.call("bg", "disable", {"reason": "bad release"})["ok"])
        self.assertEqual(code(h.call("cp", "cordon")), "E_DISABLED")
        self.assertTrue(h.call("obs", "status")["ok"])
        h2 = h.restart()
        self.assertTrue(h2.ctl.disabled)
        self.assertFalse(h2.ctl.readiness()["ready"])

    def test_pressure_blocks_admission(self):
        h = Harness()
        h.make_ready()
        h.pressure.update(under_pressure=True, reasons=["memory 95% >= 90%"])
        h.ctl.tick()
        self.assertEqual(code(h.admit("x")), "E_CAPACITY")
        self.assertFalse(h.ctl.readiness()["ready"])

    def test_persistence_failure_enters_emergency(self):
        h = Harness()
        h.make_ready()
        with mock.patch("gap01_edge_node_supervisor.store.atomic_write", side_effect=OSError(28, "ENOSPC")):
            r = h.call("cp", "cordon")
        self.assertEqual(code(r), "E_PERSISTENCE")
        self.assertIsNotNone(h.ctl.emergency)

    def test_readiness_liveness_watchdog(self):
        h = Harness()
        self.assertFalse(h.ctl.readiness()["ready"])
        h.make_ready()
        h.ctl.tick()
        self.assertTrue(h.ctl.readiness()["ready"])
        self.assertTrue(h.ctl.liveness()["live"])
        h.clock.advance(16)  # no tick -> stalled loop
        self.assertFalse(h.ctl.liveness()["live"])
        wd = Watchdog(h.ctl)
        self.assertFalse(wd.check_once())
        self.assertIsNotNone(h.ctl.emergency)

    def test_config_hot_reload(self):
        h = Harness()
        self.assertEqual(h.call("op", "reload_config", {"changes": {"rate_burst": 7}})
                         ["result"]["config"]["rate_burst"], 7)
        self.assertEqual(code(h.call("op", "reload_config", {"changes": {"max_workloads": 7}})),
                         "E_CONFIG")


class ReconciliationTest(unittest.TestCase):
    def test_orphans_terminated_lost_removed_ready_becomes_cordoned(self):
        h = Harness()
        h.make_ready()
        h.admit("kept"); h.admit("lost")
        h.rt.running.pop("lost")             # died while supervisor was down
        from gap01_edge_node_supervisor.runtime import WorkloadSpec
        h.rt.launch(WorkloadSpec("orphan", "trusted"))  # started behind our back
        h2 = h.restart()
        rep = h2.ctl.recovery_report
        self.assertEqual(rep["orphans_terminated"], ["orphan"])
        self.assertEqual(rep["lost_workloads"], ["lost"])
        self.assertEqual(set(h2.ctl.sup.workloads), {"kept"})
        self.assertEqual(h2.ctl.sup.state, "cordoned")

    def test_wal_replay_after_crash_before_checkpoint(self):
        h = Harness()
        h.make_ready()
        # simulate crash after WAL append but before checkpoint
        h.ctl.store.append_journal({"op": "cordon", "args": {}, "caller": "cp", "request_id": "x"})
        h2 = h.restart()
        self.assertEqual(h2.ctl.recovery_report["replayed"], 1)
        self.assertEqual(h2.ctl.sup.state, "cordoned")

    def test_audit_chain_intact_after_run(self):
        h = Harness()
        h.make_ready()
        h.admit("a")
        h.call("cp", "drain")
        self.assertTrue(AuditLog.verify(h.ctl.dir / "audit.jsonl")[0])


class PropertyTest(unittest.TestCase):
    """Randomised state-machine test: invariants hold for every seed."""
    OPS = ["report_health", "transition", "cordon", "uncordon", "admit", "drain", "terminate",
           "tick", "advance", "restart", "stubborn"]

    def run_seed(self, seed):
        rnd = random.Random(seed)
        h = Harness()
        for step in range(120):
            op = rnd.choice(self.OPS)
            prev = h.ctl.sup.state
            if op == "report_health":
                h.call("hr", "report_health", {"signal": "runtime", "ok": rnd.random() > 0.2})
            elif op == "transition":
                h.call("cp", "transition", {"to": rnd.choice(list(TRANSITIONS))})
            elif op in ("cordon", "uncordon", "drain"):
                h.call("cp", op)
            elif op == "admit":
                h.admit(f"w{rnd.randrange(8)}", rnd.choice(["trusted", "hostile", "untrusted"]))
            elif op == "terminate":
                h.call("op", "terminate", {"workload": f"w{rnd.randrange(8)}", "force": rnd.random() > .5})
            elif op == "tick":
                h.ctl.tick()
            elif op == "advance":
                h.clock.advance(rnd.randrange(0, 40))
            elif op == "restart":
                h = h.restart()
            elif op == "stubborn":
                h.rt.stubborn.add(f"w{rnd.randrange(8)}")
            now = h.ctl.sup.state
            self.assertIn(now, TRANSITIONS, f"seed {seed} step {step}")
            if now != prev and op not in ("restart",):
                self.assertIn(now, TRANSITIONS[prev], f"seed {seed} step {step} {prev}->{now}")
            if now == "stopped":
                self.assertEqual(h.ctl.sup.workloads, {}, f"seed {seed}: stopped with residents")
            if h.ctl.readiness()["ready"]:
                self.assertTrue(h.ctl.health.evaluate(h.ctl.clock.now())["healthy"])
            self.assertEqual(set(h.ctl.sup.workloads) - set(h.rt.running) - h.rt.leak, set())
        self.assertEqual(h.ctl.slo.report()["transition_legality"]["violations"], 0)
        self.assertEqual(h.ctl.slo.report()["drain_completeness"]["violations"], 0)

    def test_many_seeds(self):
        for seed in range(int(os.environ.get("GAP01_PROPERTY_SEEDS", "40"))):
            self.run_seed(seed)


class ConcurrencyTest(unittest.TestCase):
    def test_parallel_admit_health_drain(self):
        h = Harness(config=SupervisorConfig(rate_burst=100_000, rate_per_second=100_000,
                                            max_queue_depth=1000))
        h.make_ready()
        barrier = threading.Barrier(8)
        results = []

        def worker(i):
            barrier.wait()
            for j in range(25):
                if i == 0 and j == 12:
                    results.append(h.call("cp", "drain"))
                elif i % 2:
                    results.append(h.admit(f"w{j % 10}"))
                else:
                    results.append(h.call("hr", "report_health", {"signal": "runtime", "ok": True}))

        ts = [threading.Thread(target=worker, args=(i,)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        admitted = [r["result"]["admitted"] for r in results if r.get("ok") and "admitted" in r.get("result", {})]
        self.assertEqual(len(admitted), len(set(admitted)), "duplicate admission under race")
        self.assertIn(h.ctl.sup.state, ("draining", "stopped"))
        if h.ctl.sup.state == "stopped":
            self.assertEqual(h.ctl.sup.workloads, {})
        self.assertTrue(AuditLog.verify(h.ctl.dir / "audit.jsonl")[0])
        self.assertEqual(h.ctl.store.generation, h.restart().ctl.store.generation - 1)


class FuzzTest(unittest.TestCase):
    def test_random_bytes_never_crash(self):
        h = Harness()
        rnd = random.Random(7)
        for i in range(500):
            n = rnd.randrange(0, 300)
            blob = bytes(rnd.randrange(256) for _ in range(n))
            if i % 3 == 0:
                blob = json.dumps({"schema": "PK_NODE_LIFECYCLE/1", "op": rnd.choice(["admit", "x", 5]),
                                   "args": rnd.choice([{}, [], None, {"to": "ready"}])}).encode()
            r = h.ctl.handle(blob)
            self.assertFalse(r["ok"])
            self.assertEqual(validate("error", r["error"]), [])

    def test_oversized(self):
        h = Harness()
        r = h.ctl.handle(b"{" + b" " * 70_000 + b"}")
        self.assertEqual(code(r), "E_BAD_REQUEST")


if __name__ == "__main__":
    unittest.main()
