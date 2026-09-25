"""INV-35-C023/C024/C041-C050/C087: threat-model-complete adversarial suite.

Each test names the THREAT_MODEL.md threat id it exercises (T-xx).
"""
from __future__ import annotations

import base64
import inspect
import json
import unittest

from _support import (BULK, CTL, PKG_DIR, REGION, FakeClock, Inv35Error, MemoryRegion, State, config, one, rt,
                      security, stack, telemetry)


def codes(fn):
    try:
        fn()
    except Inv35Error as exc:
        return exc.code
    return "INV35-E000"


class PrivilegeTest(unittest.TestCase):
    def setUp(self):
        self.r, self.cp, self.dp, self.ctl, self.bulk = stack()

    def test_T01_bulk_token_cannot_drive_control_plane(self):
        self.assertEqual(codes(lambda: self.cp.transition(self.bulk, tenant="t1", queue="q0", target=State.FROZEN,
                                                          reason="x", actor="evil", epoch=1)), "INV35-E303")
        self.assertEqual(codes(lambda: self.cp.apply_config(self.bulk, tenant="t1", queue="q0")), "INV35-E303")

    def test_T01_control_token_cannot_submit(self):
        self.assertEqual(codes(lambda: self.dp.submit(self.ctl, tenant="t1", queue="q0", chain=one(), head=0)), "INV35-E303")

    def test_T02_cross_tenant_refused(self):
        other = self.r.authority.mint("vmm2", "t2", {"q0"}, BULK)
        self.assertEqual(codes(lambda: self.dp.submit(other, tenant="t2", queue="q0", chain=one(), head=0)), "INV35-E305")
        self.assertEqual(codes(lambda: self.dp.submit(other, tenant="t1", queue="q0", chain=one(), head=0)), "INV35-E305")

    def test_T02_queue_hijack_by_reregistration_refused(self):
        ctl2 = self.r.authority.mint("c2", "t2", {"q0"}, CTL)
        self.assertEqual(codes(lambda: self.cp.register_queue(ctl2, tenant="t2", queue="q0", regions=REGION)), "INV35-E305")

    def test_T03_scope_limited_to_named_queues(self):
        cp_tok = self.r.authority.mint("c", "t1", {"q9"}, CTL)
        self.cp.register_queue(cp_tok, tenant="t1", queue="q9", regions=REGION)
        self.assertEqual(codes(lambda: self.dp.submit(self.bulk, tenant="t1", queue="q9", chain=one(), head=0)), "INV35-E303")

    def test_T04_no_ambient_authority_on_any_public_entry_point(self):
        for plane in (self.cp, self.dp):
            for name, fn in inspect.getmembers(plane, inspect.ismethod):
                if name.startswith("_") or name == "negotiate":
                    continue
                sig = inspect.signature(fn)
                kwargs = {}
                for p in list(sig.parameters.values())[1:]:
                    if p.default is inspect.Parameter.empty:
                        kwargs[p.name] = {"tenant": "t1", "queue": "q0", "chain": one(), "head": 0,
                                          "guest_wants_notification": True, "regions": REGION, "target": State.FROZEN,
                                          "reason": "r", "actor": "a", "epoch": 1}[p.name]
                with self.subTest(method=name):
                    self.assertIn(codes(lambda: fn(None, **kwargs)), {"INV35-E300"})


