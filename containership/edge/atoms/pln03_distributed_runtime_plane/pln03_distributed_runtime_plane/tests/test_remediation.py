"""Remediation tests.  Test names carry the MC id they close so TRACEABILITY.json can link them."""
from __future__ import annotations

import json
import os
import random
import tempfile
import threading
import unittest

from _helpers import (KEY, FakeClock, artifacts, audit_log, cfg_with, config, durability, envelope, lifecycle,
                      make_plane, negotiation, resilience, runtime, telemetry, tokens)


class MC005_MC015_Envelope(unittest.TestCase):
    def test_mc005_every_code_has_one_outcome_class(self):
        for code, spec in envelope.CODES.items():
            self.assertIn(spec.outcome, set(envelope.Outcome), code)

    def test_mc015_envelope_round_trips_and_validates_for_every_error_class(self):
        classes = [runtime.CapabilityDenied, runtime.AdapterUnavailable, runtime.InvalidRuntimeInput,
                   runtime.PayloadTooLarge, runtime.InvocationTargetUnavailable, tokens.TokenExpired,
                   resilience.DeadlineExceeded, resilience.CircuitOpen, durability.Fenced, lifecycle.Quarantined,
                   config.ConfigInvalid, negotiation.VersionUnsupported]
        for cls in classes:
            env = envelope.to_envelope(cls("boom", limit=3), trace_id="a" * 32)
            envelope.validate_envelope(json.loads(envelope.dumps(env)))
        self.assertTrue(envelope.to_envelope(runtime.AdapterUnavailable("x"))["retryable"])
        self.assertFalse(envelope.to_envelope(runtime.CapabilityDenied("x"))["retryable"])

    def test_mc015_unknown_exception_maps_to_internal(self):
        env = envelope.to_envelope(RuntimeError("secret=abc"))
        self.assertEqual(env["code"], "PK_RUNTIME_ERROR")
        envelope.validate_envelope(env)


class MC006_MC042_Lifecycle(unittest.TestCase):
    def test_mc006_illegal_transitions_refused(self):
        lc = lifecycle.Lifecycle("x")
        with self.assertRaises(lifecycle.LifecycleRefused):
            lc.transition(lifecycle.State.READY, actor="op", reason="skip starting")
        for src, dsts in lifecycle.LEGAL.items():
            for dst in lifecycle.State:
                self.assertEqual(dst in dsts, dst in lifecycle.LEGAL[src])
        self.assertEqual(lifecycle.LEGAL[lifecycle.State.STOPPED], frozenset())

    def test_mc006_calls_refused_before_ready(self):
        gp, tok, *_ = make_plane()
        gp.lifecycle._state = lifecycle.State.STARTING
        with self.assertRaises(lifecycle.LifecycleRefused):
            gp.state_get("api", "t1", "k", token=tok)

    def test_mc042_freeze_allows_reads_refuses_writes(self):
        gp, tok, *_ = make_plane()
        gp.state_set("api", "t1", "k", b"v", token=tok)
        gp.freeze("oncall", "incident 1")
        self.assertEqual(gp.state_get("api", "t1", "k", token=tok), b"v")
        with self.assertRaises(lifecycle.LifecycleRefused):
            gp.state_set("api", "t1", "k", b"w", token=tok)
        gp.unfreeze("oncall", "resolved")
        gp.state_set("api", "t1", "k", b"w", token=tok)

    def test_mc042_emergency_disable_and_adapter_quarantine(self):
        gp, tok, *_ = make_plane()
        gp.quarantine_adapter("state-a", "sec", "suspected exfiltration")
        with self.assertRaises(lifecycle.Quarantined):
            gp.state_get("api", "t1", "k", token=tok)
        gp.release_adapter("state-a", "sec", "cleared")
        gp.state_get("api", "t1", "k", token=tok)
        gp.emergency_disable("sec", "kill switch")
        with self.assertRaises(lifecycle.Quarantined):
            gp.subscribe("api", "t1", "x", token=tok)
        self.assertFalse(gp.health()["ready"])


