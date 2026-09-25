"""P1-05..P1-19: cancellation, admission, identity, audit, telemetry, logging,
tracing, emergency disable, migration registry, lifecycle, restart, clock,
owners, ADR, compatibility matrix."""
import datetime as dt, io, json, os, threading, time, unittest
from _support import PKG_DIR, KEY, KEY2, tmpdir, make_service
import polling, admission, identity, audit, telemetry, pollog, tracing, lifecycle, governance, checkpoint, clock, config, schema_check

P = polling


class C05Cancellation(unittest.TestCase):
    def test_c05_cancel_wakes_blocked_poll_with_structured_error(self):
        tok, p, ps = P.CancelToken(), P.Pollable("x", "o"), P.PollSet("o")
        threading.Timer(0.02, tok.cancel, kwargs={"reason": "shutdown"}).start()
        t0 = time.monotonic()
        with self.assertRaises(P.PollCancelled) as cm:
            ps.poll([p], timeout_ticks=5000, cancel=tok)
        self.assertLess(time.monotonic() - t0, 1.0)
        e = cm.exception.as_dict()
        self.assertEqual((e["code"], e["details"]["reason"]), ("PK_POLL_CANCELLED", "shutdown"))
        self.assertEqual(len(p._waiters), 0)
        self.assertEqual(tok._waiter_count(), 0)
        self.assertEqual(ps.metrics_snapshot()["polls_cancelled"], 1)

    def test_c05_precancelled_token_and_readiness_wins_tie(self):
        tok = P.CancelToken(); tok.cancel()
        with self.assertRaises(P.PollCancelled):
            P.PollSet("o").poll([P.Pollable("x", "o")], timeout_ticks=10, cancel=tok)
        p = P.Pollable("x", "o"); p.signal()
        self.assertEqual(P.PollSet("o").poll([p], timeout_ticks=10, cancel=tok)["ready"], ["x"])

    def test_c05_cancel_is_idempotent_and_token_type_checked(self):
        tok = P.CancelToken()
        self.assertTrue(tok.cancel()); self.assertFalse(tok.cancel())
        with self.assertRaises(P.PollValidationError) as cm:
            P.PollSet("o").poll([P.Pollable("x", "o")], timeout_ticks=1, cancel="yes")
        self.assertEqual(cm.exception.code, "PK_POLL_INVALID_CANCEL_TOKEN")

    def test_c05_cancel_race_stress_no_leak_no_hang(self):
        ps = P.PollSet("o")
        for i in range(200):
            tok, p = P.CancelToken(), P.Pollable("x", "o")
            t = threading.Thread(target=tok.cancel) if i % 2 else threading.Thread(target=p.signal)
            t.start()
            try:
                ps.poll([p], timeout_ticks=2000, cancel=tok)
            except P.PollCancelled:
                pass
            t.join()
            self.assertEqual((len(p._waiters), tok._waiter_count()), (0, 0))


class C06Admission(unittest.TestCase):
    def test_c06_global_and_tenant_ceilings_shed_deterministically(self):
        a = admission.AdmissionController(max_concurrent=3, tenant_max=2)
        a.acquire("t1"); a.acquire("t1")
        with self.assertRaises(admission.AdmissionRefused) as cm:
            a.acquire("t1")
        self.assertEqual(cm.exception.code, "PK_POLL_TENANT_QUOTA")
        a.acquire("t2")
        with self.assertRaises(admission.AdmissionRefused) as cm:
            a.acquire("t3")
        self.assertEqual(cm.exception.code, "PK_POLL_OVERLOADED")
        for t in ("t1", "t1", "t2"):
            a.release(t)
        self.assertEqual(a.snapshot()["active"], 0)
        with self.assertRaises(admission.AdmissionRefused):
            a.release("t1")

    def test_c06_bounded_fifo_queue_and_timeout(self):
        a = admission.AdmissionController(max_concurrent=1, tenant_max=1, queue_depth=1)
        a.acquire("t1")
        threading.Timer(0.03, a.release, args=("t1",)).start()
        a.acquire("t2", wait_seconds=1.0)
        a.release("t2")
        a.acquire("t1")
        with self.assertRaises(admission.AdmissionRefused):
            a.acquire("t2", wait_seconds=0.02)
        self.assertEqual(a.snapshot()["shed"]["queue_timeout"], 1)

    def test_c06_invalid_limits_refused(self):
        for kw in ({"max_concurrent": 0, "tenant_max": 1}, {"max_concurrent": 1, "tenant_max": 2},
                   {"max_concurrent": True, "tenant_max": 1}):
            with self.assertRaises(admission.AdmissionRefused):
                admission.AdmissionController(**kw)

    def test_c06_slot_releases_on_exception(self):
        a = admission.AdmissionController(max_concurrent=1, tenant_max=1)
        with self.assertRaises(ZeroDivisionError):
            with a.slot("t"):
                1 / 0
        self.assertEqual(a.snapshot()["active"], 0)