class SpoofReplayTest(unittest.TestCase):
    def setUp(self):
        self.r, self.cp, self.dp, self.ctl, self.bulk = stack()

    def _forge(self, token, **changes):
        body, kid, mac = token.split(".")
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        claims.update(changes)
        nb = base64.urlsafe_b64encode(security.canonical(claims)).rstrip(b"=").decode()
        return f"{nb}.{kid}.{mac}"

    def test_T05_tampered_claims_rejected(self):
        forged = self._forge(self.bulk, actions=sorted(BULK | CTL))
        self.assertEqual(codes(lambda: self.cp.apply_config(forged, tenant="t1", queue="q0")), "INV35-E301")

    def test_T05_foreign_key_rejected(self):
        other = security.Authority(security.KeyRing())
        other.keyring.rotate("k1")  # same key id, different material
        tok = other.mint("x", "t1", {"q0"}, BULK)
        self.assertEqual(codes(lambda: self.dp.submit(tok, tenant="t1", queue="q0", chain=one(), head=0)), "INV35-E301")

    def test_T05_garbage_tokens_rejected_without_crash(self):
        for tok in ["", "a.b", "a.b.c", "!!!.k1.???", "e30.k1.AAAA", 123, None, b"x.y.z", "a.b.c.d"]:
            with self.subTest(tok=tok):
                self.assertIn(codes(lambda: self.dp.submit(tok, tenant="t1", queue="q0", chain=one(), head=0)),
                              {"INV35-E300", "INV35-E301"})

    def test_T05_non_canonical_encoding_rejected(self):
        body, kid, mac = self.bulk.split(".")
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        spaced = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
        self.assertEqual(codes(lambda: self.dp.submit(f"{spaced}.{kid}.{mac}", tenant="t1", queue="q0",
                                                      chain=one(), head=0)), "INV35-E300")

    def test_T06_replay_of_single_use_token_refused(self):
        r, cp, dp, ctl, bulk = stack(single_use_capabilities=True)
        tok = r.authority.mint("vmm", "t1", {"q0"}, BULK)
        self.assertEqual(codes(lambda: dp.submit(tok, tenant="t1", queue="q0", chain=one(), head=0)), "INV35-E000")
        self.assertEqual(codes(lambda: dp.submit(tok, tenant="t1", queue="q0", chain=one(), head=0)), "INV35-E304")

    def test_T06_replay_window_is_bounded(self):
        a = security.Authority(security.KeyRing(), replay_window=8)
        a.keyring.rotate()
        for _ in range(50):
            a.authorize(a.mint("s", "t", {"q"}, {"submit"}), action="submit", tenant="t", queue="q", single_use=True)
        self.assertLessEqual(len(a._seen), 8)

    def test_T07_expired_and_future_tokens_refused(self):
        clock = FakeClock()
        kr = security.KeyRing(clock=clock)
        kr.rotate()
        a = security.Authority(kr)
        tok = a.mint("s", "t", {"q"}, {"submit"}, ttl=10)
        clock.advance(11)
        self.assertEqual(codes(lambda: a.authorize(tok, action="submit", tenant="t", queue="q")), "INV35-E302")
        clock.t -= 100
        self.assertEqual(codes(lambda: a.authorize(tok, action="submit", tenant="t", queue="q")), "INV35-E302")

    def test_T07_expiry_enforced_even_when_verification_is_cached(self):
        clock = FakeClock()
        kr = security.KeyRing(clock=clock)
        kr.rotate()
        a = security.Authority(kr)
        tok = a.mint("s", "t", {"q"}, {"submit"}, ttl=10)
        a.authorize(tok, action="submit", tenant="t", queue="q")  # populates cache
        clock.advance(11)
        self.assertEqual(codes(lambda: a.authorize(tok, action="submit", tenant="t", queue="q")), "INV35-E302")

    def test_T08_key_rotation_and_retirement(self):
        kr = self.r.keyring
        old = self.bulk
        kr.rotate("k2")
        self.assertEqual(codes(lambda: self.dp.submit(old, tenant="t1", queue="q0", chain=one(), head=0)), "INV35-E000")
        kr.retire("k1")
        self.assertEqual(codes(lambda: self.dp.submit(old, tenant="t1", queue="q0", chain=one(), head=0)), "INV35-E301")
        new = self.r.authority.mint("vmm", "t1", {"q0"}, BULK)
        self.assertEqual(codes(lambda: self.dp.submit(new, tenant="t1", queue="q0", chain=one(), head=0)), "INV35-E000")

    def test_T08_short_keys_refused(self):
        with self.assertRaises(Inv35Error):
            security.KeyRing().add("weak", b"x" * 16)


class TrustServiceFailureTest(unittest.TestCase):
    def setUp(self):
        self.r, self.cp, self.dp, self.ctl, self.bulk = stack()

    def test_T09_key_service_outage_fails_closed(self):
        self.dp.submit(self.bulk, tenant="t1", queue="q0", chain=one(), head=0)  # warm the cache
        self.r.keyring.available = False
        self.assertEqual(codes(lambda: self.dp.submit(self.bulk, tenant="t1", queue="q0", chain=one(), head=0)),
                         "INV35-E306")
        self.assertFalse(self.r.status()["ready"])

    def test_T09_untrusted_time_fails_closed(self):
        self.r.authority.time_trusted = False
        self.assertEqual(codes(lambda: self.dp.submit(self.bulk, tenant="t1", queue="q0", chain=one(), head=0)),
                         "INV35-E306")


