"""Components 45 (schema conformance), 46 (fuzz/property), 47 (concurrency),
48 (fault injection), 49 (soak/burst -- LOCAL scale only).

Declared lane for 45: needs ``jsonschema``; NOT_RUN (skip with reason) otherwise.
Fuzz runs are seeded so a failure is reproducible; the seed is in the name.
"""
import json
import os
import random
import threading
import unittest
from unittest import mock

from fixtures import make_stack, sample, signed, tmpdir
from gap09_unified_observability.components.canonical import canonicalize
from gap09_unified_observability.components.controls import CircuitBreaker
from gap09_unified_observability.components.durable import DurableReplayGuard, WriteAheadBuffer
from gap09_unified_observability.components.errors import Corrupted, DependencyUnavailable
from gap09_unified_observability.components.signals import Catalogue, parse_traceparent
from gap09_unified_observability.runtime import SignalError

SCHEMAS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "schemas")
try:
    import jsonschema
except ImportError:  # pragma: no cover
    jsonschema = None


@unittest.skipUnless(jsonschema, "LANE jsonschema: package absent -- contract-schema conformance NOT_RUN")
class TestSchemaConformance(unittest.TestCase):
    def v(self, name):
        with open(os.path.join(SCHEMAS, name)) as fh:
            s = json.load(fh)
        jsonschema.Draft202012Validator.check_schema(s)
        return jsonschema.Draft202012Validator(s)

    def test_query_responses_present_and_absent(self):
        ingest, *_ = make_stack(tmpdir())
        ingest.submit(**signed([sample()]))
        val = self.v("PK_SIGNAL_QUERY_2.schema.json")
        for sig in ("cpu", "absent"):
            val.validate(ingest.store.read(caller_tenant="t1", tenant="t1", environment="prod", site="s1",
                                           workload="w1", signal=sig, now=1000))

    def test_submission_wire_shape(self):
        a = signed([sample()])
        body = {"schema": "PK_SIGNAL_SUBMISSION/2", "reporter": a["reporter"], "submission_id": a["submission_id"],
                "issued_at": a["issued_at"], "signature": a["signature"],
                "attestation": {"key_id": a["key_id"], "profile": "GAP09-CSP/1"},
                "samples": [{f: getattr(s, f) for f in ("signal", "value", "tenant", "environment", "site", "workload", "at")}
                            for s in a["samples"]]}
        self.v("PK_SIGNAL_SUBMISSION_2.schema.json").validate(body)
        bad = dict(body, key_id="k1")                          # the pre-fix wire shape
        with self.assertRaises(jsonschema.ValidationError):
            self.v("PK_SIGNAL_SUBMISSION_2.schema.json").validate(bad)

    def test_catalogue_document(self):
        c = Catalogue()
        for n, k in (("cpu", "gauge"), ("req", "counter"), ("lat", "histogram"), ("app.log", "log"), ("rpc", "trace"), ("prof", "profile")):
            c.register(n, kind=k, unit="1", owner="obs", description="d", actor="t")
        self.v("PK_SIGNAL_CATALOGUE_1.schema.json").validate(c.document())


class TestFuzzProperty(unittest.TestCase):
    SEED = 20260922

    def rand_json(self, r, depth=0):
        t = r.randrange(7 if depth < 4 else 4)
        if t == 0: return r.choice([None, True, False])
        if t == 1: return r.randint(-2**53 + 1, 2**53 - 1)
        if t == 2:
            x = r.uniform(-1e6, 1e6) * 10 ** r.randint(-30, 30)
            return x if x != 0 else 1.0
        if t == 3: return "".join(chr(r.choice([r.randint(32, 126), r.randint(0xA0, 0xD7FF), r.randint(0xE000, 0x10FFFF)])) for _ in range(r.randint(0, 8)))
        if t in (4, 5): return [self.rand_json(r, depth + 1) for _ in range(r.randint(0, 4))]
        return {self.rand_json(r, 9) if False else f"k{r.randint(0, 99)}{chr(r.randint(0xA0, 0x2FFF))}": self.rand_json(r, depth + 1)
                for _ in range(r.randint(0, 4))}

    def test_canonical_roundtrip_seed_20260922(self):
        r = random.Random(self.SEED)
        for _ in range(2000):
            v = self.rand_json(r)
            c = canonicalize(v)
            self.assertEqual(canonicalize(json.loads(c)), c)      # idempotent through a parse
            as_double = lambda t: float(t) if abs(int(t)) > 2**53 else int(t)   # what a binary64 reader sees
            self.assertEqual(json.loads(c, parse_int=as_double), json.loads(json.dumps(v)))

    def test_traceparent_never_raises_seed_20260922(self):
        r = random.Random(self.SEED)
        alphabet = "0123456789abcdefABCDEF-xz \t"
        for _ in range(5000):
            h = "".join(r.choice(alphabet) for _ in range(r.randint(0, 80)))
            parse_traceparent(h, h)

    def test_ingest_hostile_inputs_only_structured_errors_seed_20260922(self):
        ingest, *_ = make_stack(tmpdir())
        r = random.Random(self.SEED)
        hostile = ["", " x", "x\u0000", "‮", "a" * 300, "é", 1, None, 1.5]
        for i in range(400):
            s = sample(signal=r.choice(hostile + ["cpu"]), tenant=r.choice(hostile + ["t1"]), value=r.choice([1.0, float("nan"), 1e309, True, "1"]),
                       at=r.choice([100, -1, 2**63, 1001]))
            try:
                ingest.submit(**signed([s], sid=f"f{i}"))
            except SignalError:
                pass

    def test_wal_random_truncation_property_seed_20260922(self):
        r = random.Random(self.SEED)
        for trial in range(40):
            p = os.path.join(tmpdir(), "w.log")
            w = WriteAheadBuffer(p)
            for i in range(10):
                w.append({"i": i, "pad": "x" * r.randint(0, 40)})
            size = os.path.getsize(p)
            cut = r.randint(0, size)
            with open(p, "r+b") as fh:
                fh.truncate(cut)
            try:
                got = [v["i"] for _, v in WriteAheadBuffer(p).pending()]
            except Corrupted:
                self.fail("pure truncation must always recover")
            self.assertEqual(got, list(range(len(got))))          # a prefix, in order, nothing invented