class C07Identity(unittest.TestCase):
    def setUp(self):
        self.now = [1_000_000]
        self.iss = identity.Issuer(KEY, "k1", clock=lambda: self.now[0])
        self.ver = identity.Verifier({"k1": KEY}, clock=lambda: self.now[0])
        self.owner = identity.principal("acme", "billing", "i-1")

    def test_c07_valid_token_binds_owner(self):
        r = self.ver.verify(self.iss.mint(self.owner), owner=self.owner)
        self.assertEqual((r["tenant"], r["sub"]), ("acme", self.owner))

    def test_c07_cross_tenant_expired_forged_untrusted_refused(self):
        tok = self.iss.mint(self.owner)
        cases = []
        with self.assertRaises(identity.IdentityError) as cm:
            self.ver.verify(tok, owner="other/billing/i-1")
        cases.append(cm.exception.code)
        forged = identity.Issuer(KEY2, "k1").mint(self.owner)
        with self.assertRaises(identity.IdentityError) as cm:
            self.ver.verify(forged, owner=self.owner)
        cases.append(cm.exception.code)
        with self.assertRaises(identity.IdentityError) as cm:
            self.ver.verify(identity.Issuer(KEY2, "k9").mint(self.owner), owner=self.owner)
        cases.append(cm.exception.code)
        self.now[0] += 10_000
        with self.assertRaises(identity.IdentityError) as cm:
            self.ver.verify(tok, owner=self.owner)
        cases.append(cm.exception.code)
        self.assertEqual(cases, ["PK_POLL_TOKEN_SUBJECT", "PK_POLL_TOKEN_SIGNATURE", "PK_POLL_TOKEN_UNTRUSTED",
                                 "PK_POLL_TOKEN_EXPIRED"])

    def test_c07_malformed_tokens_and_principals(self):
        for bad in (None, "", "a.b.c", "x" * 3000, "!!!.???", 12):
            with self.assertRaises(identity.IdentityError) as cm:
                self.ver.verify(bad, owner=self.owner)
            self.assertEqual(cm.exception.code, "PK_POLL_TOKEN_MALFORMED")
        for seg in ("", "UPPER", "a/b", "x" * 80):
            with self.assertRaises(identity.IdentityError):
                identity.principal(seg, "c", "i")
        with self.assertRaises(identity.IdentityError):
            identity.Issuer(b"short", "k1")
        with self.assertRaises(identity.IdentityError):
            identity.Verifier({})

    def test_c07_right_and_key_rotation(self):
        tok = self.iss.mint(self.owner, rights=("metrics",))
        with self.assertRaises(identity.IdentityError) as cm:
            self.ver.verify(tok, owner=self.owner)
        self.assertEqual(cm.exception.code, "PK_POLL_TOKEN_RIGHT")
        v2 = identity.Verifier({"k1": KEY, "k2": KEY2})
        self.assertTrue(v2.verify(identity.Issuer(KEY2, "k2").mint(self.owner), owner=self.owner))

    def test_c07_refusal_does_not_disclose_other_principal(self):
        tok = self.iss.mint(self.owner)
        with self.assertRaises(identity.IdentityError) as cm:
            self.ver.verify(tok, owner="evil/x/y")
        self.assertNotIn("acme", json.dumps(cm.exception.as_dict()))


