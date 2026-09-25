"""Unit tests for the stdlib runtime modules (errors, wire, keys, iam, config, audit,
state, reliability, telemetry, supply chain)."""
from __future__ import annotations

import json
import os
import pathlib
import random
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from helpers import T0, Clock  # noqa: E402

from pln05_elasticity_plane import configuration, errors, supplychain, wire  # noqa: E402
from pln05_elasticity_plane.audit import AuditLog  # noqa: E402
from pln05_elasticity_plane.errors import PlaneError  # noqa: E402
from pln05_elasticity_plane.iam import Authenticator, Issuer, POLICY  # noqa: E402
from pln05_elasticity_plane.keys import KeyRing, TransportPolicy  # noqa: E402
from pln05_elasticity_plane.reliability import (AdmissionController, CircuitBreaker,  # noqa: E402
                                                RetryBudget, RetryPolicy)
from pln05_elasticity_plane.state import FencedSink, LeaseService, StateStore, migrate  # noqa: E402
from pln05_elasticity_plane.telemetry import Logger, Metrics, Tracer, parse_traceparent, redact  # noqa: E402

RELEASED_CODES = {  # frozen at 4.2.0: codes may be added, never changed
    "E_SCHEMA_MALFORMED": ("schema", False), "E_STALE_INPUT": ("freshness", False),
    "E_AUTHN_REPLAY": ("authn", False), "E_AUTHZ_SCOPE": ("authz", False),
    "E_NOT_LEADER": ("coordination", True), "E_FENCED": ("coordination", False),
    "E_OVERLOADED": ("overload", True), "E_CIRCUIT_OPEN": ("dependency", True),
    "E_AUDIT_UNAVAILABLE": ("audit", True), "E_ARTIFACT_UNTRUSTED": ("supply_chain", False),
}


class ErrorsTest(unittest.TestCase):
    def test_released_codes_are_stable(self):
        for code, (cat, retry) in RELEASED_CODES.items():
            self.assertEqual(errors.CODES[code][:2], (cat, retry), code)

    def test_wire_form_validates_against_error_schema(self):
        e = PlaneError("E_STALE_INPUT", "old", {"max_age_s": 30}, correlation_id="corr-0001")
        wire.validate("PK_ERROR", e.to_wire())

    def test_detail_values_are_sanitised(self):
        e = PlaneError("E_SCHEMA_FIELD", "x", {"field": "a\nb<script>", "n": 3, "obj": {"k": 1}})
        self.assertEqual(e.detail["field"], "<redacted>")
        self.assertEqual(e.detail["obj"], "<redacted>")
        self.assertEqual(e.detail["n"], 3)

    def test_unknown_code_becomes_internal(self):
        self.assertEqual(PlaneError("E_NOPE", "x").code, "E_INTERNAL")


class WireTest(unittest.TestCase):
    def test_negotiation(self):
        self.assertEqual(wire.negotiate("PK_DEMAND", [1, 2]), 1)
        with self.assertRaises(PlaneError) as cm:
            wire.negotiate("PK_DEMAND", [2, 3])
        self.assertEqual(cm.exception.code, "E_SCHEMA_VERSION")
        with self.assertRaises(PlaneError):
            wire.negotiate("PK_DEMAND", [True])

    def test_schema_checksums_are_stable_hex(self):
        sums = wire.schema_checksums()
        self.assertEqual(len(sums), 4)
        self.assertTrue(all(len(v) == 64 for v in sums.values()))

    def test_too_many_fields(self):
        body = {f"x-{i}": i for i in range(40)}
        body["schema"] = "PK_DEMAND/1"
        with self.assertRaises(PlaneError) as cm:
            wire.validate("PK_DEMAND", body)
        self.assertEqual(cm.exception.code, "E_SCHEMA_TOO_LARGE")

    def test_deep_nesting_inside_string_is_not_counted(self):
        raw = json.dumps({"x-note": "[[[[[[[[[[[[[[[[[[[["}).encode()
        self.assertIsInstance(wire.parse_bytes(raw), dict)

    def test_encode_rejects_invalid(self):
        with self.assertRaises(PlaneError):
            wire.encode("PK_DEMAND", {"schema": "PK_DEMAND/1"})


