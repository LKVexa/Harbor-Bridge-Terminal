"""G13-MC-014 / G13-MC-036: concurrent evaluations during bundle swaps (threads and processes)."""
import multiprocessing as mp
import threading
import unittest

import testkit as k
from gap13_policy_engine import errors as E

ALLOW = [{"name": "allow-read", "effect": "allow", "scope": "estate", "match": {"action": "read"}}]
DENY = [{"name": "deny-read", "effect": "deny", "scope": "estate", "match": {"action": "read"}}]


class SwapRaceTests(unittest.TestCase):
    def test_every_verdict_is_from_exactly_one_consistent_snapshot(self):
        from gap13_policy_engine.authz import Authorizer, RateLimiter
        clock = k.Clock()
        svc, c = k.service(require_separation_of_duties=False, clock=clock,
                           authorizer=Authorizer("prod", clock=clock.wall, limiter=RateLimiter(10_000)),
                           config=k.g.EngineConfig(limits=k.g.Limits(max_concurrency=1000)))
        admin = k.principal("alice", clock=c)
        app = k.principal("svc-a", ("service",), kind="service", clock=c)
        envs = [k.envelope(i, ALLOW if i % 2 else DENY) for i in range(1, 41)]
        svc.load(admin, envs[0])
        errors, verdicts, stop = [], [], threading.Event()

        def reader():
            while not stop.is_set():
                try:
                    v = svc.evaluate(app, {"action": "read"})
                    verdicts.append((v["bundle"]["generation"], v["effect"], v["rule"]))
                except Exception as exc:  # pragma: no cover
                    errors.append(exc)

        threads = [threading.Thread(target=reader) for _ in range(8)]
        for t in threads:
            t.start()
        try:
            for env in envs[1:]:
                svc.load(admin, env)
        finally:
            stop.set()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        self.assertGreater(len(verdicts), 0)
        for gen, effect, rule in verdicts:
            want = ("allow", "allow-read") if gen % 2 else ("deny", "deny-read")
            self.assertEqual((effect, rule), want, f"torn read at generation {gen}")

    def test_concurrent_arrivals_single_winner_floor(self):
        svc, c = k.service(require_separation_of_duties=False)
        admin = k.principal("alice", clock=c)
        results = []

        def push(gen):
            try:
                svc.load(admin, k.envelope(gen))
                results.append(gen)
            except E.ReplayRejected:
                results.append(-gen)
        ts = [threading.Thread(target=push, args=(g,)) for g in (5, 3, 4, 5, 2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(svc.status()["anti_rollback"]["gap07-publisher|estate|prod"]["generation"], 5)
        self.assertEqual(svc.status()["active"]["generation"], 5)


def _proc_eval(q):
    svc, c = k.service(require_separation_of_duties=False)
    svc.load(k.principal("alice", clock=c), k.envelope(1))
    app = k.principal("svc-a", ("service",), kind="service", clock=c)
    q.put([svc.evaluate(app, {"action": "read"})["effect"] for _ in range(200)])


class MultiProcessTests(unittest.TestCase):
    def test_workers_are_independent_and_deterministic(self):
        ctx = mp.get_context("spawn")
        q = ctx.Queue()
        ps = [ctx.Process(target=_proc_eval, args=(q,)) for _ in range(3)]
        [p.start() for p in ps]
        outs = [q.get(timeout=60) for _ in ps]
        [p.join(timeout=60) for p in ps]
        self.assertTrue(all(o == ["allow"] * 200 for o in outs))


if __name__ == "__main__":
    unittest.main()
