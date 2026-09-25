"""Standalone stdlib tests for the GAP-09 hardened runtime."""
from __future__ import annotations

import importlib
import pathlib
import sys
import threading
import unittest

PKG_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG_DIR.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

pkg = importlib.import_module(PKG_DIR.name)

Sample = pkg.Sample
SignalStore = pkg.SignalStore
ReporterAuthority = pkg.ReporterAuthority
HMACFixtureVerifier = pkg.HMACFixtureVerifier
ReporterUntrusted = pkg.ReporterUntrusted
ReplayDetected = pkg.ReplayDetected
ScopeViolation = pkg.ScopeViolation
TimestampConflict = pkg.TimestampConflict
CapacityExceeded = pkg.CapacityExceeded
TrustUnavailable = pkg.TrustUnavailable
InvalidBatch = pkg.InvalidBatch
InvalidSample = pkg.InvalidSample
InvalidTime = pkg.InvalidTime
CrossTenantQuery = pkg.CrossTenantQuery
Unattributed = pkg.Unattributed

KEY = b"unit-test-key"


def make_store(**kwargs):
    authority = ReporterAuthority(
        reporter="n1",
        attested_level="hardware",
        tenants=frozenset({"t1"}),
        environments=frozenset({"prod"}),
        sites=frozenset({"s1"}),
        workloads=frozenset({"w1"}),
    )
    verifier = HMACFixtureVerifier({("n1", "k1"): KEY}, {"n1": authority})
    return SignalStore(trust_verifier=verifier, **kwargs), verifier


def submit(store, verifier, samples, *, sid="s1", now=10, reporter="n1", key=KEY):
    payload = store.canonical_submission_payload(
        reporter=reporter, submission_id=sid, issued_at=now, samples=samples
    )
    sig = verifier.sign(key, payload)
    return store.submit_verified(
        reporter,
        samples,
        submission_id=sid,
        issued_at=now,
        signature=sig,
        attestation={"key_id": "k1"},
        now=now,
    )