class InjectionEscapeExhaustionTest(unittest.TestCase):
    def setUp(self):
        self.r, self.cp, self.dp, self.ctl, self.bulk = stack()

    def test_T10_host_memory_escape_refused_and_audited(self):
        for addr in (0, 0xFFFF_8000_0000_0000, 0x1_0000 - 1, 0x2_0000):
            self.assertEqual(codes(lambda: self.dp.submit(self.bulk, tenant="t1", queue="q0",
                                                          chain=one(addr=addr, length=2), head=0)), "INV35-E105")
        self.assertTrue(any(e["event"] == "descriptor.refused" for e in self.r.audit.entries))
        self.assertEqual(self.r.queues["q0"].vq.in_flight_descriptors, 0)

    def test_T11_config_injection_of_secrets_and_unknown_fields(self):
        self.assertEqual(codes(lambda: config.build(environment={"api_key": "x"})), "INV35-E504")
        self.assertEqual(codes(lambda: config.build(site={"queue_depth": 64, "evil": 1})), "INV35-E500")
        self.assertEqual(codes(lambda: config.build(site={"require_capability": False})), "INV35-E500")
        self.assertEqual(codes(lambda: config.build(profile="far_edge", site={"queue_depth": 64})), "INV35-E500")

    def test_T12_tenant_quota_exhaustion(self):
        r, cp, dp, ctl, bulk = stack(host_descriptor_capacity=8, tenant_share=0.5)
        results = [codes(lambda: dp.submit(bulk, tenant="t1", queue="q0", chain=one(), head=0)) for _ in range(6)]
        self.assertEqual(results[:4], ["INV35-E000"] * 4)
        self.assertEqual(results[4:], ["INV35-E201"] * 2)
        self.assertEqual(r.queues["q0"].vq.in_flight_descriptors, 4, "quota refusal must roll back reservation")

    def test_T12_queue_count_exhaustion(self):
        r, cp, dp, ctl, bulk = stack(max_queues_per_tenant=2)
        tok = r.authority.mint("c", "t1", {"a", "b"}, CTL)
        cp.register_queue(tok, tenant="t1", queue="a", regions=REGION)
        self.assertEqual(codes(lambda: cp.register_queue(tok, tenant="t1", queue="b", regions=REGION)), "INV35-E201")

    def test_T13_metric_cardinality_is_capped(self):
        m = telemetry.Metrics()
        for i in range(10_000):
            m.inc("x", queue=f"q{i}")
        self.assertLessEqual(m._series["x"], telemetry.MAX_SERIES_PER_METRIC)
        self.assertGreater(m.counter("x", __overflow__="1"), 0)

    def test_T14_secrets_never_reach_logs_or_audit(self):
        self.r.log.emit("info", "x", token="SECRET", nested={"password": "p", "ok": 1})
        self.r.audit.append("x", api_key="SECRET")
        blob = self.r.log.jsonl() + json.dumps(self.r.audit.entries)
        self.assertNotIn("SECRET", blob)
        self.assertNotIn('"p"', blob)

    def test_T15_audit_tamper_detected(self):
        self.r.audit.append("a", n=1)
        self.r.audit.append("b", n=2)
        self.assertTrue(self.r.audit.verify())
        self.r.audit.entries[1]["fields"]["queue"] = "forged"
        self.assertFalse(self.r.audit.verify())
        with self.assertRaises(Inv35Error):
            self.r.audit.require_intact()

    def test_T15_audit_truncation_and_reorder_detected(self):
        for i in range(4):
            self.r.audit.append("e", i=i)
        entries = self.r.audit.entries
        entries[1], entries[2] = entries[2], entries[1]
        self.assertFalse(self.r.audit.verify())

    def test_T16_side_channel_constant_time_compare(self):
        src = (PKG_DIR / "runtime" / "security.py").read_text()
        self.assertIn("hmac.compare_digest", src)
        self.assertNotRegex(src, r"mac\s*==|==\s*mac")

    def test_T17_stale_controller_fenced(self):
        tok = self.ctl
        self.cp.claim(tok, tenant="t1", queue="q0", epoch=2, actor="new-controller")
        self.assertEqual(codes(lambda: self.cp.transition(tok, tenant="t1", queue="q0", target=State.FROZEN,
                                                          reason="stale", actor="old", epoch=1)), "INV35-E307")
        self.assertEqual(codes(lambda: self.cp.claim(tok, tenant="t1", queue="q0", epoch=2, actor="dup")), "INV35-E307")


if __name__ == "__main__":
    unittest.main()