class C08Audit(unittest.TestCase):
    def test_c08_chain_verifies_and_detects_edit_delete_reorder_truncate(self):
        d = tmpdir(); path = os.path.join(d, "a.jsonl")
        s = audit.AuditSink(path, KEY, clock=lambda: 1.0)
        for i in range(5):
            s.append("poll.refused.foreign_owner", correlation_id=f"c{i}", details={"i": i})
        head = s.head
        self.assertTrue(audit.verify_chain(path, KEY, expected_head=head)["ok"])
        lines = open(path, "rb").read().splitlines()
        def check(ls, **kw):
            p2 = os.path.join(d, "t.jsonl"); open(p2, "wb").write(b"\n".join(ls) + b"\n")
            return audit.verify_chain(p2, KEY, **kw)
        edited = list(lines); edited[2] = edited[2].replace(b'"i":2', b'"i":9')
        self.assertEqual(check(edited)["error"], "mac")
        self.assertEqual(check(lines[:2] + lines[3:])["error"], "chain_break")
        self.assertEqual(check([lines[1], lines[0]] + lines[2:])["error"], "chain_break")
        self.assertTrue(check(lines[:4])["ok"])  # a chain alone cannot see tail truncation...
        self.assertEqual(check(lines[:4], expected_head=head)["error"], "head_mismatch")  # ...the external head can
        self.assertEqual(audit.verify_chain(path, KEY2)["error"], "mac")

    def test_c08_reopen_resumes_and_corrupt_log_refused(self):
        d = tmpdir(); path = os.path.join(d, "a.jsonl")
        audit.AuditSink(path, KEY).append("poll.deprecated_use", correlation_id="x")
        s2 = audit.AuditSink(path, KEY)
        self.assertEqual(s2.append("poll.deprecated_use", correlation_id="y")["seq"], 2)
        open(path, "ab").write(b"garbage\n")
        with self.assertRaises(audit.AuditError) as cm:
            audit.AuditSink(path, KEY)
        self.assertEqual(cm.exception.code, "PK_AUDIT_CORRUPT")

    def test_c08_unwritable_sink_fails_closed_and_secrets_redacted(self):
        d = tmpdir()
        s = audit.AuditSink(os.path.join(d, "missing-dir", "a.jsonl"), KEY)
        with self.assertRaises(audit.AuditError) as cm:
            s.append("poll.deprecated_use", correlation_id="x")
        self.assertEqual(cm.exception.code, "PK_AUDIT_UNAVAILABLE")
        path = os.path.join(d, "b.jsonl")
        audit.AuditSink(path, KEY).append("poll.refused.identity", correlation_id="x",
                                          details={"token": "eyJabcdefghijk.eyJabcdefghijk.sig", "note": "password=hunter2"})
        raw = open(path).read()
        self.assertNotIn("hunter2", raw); self.assertNotIn("eyJabcdefghijk", raw)
        rec = json.loads(raw)
        self.assertEqual(schema_check.check(rec, "pk_poll_audit.schema.json"), [])
        with self.assertRaises(audit.AuditError):
            audit.AuditSink(path, KEY).append("made.up", correlation_id="x")


class C09Telemetry(unittest.TestCase):
    def test_c09_prometheus_exposition_parses_with_stable_labels(self):
        t = telemetry.Telemetry(seed=3)
        t.record("acme", "ready", latency_ms=3); t.record("acme", "timeout", latency_ms=70)
        t.record("acme", "refused", "foreign_owner"); t.record("acme", "weird", "nonsense")
        samples = telemetry.parse_prometheus(t.prometheus_text())
        labelsets = {frozenset(l) for _, l, _ in samples}
        self.assertTrue(all(ls <= {"component", "tenant", "outcome", "reason", "le"} for ls in labelsets))
        self.assertIn(("inv14_polls_total", {"component": "INV-14", "tenant": "acme", "outcome": "refused",
                                             "reason": "invalid"}, 1.0), samples)
        buckets = [v for n, l, v in samples if n == "inv14_poll_latency_ms_bucket"]
        self.assertEqual(buckets, sorted(buckets))

    def test_c09_tenant_cardinality_is_bounded(self):
        t = telemetry.Telemetry()
        for i in range(1000):
            t.record(f"tenant-{i}", "ready")
        tenants = {l["tenant"] for _, l, _ in telemetry.parse_prometheus(t.prometheus_text())}
        self.assertLessEqual(len(tenants), telemetry.MAX_TENANT_SERIES + 16)

    def test_c09_sampling_applies_to_latency_only(self):
        t = telemetry.Telemetry(sample_rate=0.0)
        for _ in range(10):
            t.record("a", "ready", latency_ms=1)
        self.assertEqual(t.samples_dropped, 10)
        self.assertIn('outcome="ready",reason="none"} 10', t.prometheus_text())
        with self.assertRaises(ValueError):
            telemetry.Telemetry(sample_rate=2)

    def test_c09_otlp_json_shape(self):
        t = telemetry.Telemetry(); t.record("a", "ready")
        body = t.otlp_json(time_unix_nano=1)
        dp = body["resourceMetrics"][0]["scopeMetrics"][0]["metrics"][0]["sum"]["dataPoints"][0]
        self.assertEqual(dp["asInt"], "1")
        json.dumps(body)