class KeysTest(unittest.TestCase):
    def test_rotation_overlap_and_revocation(self):
        ring = KeyRing()
        ring.add("k1", b"a" * 32, T0, T0 + 100)
        kid, mac = ring.sign(b"x", T0 + 1)
        ring.add("k2", b"b" * 32, T0 + 50, T0 + 200)
        self.assertEqual(ring.sign(b"x", T0 + 60)[0], "k2")  # newest signs
        ring.verify(kid, b"x", mac, T0 + 60)  # old still verifies in overlap
        with self.assertRaises(PlaneError) as cm:
            ring.verify(kid, b"x", mac, T0 + 150)
        self.assertEqual(cm.exception.code, "E_AUTHN_EXPIRED")
        ring.revoke("k2")
        with self.assertRaises(PlaneError) as cm:
            ring.sign(b"x", T0 + 150)
        self.assertEqual(cm.exception.code, "E_SECURITY_DEPENDENCY")

    def test_short_key_and_repr(self):
        ring = KeyRing()
        with self.assertRaises(PlaneError):
            ring.add("k", b"short", T0, T0 + 1)
        ring.add("k", b"s" * 32, T0, T0 + 1)
        self.assertNotIn("ssss", repr(ring._keys["k"]))

    def test_transport_policy(self):
        pol = TransportPolicy()
        ok = dict(protocol="TLSv1.3", cipher="TLS_AES_128_GCM_SHA256", peer_identity="spiffe://pk/pln01",
                  expected_identity="spiffe://pk/pln01", cert_not_after=T0 + 10, revoked=False, now=T0, mutual=True)
        pol.check_peer(**ok)
        for change, code in [({"protocol": "TLSv1.1"}, "E_AUTHN_FAILED"), ({"cipher": "RC4-MD5"}, "E_AUTHN_FAILED"),
                             ({"mutual": False}, "E_AUTHN_FAILED"), ({"peer_identity": "spiffe://pk/evil"}, "E_AUTHN_FAILED"),
                             ({"revoked": True}, "E_AUTHN_REVOKED"), ({"now": T0 + 11}, "E_AUTHN_EXPIRED")]:
            with self.subTest(change), self.assertRaises(PlaneError) as cm:
                pol.check_peer(**dict(ok, **change))
            self.assertEqual(cm.exception.code, code)


