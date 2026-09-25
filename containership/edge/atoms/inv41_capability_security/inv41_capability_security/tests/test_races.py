"""Deterministic race and stress suite (Section 21).

Linearization contract (docs/REQUIREMENTS.md REQ-CON-003): once
``Membrane.revoke()`` has returned, no use/attenuate/wrap/bind of a descendant
may succeed.  A use that *started* before revoke may complete.  These tests
force the dangerous interleavings with barriers and random yields.
"""
from __future__ import annotations

import gc
import os
import sys
import threading
import time
import unittest

from _common import SEED, rng

from inv41_capability_security.capabilities import Authority, CapabilityError, Membrane, Revoked

WORKERS = int(os.environ.get("INV41_RACE_WORKERS", "12"))
ROUNDS = int(os.environ.get("INV41_RACE_ROUNDS", "40"))


def _run(workers):
    for w in workers:
        w.start()
    for w in workers:
        w.join(timeout=10)
    return [w for w in workers if w.is_alive()]


class RaceTest(unittest.TestCase):
    def setUp(self):
        self.old = sys.getswitchinterval()
        sys.setswitchinterval(1e-6)  # maximize preemption
        self.a = Authority({"s": {"read", "write"}}, authority_id="race")

    def tearDown(self):
        sys.setswitchinterval(self.old)

    def _post_revoke_probe(self, action_factory, rounds=ROUNDS):
        stale = []
        for rnd in range(rounds):
            m = Membrane(f"m{rnd}")
            base = m.wrap(self.a.grant("s"))
            done = threading.Event()
            barrier = threading.Barrier(WORKERS + 1)
            action = action_factory(base, m)

            def worker():
                barrier.wait()
                for _ in range(50):
                    after = done.is_set()
                    try:
                        action()
                    except Revoked:
                        continue
                    except CapabilityError:
                        continue
                    if after:
                        stale.append(rnd)

            ts = [threading.Thread(target=worker) for _ in range(WORKERS)]
            for t in ts:
                t.start()
            barrier.wait()
            time.sleep(0)
            m.revoke()
            done.set()
            for t in ts:
                t.join(timeout=10)
            self.assertFalse([t for t in ts if t.is_alive()], "deadlock/hang")
        self.assertEqual(stale, [], f"seed={SEED}: success observed after revoke() returned")

    def test_RC001_use_vs_revoke(self):
        self._post_revoke_probe(lambda ref, m: (lambda: ref.invoke("read")))

    def test_RC002_attenuate_vs_revoke(self):
        self._post_revoke_probe(lambda ref, m: (lambda: ref.attenuate({"read"})))

    def test_RC003_bind_vs_revoke(self):
        self._post_revoke_probe(lambda ref, m: (lambda: self.a.bind_holder("h", {"x": ref})))

    def test_RC004_nested_wrap_vs_inner_and_outer_revoke(self):
        def factory(ref, inner):
            outer = Membrane("outer")

            def act():
                w = outer.wrap(ref)
                w.invoke("read")
            return act
        self._post_revoke_probe(factory)

    def test_RC005_concurrent_double_revoke(self):
        for _ in range(ROUNDS):
            m = Membrane("dbl")
            refs = [m.wrap(self.a.grant("s")) for _ in range(20)]
            results = []
            barrier = threading.Barrier(WORKERS)
            ts = [threading.Thread(target=lambda: (barrier.wait(), results.append(m.revoke()))) for _ in range(WORKERS)]
            self.assertEqual(_run(ts), [])
            self.assertTrue(all(r["revoked"] for r in results))
            self.assertTrue(all(r["references_killed"] == 20 for r in results))
            for r in refs:
                with self.assertRaises(Revoked):
                    r.invoke("read")

    def test_RC006_live_reference_accounting_under_churn(self):
        m = Membrane("acct")
        keep = []
        lock = threading.Lock()
        r = rng(60)
        seeds = [r.random() for _ in range(WORKERS)]

        def churn(p):
            local = []
            for i in range(300):
                ref = m.wrap(self.a.grant("s"))
                if (i * p) % 1 < 0.3:
                    local.append(ref)
            with lock:
                keep.extend(local)

        self.assertEqual(_run([threading.Thread(target=churn, args=(s,)) for s in seeds]), [])
        gc.collect()
        self.assertEqual(m.live_reference_count, len(keep))
        result = m.revoke()
        self.assertEqual(result["references_killed"], len(keep))

    def test_RC007_multi_membrane_graph_revoke_levels(self):
        root = Membrane("root")
        mids = [Membrane(f"mid{i}") for i in range(4)]
        leaves = []
        base = root.wrap(self.a.grant("s"))
        for mid in mids:
            mref = mid.wrap(base)
            for j in range(5):
                leaves.append((mid, Membrane(f"leaf{j}").wrap(mref.attenuate({"read"}))))
        mids[1].revoke()
        for mid, leaf in leaves:
            if mid is mids[1]:
                with self.assertRaises(Revoked):
                    leaf.invoke("read")
            else:
                self.assertTrue(leaf.invoke("read")["permitted"])
        stop = threading.Event()
        errors = []

        def user(leaf):
            while not stop.is_set():
                try:
                    leaf.invoke("read")
                except Revoked:
                    return
                except Exception as exc:
                    errors.append(exc)
                    return

        ts = [threading.Thread(target=user, args=(l,)) for _m, l in leaves]
        for t in ts:
            t.start()
        root.revoke()
        stop.set()
        for t in ts:
            t.join(timeout=5)
        self.assertEqual(errors, [])
        for _m, leaf in leaves:
            with self.assertRaises(Revoked):
                leaf.invoke("read")


if __name__ == "__main__":
    unittest.main()
