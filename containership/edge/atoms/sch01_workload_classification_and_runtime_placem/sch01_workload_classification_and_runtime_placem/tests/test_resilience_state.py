"""MC-08, MC-09, MC-18, MC-21, MC-22, MC-23, MC-29..MC-34, MC-37..MC-41, MC-47, MC-53."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import tempfile
import threading
import unittest

from _fx import Rig, cfg, keys, rs, sch
from sch01_workload_classification_and_runtime_placem import errors, lifecycle, state
from sch01_workload_classification_and_runtime_placem.errors import SchedulerError


class ErrorContractTest(unittest.TestCase):
    """MC-18 unified error contract."""

    def test_every_code_documented(self):
        for code, spec in errors.CATALOG.items():
            self.assertTrue(spec.action and spec.category and isinstance(spec.retryable, bool), code)

    def test_engine_exceptions_translated(self):
        self.assertEqual(errors.from_exception(ValueError("x")).code, "INVALID_REQUEST")
        self.assertEqual(errors.from_exception(sch.Unplaceable("x", code="NO_CANDIDATE")).code, "NO_CANDIDATE")
        e = errors.from_exception(RuntimeError("secret internals"))
        self.assertEqual(e.code, "INTERNAL"); self.assertNotIn("secret", str(e))
        self.assertEqual(SchedulerError("BOGUS", "m").code, "INTERNAL")

    def test_service_raises_only_catalogued(self):
        r = Rig()
        with self.assertRaises(SchedulerError) as e: r.place()
        self.assertEqual(e.exception.as_dict()["schema"], "PK_SCHEDULER_ERROR/2")


class LifecycleTest(unittest.TestCase):
    """MC-08 state machine and MC-09 version policy."""

    def test_lease_transitions(self):
        r = Rig(); r.node("n1"); lid = r.place()["lease_id"]
        r.s.transition(r.tok(), lid, "ADMITTED"); r.s.transition(r.tok(), lid, "RUNNING")
        with self.assertRaises(SchedulerError) as e: r.s.transition(r.tok(), lid, "ADMITTED")
        self.assertEqual(e.exception.code, "ILLEGAL_TRANSITION")
        r.s.transition(r.tok(), lid, "RELEASED")
        with self.assertRaises(SchedulerError): r.s.transition(r.tok(), lid, "RUNNING")

    def test_expiry(self):
        r = Rig(); r.node("n1"); lid = r.place()["lease_id"]
        r.clock.t += 61; self.assertEqual(r.s.expire(), [lid])

    def test_result_classes(self):
        self.assertEqual(lifecycle.result_class("NO_CANDIDATE"), "RETRYABLE_FAILURE")
        self.assertEqual(lifecycle.result_class("FORBIDDEN"), "TERMINAL_FAILURE")

    def test_version_negotiation_and_downgrade(self):
        self.assertEqual(lifecycle.negotiate("PK_PLACEMENT/1"), "deprecated")
        for bad in ("PK_PLACEMENT/9", "junk", "NOPE/1"):
            with self.assertRaises(SchedulerError): lifecycle.negotiate(bad)
        r = Rig(); r.node("n1"); v1 = lifecycle.downgrade_placement_v2_to_v1(r.place())
        self.assertEqual(v1["schema"], "PK_PLACEMENT/1")


class ConfigTest(unittest.TestCase):
    """MC-22 declarative config and MC-23 provenance + transactional activation/rollback."""

    def test_activate_reject_rollback(self):
        r = Rig(); c = r.config
        doc = dict(cfg.DEFAULT_CONFIG, lease_ticks=120)
        rev = c.activate(c.sign(doc, c.active.rev_id), author="ops", at=5, reason="longer leases")
        self.assertEqual((rev.rev, c.get("lease_ticks")), (2, 120))
        with self.assertRaises(SchedulerError): c.activate(c.sign(dict(doc, lease_ticks=-1), c.active.rev_id), author="x", at=6)
        with self.assertRaises(SchedulerError): c.activate(c.sign(doc, "stale"), author="x", at=6)
        forged = c.sign(dict(doc, lease_ticks=5), c.active.rev_id); forged["body"]["doc"]["lease_ticks"] = 1
        with self.assertRaises(SchedulerError): c.activate(forged, author="x", at=6)
        self.assertEqual(c.active.rev, 2); self.assertEqual(len(c.rejected), 3)
        c.rollback(1, author="ops", at=7); self.assertEqual(c.get("lease_ticks"), 60)
        self.assertEqual([p["rev"] for p in c.provenance()], [1, 2, 3])

    def test_unknown_keys_rejected(self):
        self.assertTrue(cfg.validate_config(dict(cfg.DEFAULT_CONFIG, surprise=1)))

    def test_concurrent_activation_one_wins(self):
        r = Rig(); c = r.config; parent = c.active.rev_id; wins = []
        def go(n):
            try: c.activate(c.sign(dict(cfg.DEFAULT_CONFIG, lease_ticks=60 + n), parent), author=str(n), at=1); wins.append(n)
            except SchedulerError: pass
        ts = [threading.Thread(target=go, args=(i,)) for i in range(8)]; [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(wins), 1)


class RequestContractTest(unittest.TestCase):
    """MC-21 deadline, cancellation, idempotency, backpressure; MC-30 breaker, retry."""

    def test_idempotent_replay_and_conflict(self):
        r = Rig(); r.node("n1"); ctx = r.ctx(key="K")
        a = r.place(ctx=ctx); b = r.place(ctx=r.ctx(key="K"))
        self.assertEqual(a, b); self.assertEqual(len(r.s.leases), 1)
        with self.assertRaises(SchedulerError) as e: r.place(r.req(name="other"), ctx=r.ctx(key="K"))
        self.assertEqual(e.exception.code, "IDEMPOTENCY_CONFLICT")

    def test_deadline_and_cancel_commit_nothing(self):
        r = Rig(); r.node("n1")
        with self.assertRaises(SchedulerError) as e: r.place(ctx=r.ctx(deadline=r.clock() - 1))
        self.assertEqual(e.exception.code, "DEADLINE_EXCEEDED")
        c = r.ctx(); c.cancelled.set()
        with self.assertRaises(SchedulerError): r.place(ctx=c)
        self.assertEqual(r.s.leases, {})

    def test_breaker_opens_and_half_opens(self):
        clk = [0]; b = rs.CircuitBreaker("x", 2, 10, lambda: clk[0])
        def boom(): raise SchedulerError("SECRET_UNAVAILABLE", "down")
        for _ in range(2):
            with self.assertRaises(SchedulerError): b.call(boom)
        with self.assertRaises(SchedulerError) as e: b.call(lambda: 1)
        self.assertEqual(e.exception.code, "CIRCUIT_OPEN")
        clk[0] = 10; self.assertEqual(b.call(lambda: 1), 1); self.assertEqual(b.state, "CLOSED")

    def test_retry_bounded_and_skips_terminal(self):
        calls, slept = [], []
        def f():
            calls.append(1); raise SchedulerError("OVERLOADED", "x")
        with self.assertRaises(SchedulerError): rs.retry(f, max_attempts=3, sleep=slept.append)
        self.assertEqual(len(calls), 3)
        calls.clear()
        with self.assertRaises(SchedulerError): rs.retry(lambda: (calls.append(1), (_ for _ in ()).throw(SchedulerError("FORBIDDEN", "x"))), max_attempts=3, sleep=slept.append)
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(d <= 2000 for d in rs.backoff_schedule(10, 50, 2000)))


class DurableStateTest(unittest.TestCase):
    """MC-31 restart/replay, MC-53 backup/restore, torn writes, corruption."""

    def test_restart_reconstructs_leases_and_quota(self):
        r = Rig(tenant_quota={"t1": 1}); r.node("n1"); r.place()
        r2 = Rig(tmp=r.tmp, secrets=r.secrets, clock=r.clock, tenant_quota={"t1": 1}); r2.node("n1")
        self.assertEqual(len(r2.s.leases), 1)
        with self.assertRaises(SchedulerError) as e: r2.place(name="w2")
        self.assertEqual(e.exception.code, "QUOTA_EXCEEDED")

    def test_torn_tail_tolerated_corruption_refused(self):
        r = Rig(); r.node("n1"); r.place(); j = r.s.journal.path
        with open(j, "a") as f: f.write('{"seq": 2, "trunc')
        self.assertEqual(len(state.Journal(j).replay()), 1)
        lines = j.read_text().splitlines()[:1]; rec = json.loads(lines[0]); rec["event"]["lease"]["node"] = "evil"
        j.write_text(json.dumps(rec) + "\n")
        with self.assertRaises(SchedulerError) as e: state.Journal(j).replay()
        self.assertEqual(e.exception.code, "STATE_CORRUPT")

    def test_backup_restore(self):
        r = Rig(); r.node("n1"); r.place()
        d = tempfile.mkdtemp(); man = state.backup(r.s.journal, os.path.join(d, "b.jsonl"))
        j = state.restore(os.path.join(d, "b.jsonl"), os.path.join(d, "restored.jsonl"))
        self.assertEqual(j.head, man["head"])
        with open(os.path.join(d, "b.jsonl"), "a") as f: f.write("x\n")
        with self.assertRaises(SchedulerError): state.restore(os.path.join(d, "b.jsonl"), os.path.join(d, "r2.jsonl"))


def _worker(tmp, q):
    """Separate OS process: acquires a new epoch, then the old owner must be fenced."""
    fa = state.FencingAuthority(os.path.join(tmp, "epoch")); q.put(fa.acquire())


class FencingRaceTest(unittest.TestCase):
    """MC-32 fencing and MC-47 multi-process race / stale-writer / split-brain tests."""

    def test_stale_writer_fenced_after_other_process_takes_over(self):
        r = Rig(); r.node("n1"); r.place()
        q = mp.Queue(); p = mp.Process(target=_worker, args=(r.tmp, q)); p.start(); p.join()
        self.assertGreater(q.get(), r.s.epoch)
        with self.assertRaises(SchedulerError) as e: r.place(name="w2")
        self.assertEqual(e.exception.code, "FENCED")
        self.assertEqual(r.s.health()["state"], "FENCED")
        self.assertEqual(len(state.Journal(r.s.journal.path).replay()), 1)   # nothing written by stale owner

    def test_concurrent_epoch_acquisition_unique(self):
        tmp = tempfile.mkdtemp(); q = mp.Queue()
        ps = [mp.Process(target=_worker, args=(tmp, q)) for _ in range(6)]; [p.start() for p in ps]; [p.join() for p in ps]
        got = sorted(q.get() for _ in ps); self.assertEqual(got, list(range(1, 7)))

    def test_threads_do_not_oversubscribe(self):
        r = Rig(); r.node("n1", slots=5); ok, bad = [], []
        def go(i):
            try: ok.append(r.place(name=f"w{i}", tenant="t1"))
            except SchedulerError as e: bad.append(e.code)
        ts = [threading.Thread(target=go, args=(i,)) for i in range(20)]; [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(ok), 5)


class OperatorAndFaultTest(unittest.TestCase):
    """MC-33 operator controls and MC-34 fault injection / recovery."""

    def op(self, r): return r.tok("op", "human", (), ("operator",))

    def test_freeze_disable_quarantine(self):
        r = Rig(); r.node("n1"); r.node("n2")
        r.s.operator(self.op(r), "freeze", reason="incident")
        with self.assertRaises(SchedulerError) as e: r.place(); self.assertEqual(e.exception.code, "FROZEN")
        r.s.operator(self.op(r), "unfreeze", reason="ok")
        r.s.operator(self.op(r), "quarantine", node="n1", reason="bad dimm")
        self.assertEqual(r.place()["node"], "n2")
        r.s.operator(self.op(r), "disable", reason="kill switch")
        with self.assertRaises(SchedulerError) as e: r.place(name="w2")
        self.assertEqual(e.exception.code, "SCHEDULER_DISABLED")
        self.assertTrue(any(a["action"] == "operator.disable" for a in r.s.audit.read()))

    def test_clock_regression_refused(self):
        r = Rig(); r.node("n1"); r.place(); r.clock.t -= 5
        with self.assertRaises(SchedulerError): r.place(name="w2")

    def test_node_loss_and_site_partition(self):
        r = Rig(); r.node("a", site="eu"); r.clock.t += 31
        with self.assertRaises(SchedulerError) as e: r.place(site_affinity="eu")
        self.assertIn("STALE_REPORT", e.exception.details["rejection_counts"])

    def test_crash_mid_commit_recovers(self):
        r = Rig(); r.node("n1"); r.place()
        with open(r.s.journal.path, "a") as f: f.write('{"partial":')     # crash during append
        r2 = Rig(tmp=r.tmp, secrets=r.secrets, clock=r.clock); r2.node("n1")
        self.assertEqual(r2.s.state, "READY"); r2.place(name="w2")
        self.assertEqual(len(r2.s.journal.replay()), 2)


class ObservabilityTest(unittest.TestCase):
    """MC-37 health, MC-38 metrics, MC-39 logs, MC-40 traces, MC-41 explain."""

    def test_surfaces(self):
        r = Rig(); r.node("n1")
        tp = "00-" + "a" * 32 + "-" + "b" * 16 + "-01"
        out = r.s.place(r.tok(), r.req(), r.ctx(), traceparent=tp)
        h = r.s.health()
        self.assertTrue(h["ready"]); self.assertEqual(h["version"], sch.__version__)
        txt = r.s.metrics.export()
        self.assertIn('sch01_placements_total{outcome="placed"', txt); self.assertIn("sch01_placement_seconds_bucket", txt)
        log = r.s.log.lines[-1]
        self.assertEqual(set(log), set(__import__("sch01_workload_classification_and_runtime_placem.telemetry", fromlist=["x"]).LOG_FIELDS))
        self.assertNotEqual(log["tenant_ref"], "t1")
        self.assertEqual(r.s.tracer.spans[-1]["trace_id"], "a" * 32); self.assertEqual(out["explain"]["trace_id"], "a" * 32)
        ex = r.s.explain(r.tok(roles=("auditor",)), out["lease_id"])
        self.assertEqual(ex["config"]["rev"], 1); self.assertTrue(ex["audit"])
        with self.assertRaises(SchedulerError): r.s.explain(r.tok(tenants=("t2",), roles=("auditor",)), out["lease_id"])


if __name__ == "__main__":
    unittest.main()