class MC013_MC033_Tokens(unittest.TestCase):
    def setUp(self):
        self.gp, self.tok, self.issuer, self.clock, _ = make_plane()

    def test_mc013_absent_token_fails_closed(self):
        with self.assertRaises(tokens.TokenInvalid):
            self.gp.state_get("api", "t1", "k", token=None)
        self.assertEqual(self.gp.metrics.get("capability_denials", capability="state", code="PK_TOKEN_INVALID"), 1)

    def test_mc013_expired_token_fails_closed(self):
        self.clock.advance(301 + tokens.CLOCK_SKEW_SECONDS)
        with self.assertRaises(tokens.TokenExpired):
            self.gp.state_get("api", "t1", "k", token=self.tok)

    def test_mc013_tampered_wrong_subject_wrong_capability(self):
        body, sig = self.tok.split(".")
        with self.assertRaises(tokens.TokenInvalid):
            self.gp.state_get("api", "t1", "k", token=body + "." + sig[::-1])
        with self.assertRaises(tokens.TokenInvalid):
            self.gp.state_get("api", "t2", "k", token=self.tok)
        narrow = self.issuer.mint("api", "t1", {"state"})
        with self.assertRaises(tokens.TokenInvalid):
            self.gp.subscribe("api", "t1", "x", token=narrow)

    def test_mc013_valid_token_but_no_binding_still_denied(self):
        gp, _, issuer, *_ = make_plane(caps=("state",))
        tok = issuer.mint("api", "t1", {"state", "messaging"})
        with self.assertRaises(runtime.CapabilityDenied):
            gp.publish("api", "t1", "x", b"p", "i", token=tok)

    def test_mc032_key_rotation_and_retirement(self):
        ring = self.gp.verifier.ring
        ring.add("k2", b"z" * 32, activate=True)
        new = self.issuer.mint("api", "t1", {"state"})
        self.gp.state_get("api", "t1", "k", token=new)
        self.gp.state_get("api", "t1", "k", token=self.tok)     # old key still valid until retired
        ring.retire("k1")
        with self.assertRaises(tokens.TokenInvalid):
            self.gp.state_get("api", "t1", "k", token=self.tok)
        with self.assertRaises(ValueError):
            ring.retire("k2")
        with self.assertRaises(ValueError):
            ring.add("short", b"x")

    def test_mc033_time_and_revocation_outage_fail_closed(self):
        v = tokens.TokenVerifier(self.gp.verifier.ring, self.clock, clock_ok=lambda: False)
        with self.assertRaises(tokens.SecurityDependencyUnavailable):
            v.verify(self.tok, workload="api", tenant="t1", capability="state")

        def down(_):
            raise OSError("revocation service down")
        v = tokens.TokenVerifier(self.gp.verifier.ring, self.clock, revoked=down)
        with self.assertRaises(tokens.SecurityDependencyUnavailable):
            v.verify(self.tok, workload="api", tenant="t1", capability="state")
        v = tokens.TokenVerifier(self.gp.verifier.ring, self.clock, revoked=lambda j: True)
        with self.assertRaises(tokens.TokenInvalid):
            v.verify(self.tok, workload="api", tenant="t1", capability="state")