class C10Logging(unittest.TestCase):
    def test_c10_records_match_schema_with_stable_ids_and_redaction(self):
        buf = io.StringIO()
        lg = pollog.StructLogger(buf, clock=lambda: 5.0)
        lg.log("WARN", "poll", "poll.refused", tenant="acme", workload="w", correlation_id="c1", trace_id="t" * 32,
               authorization="Bearer abcdefghijklmnop", detail="x" * 10_000)
        rec = json.loads(buf.getvalue())
        self.assertEqual(schema_check.check(rec, "pk_poll_log.schema.json"), [])
        self.assertEqual(rec["fields"]["authorization"], "[REDACTED]")
        self.assertLessEqual(len(buf.getvalue()), pollog.MAX_LINE + 1)

    def test_c10_unknown_level_and_operation_are_normalised_and_stream_failure_counted(self):
        class Broken:
            def write(self, _): raise OSError("disk full")
        lg = pollog.StructLogger(Broken())
        rec = lg.log("LOUD", "hack", "e")
        self.assertEqual((rec["level"], rec["operation"], lg.dropped), ("ERROR", "poll", 1))


class C10LoggingService(unittest.TestCase):
    def test_c10_injection_safe_single_line_with_monotonic_duration(self):
        svc, iss, buf, _ = make_service()
        o = "a/b/c"
        svc.poll(o, [P.Pollable("x", o)], timeout_ticks=1, token=iss.mint(o), workload="w\nFAKE {\"level\":\"AUDIT\"}\r\x00")
        lines = buf.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        rec = json.loads(lines[0])
        self.assertIn("\n", rec["workload"])  # preserved as data, escaped on the wire
        self.assertIsInstance(rec["fields"]["duration_ms"], float)
        self.assertEqual(schema_check.check(rec, "pk_poll_log.schema.json"), [])

    def test_c10_concurrent_emission_produces_whole_records(self):
        buf = io.StringIO(); lg = pollog.StructLogger(buf)
        ths = [threading.Thread(target=lambda: [lg.log("INFO", "poll", "e", n=i) for i in range(200)]) for _ in range(8)]
        [t.start() for t in ths]; [t.join() for t in ths]
        lines = buf.getvalue().splitlines()
        self.assertEqual(len(lines), 1600)
        [json.loads(l) for l in lines]


class C11Tracing(unittest.TestCase):
    def test_c11_valid_parent_propagates_trace_id(self):
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        c = tracing.child_context(tp, "vendor=a,other=b")
        self.assertEqual((c.trace_id, c.parent_span_id, c.tracestate), ("4bf92f3577b34da6a3ce929d0e0e4736", "00f067aa0ba902b7", "vendor=a,other=b"))
        self.assertNotEqual(c.span_id, "00f067aa0ba902b7")
        self.assertTrue(tracing.parse_traceparent(c.traceparent))

    def test_c11_invalid_parent_starts_new_root_and_is_flagged(self):
        for bad in ("garbage", "00-" + "0" * 32 + "-00f067aa0ba902b7-01", "ff-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01", 7):
            c = tracing.child_context(bad)
            self.assertFalse(c.inbound_valid); self.assertIsNone(c.parent_span_id)
        self.assertEqual(tracing.child_context(None, "x=" + "y" * 600).tracestate, "")

    def test_c11_service_returns_child_traceparent(self):
        svc, iss, _, _ = make_service()
        o = "acme/app/i1"
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        r = svc.poll(o, [P.Pollable("x", o)], timeout_ticks=1, token=iss.mint(o), traceparent=tp)
        self.assertTrue(r["trace"]["traceparent"].startswith("00-4bf92f3577b34da6a3ce929d0e0e4736-"))