class IamTest(unittest.TestCase):
    def setUp(self):
        self.ring = KeyRing.ephemeral(T0)
        self.iss = Issuer(self.ring)
        self.auth = Authenticator(self.ring)

    def tok(self, cls="operator", **kw):
        kw.setdefault("tenant", "t1")
        kw.setdefault("now", T0)
        return self.iss.mint(sub="u", actor_class=cls, **kw)

    def test_default_deny_every_action_not_granted(self):
        p = self.auth.authenticate(self.tok("telemetry_collector"), T0)
        for action in POLICY["actions"]:
            if action in POLICY["actor_classes"]["telemetry_collector"]["capabilities"]:
                continue
            with self.subTest(action), self.assertRaises(PlaneError) as cm:
                self.auth.authorize(p, action, tenant="t1", site="dub", now=T0)
            self.assertEqual(cm.exception.code, "E_AUTHZ_DENIED")

    def test_capability_escalation_in_token_is_refused(self):
        t = self.tok("demand_reporter", source="r1", caps=["demand.submit", "limits.update"])
        with self.assertRaises(PlaneError) as cm:
            self.auth.authenticate(t, T0)
        self.assertEqual(cm.exception.code, "E_AUTHORITY_ESCALATION")

    def test_wildcard_tenant_only_for_any_scope_classes(self):
        with self.assertRaises(PlaneError) as cm:
            self.auth.authenticate(self.tok("operator", tenant="*"), T0)
        self.assertEqual(cm.exception.code, "E_AUTHORITY_ESCALATION")
        self.auth.authenticate(self.tok("emergency_admin", tenant="*", ticket="INC-1"), T0)

    def test_expired_future_and_overlong(self):
        with self.assertRaises(PlaneError) as cm:
            self.auth.authenticate(self.tok(lifetime=10), T0 + 11)
        self.assertEqual(cm.exception.code, "E_AUTHN_EXPIRED")
        with self.assertRaises(PlaneError):
            self.auth.authenticate(self.tok(iat=T0 + 60), T0)
        with self.assertRaises(PlaneError):
            self.auth.authenticate(self.tok(lifetime=99999), T0)

    def test_tampered_token(self):
        t = self.tok()
        parts = t.split(".")
        parts[2] = parts[2][:-2] + ("AA" if parts[2][-2:] != "AA" else "BB")
        with self.assertRaises(PlaneError) as cm:
            self.auth.authenticate(".".join(parts), T0)
        self.assertEqual(cm.exception.code, "E_AUTHN_FAILED")
        for junk in (None, "", "a.b.c", "v2.k1.x.y", "x" * 5000):
            with self.assertRaises(PlaneError):
                self.auth.authenticate(junk, T0)

    def test_single_use_control_tokens(self):
        p = self.auth.authenticate(self.tok("operator"), T0)
        self.auth.authorize(p, "control.freeze", tenant="t1", site="dub", now=T0)
        with self.assertRaises(PlaneError) as cm:
            self.auth.authorize(p, "control.freeze", tenant="t1", site="dub", now=T0 + 1)
        self.assertEqual(cm.exception.code, "E_AUTHN_REPLAY")
        # read actions are reusable
        self.auth.authorize(p, "status.read", tenant="t1", site="dub", now=T0)
        self.auth.authorize(p, "status.read", tenant="t1", site="dub", now=T0)

    def test_site_and_tenant_scope(self):
        p = self.auth.authenticate(self.tok("operator", sites=["dub"]), T0)
        for tenant, site in (("t2", "dub"), ("t1", "ams")):
            with self.assertRaises(PlaneError) as cm:
                self.auth.authorize(p, "status.read", tenant=tenant, site=site, now=T0)
            self.assertEqual(cm.exception.code, "E_AUTHZ_SCOPE")

    def test_break_glass_requires_ticket_and_reporter_requires_source(self):
        with self.assertRaises(PlaneError):
            self.auth.authenticate(self.tok("emergency_admin", tenant="*"), T0)
        with self.assertRaises(PlaneError):
            self.auth.authenticate(self.tok("demand_reporter"), T0)

    def test_replay_cache_is_bounded_and_fails_closed(self):
        self.auth.NONCE_CAPACITY = 3
        for _ in range(3):
            p = self.auth.authenticate(self.tok("operator"), T0)
            self.auth.authorize(p, "control.freeze", tenant="t1", site="dub", now=T0)
        p = self.auth.authenticate(self.tok("operator"), T0)
        with self.assertRaises(PlaneError) as cm:
            self.auth.authorize(p, "control.freeze", tenant="t1", site="dub", now=T0)
        self.assertEqual(cm.exception.code, "E_OVERLOADED")
        # nonces expire with their tokens, freeing the cache
        self.auth.authorize(p, "control.freeze", tenant="t1", site="dub", now=T0 + 301)


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.ring = KeyRing.ephemeral(T0)

    def test_defaults_valid_and_precedence(self):
        cfg = configuration.compose({"environment": {"revision": 2, "stale_after_s": 40},
                                     "site": {"stale_after_s": 50, "retry": {"max_attempts": 2}},
                                     "emergency-override": {"stale_after_s": 60}})
        configuration.validate(cfg)
        self.assertEqual(cfg["stale_after_s"], 60)
        self.assertEqual(cfg["retry"]["max_attempts"], 2)
        self.assertEqual(cfg["retry"]["base_ms"], configuration.DEFAULTS["retry"]["base_ms"])

    def test_list_replaced_not_merged(self):
        cfg = configuration.compose({"site": {"telemetry": {"label_allowlist": ["outcome"]}}})
        self.assertEqual(cfg["telemetry"]["label_allowlist"], ["outcome"])

    def test_invalid_candidates_never_activate(self):
        store = configuration.ConfigStore(self.ring, T0)
        before = store.active.checksum
        for bad in ({"site": {"revision": 2, "stale_after_s": -1}},
                    {"site": {"revision": 2, "unknown": 1}},
                    {"site": {"revision": 2, "retry": {"surprise": 1}}},
                    {"site": {"revision": 2, "stale_after_s": None}},
                    {"site": {"revision": 2, "stale_after_s": True}},
                    {"site": {"revision": 2, "x-api_key": "plaintext"}},
                    {"site": {"revision": 2, "retry": {"base_ms": 5000, "max_ms": 10}}},
                    {"bogus-layer": {"revision": 2}},
                    {"site": {"revision": 1}}):
            with self.subTest(bad), self.assertRaises(PlaneError):
                store.activate(bad, issuer="op", now=T0)
            self.assertEqual(store.active.checksum, before)

    def test_secret_references_allowed(self):
        cfg = configuration.compose({"site": {"x-sink_token": "secretref://vault/pln05/sink"}})
        configuration.validate(cfg)

    def test_activate_rollback_provenance_and_dry_run(self):
        store = configuration.ConfigStore(self.ring, T0)
        dry = store.dry_run({"site": {"revision": 2, "stale_after_s": 45}})
        self.assertEqual(dry["diff"][0]["field"], "revision")
        snap = store.activate({"site": {"revision": 2, "stale_after_s": 45}}, issuer="op", now=T0 + 1)
        self.assertEqual(snap.get("stale_after_s"), 45)
        self.assertEqual(snap.provenance[-1]["issuer"], "op")
        back = store.rollback(now=T0 + 2)
        self.assertEqual(back.revision, 1)
        with self.assertRaises(PlaneError) as cm:
            store.rollback(now=T0 + 3)
        self.assertEqual(cm.exception.code, "E_CONFIG_NO_ROLLBACK")

    def test_snapshot_is_immutable(self):
        store = configuration.ConfigStore(self.ring, T0)
        with self.assertRaises(TypeError):
            store.active.data["stale_after_s"] = 1  # type: ignore[index]

    def test_journal_restart_and_crash_safety(self):
        with tempfile.TemporaryDirectory() as d:
            store = configuration.ConfigStore(self.ring, T0, d)
            store.activate({"site": {"revision": 2, "stale_after_s": 45}}, issuer="op", now=T0)

            class Crash(Exception):
                pass

            def hook(stage):
                if stage == "after-temp-write":
                    raise Crash
            with self.assertRaises(Crash):
                store.activate({"site": {"revision": 3, "stale_after_s": 50}}, issuer="op", now=T0, crash_hook=hook)
            again = configuration.ConfigStore(self.ring, T0, d)
            self.assertEqual(again.active.revision, 2)  # torn write never became active
            self.assertFalse((pathlib.Path(d) / "active.json.tmp").exists())
            # tamper -> refuse to start with it
            p = pathlib.Path(d) / "active.json"
            p.write_bytes(p.read_bytes().replace(b'"stale_after_s":45', b'"stale_after_s":46'))
            with self.assertRaises(PlaneError) as cm:
                configuration.ConfigStore(self.ring, T0, d)
            self.assertEqual(cm.exception.code, "E_STATE_CORRUPT")