class MC014_MC037_MC038_Resilience(unittest.TestCase):
    def test_mc014_deadline_and_cancellation(self):
        c = FakeClock()
        d = resilience.Deadline(1.0, c)
        d.check()
        c.advance(1.1)
        with self.assertRaises(resilience.DeadlineExceeded):
            d.check()
        d2 = resilience.Deadline(5, c)
        d2.cancel("client went away")
        with self.assertRaises(resilience.Cancelled):
            d2.check()

    def test_mc037_retries_only_retryable_with_bounded_jittered_backoff(self):
        c = FakeClock()
        lim = resilience.Limits(retry_max_attempts=4, retry_base_s=0.01, retry_cap_s=0.05)
        sleeps, calls = [], []

        def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise runtime.AdapterUnavailable("down")
            return "ok"
        out = resilience.retry_call(flaky, limits=lim, deadline=resilience.Deadline(10, c),
                                    budget=resilience.RetryBudget(1.0), sleep=sleeps.append, rng=random.Random(1))
        self.assertEqual(out, "ok")
        self.assertEqual(len(sleeps), 2)
        self.assertTrue(all(0 <= s <= 0.05 for s in sleeps))
        calls.clear()

        def terminal():
            calls.append(1)
            raise runtime.CapabilityDenied("no")
        with self.assertRaises(runtime.CapabilityDenied):
            resilience.retry_call(terminal, limits=lim, deadline=resilience.Deadline(10, c),
                                  budget=resilience.RetryBudget(1.0), sleep=sleeps.append)
        self.assertEqual(len(calls), 1)

    def test_mc037_retry_budget_exhaustion_stops_retry_storm(self):
        c = FakeClock()
        b = resilience.RetryBudget(0.0, cap=10)
        b.tokens = 0
        n = []

        def down():
            n.append(1)
            raise runtime.AdapterUnavailable("x")
        with self.assertRaises(runtime.AdapterUnavailable):
            resilience.retry_call(down, limits=resilience.Limits(), deadline=resilience.Deadline(10, c),
                                  budget=b, sleep=lambda s: None)
        self.assertEqual(len(n), 1)

    def test_mc038_circuit_breaker_opens_and_half_opens(self):
        c = FakeClock()
        br = resilience.CircuitBreaker(2, 5.0, c)
        br.record(False)
        br.record(False)
        with self.assertRaises(resilience.CircuitOpen):
            br.before("db")
        c.advance(5)
        br.before("db")
        self.assertEqual(br.state, "half_open")
        br.record(True)
        self.assertEqual(br.state, "closed")

    def test_mc038_plane_breaker_opens_on_dead_adapter(self):
        cfg = cfg_with(limits={**config.DEFAULT["limits"], "breaker_failure_threshold": 2, "retry_max_attempts": 1})
        gp, tok, _, _, ad = make_plane(cfg=cfg)
        ad["state"].available = False
        for _ in range(2):
            with self.assertRaises(runtime.AdapterUnavailable):
                gp.state_get("api", "t1", "k", token=tok)
        with self.assertRaises(resilience.CircuitOpen):
            gp.state_get("api", "t1", "k", token=tok)
        self.assertEqual(gp.health()["breakers"]["state-a"], "open")

    def test_mc008_mc038_rate_limit_and_tenant_fairness(self):
        c = FakeClock()
        lim = resilience.Limits(rate_per_tenant_per_s=1, burst_per_tenant=2, max_concurrency_per_tenant=1,
                                max_concurrency_global=2, max_tenants_tracked=3)
        a = resilience.Admission(lim, c)
        a.acquire("t1")
        with self.assertRaises(resilience.QuotaExceeded):
            a.acquire("t1")                     # t1 cannot monopolise the pool
        a.acquire("t2")
        with self.assertRaises(resilience.RateLimited):
            a.acquire("t3")                     # global ceiling -> load shed
        a.release("t1"); a.release("t2")
        a.acquire("t1"); a.release("t1")
        with self.assertRaises(resilience.RateLimited):
            a.acquire("t1")                     # bucket empty
        c.advance(1)
        a.acquire("t1"); a.release("t1")
        a.acquire("t3"); a.release("t3")
        with self.assertRaises(resilience.QuotaExceeded):
            a.acquire("t4")                     # bounded tenant tracking
        self.assertEqual(a.in_flight, 0)