class TestConcurrency(unittest.TestCase):
    def test_exactly_once_under_races(self):
        ingest, *_ = make_stack(tmpdir())
        results, errs = [], []
        def worker(tid):
            for j in range(20):
                sid = f"shared-{j}" if j % 2 == 0 else f"own-{tid}-{j}"
                try:
                    ingest.submit(**signed([sample(at=100 + j, signal=f"s{j}")], sid=sid))
                    results.append(sid)
                except SignalError as exc:
                    errs.append(exc.code)
        ts = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
        [t.start() for t in ts]; [t.join() for t in ts]
        shared = [s for s in results if s.startswith("shared-")]
        self.assertEqual(len(shared), len(set(shared)))           # each shared id accepted at most once
        self.assertEqual(len(set(shared)), 10)
        self.assertTrue(set(errs) <= {"replay_detected", "timestamp_conflict"})
        self.assertEqual(ingest.admission.inflight, 0)
        ingest.audit.verify(ingest.audit.head())                  # chain intact after concurrent appends

    def test_replay_guard_threads(self):
        g = DurableReplayGuard(os.path.join(tmpdir(), "r.log"), window=100)
        ok = []
        def go():
            try:
                g.check_and_record("a", "same", 1000, 1000); ok.append(1)
            except SignalError:
                pass
        ts = [threading.Thread(target=go) for _ in range(16)]
        [t.start() for t in ts]; [t.join() for t in ts]
        self.assertEqual(len(ok), 1)


class TestFaultInjection(unittest.TestCase):
    def test_fsync_failure_means_no_acceptance(self):
        ingest, *_ = make_stack(tmpdir())
        with mock.patch("os.fsync", side_effect=OSError("EIO")):
            with self.assertRaises(OSError):
                ingest.submit(**signed([sample()]))
        self.assertEqual(len(ingest.store.latest), 0)             # nothing committed on a failed durable write
        self.assertEqual(ingest.admission.inflight, 0)

    def test_trust_dependency_timeout_opens_breaker_and_refuses(self):
        b = CircuitBreaker("attest", threshold=1, cooldown=30)
        def slow():
            raise TimeoutError("verifier timeout")
        with self.assertRaises(TimeoutError):
            b.call(slow, 0)
        with self.assertRaises(DependencyUnavailable):
            b.call(lambda: "would-trust", 1)                      # open breaker never bypasses trust

    def test_restart_mid_stream(self):
        d = tmpdir()
        ingest, *_ = make_stack(d)
        ingest.submit(**signed([sample()], sid="a1"))
        ingest2, *_ = make_stack(d)                               # process restart, same state dir
        with self.assertRaises(SignalError) as cm:
            ingest2.submit(**signed([sample()], sid="a1"))
        self.assertEqual(cm.exception.code, "replay_detected")


class TestSoakBurstLocal(unittest.TestCase):
    """LOCAL-scale burst: 2,000 submissions x 5 samples.  Fleet-scale soak
    (component 49 proper) is BLOCKED: no fleet exists in this environment."""

    def test_burst(self):
        ingest, *_ = make_stack(tmpdir(), tenant_series=100_000, rate=1e9)
        for i in range(2000):
            ingest.submit(**signed([sample(signal=f"s{i % 50}.{k}", at=100 + i // 50) for k in range(5)], sid=f"b{i}"))
        m = ingest.store.metrics()
        self.assertEqual((ingest.accepted, m["active_signals"]), (2000, 250))


if __name__ == "__main__":
    unittest.main()
