"""Components 05 (controller adapters), 06 (live-state applier), 07 (atomic
apply), 08 (persistent state), 09 (leases/fencing), 19 (crash recovery), 32
(backup/restore)."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
import unittest

import fixtures as F
from inv07_gitops_transition_layer.components import errors as E
from inv07_gitops_transition_layer.components.apply import Transaction, plan
from inv07_gitops_transition_layer.components.controllers import ArgoCDAdapter, FluxAdapter, wait_converged
from inv07_gitops_transition_layer.components.lease import FenceGate, FileLease
from inv07_gitops_transition_layer.components.state import ControllerState, backup, restore, verify_backup
from inv07_gitops_transition_layer.components.target import OWNER_ANN, DirectoryTarget, KubernetesTarget


def cm(name, v="1", ns="team-a"):
    return {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": name, "namespace": ns}, "data": {"v": v}}


def rid(o):
    return ("", o["kind"], o["metadata"].get("namespace", ""), o["metadata"]["name"])


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="inv07-t-")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)


class TestTarget(_Tmp):
    def test_cas_ownership_fencing_and_delete_safety(self):
        t = DirectoryTarget(os.path.join(self.d, "t"), namespaces=("team-a",))
        o = cm("a")
        v1 = t.apply(rid(o), o, expected_version=None, epoch=1, owner="me")
        with self.assertRaises(E.Conflict):
            t.apply(rid(o), o, expected_version=None, epoch=1, owner="me")          # stale precondition
        with self.assertRaises(E.Conflict):
            t.apply(rid(o), o, expected_version=v1, epoch=1, owner="someone-else")  # field ownership
        t.apply(rid(o), o, expected_version=v1, epoch=2, owner="me")
        with self.assertRaises(E.FencedOff):
            t.apply(rid(o), o, expected_version="2", epoch=1, owner="me")          # stale leader
        with self.assertRaises(E.Conflict):
            t.delete(rid(o), expected_version="2", epoch=2, owner="me")              # prune disabled
        with self.assertRaises(E.TenantViolation):
            t.apply(rid(cm("x", ns="other")), cm("x", ns="other"), expected_version=None, epoch=2, owner="me")
        self.assertEqual(t.apply(rid(o), o, expected_version="2", epoch=2, owner="me", dry_run=True), "3")
        self.assertEqual(t.get(rid(o))[1], "2")                                     # dry-run wrote nothing

    def test_fence_gate_is_durable(self):
        p = os.path.join(self.d, "fence")
        FenceGate(p).check(7)
        with self.assertRaises(E.FencedOff):
            FenceGate(p).check(6)


class TestKubernetesAdapter(unittest.TestCase):
    def test_server_side_apply_requests(self):
        calls = []

        def transport(method, path, headers, body):
            calls.append((method, path, headers, json.loads(body)))
            return (200, json.dumps({"metadata": {"resourceVersion": "42"}}).encode())
        k = KubernetesTarget(transport, fence=FenceGate(), allow_delete=True, namespaces=("team-a",))
        dep = {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "web", "namespace": "team-a"}}
        self.assertEqual(k.apply(("apps", "Deployment", "team-a", "web"), dep, expected_version="41", epoch=1,
                                 owner="inv07"), "42")
        m, path, h, body = calls[0]
        self.assertEqual((m, h["Content-Type"]), ("PATCH", "application/apply-patch+yaml"))
        self.assertEqual(path, "/apis/apps/v1/namespaces/team-a/deployments/web?fieldManager=inv07-gitops&force=false")
        self.assertEqual(body["metadata"]["resourceVersion"], "41")
        self.assertEqual(body["metadata"]["annotations"][OWNER_ANN], "inv07")
        k.delete(("", "ConfigMap", "team-a", "c"), expected_version="5", epoch=1, owner="inv07")
        self.assertEqual(calls[1][3]["preconditions"], {"resourceVersion": "5"})
        with self.assertRaises(E.Malformed):
            k.path("v1", "ConfigMap", "team-a", "../../x")
        with self.assertRaises(E.Malformed):
            k.path("v1", "Unknown", "team-a", "x")

    def test_status_mapping(self):
        for st, exc in ((409, E.Conflict), (503, E.TargetUnavailable), (403, E.Conflict)):
            k = KubernetesTarget(lambda *a, s=st: (s, b"{}"), fence=FenceGate())
            with self.subTest(st=st), self.assertRaises(exc):
                k.apply(("", "ConfigMap", "team-a", "c"), cm("c"), expected_version=None, epoch=1, owner="o")


class TestControllerAdapters(unittest.TestCase):
    OID = "a" * 40

    def test_argo_render_pins_oid_and_normalises(self):
        a = ArgoCDAdapter()
        app = a.render(name="web", repo_url="https://git.example/r", oid=self.OID, path="deploy", dest_ns="team-a")
        self.assertEqual(app["spec"]["source"]["targetRevision"], self.OID)
        with self.assertRaises(E.Malformed):
            a.render(name="w", repo_url="u", oid="main", path="p", dest_ns="n")
        mk = lambda s, h, r=self.OID: {"status": {"sync": {"status": s, "revision": r}, "health": {"status": h}}}
        self.assertEqual(a.normalise(mk("Synced", "Healthy"), oid=self.OID)["state"], "converged")
        self.assertEqual(a.normalise(mk("OutOfSync", "Healthy"), oid=self.OID)["state"], "drifted")
        self.assertEqual(a.normalise(mk("Synced", "Progressing"), oid=self.OID)["state"], "in_progress")
        self.assertEqual(a.normalise(mk("Synced", "Degraded"), oid=self.OID)["state"], "failed")
        self.assertEqual(a.normalise(mk("Synced", "Healthy", "b" * 40), oid=self.OID)["state"], "failed")
        self.assertEqual(a.normalise({}, oid=self.OID)["state"], "unknown")

    def test_flux_render_and_normalise(self):
        f = FluxAdapter()
        objs = f.render(name="web", repo_url="https://git.example/r", oid=self.OID, path="./deploy")
        self.assertEqual(objs[0]["spec"]["ref"], {"commit": self.OID})
        ok = {"status": {"lastAppliedRevision": "main@sha1:" + self.OID,
                         "conditions": [{"type": "Ready", "status": "True", "reason": "ReconciliationSucceeded"}]}}
        self.assertEqual(f.normalise(ok, oid=self.OID)["state"], "converged")
        bad = {"status": {"conditions": [{"type": "Stalled", "status": "True"}, {"type": "Ready", "status": "False"}]}}
        self.assertEqual(f.normalise(bad, oid=self.OID)["state"], "failed")
        other = {"status": {"lastAppliedRevision": "main@sha1:" + "c" * 40,
                            "conditions": [{"type": "Ready", "status": "True"}]}}
        self.assertEqual(f.normalise(other, oid=self.OID)["state"], "failed")

    def test_bounded_wait(self):
        a = ArgoCDAdapter()
        seq = iter([{"status": {"health": {"status": "Progressing"}}}] * 3 +
                   [{"status": {"sync": {"status": "Synced", "revision": self.OID}, "health": {"status": "Healthy"}}}])
        self.assertEqual(wait_converged(lambda: next(seq), a.normalise, oid=self.OID, deadline_s=100,
                                        sleep=lambda s: None)["state"], "converged")
        clock = iter(range(0, 1000, 10))
        with self.assertRaises(E.DeadlineExceeded):
            wait_converged(lambda: {}, a.normalise, oid=self.OID, deadline_s=25, interval=10, sleep=lambda s: None,
                           clock=lambda: next(clock))


class TestTransaction(_Tmp):
    def _setup(self, fail=None, prune=False):
        t = DirectoryTarget(os.path.join(self.d, "t"), fail=fail, allow_delete=prune)
        s = ControllerState(os.path.join(self.d, "s"))
        return t, s

    def test_deterministic_order_and_noop(self):
        desired = {rid(o): o for o in (cm("b"), cm("a"))}
        desired[("", "Namespace", "", "team-a")] = {"apiVersion": "v1", "kind": "Namespace",
                                                    "metadata": {"name": "team-a"}}
        a1 = plan(desired, {}, owner="me", prune=False, revision="r")
        a2 = plan(dict(reversed(list(desired.items()))), {}, owner="me", prune=False, revision="r")
        self.assertEqual(a1, a2)
        self.assertEqual(a1[0]["rid"][1], "Namespace")
        t, s = self._setup()
        Transaction(t, s, owner="me", epoch=1, revision="r" * 40, ref="refs/heads/main").run(a1, desired, {}, at=1)
        self.assertEqual(plan(desired, t.list(), owner="me", prune=False, revision="r"), [])

    def test_preflight_failure_mutates_nothing(self):
        n = {"i": 0}

        def fail(op, r):
            if r[3] == "b":
                raise E.TargetUnavailable("injected")
        t, s = self._setup(fail=fail)
        desired = {rid(o): o for o in (cm("a"), cm("b"))}
        with self.assertRaises(E.ApplyFailed):
            Transaction(t, s, owner="me", epoch=1, revision="r" * 40, ref="x").run(
                plan(desired, {}, owner="me", prune=False, revision="r"), desired, {}, at=1)
        self.assertEqual(t.list(), {})
        self.assertEqual(s.s["intents"], {})
        self.assertEqual(n["i"], 0)

    def test_mid_apply_failure_is_compensated(self):
        calls = {"n": 0}
        t, s = self._setup()
        base = {rid(cm("a", "1")): cm("a", "1")}
        Transaction(t, s, owner="me", epoch=1, revision="1" * 40, ref="x").run(
            plan(base, {}, owner="me", prune=False, revision="1"), base, {}, at=1)
        live = t.list()

        def fail(op, r):
            if op == "apply":
                calls["n"] += 1
                if calls["n"] == 4:     # 2 preflights pass, 1st real apply ok, 2nd real apply fails
                    raise E.TargetUnavailable("injected")
        t._fail = fail
        desired = {rid(cm("a", "2")): cm("a", "2"), rid(cm("b")): cm("b")}
        with self.assertRaises(E.ApplyFailed):
            Transaction(t, s, owner="me", epoch=1, revision="2" * 40, ref="x").run(
                plan(desired, live, owner="me", prune=False, revision="2"), desired, live, at=2)
        after = t.list()
        self.assertEqual(set(after), set(live))
        self.assertEqual(after[rid(cm("a"))][0]["data"], {"v": "1"})
        self.assertTrue(any(v["status"] == "aborted:compensated" for v in s.s["intents"].values()))

    def test_failed_compensation_is_partial_apply(self):
        t, s = self._setup()
        calls = {"n": 0}

        def fail(op, r):
            calls["n"] += 1
            if calls["n"] >= 4:
                raise E.TargetUnavailable("down")
        t._fail = fail
        desired = {rid(o): o for o in (cm("a"), cm("b"))}
        with self.assertRaises(E.PartialApply):
            Transaction(t, s, owner="me", epoch=1, revision="3" * 40, ref="x").run(
                plan(desired, {}, owner="me", prune=False, revision="3"), desired, {}, at=1)

    def test_duplicate_intent_suppressed(self):
        t, s = self._setup()
        desired = {rid(cm("a")): cm("a")}
        acts = plan(desired, {}, owner="me", prune=False, revision="4")
        tx = Transaction(t, s, owner="me", epoch=1, revision="4" * 40, ref="x")
        self.assertFalse(tx.run(acts, desired, {}, at=1)["duplicate"])
        t2 = DirectoryTarget(os.path.join(self.d, "t2"))
        self.assertTrue(Transaction(t2, s, owner="me", epoch=1, revision="4" * 40, ref="x")
                        .run(acts, desired, {}, at=1)["duplicate"])

    def test_prune_deletes_only_owned_in_reverse_order(self):
        t, s = self._setup(prune=True)
        desired = {rid(o): o for o in (cm("a"), cm("b"))}
        Transaction(t, s, owner="me", epoch=1, revision="5" * 40, ref="x").run(
            plan(desired, {}, owner="me", prune=True, revision="5"), desired, {}, at=1)
        foreign = cm("human")
        t.apply(rid(foreign), foreign, expected_version=None, epoch=1, owner="human")
        acts = plan({}, t.list(), owner="me", prune=True, revision="6")
        self.assertEqual([a["rid"][3] for a in acts], ["b", "a"])


class TestState(_Tmp):
    def test_persistence_and_schema_version(self):
        s = ControllerState(self.d)
        s.begin("k", oid="a" * 40, ref="r", plan=[], fence=1)
        s.commit("k", oid="a" * 40, ref="r", at=1, live_digest_map={"x": "y"})
        s.cursor("r", "a" * 40)
        s.drift({"n": 1})
        s2 = ControllerState(self.d)
        self.assertEqual(s2.applied()[0]["oid"], "a" * 40)
        self.assertEqual(s2.s["cursors"], {"r": "a" * 40})
        self.assertEqual(s2.s["last_live"], {"x": "y"})
        s2.checkpoint()
        s3 = ControllerState(self.d)
        self.assertEqual(s3.s["seq"], s2.s["seq"])
        with open(os.path.join(self.d, "STATE_VERSION"), "w") as fh:
            fh.write("PK_GITOPS_STATE/99")
        with self.assertRaises(E.StateVersion):
            ControllerState(self.d)

    def test_journal_bound(self):
        s = ControllerState(self.d, max_journal_bytes=300)
        with self.assertRaises(E.LimitExceeded):
            for i in range(20):
                s.cursor("r", str(i) * 40)


class TestRecovery(_Tmp):
    def test_torn_tail_truncated_mid_file_corruption_raises(self):
        s = ControllerState(self.d)
        s.cursor("r", "a" * 40)
        s.cursor("r", "b" * 40)
        with open(os.path.join(self.d, "journal.wal"), "ab") as fh:
            fh.write(b"deadbeef\t{\"half")
        s2 = ControllerState(self.d)
        self.assertGreater(s2.recovered_dropped_bytes, 0)
        self.assertEqual(s2.s["cursors"]["r"], "b" * 40)
        with open(os.path.join(self.d, "journal.wal"), "rb") as fh:
            data = bytearray(fh.read())
        data[12] ^= 0x01
        with open(os.path.join(self.d, "journal.wal"), "wb") as fh:
            fh.write(bytes(data))
        with self.assertRaises(E.Corrupted):
            ControllerState(self.d)

    def test_ambiguous_intent_after_crash_is_read_back(self):
        e = F.Env()
        try:
            e.commit({"a.json": F.configmap()})
            c = e.controller()
            c.state.begin("crashed", oid="f" * 40, ref="refs/heads/main", plan=[], fence=1)   # crash mid-apply
            c2 = e.controller()   # restart: build() calls recover()
            self.assertEqual(c2.state.pending_intents(), {})
            self.assertTrue(any(x["kind"] == "recover.ambiguous_intent" for x in c2.audit.entries()))
            self.assertEqual(c2.reconcile("refs/heads/main")["outcome"], "applied")
        finally:
            e.cleanup()


class TestLease(_Tmp):
    def test_single_leader_takeover_and_fencing(self):
        now = {"t": 1000.0}
        clk = lambda: now["t"]  # noqa: E731
        a = FileLease(self.d, "c", node="a", ttl=10, clock=clk)
        b = FileLease(self.d, "c", node="b", ttl=10, clock=clk)
        ea = a.acquire()
        with self.assertRaises(E.NotLeader):
            b.acquire()
        now["t"] += 5
        self.assertEqual(a.renew(), ea)
        now["t"] += 11                       # a paused past ttl
        eb = b.acquire()
        self.assertEqual(eb, ea + 1)
        with self.assertRaises(E.FencedOff):
            a.renew()
        gate = FenceGate()
        gate.check(eb)
        with self.assertRaises(E.FencedOff):
            gate.check(ea)                   # split brain harmless
        b.release()
        self.assertEqual(a.acquire(), eb + 1)

    def test_concurrent_acquire_one_winner(self):
        wins, errs = [], []

        def go(n):
            try:
                wins.append((n, FileLease(self.d, "race", node=n, ttl=30).acquire()))
            except E.NotLeader:
                errs.append(n)
        ts = [threading.Thread(target=go, args=(f"n{i}",)) for i in range(8)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(len(wins), 1, wins)


class TestBackup(_Tmp):
    def test_backup_verify_restore_refuse_overwrite_and_tamper(self):
        src = os.path.join(self.d, "src")
        s = ControllerState(src)
        s.cursor("r", "a" * 40)
        man = backup(src, os.path.join(self.d, "bk"))
        self.assertIn("journal.wal", man["files"])
        verify_backup(os.path.join(self.d, "bk"))
        restore(os.path.join(self.d, "bk"), os.path.join(self.d, "dst"))
        self.assertEqual(ControllerState(os.path.join(self.d, "dst")).s["cursors"], {"r": "a" * 40})
        with self.assertRaises(E.Corrupted):
            restore(os.path.join(self.d, "bk"), os.path.join(self.d, "dst"))
        with open(os.path.join(self.d, "bk", "journal.wal"), "ab") as fh:
            fh.write(b"x")
        with self.assertRaises(E.Corrupted):
            restore(os.path.join(self.d, "bk"), os.path.join(self.d, "dst2"))


if __name__ == "__main__":
    unittest.main()