class MC021_to_MC025_Config(unittest.TestCase):
    def test_mc021_secure_defaults_validate(self):
        config.validate(config.DEFAULT)

    def test_mc021_invalid_configs_refused_before_activation(self):
        bad = [cfg_with(consistency="linearish"), cfg_with(tokens={"required": False}),
               cfg_with(site={**config.DEFAULT["site"], "class": "moon"}),
               cfg_with(limits={**config.DEFAULT["limits"], "max_concurrency_per_tenant": 10**6}),
               cfg_with(limits={**config.DEFAULT["limits"], "bogus": 1}),
               {**config.DEFAULT, "extra": 1}, {**config.DEFAULT, "schema": "v0"}]
        store = config.ConfigStore()
        good = store.activate(config.DEFAULT, author="a", source="s", reason="r")
        for b in bad:
            with self.assertRaises(config.ConfigInvalid):
                store.activate(b, author="a", source="s", reason="r")
            self.assertIs(store.active, good)

    def test_mc010_residency_precedes_slo(self):
        cfg = cfg_with(site={**config.DEFAULT["site"], "residency_zones": ["eu"]},
                       adapters={"state": {"name": "fast-us", "residency_zone": "us"}})
        with self.assertRaises(config.ConfigInvalid):
            config.validate(cfg)
        self.assertEqual(config.CONSTRAINT_PRECEDENCE[0], "security")

    def test_mc022_mc024_provenance_and_rollback(self):
        c = FakeClock()
        store = config.ConfigStore(clock=c)
        r1 = store.activate(config.DEFAULT, author="alice", source="git:abc", reason="initial")
        c.advance(10)
        r2 = store.activate(cfg_with(consistency="eventual"), author="bob", source="git:def", reason="edge")
        self.assertNotEqual(r1.digest, r2.digest)
        r3 = store.rollback(author="oncall", reason="SLO burn")
        self.assertEqual(r3.digest, r1.digest)
        led = store.ledger()
        self.assertEqual([e["revision"] for e in led], [1, 2, 3])
        self.assertTrue(led[-1]["active"] and led[-1]["source"].startswith("rollback:1:"))
        self.assertEqual({e["author"] for e in led}, {"alice", "bob", "oncall"})

    def test_mc023_atomic_activation_under_concurrency(self):
        store = config.ConfigStore()
        store.activate(config.DEFAULT, author="a", source="s", reason="r")
        seen = set()

        def reader():
            for _ in range(500):
                seen.add((store.active.digest, store.active.config["consistency"]))
        t = threading.Thread(target=reader)
        t.start()
        for i in range(50):
            store.activate(cfg_with(consistency=["eventual", "strong"][i % 2]), author="a", source="s", reason="r")
        t.join()
        pairs = {d: c for d, c in seen}
        for d, c in seen:
            self.assertEqual(pairs[d], c)          # never a torn (digest, content) pair

    def test_mc025_secrets_refused_and_redacted(self):
        with self.assertRaises(config.ConfigInvalid):
            config.validate(cfg_with(adapters={"state": {"name": "x", "password": "p"}}))
        with self.assertRaises(config.ConfigInvalid):
            config.validate(cfg_with(site={**config.DEFAULT["site"], "id": "-----BEGIN RSA PRIVATE KEY-----"}))
        red = config.redact({"api_key": "abc", "nested": [{"token": "x"}], "blob": b"\x00" * 9, "ok": 1})
        self.assertEqual(red["api_key"], config.REDACTED)
        self.assertEqual(red["nested"][0]["token"], config.REDACTED)
        self.assertEqual(red["blob"], "<9 bytes>")

    def test_mc025_no_payload_or_secret_in_logs_audit_or_metrics(self):
        gp, tok, *_ = make_plane()
        gp.core._bindings["api:secrets"].set("t1/db", b"SUPERSECRETVALUE")
        self.assertEqual(gp.secret_fetch("api", "t1", "db", token=tok), b"SUPERSECRETVALUE")
        gp.state_set("api", "t1", "k", b"PAYLOADMARKER", token=tok)
        try:
            gp.state_get("api", "t1", "k", token="garbage.token")
        except tokens.TokenInvalid:
            pass
        blob = json.dumps(list(gp.audit.events)) + json.dumps(gp.log.records) + gp.metrics.exposition()
        for needle in ("SUPERSECRETVALUE", "PAYLOADMARKER", tok, "garbage.token"):
            self.assertNotIn(needle, blob)