class AuditTest(unittest.TestCase):
    def setUp(self):
        self.ring = KeyRing.ephemeral(T0)

    def _log(self, n=5, **kw):
        log = AuditLog(self.ring, **kw)
        for i in range(n):
            log.append(actor="a", actor_class="operator", tenant="t1", site="dub", action="control.freeze",
                       result="applied", reason_code="R_FROZEN", now=T0 + i)
        return log

    def test_chain_and_anchor_verify(self):
        log = self._log()
        self.assertTrue(AuditLog.verify(log.records, log.anchor(T0), self.ring, T0)["ok"])

    def test_detects_edit_gap_reorder_truncation(self):
        log = self._log()
        anchor = log.anchor(T0)
        edited = [dict(r) for r in log.records]
        edited[2]["result"] = "denied"
        self.assertFalse(AuditLog.verify(edited, anchor, self.ring, T0)["ok"])
        self.assertFalse(AuditLog.verify(list(log.records)[:2] + list(log.records)[3:], anchor, self.ring, T0)["ok"])
        swapped = list(log.records)
        swapped[1], swapped[2] = swapped[2], swapped[1]
        self.assertFalse(AuditLog.verify(swapped, anchor, self.ring, T0)["ok"])
        res = AuditLog.verify(list(log.records)[:4], anchor, self.ring, T0)
        self.assertFalse(res["ok"])
        self.assertIn("truncated", res["problems"][0])

    def test_sink_outage_buffers_then_refuses(self):
        log = AuditLog(self.ring, buffer_capacity=2)
        log.set_sink(False)
        for _ in range(2):
            log.append(actor="a", actor_class="c", tenant="t", site="s", action="x", result="r",
                       reason_code="R", now=T0)
        with self.assertRaises(PlaneError) as cm:
            log.append(actor="a", actor_class="c", tenant="t", site="s", action="x", result="r",
                       reason_code="R", now=T0)
        self.assertEqual(cm.exception.code, "E_AUDIT_UNAVAILABLE")
        log.set_sink(True)
        self.assertEqual(len(log.records), 2)
        self.assertTrue(AuditLog.verify(log.records, log.anchor(T0), self.ring, T0)["ok"])

    def test_bounded_window_still_verifies(self):
        log = AuditLog(self.ring, retain=10)
        for i in range(25):
            log.append(actor="a", actor_class="c", tenant="t", site="s", action="x", result="r",
                       reason_code="R", now=T0)
        self.assertEqual(len(log.records), 10)
        self.assertTrue(AuditLog.verify(log.records, log.anchor(T0), self.ring, T0, log.window_start)["ok"])
        self.assertFalse(AuditLog.verify(log.records, log.anchor(T0), self.ring, T0)["ok"])

    def test_file_sink(self):
        with tempfile.TemporaryDirectory() as d:
            log = AuditLog(self.ring, pathlib.Path(d) / "a.jsonl")
            log.append(actor="a", actor_class="c", tenant="t", site="s", action="x", result="r",
                       reason_code="R", now=T0)
            lines = (pathlib.Path(d) / "a.jsonl").read_text().splitlines()
            self.assertEqual(json.loads(lines[0])["seq"], 1)