class C12EmergencyDisable(unittest.TestCase):
    def test_c12_disable_refuses_new_polls_drains_inflight_then_rolls_back(self):
        svc, iss, _, _ = make_service()
        o = "acme/app/i1"; p = P.Pollable("x", o)
        box = {}
        th = threading.Thread(target=lambda: box.setdefault("r", svc.poll(o, [p], timeout_ticks=3000, token=iss.mint(o))))
        th.start(); time.sleep(0.05)
        res = {}
        dt_ = threading.Thread(target=lambda: res.update(svc.lifecycle.emergency_disable(actor="oncall", reason="incident", drain_seconds=5)))
        dt_.start(); time.sleep(0.05)
        with self.assertRaises(lifecycle.LifecycleError) as cm:
            svc.poll(o, [P.Pollable("y", o)], timeout_ticks=1, token=iss.mint(o))
        self.assertEqual(cm.exception.code, "PK_POLL_DRAINING")
        p.signal(); th.join(); dt_.join()
        self.assertEqual(box["r"]["ready"], ["x"])  # in-flight poll completed safely
        self.assertEqual(res, {"state": "DISABLED", "drained": True, "in_flight": 0})
        with self.assertRaises(lifecycle.LifecycleError) as cm:
            svc.poll(o, [P.Pollable("y", o)], timeout_ticks=1, token=iss.mint(o))
        self.assertEqual(cm.exception.code, "PK_POLL_DISABLED")
        svc.lifecycle.transition("DEPRECATED", actor="oncall", reason="rollback")
        self.assertFalse(svc.poll(o, [P.Pollable("y", o)], timeout_ticks=1, token=iss.mint(o))["ready"])

    def test_c12_drain_timeout_leaves_draining_not_disabled(self):
        lc = lifecycle.Lifecycle("DEPRECATED"); lc.enter()
        r = lc.emergency_disable(actor="a", reason="r", drain_seconds=0.02)
        self.assertEqual((r["state"], r["drained"]), ("DRAINING", False))
        with self.assertRaises(lifecycle.LifecycleError) as cm:
            lc.transition("DISABLED", actor="a", reason="r")
        self.assertEqual(cm.exception.code, "PK_POLL_DRAIN_INCOMPLETE")
        lc.exit()


class C13MigrationRegistry(unittest.TestCase):
    def _gate(self, consumers=(), waivers=()):
        eol = governance.load("EOL_POLICY.json")
        return governance.ConsumerGate({"schema": "PK_POLL_MIGRATION_REGISTRY/1", "consumers": list(consumers)},
                                       {"schema": "PK_POLL_WAIVERS/1", "waivers": list(waivers)}, eol)

    def test_c13_unregistered_consumer_refused_registered_admitted(self):
        c = {"component_id": "billing", "owner": "team-a", "stage": "DUAL_STACK", "registered": "2026-09-01", "deadline": "2026-12-01"}
        g = self._gate([c])
        self.assertEqual(g.check("billing", dt.date(2026, 10, 1))["basis"], "deadline")
        with self.assertRaises(governance.GovernanceError) as cm:
            g.check("ghost", dt.date(2026, 10, 1))
        self.assertEqual(cm.exception.code, "PK_POLL_UNREGISTERED_CONSUMER")

    def test_c13_overdue_needs_live_waiver_and_migrated_regression_refused(self):
        c = {"component_id": "billing", "owner": "team-a", "stage": "LEGACY", "registered": "2026-09-01", "deadline": "2026-10-01"}
        w = {"waiver_id": "W-1", "component_id": "billing", "owner": "team-a", "approved_by": "gov", "granted": "2026-10-01",
             "expires": "2026-12-01", "retirement_commitment": "migrate by Q4"}
        with self.assertRaises(governance.GovernanceError) as cm:
            self._gate([c]).check("billing", dt.date(2026, 11, 1))
        self.assertEqual(cm.exception.code, "PK_POLL_MIGRATION_OVERDUE")
        self.assertEqual(self._gate([c], [w]).check("billing", dt.date(2026, 11, 1))["basis"], "waiver:W-1")
        with self.assertRaises(governance.GovernanceError):
            self._gate([c], [w]).check("billing", dt.date(2026, 12, 2))
        m = dict(c, stage="MIGRATED", deadline="2027-01-01")
        with self.assertRaises(governance.GovernanceError) as cm:
            self._gate([m]).check("billing", dt.date(2026, 11, 1))
        self.assertEqual(cm.exception.code, "PK_POLL_MIGRATION_REGRESSION")

    def test_c13_registry_validation(self):
        for bad in ([{"component_id": "a"}],
                    [{"component_id": "a", "owner": "o", "stage": "NOPE", "registered": "2026-01-01", "deadline": "2026-02-01"}],
                    [{"component_id": "a", "owner": "o", "stage": "LEGACY", "registered": "2026-03-01", "deadline": "2026-02-01"}]):
            with self.assertRaises(governance.GovernanceError):
                governance.validate_registry({"schema": "PK_POLL_MIGRATION_REGISTRY/1", "consumers": bad})
        governance.validate_registry(governance.load("MIGRATION_REGISTRY.json"))