class RuntimeTest(unittest.TestCase):
    def test_package_imports_without_pk_core(self):
        self.assertEqual(pkg.__version__, "5.0.0")
        self.assertTrue(callable(SignalStore))

    def test_verified_submission_and_zero_vs_absent(self):
        store, verifier = make_store()
        submit(store, verifier, [Sample("cpu", 0.0, "t1", "prod", "s1", "w1", 10)])
        zero = store.read(caller_tenant="t1", tenant="t1", environment="prod", site="s1", workload="w1", signal="cpu", now=10)
        absent = store.read(caller_tenant="t1", tenant="t1", environment="prod", site="s1", workload="w1", signal="missing", now=10)
        self.assertTrue(zero["present"])
        self.assertEqual(zero["schema"], "PK_SIGNAL_QUERY/2")
        self.assertEqual(absent["schema"], "PK_SIGNAL_QUERY/2")
        self.assertEqual(zero["value"], 0.0)
        self.assertEqual(zero["tenant"], "t1")
        self.assertEqual(zero["environment"], "prod")
        self.assertEqual(zero["site"], "s1")
        self.assertEqual(zero["workload"], "w1")
        self.assertEqual(zero["reporter"], "n1")
        self.assertEqual(zero["submission_id"], "s1")
        self.assertFalse(absent["present"])
        self.assertIsNone(absent["value"])

    def test_legacy_trust_is_fail_closed_by_default(self):
        store, _ = make_store()
        with self.assertRaises(ReporterUntrusted):
            store.submit(
                "n1",
                [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)],
                attested_level="hardware",
                signed=True,
                now=0,
            )

    def test_legacy_can_be_enabled_only_explicitly(self):
        store = SignalStore(allow_legacy_trust=True)
        self.assertEqual(
            store.submit(
                "n1",
                [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)],
                attested_level="hardware",
                signed=True,
                now=0,
            ),
            1,
        )

    def test_bad_signature_is_rejected_without_mutation(self):
        store, _ = make_store()
        s = Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)
        with self.assertRaises(ReporterUntrusted):
            store.submit_verified(
                "n1",
                [s],
                submission_id="bad-sig",
                issued_at=0,
                signature="00",
                attestation={"key_id": "k1"},
                now=0,
            )
        self.assertEqual(store.latest, {})

    def test_unapproved_reporter_is_rejected(self):
        store, verifier = make_store()
        s = Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)
        payload = store.canonical_submission_payload(
            reporter="rogue", submission_id="x", issued_at=0, samples=[s]
        )
        with self.assertRaises(ReporterUntrusted):
            store.submit_verified(
                "rogue", [s], submission_id="x", issued_at=0,
                signature=verifier.sign(KEY, payload), attestation={"key_id": "k1"}, now=0,
            )

    def test_authorization_scope_is_enforced(self):
        store, verifier = make_store()
        s = Sample("cpu", 1.0, "t2", "prod", "s1", "w1", 0)
        with self.assertRaises(ScopeViolation):
            submit(store, verifier, [s], sid="scope", now=0)
        self.assertEqual(store.latest, {})


    def test_environment_scope_is_enforced(self):
        store, verifier = make_store()
        s = Sample("cpu", 1.0, "t1", "staging", "s1", "w1", 0)
        with self.assertRaises(ScopeViolation):
            submit(store, verifier, [s], sid="env-scope", now=0)
        self.assertEqual(store.latest, {})

    def test_concurrent_updates_converge_on_newest_timestamp(self):
        store, verifier = make_store()
        failures = []

        def worker(i):
            try:
                sample = Sample("cpu", float(i), "t1", "prod", "s1", "w1", i)
                payload = store.canonical_submission_payload(
                    reporter="n1", submission_id=f"thread-{i}", issued_at=100, samples=[sample]
                )
                store.submit_verified(
                    "n1", [sample], submission_id=f"thread-{i}", issued_at=100,
                    signature=verifier.sign(KEY, payload), attestation={"key_id": "k1"}, now=100,
                )
            except Exception as exc:  # pragma: no cover - collected for assertion
                failures.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(failures, [])
        got = store.read(
            caller_tenant="t1", tenant="t1", environment="prod", site="s1",
            workload="w1", signal="cpu", now=100,
        )
        self.assertEqual(got["sample_at"], 19)
        self.assertEqual(got["value"], 19.0)

    def test_replay_id_is_rejected(self):
        store, verifier = make_store()
        s = Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)
        submit(store, verifier, [s], sid="replay", now=0)
        with self.assertRaises(ReplayDetected):
            submit(store, verifier, [s], sid="replay", now=0)

    def test_equal_timestamp_conflict_is_rejected_transactionally(self):
        store, verifier = make_store()
        a = Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)
        b = Sample("cpu", 2.0, "t1", "prod", "s1", "w1", 0)
        submit(store, verifier, [a], sid="a", now=0)
        with self.assertRaises(TimestampConflict):
            submit(store, verifier, [b], sid="b", now=0)
        got = store.read(caller_tenant="t1", tenant="t1", environment="prod", site="s1", workload="w1", signal="cpu", now=0)
        self.assertEqual(got["value"], 1.0)

    def test_conflict_inside_batch_does_not_partially_commit(self):
        store, verifier = make_store()
        batch = [
            Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0),
            Sample("cpu", 2.0, "t1", "prod", "s1", "w1", 0),
        ]
        with self.assertRaises(TimestampConflict):
            submit(store, verifier, batch, sid="batch-conflict", now=0)
        self.assertEqual(store.latest, {})

    def test_late_sample_does_not_overwrite(self):
        store, verifier = make_store()
        submit(store, verifier, [Sample("cpu", 2.0, "t1", "prod", "s1", "w1", 10)], sid="new", now=10)
        submit(store, verifier, [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 5)], sid="old", now=11)
        got = store.read(caller_tenant="t1", tenant="t1", environment="prod", site="s1", workload="w1", signal="cpu", now=11)
        self.assertEqual(got["value"], 2.0)

    def test_whole_batch_validation_precedes_commit(self):
        store, verifier = make_store()
        batch = [
            Sample("ok", 1.0, "t1", "prod", "s1", "w1", 0),
            Sample("bad", 1.0, "t1", "prod", "", "w1", 0),
        ]
        with self.assertRaises(Unattributed):
            submit(store, verifier, batch, sid="bad-attr", now=0)
        self.assertEqual(store.latest, {})

    def test_empty_batch_does_not_refresh_reporter(self):
        store, verifier = make_store()
        with self.assertRaises(InvalidBatch):
            submit(store, verifier, [], sid="empty", now=0)
        self.assertEqual(store.last_submission, {})

    def test_nonfinite_and_bool_values_rejected(self):
        store, verifier = make_store()
        for idx, value in enumerate([float("nan"), float("inf"), float("-inf"), True]):
            with self.subTest(value=value):
                with self.assertRaises(InvalidSample):
                    submit(store, verifier, [Sample("cpu", value, "t1", "prod", "s1", "w1", 0)], sid=f"nf-{idx}", now=0)


    def test_timestamp_domain_is_bounded(self):
        store, verifier = make_store()
        for sid, at, now in (("neg", -1, 0), ("huge", (1 << 63), (1 << 63))):
            with self.subTest(sid=sid):
                with self.assertRaises(InvalidTime):
                    submit(
                        store, verifier,
                        [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", at)],
                        sid=sid, now=now,
                    )

    def test_extreme_integer_value_is_rejected_without_overflow(self):
        store, verifier = make_store()
        with self.assertRaises(InvalidSample):
            submit(
                store, verifier,
                [Sample("cpu", 10 ** 10000, "t1", "prod", "s1", "w1", 0)],
                sid="huge-value", now=0,
            )

    def test_non_ascii_fixture_signature_is_untrusted_not_dependency_failure(self):
        store, _ = make_store()
        sample = Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)
        with self.assertRaises(ReporterUntrusted):
            store.submit_verified(
                "n1", [sample], submission_id="unicode-sig", issued_at=0,
                signature="é" * 64, attestation={"key_id": "k1"}, now=0,
            )

    def test_future_sample_and_time_regression_rejected(self):
        store, verifier = make_store()
        with self.assertRaises(InvalidTime):
            submit(store, verifier, [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 11)], sid="future", now=10)
        submit(store, verifier, [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 10)], sid="ok", now=10)
        with self.assertRaises(InvalidTime):
            store.read(caller_tenant="t1", tenant="t1", environment="prod", site="s1", workload="w1", signal="cpu", now=9)

    def test_cross_tenant_query_refused_and_counted(self):
        store, verifier = make_store()
        submit(store, verifier, [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)], sid="q", now=0)
        with self.assertRaises(CrossTenantQuery):
            store.read(caller_tenant="t2", tenant="t1", environment="prod", site="s1", workload="w1", signal="cpu", now=1)
        self.assertEqual(store.metrics()["cross_tenant_denials"], 1)

    def test_configured_staleness_bound_is_used(self):
        store, verifier = make_store(staleness_bound=5)
        submit(store, verifier, [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)], sid="stale", now=0)
        self.assertFalse(store.read(caller_tenant="t1", tenant="t1", environment="prod", site="s1", workload="w1", signal="cpu", now=5)["stale"])
        self.assertTrue(store.read(caller_tenant="t1", tenant="t1", environment="prod", site="s1", workload="w1", signal="cpu", now=6)["stale"])

    def test_capacity_limits_are_fail_closed(self):
        store, verifier = make_store(max_signals=1)
        submit(store, verifier, [Sample("a", 1.0, "t1", "prod", "s1", "w1", 0)], sid="cap-a", now=0)
        with self.assertRaises(CapacityExceeded):
            submit(store, verifier, [Sample("b", 1.0, "t1", "prod", "s1", "w1", 1)], sid="cap-b", now=1)
        self.assertEqual(len(store.latest), 1)

    def test_rejection_log_is_bounded(self):
        store = SignalStore(max_rejections=2)
        sample = Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)
        for i in range(3):
            with self.assertRaises(ReporterUntrusted):
                store.submit("n1", [sample], attested_level="hardware", signed=True, now=i)
        self.assertEqual(len(store.rejected), 2)


    def test_state_snapshots_are_read_only(self):
        store, verifier = make_store()
        submit(store, verifier, [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)], sid="immutable", now=0)
        with self.assertRaises(TypeError):
            store.latest[("t1", "prod", "s1", "w1", "cpu")] = Sample("cpu", 9.0, "t1", "prod", "s1", "w1", 0)
        with self.assertRaises(TypeError):
            store.last_submission["n1"] = 999

    def test_trust_dependency_exception_fails_closed(self):
        class BrokenVerifier:
            def verify(self, **kwargs):
                raise RuntimeError("dependency down")

        store = SignalStore(trust_verifier=BrokenVerifier())
        s = Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)
        with self.assertRaises(TrustUnavailable) as ctx:
            store.submit_verified(
                "n1", [s], submission_id="trust-down", issued_at=0,
                signature="00", attestation={"key_id": "k1"}, now=0,
            )
        self.assertEqual(ctx.exception.code, "trust_unavailable")
        self.assertEqual(store.latest, {})

    def test_sample_may_not_postdate_signed_envelope(self):
        store, verifier = make_store()
        s = Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 5)
        # Build the payload directly to model a malformed external envelope.
        payload = pkg.runtime._canonical_payload("n1", "issued-order", 4, [s])
        sig = verifier.sign(KEY, payload)
        with self.assertRaises(InvalidTime):
            store.submit_verified(
                "n1", [s], submission_id="issued-order", issued_at=4,
                signature=sig, attestation={"key_id": "k1"}, now=5,
            )


    def test_generator_materialization_is_bounded(self):
        store, _ = make_store(max_batch_size=2)
        consumed = []

        def many():
            i = 0
            while True:
                consumed.append(i)
                yield Sample(f"s{i}", 1.0, "t1", "prod", "s1", "w1", 0)
                i += 1

        with self.assertRaises(CapacityExceeded):
            store.canonical_submission_payload(
                reporter="n1", submission_id="too-many", issued_at=0, samples=many()
            )
        self.assertEqual(len(consumed), 3)

    def test_identifier_controls_and_non_normalized_unicode_are_rejected(self):
        store, verifier = make_store()
        with self.assertRaises(InvalidSample):
            submit(store, verifier, [Sample("cpu\nforge", 1.0, "t1", "prod", "s1", "w1", 0)], sid="control", now=0)
        with self.assertRaises(InvalidSample):
            submit(store, verifier, [Sample("e\u0301", 1.0, "t1", "prod", "s1", "w1", 0)], sid="nfc", now=0)

    def test_signature_and_attestation_bounds(self):
        store, _ = make_store(max_signature_size=8, max_attestation_fields=1)
        s = Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)
        with self.assertRaises(ReporterUntrusted):
            store.submit_verified(
                "n1", [s], submission_id="sig-big", issued_at=0, signature="x" * 9,
                attestation={"key_id": "k1"}, now=0,
            )
        with self.assertRaises(ReporterUntrusted):
            store.submit_verified(
                "n1", [s], submission_id="att-big", issued_at=0, signature="ok",
                attestation={"key_id": "k1", "extra": "x"}, now=0,
            )

    def test_silent_reporters_deduplicates_and_detects_never_seen(self):
        store, verifier = make_store(reporters_silent_after=5)
        submit(store, verifier, [Sample("cpu", 1.0, "t1", "prod", "s1", "w1", 0)], sid="alive", now=0)
        self.assertEqual(store.silent_reporters(["n1", "n1", "n2"], now=1), ["n2"])
        self.assertEqual(store.silent_reporters(["n1"], now=6), ["n1"])


if __name__ == "__main__":
    unittest.main()