class StateTest(unittest.TestCase):
    def setUp(self):
        self.ring = KeyRing.ephemeral(T0)
        self.tmp = tempfile.TemporaryDirectory()
        self.store = StateStore(self.tmp.name, self.ring)
        self.doc = {"current": 3, "below": 1, "suppressed": 0,
                    "limits": {"floor": 0, "ceiling": 8, "scale_up_at": 0.75, "scale_down_at": 0.25,
                               "grace_samples": 3}, "controls": {}, "sources": {}, "seen": [], "epoch": 2}

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip_and_scope_isolation(self):
        self.store.save("t1/dub/w1", self.doc, T0)
        self.assertEqual(self.store.load("t1/dub/w1", T0)["current"], 3)
        self.assertIsNone(self.store.load("t2/dub/w1", T0))
        with self.assertRaises(PlaneError):
            self.store.save("../../etc", self.doc, T0)

    def test_crash_mid_write_keeps_previous(self):
        self.store.save("t1/dub/w1", self.doc, T0)

        class Crash(Exception):
            pass
        for stage in ("mid-write", "before-rename"):
            def hook(s, stage=stage):
                if s == stage:
                    raise Crash
            with self.assertRaises(Crash):
                self.store.save("t1/dub/w1", dict(self.doc, current=7), T0, crash_hook=hook)
            self.assertEqual(self.store.load("t1/dub/w1", T0)["current"], 3)

    def test_corruption_and_future_version_refused(self):
        self.store.save("t1/dub/w1", self.doc, T0)
        path = next(pathlib.Path(self.tmp.name).glob("*.state.json"))
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b'"current":3', b'"current":8'))
        with self.assertRaises(PlaneError) as cm:
            self.store.load("t1/dub/w1", T0)
        self.assertEqual(cm.exception.code, "E_STATE_CORRUPT")
        path.write_bytes(raw[: len(raw) // 2])
        with self.assertRaises(PlaneError):
            self.store.load("t1/dub/w1", T0)
        with self.assertRaises(PlaneError) as cm:
            migrate({"schema": "PLN05_STATE/9"})
        self.assertEqual(cm.exception.code, "E_STATE_VERSION")

    def test_v1_migration(self):
        out = migrate({"schema": "PLN05_STATE/1", "current": 2, "limits": self.doc["limits"]})
        self.assertEqual(out["schema"], "PLN05_STATE/2")
        self.assertEqual(out["epoch"], 0)

    def test_lease_epochs_and_fencing(self):
        svc = LeaseService()
        a = svc.acquire("s", "a", T0, 10)
        with self.assertRaises(PlaneError) as cm:
            svc.acquire("s", "b", T0 + 1, 10)
        self.assertEqual(cm.exception.code, "E_NOT_LEADER")
        b = svc.acquire("s", "b", T0 + 11, 10)
        self.assertGreater(b.epoch, a.epoch)
        with self.assertRaises(PlaneError):
            svc.renew(a, T0 + 12, 10)
        sink = FencedSink()
        base = {"tenant": "t", "site": "s", "workload": "w"}
        sink.apply(dict(base, decision_id="d2", fencing_token=b.epoch))
        with self.assertRaises(PlaneError) as cm:
            sink.apply(dict(base, decision_id="d1", fencing_token=a.epoch))
        self.assertEqual(cm.exception.code, "E_FENCED")
        self.assertFalse(sink.apply(dict(base, decision_id="d2", fencing_token=b.epoch)))


class ReliabilityTest(unittest.TestCase):
    def _policy(self, **kw):
        args = dict(max_attempts=4, base_ms=10, max_ms=100, deadline_ms=1000, budget=RetryBudget(1.0),
                    rng=random.Random(1))
        args.update(kw)
        return RetryPolicy(**args)

    def test_retry_bounds(self):
        clock = Clock(0)
        calls = []

        def op():
            calls.append(1)
            raise PlaneError("E_CIRCUIT_OPEN", "x")
        with self.assertRaises(PlaneError):
            self._policy(budget=RetryBudget(10.0)).run(op, idempotent=True, clock=clock, sleep=clock.advance)
        self.assertEqual(len(calls), 4)  # max_attempts is a hard bound even with budget to spare
        delays = list(__import__("itertools").islice(self._policy().delays(), 50))
        self.assertTrue(all(10 <= d <= 100 for d in delays))

    def test_no_retry_for_non_idempotent_or_non_retryable(self):
        clock = Clock(0)
        for idem, code in ((False, "E_CIRCUIT_OPEN"), (True, "E_SCHEMA_FIELD")):
            calls = []

            def op(code=code):
                calls.append(1)
                raise PlaneError(code, "x")
            with self.assertRaises(PlaneError):
                self._policy().run(op, idempotent=idem, clock=clock, sleep=clock.advance)
            self.assertEqual(len(calls), 1)

    def test_deadline_budget_stale_and_cancel(self):
        clock = Clock(0)

        def fail():
            raise PlaneError("E_OVERLOADED", "x")
        with self.assertRaises(PlaneError) as cm:
            self._policy(deadline_ms=5).run(fail, idempotent=True, clock=clock, sleep=clock.advance)
        self.assertEqual(cm.exception.code, "E_DEADLINE")
        pol = self._policy(budget=RetryBudget(0.0))
        pol.budget.retries = 1
        with self.assertRaises(PlaneError) as cm:
            pol.run(fail, idempotent=True, clock=clock, sleep=clock.advance)
        self.assertEqual(cm.exception.code, "E_RETRY_BUDGET")
        with self.assertRaises(PlaneError) as cm:
            self._policy().run(fail, idempotent=True, clock=clock, sleep=clock.advance, is_stale=lambda: True)
        self.assertEqual(cm.exception.code, "E_STALE_INPUT")
        with self.assertRaises(PlaneError) as cm:
            self._policy().run(fail, idempotent=True, clock=clock, sleep=clock.advance, cancelled=lambda: True)
        self.assertEqual(cm.exception.code, "E_CANCELLED")

    def test_admission_priority_reserve_and_shedding(self):
        adm = AdmissionController(4, 1)
        for i in range(3):
            adm.offer("telemetry", i)
        with self.assertRaises(PlaneError):
            adm.offer("telemetry", 99)
        adm.offer("demand", "d")  # sheds a telemetry item
        self.assertEqual(adm.shed["telemetry"], 1)
        adm.offer("control", "c")  # reserve slot
        self.assertEqual(adm.take(), "c")
        self.assertEqual(adm.take(), "d")
        self.assertLessEqual(len(adm), 4)

    def test_breaker_state_machine(self):
        br = CircuitBreaker("dep", 2, 10, 1)

        def fail():
            raise PlaneError("E_OVERLOADED", "x")
        for _ in range(2):
            with self.assertRaises(PlaneError):
                br.call(fail, T0)
        self.assertEqual(br.state, "open")
        with self.assertRaises(PlaneError) as cm:
            br.call(lambda: 1, T0 + 1)
        self.assertEqual(cm.exception.code, "E_CIRCUIT_OPEN")
        self.assertEqual(br.call(lambda: 1, T0 + 13), 1)  # after jittered cooldown (<= 12s)
        self.assertEqual(br.state, "closed")
        # caller errors do not open the breaker
        br2 = CircuitBreaker("dep2", 1, 10, 1)
        with self.assertRaises(PlaneError):
            br2.call(lambda: (_ for _ in ()).throw(PlaneError("E_SCHEMA_FIELD", "x")), T0)
        self.assertEqual(br2.state, "closed")

    def test_breaker_cooldowns_desynchronise(self):
        cds = set()
        for i in range(10):
            br = CircuitBreaker(f"replica-{i}", 1, 10, 1)
            br.record(False, T0)
            cds.add(round(br._cooldown, 6))
        self.assertGreater(len(cds), 5)


class TelemetryTest(unittest.TestCase):
    def test_cardinality_cap_and_label_allowlist(self):
        m = Metrics(["outcome"], max_series=10)
        for i in range(100):
            m.inc("decisions", {"outcome": f"o{i}", "tenant": f"t{i}"})
        self.assertEqual(m.series(), 10)
        self.assertEqual(m.dropped_series, 90)
        self.assertGreater(m.dropped_labels, 0)
        self.assertNotIn("tenant", m.exposition())

    def test_histogram(self):
        m = Metrics([], 10)
        for v in (0.01, 3, 500):
            m.observe("lat", v)
        h = next(iter(m.hist.values()))
        self.assertEqual(h[-1], 3)

    def test_redaction(self):
        ring = KeyRing.ephemeral(T0)
        tok = Issuer(ring).mint(sub="u", actor_class="operator", tenant="t1", now=T0)
        out = redact({"token": "abc", "note": f"used {tok}", "auth": "Bearer abcdefghijk",
                      "nested": {"private_key": "x", "pem": "-----BEGIN PRIVATE KEY-----"}})
        text = json.dumps(out)
        self.assertNotIn(tok, text)
        self.assertNotIn("abcdefghijk", text)
        self.assertNotIn("BEGIN PRIVATE", text)
        self.assertEqual(out["token"], "<redacted>")

    def test_logger_never_raises(self):
        class Bad:
            def write(self, s):
                raise OSError("disk full")
        log = Logger(stream=Bad())
        log.log("INFO", "x", a=1)
        self.assertEqual(log.errors, 1)

    def test_traceparent(self):
        tp = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
        self.assertEqual(parse_traceparent(tp)[0], "4bf92f3577b34da6a3ce929d0e0e4736")
        for bad in ("", "00-" + "0" * 32 + "-00f067aa0ba902b7-01", None, "zz"):
            self.assertIsNone(parse_traceparent(bad))
        tr = Tracer(0.0)
        tid, sid = tr.start(tp)
        self.assertEqual(tid, "4bf92f3577b34da6a3ce929d0e0e4736")
        tr.span(tid, sid, "x", 1.0)
        self.assertEqual(len(tr.spans), 0)  # unsampled
        tr.span(tid, sid, "x", 1.0, error=True)
        self.assertEqual(len(tr.spans), 1)  # errors always kept


class SupplyChainTest(unittest.TestCase):
    def test_verify_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "a.zip"
            p.write_bytes(b"payload")
            digest = supplychain.sha256_file(p)
            supplychain.verify_artifact(p, expected_sha256=digest, name="pln05-elasticity-plane", version="4.2.0")
            for kw in ({"expected_sha256": "0" * 64, "version": "4.2.0"},
                       {"expected_sha256": digest, "version": "9.9.9"}):
                with self.assertRaises(PlaneError) as cm:
                    supplychain.verify_artifact(p, name="pln05-elasticity-plane", **kw)
                self.assertEqual(cm.exception.code, "E_ARTIFACT_UNTRUSTED")

    def test_sbom_and_provenance_shape(self):
        s = supplychain.sbom("pln05-elasticity-plane", "4.2.0", {"a": "b"}, "2026-01-01T00:00:00Z")
        self.assertEqual(s["bomFormat"], "CycloneDX")
        self.assertTrue(any(c["name"] == "pk_core" for c in s["components"]))
        prov = supplychain.provenance({"x": "0" * 64}, source_revision="abc", builder="b",
                                      build_time="t", params={})
        self.assertEqual(prov["subject"][0]["digest"]["sha256"], "0" * 64)


if __name__ == "__main__":
    unittest.main()