class MC034_Audit(unittest.TestCase):
    def test_mc034_every_call_and_denial_is_chained(self):
        gp, tok, *_ = make_plane()
        gp.state_set("api", "t1", "k", b"v", token=tok)
        gp.secret_fetch.__self__  # noqa
        with self.assertRaises(tokens.TokenInvalid):
            gp.state_get("api", "t1", "k", token=None)
        actions = [e["action"] for e in gp.audit.events]
        self.assertIn("state.write", actions)
        self.assertIn("deny", actions)
        ok, msg = audit_log.verify_chain(gp.audit.events)
        self.assertTrue(ok, msg)

    def test_mc034_tamper_detected_and_seal_enforced(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "audit.jsonl")
            log = audit_log.AuditLog(p, seal_key=KEY)
            for i in range(5):
                log.emit("state.read", workload="api", tenant="t1", outcome="success", n=i)
            log2 = audit_log.AuditLog(p, seal_key=KEY)          # resumes chain after restart
            log2.emit("state.read", workload="api", tenant="t1", outcome="success")
            evs = audit_log.read_jsonl(p)
            self.assertEqual(audit_log.verify_chain(evs, KEY), (True, "ok"))
            evs[2]["outcome"] = "failure"
            self.assertFalse(audit_log.verify_chain(evs, KEY)[0])
            evs = audit_log.read_jsonl(p)
            del evs[3]
            self.assertFalse(audit_log.verify_chain(evs, KEY)[0])
            evs = audit_log.read_jsonl(p)
            self.assertFalse(audit_log.verify_chain(evs, b"q" * 32)[0])