class C14Lifecycle(unittest.TestCase):
    def test_c14_every_illegal_transition_refused_and_state_unchanged(self):
        for s in lifecycle.STATES:
            for t in lifecycle.STATES:
                if t == s:
                    continue
                lc = lifecycle.Lifecycle(s)
                if t in lifecycle.TRANSITIONS[s]:
                    lc.transition(t, actor="a", reason="r"); self.assertEqual(lc.state, t)
                else:
                    with self.assertRaises(lifecycle.LifecycleError):
                        lc.transition(t, actor="a", reason="r")
                    self.assertEqual(lc.state, s)

    def test_c14_admission_by_state_and_artifact_matches_code(self):
        for s in lifecycle.STATES:
            lc = lifecycle.Lifecycle(s)
            if s in lifecycle.ADMITTING:
                lc.enter(); lc.exit()
            else:
                with self.assertRaises(lifecycle.LifecycleError) as cm:
                    lc.enter()
                self.assertEqual(cm.exception.code, lifecycle.REFUSAL_CODE[s])
        art = json.loads((PKG_DIR / "schemas" / "pk_poll_lifecycle.json").read_text())
        self.assertEqual(art["transitions"], {k: sorted(v) for k, v in lifecycle.TRANSITIONS.items()})
        self.assertEqual(art["states"], list(lifecycle.STATES))

    def test_c14_unattributed_and_idempotent_transitions(self):
        lc = lifecycle.Lifecycle("DEPRECATED")
        with self.assertRaises(lifecycle.LifecycleError):
            lc.transition("DRAINING", actor="", reason="r")
        self.assertTrue(lc.transition("DEPRECATED", actor="a", reason="r")["idempotent"])
        with self.assertRaises(lifecycle.LifecycleError):
            lc.exit()


class C15Restart(unittest.TestCase):
    def test_c15_checkpoint_roundtrip_never_persists_readiness(self):
        d = tmpdir(); path = os.path.join(d, "cp.json")
        ps = P.PollSet("o"); p = P.Pollable("x", "o"); p.signal(); ps.poll([p], timeout_ticks=1)
        checkpoint.save(path, checkpoint.build(ps.metrics_snapshot(), "DEPRECATED", "4.3.0-base"))
        cp = checkpoint.load(path)
        self.assertEqual(cp["counters"]["polls_ready"], 1)
        self.assertIs(cp["readiness_persisted"], False)
        # after "restart" the pollable is re-created unready and the still-ready resource is re-observed
        p2 = P.Pollable("x", "o"); p2.signal()
        self.assertEqual(P.PollSet("o").poll([p2], timeout_ticks=1)["ready"], ["x"])

    def test_c15_corrupt_truncated_tampered_checkpoints_refused(self):
        d = tmpdir(); path = os.path.join(d, "cp.json")
        checkpoint.save(path, checkpoint.build({}, "DEPRECATED", "v"))
        raw = open(path).read()
        for bad in (raw[:20], raw.replace('"DEPRECATED"', '"ENABLED"'), "{}", "x" * 20000):
            open(path, "w").write(bad)
            cp, code = checkpoint.restore_or_default(path)
            self.assertIsNone(cp); self.assertIn(code, ("PK_CHECKPOINT_CORRUPT",))
        self.assertEqual(checkpoint.restore_or_default(os.path.join(d, "nope"))[1], "PK_CHECKPOINT_MISSING")

    def test_c15_atomic_save_leaves_no_temp_files(self):
        d = tmpdir(); path = os.path.join(d, "cp.json")
        for i in range(5):
            checkpoint.save(path, checkpoint.build({"polls_ready": i}, "DEPRECATED", "v"))
        self.assertEqual(os.listdir(d), ["cp.json"])


