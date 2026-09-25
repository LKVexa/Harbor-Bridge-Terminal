"""Items 49-53: fuzz/property, concurrency, threat-model adversarial, performance, faults.

These run in-process. They are necessary evidence, not sufficient: items 47,
48, 52 and 53 also require a real cluster, runtime matrix and fleet, which
this archive does not have (recorded as BLOCKED in CHECKLIST_STATUS.json).
"""
import copy
import os
import random
import tempfile
import threading
import time
import unittest

from hkit import APPROVER, REQUESTER, build, hardened_pod, request

from inv03_container_hardening.hardening.baseline import BaselineError, default_document, sign_baseline
from inv03_container_hardening.hardening.controls import CONTROLS_43

SEED = int(os.environ.get("INV03_FUZZ_SEED", "20260922"))
ITER = int(os.environ.get("INV03_FUZZ_ITER", "3000"))
JUNK = [None, True, False, 0, -1, 2**63, 1.5, float("nan"), "", "0", "root", "ALL", "Localhost",
        [], [None], {}, {"a": None}, "x" * 5000, ["ALL"], {"type": "RuntimeDefault"}]


def paths(obj, prefix=()):
    yield prefix
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from paths(v, prefix + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from paths(v, prefix + (i,))


def set_path(obj, path, value):
    for p in path[:-1]:
        obj = obj[p]
    obj[path[-1]] = value


class Fuzz(unittest.TestCase):
    def test_item49_mutation_fuzz_never_crashes_and_admit_is_sound(self):
        eng, *_ = build()
        rng = random.Random(SEED)
        base = hardened_pod()
        all_paths = [p for p in paths(base) if p]
        admits = 0
        for _ in range(ITER):
            pod = copy.deepcopy(base)
            for _ in range(rng.randint(1, 3)):
                p = rng.choice(all_paths)
                try:
                    set_path(pod, p, rng.choice(JUNK))
                except (KeyError, IndexError, TypeError):
                    pass
            d = eng.decide(request(pod))
            self.assertIn(d["admit"], (True, False))
            if d["admit"]:
                admits += 1
                ctx = dict(default_document()["settings"], namespace_default_deny=True)
                for name, fn in CONTROLS_43.items():
                    self.assertEqual(fn(pod, ctx), [], f"admitted pod violates {name}: {pod}")
        self.assertLess(admits, ITER)  # the fuzzer actually produced denials

    def test_item49_hostile_top_level_inputs(self):
        eng, *_ = build()
        deep = {}
        cur = deep
        for _ in range(200):
            cur["x"] = {}
            cur = cur["x"]
        hostile = [None, [], "pod", {"workload": "w"}, request(pod=deep), request(pod={"containers": [1] * 100}),
                   request(pod={"containers": [{"name": "a" * 10**6}]}), request(workload=""),
                   request(workload="w" * 300), dict(request(), scope={"tenant": "t"}),
                   request(pod={"containers": []})]
        for h in hostile:
            d = eng.decide(h)
            self.assertFalse(d["admit"])
            self.assertIn(d["reason"], ("MALFORMED_INPUT", "POLICY_REJECTED"))

    def test_item49_fixture_corpus(self):
        import json
        root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fixtures")
        eng, *_ = build()
        n = 0
        for kind in ("valid", "invalid"):
            for f in sorted(os.listdir(os.path.join(root, kind))):
                with open(os.path.join(root, kind, f)) as fh:
                    case = json.load(fh)
                d = eng.decide(request(case["pod"]))
                self.assertEqual(d["admit"], case["expect"]["admit"], f)
                self.assertEqual(d["failed"], case["expect"]["failed"], f)
                n += 1
        self.assertGreaterEqual(n, 10)


class Concurrency(unittest.TestCase):
    def test_item50_concurrent_rollout_single_winner(self):
        eng, *_ = build()
        kr = __import__("hkit").Keyring({"release-signer": b"s" * 32})
        start = eng.baselines.epoch
        results = []

        def attempt(i):
            doc = dict(default_document(), version=f"4.3.{i + 1}")
            try:
                results.append(eng.baselines.activate(sign_baseline(doc, kr, "release-signer"), start))
            except BaselineError as e:
                results.append(e.code)
        ts = [threading.Thread(target=attempt, args=(i,)) for i in range(16)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        self.assertEqual(sum(isinstance(r, int) for r in results), 1)
        self.assertEqual(results.count("EPOCH_CONFLICT"), 15)

    def test_item50_issue_revoke_race_and_duplicate_admission(self):
        eng, *_ = build()
        wl = "team-a/Deployment/api"
        rid = eng.exceptions.request(REQUESTER, wl, "read-only-root", "r", "T", "o", 3600)
        eng.exceptions.approve(APPROVER, rid)
        pod = hardened_pod()
        pod["containers"][0]["securityContext"]["readOnlyRootFilesystem"] = False
        stop = threading.Event()
        after = []

        def admitter():
            while not stop.is_set():
                d = eng.decide(request(pod))
                after.append((revoked.is_set(), d["admit"]))
        revoked = threading.Event()
        ts = [threading.Thread(target=admitter) for _ in range(4)]
        [t.start() for t in ts]
        time.sleep(0.05)
        eng.exceptions.revoke(APPROVER, rid)
        revoked.set()
        time.sleep(0.05)
        stop.set()
        [t.join() for t in ts]
        # any decision *started* after revocation completed must deny
        late = [a for r, a in after[-20:]]
        self.assertFalse(any(late))
        ok, msg = eng.ledger.verify()
        self.assertTrue(ok, msg)


class Adversarial(unittest.TestCase):
    """Item 51: scenarios derived from the contract's threat list."""

    def setUp(self):
        self.eng, self.ft, _ = build()

    def deny(self, mutate, why):
        pod = hardened_pod()
        mutate(pod)
        self.assertFalse(self.eng.decide(request(pod))["admit"], why)

    def test_escape_and_escalation_scenarios(self):
        c = lambda p: p["containers"][0]["securityContext"]  # noqa: E731
        self.deny(lambda p: c(p).update(privileged=True), "privileged escape")
        self.deny(lambda p: c(p)["capabilities"].update(add=["SYS_ADMIN"]), "CAP_SYS_ADMIN escape")
        self.deny(lambda p: p["volumes"].append({"name": "s", "hostPath": {"path": "/var/run/docker.sock"}}), "docker socket")
        self.deny(lambda p: p.update(hostPID=True), "host PID nsenter")
        self.deny(lambda p: c(p).update(allowPrivilegeEscalation=True), "setuid escalation")
        self.deny(lambda p: p.update(runtimeClassName=None), "sandbox bypass by omission")
        self.deny(lambda p: c(p).update(procMount="Unmasked"), "proc unmask")
        self.deny(lambda p: p["containers"][0].update(securityContext=None), "security context nulled")
        self.deny(lambda p: p.update(initContainers=[{"name": "i", "securityContext": {"privileged": True}}]),
                  "privileged init container smuggling")

    def test_exception_tampering_and_permanent_exceptions(self):
        with self.assertRaises(Exception):
            self.eng.exceptions.request(REQUESTER, "w", "seccomp", "r", "T", "o", 10**9)
        # caller-supplied exception data has no path into the engine
        d = self.eng.decide(dict(request(), exceptions={"team-a/Deployment/api/seccomp": {"expires": 10**12}}))
        self.assertTrue(d["admit"])  # hardened pod; extra field ignored, not honoured
        pod = hardened_pod()
        pod["securityContext"]["seccompProfile"] = {"type": "Unconfined"}
        d = self.eng.decide(dict(request(pod), exceptions={("team-a/Deployment/api", "seccomp"): {"expires": 10**12,
                                                                                                    "reason": "x"}}))
        self.assertFalse(d["admit"])

    def test_replayed_old_baseline_refused(self):
        kr = __import__("hkit").Keyring({"release-signer": b"s" * 32})
        new = dict(default_document(), version="4.3.5")
        self.eng.baselines.activate(sign_baseline(new, kr, "release-signer"), self.eng.baselines.epoch)
        with self.assertRaises(BaselineError):
            self.eng.baselines.activate(sign_baseline(default_document(), kr, "release-signer"),
                                        self.eng.baselines.epoch)

    def test_time_rollback_cannot_revive_expired_exception(self):
        wl = "team-a/Deployment/api"
        rid = self.eng.exceptions.request(REQUESTER, wl, "read-only-root", "r", "T", "o", 10)
        self.eng.exceptions.approve(APPROVER, rid)
        self.ft.t += 100
        pod = hardened_pod()
        pod["containers"][0]["securityContext"]["readOnlyRootFilesystem"] = False
        self.assertFalse(self.eng.decide(request(pod))["admit"])
        self.ft.t -= 100
        self.assertEqual(self.eng.decide(request(pod))["reason"], "CLOCK_UNTRUSTED")

    def test_resource_exhaustion_bounded(self):
        pod = hardened_pod()
        pod["containers"] = [copy.deepcopy(pod["containers"][0]) for _ in range(65)]
        t0 = time.perf_counter()
        self.assertFalse(self.eng.decide(request(pod))["admit"])
        self.assertLess(time.perf_counter() - t0, 0.5)


class Performance(unittest.TestCase):
    def test_item52_local_p99_under_contract_slo(self):
        eng, *_ = build()
        for _ in range(2000):
            eng.decide(request())
        p99 = eng.metrics.quantile_ms(0.99)
        self.assertLessEqual(p99, 5, f"p99 bucket {p99}ms exceeds 5ms contract SLO")


class Faults(unittest.TestCase):
    def test_item53_dependency_faults_fail_closed(self):
        eng, ft, _ = build()
        eng.baselines.active = lambda: (_ for _ in ()).throw(BaselineError("BASELINE_UNAVAILABLE", "store down"))
        self.assertEqual(eng.decide(request())["reason"], "BASELINE_UNAVAILABLE")
        eng, ft, _ = build()
        eng.clock._source = lambda: (_ for _ in ()).throw(OSError("time service down"))
        self.assertEqual(eng.decide(request())["reason"], "CLOCK_UNTRUSTED")
        eng, ft, _ = build()
        eng.exceptions.active_for = lambda *a: (_ for _ in ()).throw(RuntimeError("store partition"))
        pod = hardened_pod()
        pod["hostIPC"] = True
        self.assertFalse(eng.decide(request(pod))["admit"])
        eng, ft, _ = build()
        ft.t += 10_000  # runtime report now stale
        self.assertFalse(eng.runtimes.check("gvisor", "node-1", int(ft.t))[0])

    def test_item53_restart_recovers_state(self):
        with tempfile.TemporaryDirectory() as d:
            eng, ft, _ = build(d)
            eng.decide(request())
            head = eng.ledger.head
            eng2, *_ = build(d)  # restart: ledger + baseline reload
            self.assertTrue(eng2.ledger.verify()[0])
            self.assertEqual(eng2.ledger.events()[len(eng.ledger.events()) - 1]["hash"], head)


if __name__ == "__main__":
    unittest.main()