class MC009_MC039_MC040_MC041_Durability(unittest.TestCase):
    def test_mc041_journal_replay_after_crash_and_torn_tail(self):
        with tempfile.TemporaryDirectory() as d:
            j = os.path.join(d, "state.wal")
            a = durability.DurableAdapter("s", j, fsync=False)
            rt = runtime.DistributedRuntime({"api:state": a, "api:messaging": a})
            rt.state_set("api", "t1", "a", b"1")
            rt.state_transact("api", "t1", [("set", "b", b"2"), ("delete", "a", None)])
            rt.publish("api", "t1", "q", b"m", "idem")
            with open(j, "a") as fh:
                fh.write('{"b": {"op": "set", "k": "t1/x"')       # torn write at crash
            b = durability.DurableAdapter("s", j, fsync=False)
            rt2 = runtime.DistributedRuntime({"api:state": b, "api:messaging": b})
            self.assertIsNone(rt2.state_get("api", "t1", "a"))
            self.assertEqual(rt2.state_get("api", "t1", "b"), b"2")
            self.assertEqual(rt2.subscribe("api", "t1", "q"), (b"m",))
            self.assertFalse(rt2.publish("api", "t1", "q", b"m", "idem"))   # dedupe survives restart
            self.assertEqual(b.discarded_tail, 1)

    def test_mc041_interior_corruption_is_fatal(self):
        with tempfile.TemporaryDirectory() as d:
            j = os.path.join(d, "w")
            a = durability.DurableAdapter("s", j, fsync=False)
            a.set("k1", b"1"); a.set("k2", b"2")
            with open(j) as fh:
                lines = fh.read().splitlines()
            lines[0] = lines[0].replace('"k1"', '"kX"')
            with open(j, "w") as fh:
                fh.write("\n".join(lines) + "\n")
            with self.assertRaises(runtime.RuntimePlaneError):
                durability.DurableAdapter("s", j, fsync=False)

    def test_mc041_fencing_refuses_stale_writer(self):
        with tempfile.TemporaryDirectory() as d:
            c = FakeClock()
            lm = durability.LeaseManager(ttl=10, clock=c)
            a = durability.DurableAdapter("s", os.path.join(d, "w"), fsync=False)
            old = lm.acquire("node-a")
            a.advance_epoch(old.epoch)
            with self.assertRaises(durability.Fenced):
                lm.acquire("node-b")                 # split brain refused while lease live
            c.advance(11)
            new = lm.acquire("node-b")
            a.advance_epoch(new.epoch)
            with self.assertRaises(durability.Fenced):
                a.set("k", b"stale", epoch=old.epoch)
            a.set("k", b"fresh", epoch=new.epoch)
            self.assertEqual(durability.DurableAdapter("s", os.path.join(d, "w"), fsync=False).epoch, new.epoch)

    def test_mc009_mc040_partition_buffer_and_reconcile_without_duplicates(self):
        cfg = cfg_with(degraded={"allow_local_buffer": True, "read_only_on_partition": True},
                       limits={**config.DEFAULT["limits"], "retry_max_attempts": 1,
                               "max_offline_buffer_msgs": 3})
        gp, tok, _, _, ad = make_plane(cfg=cfg)
        gp.publish("api", "t1", "q", b"m0", "i0", token=tok)
        ad["messaging"].available = False
        r = gp.publish("api", "t1", "q", b"m1", "i1", token=tok)
        self.assertEqual(r.outcome, "degraded")
        gp.publish("api", "t1", "q", b"m0-again", "i0", token=tok)   # duplicate of pre-partition msg
        gp.publish("api", "t1", "q", b"m2", "i2", token=tok)
        with self.assertRaises(durability.ReadOnly):
            gp.publish("api", "t1", "q", b"m3", "i3", token=tok)      # bounded buffer -> read-only
        ad["messaging"].available = True
        rep = gp.reconcile()
        self.assertEqual(rep, {"replayed": 2, "deduplicated": 1, "remaining": 0})
        self.assertEqual(gp.core.subscribe("api", "t1", "q"), (b"m0", b"m1", b"m2"))

    def test_mc040_without_buffer_policy_partition_is_retryable_error(self):
        gp, tok, _, _, ad = make_plane()
        ad["messaging"].available = False
        with self.assertRaises(runtime.AdapterUnavailable):
            gp.publish("api", "t1", "q", b"m", "i", token=tok)

    def test_mc039_failover_respects_residency_then_consistency(self):
        S = durability.Site
        cands = [S("us-1", "us", True, "strong"), S("eu-2", "eu", True, "eventual"),
                 S("eu-1", "eu", True, "strong", lag_s=0.5), S("eu-3", "eu", False, "strong")]
        self.assertEqual(durability.select_failover(cands, allowed_zones={"eu"}, required_consistency="strong",
                                                    max_lag_s=1).name, "eu-1")
        with self.assertRaises(durability.ResidencyViolation):
            durability.select_failover(cands, allowed_zones={"ap"}, required_consistency="eventual", max_lag_s=9)
        with self.assertRaises(durability.ReadOnly):
            durability.select_failover(cands, allowed_zones={"eu"}, required_consistency="strong", max_lag_s=0.1)


class MC016_Negotiation(unittest.TestCase):
    def test_mc016_common_major_selected_and_mismatch_terminal(self):
        agr = negotiation.negotiate(negotiation.hello())
        self.assertEqual(agr.versions, {k: 1 for k in negotiation.SUPPORTED})
        peer = {"schema": "pk.hello/1", "runtime": "5.0.0",
                "interfaces": {"PK_STATE": [1, 2], "PK_MESSAGE": [2], "PK_SECRET": [1], "PK_INVOKE": [1]}}
        with self.assertRaises(negotiation.VersionUnsupported):
            negotiation.negotiate(peer)
        self.assertEqual(negotiation.negotiate(peer, required=("PK_STATE",)).versions, {"PK_STATE": 1})
        with self.assertRaises(negotiation.VersionUnsupported):
            negotiation.negotiate({"interfaces": {}})