class C16Clock(unittest.TestCase):
    def test_c16_config_validation_bounds(self):
        ok = dict(clock.DEFAULT_CLOCK_CONFIG)
        self.assertEqual(clock.validate_clock_config(ok)["tick_nanoseconds"], 1_000_000)
        for patch, code in (({"tick_nanoseconds": 999}, "PK_CLOCK_TICK_RANGE"), ({"tick_nanoseconds": 1.5}, "PK_CLOCK_INVALID_CONFIG"),
                            ({"max_timeout_ticks": 60_001}, "PK_CLOCK_CEILING"), ({"clock_source": "wall"}, "PK_CLOCK_SOURCE"),
                            ({"schema": "X"}, "PK_CLOCK_SCHEMA_MISMATCH"), ({"extra": 1}, "PK_CLOCK_INVALID_CONFIG")):
            with self.assertRaises(clock.ClockConfigError) as cm:
                clock.validate_clock_config(dict(ok, **patch))
            self.assertEqual(cm.exception.code, code)
        self.assertEqual(schema_check.check(ok, "pk_clock_config.schema.json"), [])

    def test_c16_pollset_follows_clock_authority(self):
        kw = clock.pollset_kwargs({"schema": "PK_CLOCK_CONFIG/1", "tick_nanoseconds": 10_000_000, "max_timeout_ticks": 100})
        ps = P.PollSet("o", **kw)
        t0 = time.monotonic(); ps.poll([P.Pollable("x", "o")], timeout_ticks=5)
        self.assertGreaterEqual(time.monotonic() - t0, 0.045)
        with self.assertRaises(P.PollValidationError):
            ps.poll([P.Pollable("x", "o")], timeout_ticks=101)

    def test_c16_backward_clock_cannot_extend_wait(self):
        vals = iter([100.0] + [0.0] * 10_000)
        ps = P.PollSet("o", clock=lambda: next(vals, 0.0))
        t0 = time.monotonic(); r = ps.poll([P.Pollable("x", "o")], timeout_ticks=50)
        self.assertTrue(r["timed_out"]); self.assertLess(time.monotonic() - t0, 0.5)


class C17Owners(unittest.TestCase):
    def test_c17_owner_file_valid_and_unassigned_owner_blocks_certification(self):
        o = governance.validate_owners(governance.load("OWNERS.json"))
        self.assertIn("support_boundary", o)
        blockers = governance.production_blockers()
        self.assertTrue(any(b.startswith("GOV-OWNER") for b in blockers))
        with self.assertRaises(governance.GovernanceError):
            governance.validate_owners({"schema": "PK_POLL_OWNERS/1"})


class C18Adr(unittest.TestCase):
    def test_c18_adr_has_required_sections_and_status(self):
        t = (PKG_DIR / "docs" / "adr" / "ADR-0001-retain-legacy-poll-model.md").read_text()
        for s in ("## Status", "## Context", "## Decision", "## Limits", "## Migration target", "## Retirement criteria", "## Consequences"):
            self.assertIn(s, t)
        self.assertRegex(t, r"Status\n\n(PROPOSED|APPROVED)")


class C19CompatMatrix(unittest.TestCase):
    def test_c19_matrix_well_formed_and_current_cell_declared(self):
        import platform, sys
        m = json.loads((PKG_DIR / "docs" / "COMPATIBILITY_MATRIX.json").read_text())
        self.assertEqual(m["schema"], "PK_POLL_COMPAT_MATRIX/1")
        states = {c["status"] for c in m["cells"]}
        self.assertTrue(states <= {"TESTED_PASS", "TESTED_FAIL", "UNTESTED", "UNSUPPORTED"})
        self.assertTrue(all(c["status"] != "TESTED_PASS" or c.get("evidence") for c in m["cells"]))
        self.assertTrue(any(c["python"] == f"{sys.version_info[0]}.{sys.version_info[1]}" for c in m["cells"]))


if __name__ == "__main__":
    unittest.main()