class MC030_Artifacts(unittest.TestCase):
    def test_mc030_digest_allowlist_and_provenance(self):
        import hashlib, hmac as _h
        data = b"component-wasm"
        dg = hashlib.sha256(data).hexdigest()
        prov = {"subject": [{"digest": {"sha256": dg}}],
                "predicate": {"builder": {"id": "ci://pln03"}, "source": "git+https://example.invalid/pln03"}}
        raw = json.dumps(prov, sort_keys=True, separators=(",", ":")).encode()
        prov["seal"] = _h.new(KEY, raw, hashlib.sha256).hexdigest()
        kw = dict(allowed_builders={"ci://pln03"}, allowed_sources={"git+https://example.invalid/pln03"},
                  provenance_key=KEY)
        self.assertEqual(artifacts.verify_artifact(data, allowlist={"sha256:" + dg}, provenance=prov, **kw),
                         "sha256:" + dg)
        for bad in (dict(allowlist=set(), provenance=prov), dict(allowlist={"sha256:" + dg}, provenance=None),
                    dict(allowlist={"sha256:" + dg}, provenance={**prov, "seal": "0"})):
            with self.assertRaises(artifacts.ArtifactRejected):
                artifacts.verify_artifact(data, **bad, **kw)
        with self.assertRaises(artifacts.ArtifactRejected):
            artifacts.verify_artifact(b"other", allowlist={"sha256:" + dg}, provenance=prov, **kw)


class MC036_MC045_Telemetry(unittest.TestCase):
    def test_mc045_metrics_health_and_trace_propagation(self):
        gp, tok, *_ = make_plane()
        tp = "00-" + "ab" * 16 + "-" + "cd" * 8 + "-01"
        gp.state_set("api", "t1", "k", b"v", token=tok, traceparent=tp)
        self.assertEqual(gp.audit.events[-1]["meta"]["trace_id"], "ab" * 16)
        self.assertEqual(gp.metrics.get("adapter_calls", capability="state", outcome="success"), 1)
        text = gp.metrics.exposition()
        self.assertIn('pk_pln03_state_latency_seconds_bucket{le="+Inf"} 1', text)
        h = gp.health()
        self.assertTrue(h["live"] and h["ready"])
        self.assertEqual(h["accountable_owner"], "role:pln03-owner")
        self.assertTrue(h["config_digest"].startswith("sha256:"))
        self.assertEqual(len(telemetry.parse_traceparent("junk")), 32)

    def test_mc045_metric_cardinality_is_bounded(self):
        m = telemetry.Metrics()
        for i in range(telemetry.MAX_SERIES + 50):
            m.inc("x", tenant=str(i))
        self.assertEqual(m.dropped_series, 50)

    def test_mc036_watchdog_detects_stall_and_readiness_drops(self):
        c = FakeClock()
        w = telemetry.Watchdog(2.0, c)
        t = w.start("state.read")
        c.advance(3)
        self.assertEqual([op for op, _ in w.stalled()], ["state.read"])
        w.stop(t)
        self.assertEqual(w.stalled(), [])


class MC028_MC031_Isolation(unittest.TestCase):
    def test_mc031_tenant_isolation_across_every_capability(self):
        gp, tok, issuer, *_ = make_plane()
        tok2 = issuer.mint("api", "t2", {"state", "messaging", "secrets", "invoke"})
        gp.state_set("api", "t1", "k", b"one", token=tok)
        gp.publish("api", "t1", "q", b"m", "i", token=tok)
        gp.core._bindings["api:secrets"].set("t1/s", b"sec")
        gp.core._bindings["api:invoke"].register_target("t1:svc", lambda p: b"t1-only")
        self.assertIsNone(gp.state_get("api", "t2", "k", token=tok2))
        self.assertEqual(gp.subscribe("api", "t2", "q", token=tok2), ())
        with self.assertRaises(runtime.SecretNotFound):
            gp.secret_fetch("api", "t2", "s", token=tok2)
        with self.assertRaises(runtime.InvocationTargetUnavailable):
            gp.invoke("api", "t2", "svc", b"", token=tok2)
        with self.assertRaises(tokens.TokenInvalid):
            gp.state_get("api", "t1", "k", token=tok2)       # t2's token cannot read t1


if __name__ == "__main__":
    unittest.main()
